import json
import os
from aws_lambda_typing import context as context_, events
from google import genai

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


def handle_event(event: events.APIGatewayProxyEventV2, context: context_.Context):
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
        return {
            'statusCode': 200,
            'body': response
        }
    else:
        return {
            'statusCode': 200,
            'body': json.dumps({"message", "not a transaction message"})
        }