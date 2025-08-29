import os
import requests
from dotenv import load_dotenv

load_dotenv()

tenantId=os.environ['tenantId']
clientId=os.environ['clientId']
clientkey=os.environ['clientkey']


def get_ms_token():
    url = f'https://login.microsoftonline.com/{tenantId}/oauth2/v2.0/token'
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    body = {
        'grant_type': 'client_credentials',
        'client_id': clientId,
        'client_secret': clientkey,
        'scope': 'https://graph.microsoft.com/.default'
    }
    response = requests.post(url, headers=headers, data=body)
    response.raise_for_status() 
    return response.json()['access_token']

def send_ms_email(token, from_email, to_email, subject, html_content):
    url = f'https://graph.microsoft.com/v1.0/users/{from_email}/sendMail'
    headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
    }
    body = {
            "message": {
                "subject": subject,
                "body": {
                    "contentType": "HTML",
                    "content": html_content
                },
                "toRecipients": [
                    {
                        "emailAddress": {
                            "address": to_email
                        }
                    }
                ]
            },
            "saveToSentItems": "true"
    }
    response = requests.post(url, headers=headers, json=body)
    return response.status_code, response.text