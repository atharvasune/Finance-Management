import json

def lambda_handler(event, context):
    return {
        'statusCode': 200,
        'body': "Hello from Financial Manager Process Message Input Lambda"
    }