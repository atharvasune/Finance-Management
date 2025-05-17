import json
from aws_lambda_typing import context as context_, events
from google import genai
from pydantic import BaseModel, Field
from typing import Literal

gemini_client = genai.Client()


class GeminiResponse(BaseModel):
    transaction_message: bool = Field(description="Whether the current message denotes a transaction that has been completed")
    transaction_type: Literal["Credit", "Debit"] = Field(description="If message is a transaction message denotes whether its a debit transaction or a credit transaction")
    transaction_amount: float = Field(description="If a transaction message, then represents the amount of transaction")
    transaction_date: str = Field(description="Represents the date of the transaction in a DD/MM/YYYY format")


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
            'response_schema': GeminiResponse,
            'system_instruction': "You are an expert financial message parser who can accurately detect whether a message represents a transaction message. A transaction message is one which represents a transaction that has been completed. If it denotes a future transaction then its not a transaction message."
        }
    )

    return response.parsed


def handle_event(event: events.APIGatewayProxyEventV2, context: context_.Context):
    message = event["body"]["message"]
    return {
        'statusCode': 200,
        'body': parseMessage(message)
    }