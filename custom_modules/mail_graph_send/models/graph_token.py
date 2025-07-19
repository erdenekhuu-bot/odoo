# models/graph_token.py
import os
import requests
import logging
from odoo import models
from dotenv import load_dotenv

# .env ачаалж утгуудыг environment-д оруулах
load_dotenv()

_logger = logging.getLogger(__name__)

class MsGraphToken(models.Model):
    _name = 'ms.graph.token'
    _description = 'Microsoft Graph Access Token'

    def get_access_token(self):
        # .env-оос шууд авна
        tenant_id = os.getenv('tenantId')
        client_id = os.getenv('clientId')
        client_secret = os.getenv('clientSecret')

        token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"

        data = {
            'client_id': client_id,
            'scope': 'https://graph.microsoft.com/.default',
            'client_secret': client_secret,
            'grant_type': 'client_credentials',
        }

        response = requests.post(token_url, data=data)
        if response.status_code == 200:
            token = response.json().get('access_token')
            return token
        else:
            _logger.error(f"[Graph API] Token авахад алдаа гарлаа: {response.text}")
            return None
