import json
import os
from aws_lambda_typing import context as context_, events
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from datetime import datetime


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

        header_row = [
            ["Date", "Type", "Amount", "Receiver", "Sent From", "Is Transaction?"]
        ]
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=f"{month_name}!A1",
            valueInputOption="USER_ENTERED",
            body={"values": header_row}
        ).execute()

def get_creds():
    creds_data = json.loads(os.environ['SHEETS_CREDS'])
    creds = Credentials.from_authorized_user_info(creds_data)
    
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    
    return creds

def handle_event(event: events.APIGatewayProxyEventV2, context: context_.Context):
    try:
        if event.get("body", None) is not None:
            body = json.loads(event["body"])
        elif event.get("body") is not None:
            body = event["body"]
        else:
            body = None
        if body is None:
            return {
                'statusCode': 400,
                'body': json.dumps({"message": "no body provided"})
            }
        
        if (body.get("transaction_message", False)) :
            creds = get_creds()
            service = build("sheets", "v4", credentials=creds)
            spreadsheet_id = os.environ["SPREADSHEET_ID"]

            # 4. Determine month name from date
            txn_date = body.get("transaction_date", "")
            month_name = "Unknown"
            if txn_date:
                try:
                    month_name = datetime.strptime(txn_date, "%d/%m/%Y").strftime("%B")
                except Exception:
                    pass  # fallback to default

            # 5. Ensure sheet and append data
            ensure_month_sheet_exists(service, spreadsheet_id, month_name)
            append_transaction(service, spreadsheet_id, month_name, body)

            return {
                'statusCode': 200,
                'body': json.dumps({
                    "message": "Transaction added to sheet"
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