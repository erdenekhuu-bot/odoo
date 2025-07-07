from odoo import models, fields, api
import logging
import os
from dotenv import load_dotenv
import requests

load_dotenv()

_logger = logging.getLogger(__name__)

class Graph(models.Model):
    _inherit='mailing.mailing'

    tenantId=os.environ['tenantId']
    clientId=os.environ['clientId']
    clientSecret=os.environ['clientSecret']
    sender_email = 'no-reply@gmobile.mn'

    recipient_email = 'erdenekhuu.e@gmobile.mn'
    subject = 'Test email'
    body_content = 'Hello, this is a test email sent using Microsoft Graph API.'

    html_body = """
    <h2>Hello!</h2>
    <p>HYDRA</p>
    """

    def action_test(self):
        token=self._get_token()
        _logger.info(f"**************** {token} ********************")
        return self._send_email(token)

    def _get_token(self):
        url = f'https://login.microsoftonline.com/{self.tenantId}/oauth2/v2.0/token'
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        body = {
            'grant_type': 'client_credentials',
            'client_id': self.clientId,
            'client_secret': self.clientSecret,
            'scope': 'https://graph.microsoft.com/.default'
        }
        response = requests.post(url, headers=headers, data=body)
        response.raise_for_status() 
        return response.json()['access_token']

    def _send_email(self,access_token):
        url = f'https://graph.microsoft.com/v1.0/users/{self.sender_email}/sendMail'
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        body = {
            "message": {
                "subject": self.subject,
                "body": {
                    "contentType": "HTML",
                    "content": self.html_body
                },
                "toRecipients": [
                    {
                        "emailAddress": {
                            "address": self.recipient_email
                        }
                    }
                ]
            },
            "saveToSentItems": "true"
        }
        response = requests.post(url, headers=headers, json=body)
        response.raise_for_status() 
        _logger.info(f"**************** {response.status_code} ********************")
        return response.status_code