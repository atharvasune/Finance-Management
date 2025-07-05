import json
import os
from aws_lambda_typing import context as context_, events
from google import genai
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from datetime import datetime

gemini_client = genai.Client(api_key = os.getenv("GEMINI_API_KEY"))

def parseMessage(message: str):
    response = gemini_client.models.generate_content(
        model="gemini-1.5-flash",
        contents = {
            "role": "user",
            "parts": [
                {
                    "text": message
                }
            ]
        },
        config={
            'response_mime_type': 'application/json',
            'response_schema': {
                "type": "object",
                "properties": {
                    "transaction_message": {
                        "type": "boolean",
                        "description": "Whether the current message denotes a transaction that has been completed",
                    },
                    "transaction_type": {
                        "type": "string",
                        "enum": ["credit", "debit"],
                        "description": "If message is a transaction message denotes whether its a debit transaction or a credit transaction",
                    },
                    "transaction_amount": {
                        "type": "number",
                        "description": "If a transaction message, then represents the amount of transaction"
                    },
                    "transaction_date": {
                        "type": "string",
                        "description": "Represents the date of the transaction in a DD/MM/YYYY format"
                    },
                    "receiver": {
                        "type": "string",
                        "description": "If available then receiver of the transaction else an empty string"
                    },
                    "sent_from": {
                        "type": "string",
                        "description": "If available a description of which account / source this transaction has been done else an empty string"
                    }
                }
            },
            'system_instruction': "You are an expert financial message parser who can accurately detect whether a message represents a transaction message. A transaction message is one which represents a transaction that has been completed. If it denotes a future transaction then its not a transaction message."
        }
    )

    return response.parsed


def append_transaction(service, spreadsheet_id, month_name, data: dict):
    row = [
        data.get("transaction_date", ""),
        "Credit" if data.get("transaction_type") == "credit" else "Debit",
        data.get("transaction_amount", ""),
        data.get("receiver", ""),
        data.get("sent_from", ""),
        "Yes" if data.get("transaction_message") else "No"
    ]
    
    service.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range=f"{month_name}!A1",
        valueInputOption="USER_ENTERED",
        body={"values": [row]}
    ).execute()

def ensure_month_sheet_exists(service, spreadsheet_id, month_name):
    sheets_metadata = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    sheet_titles = [sheet['properties']['title'] for sheet in sheets_metadata['sheets']]
    
    if month_name not in sheet_titles:
        add_sheet_body = {
            "requests": [
                {
                    "addSheet": {
                        "properties": {
                            "title": month_name
                        }
                    }
                }
            ]
        }
        service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=add_sheet_body).execute()

def get_creds():
    creds_data = json.loads(os.environ['SHEETS_CREDS'])
    creds = Credentials.from_authorized_user_info(creds_data)
    
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    
    return creds

def handle_event(event: events.APIGatewayProxyEventV2, context: context_.Context):
    try:
        if event.get("body", None) is not None:
            message = json.loads(event["body"]).get("message", None)
        elif event.get("message") is not None:
            message = event["message"]
        else:
            message = None
        if message is None:
            return {
                'statusCode': 400,
                'body': json.dumps({"message": "no message provided"})
            }
        
        response = parseMessage(message)
        if (response.get("transaction_message", False)) :
            creds = get_creds()
            service = build("sheets", "v4", credentials=creds)
            spreadsheet_id = os.environ["SPREADSHEET_ID"]

            # 4. Determine month name from date
            txn_date = response.get("transaction_date", "")
            month_name = "Unknown"
            if txn_date:
                try:
                    month_name = datetime.strptime(txn_date, "%d/%m/%Y").strftime("%B")
                except Exception:
                    pass  # fallback to default

            # 5. Ensure sheet and append data
            ensure_month_sheet_exists(service, spreadsheet_id, month_name)
            append_transaction(service, spreadsheet_id, month_name, response)

            return {
                'statusCode': 200,
                'body': json.dumps({
                    "message": "Transaction added to sheet",
                    "parsed": response
                })
            }
        else:
            return {
                'statusCode': 200,
                'body': json.dumps({"message", "not a transaction message"})
            }
    except Exception as e :
        return {
            'statusCode': 500,
            'body': json.dumps({"error": str(e)})
        }