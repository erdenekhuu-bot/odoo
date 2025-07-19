import requests
import logging
from odoo import models

_logger = logging.getLogger(__name__)

class MailMail(models.Model):
    _inherit = 'mail.mail'

    def _send(self, auto_commit=False, raise_exception=False):
        for mail in self:
            token = self.env['ms.graph.token'].get_access_token()
            if not token:
                _logger.error("[Graph API] Access token олдсонгүй.")
                mail.state = 'exception'
                continue

            data = {
                "message": {
                    "subject": mail.subject or "(No subject)",
                    "body": {
                        "contentType": "HTML",
                        "content": mail.body_html or mail.body or ""
                    },
                    "toRecipients": [{"emailAddress": {"address": mail.email_to}}],
                    "from": {"emailAddress": {"address": mail.email_from}},
                }
            }

            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }

            sender_email = mail.email_from
            url = f'https://graph.microsoft.com/v1.0/users/{sender_email}/sendMail'

            response = requests.post(url, json=data, headers=headers)
            if response.status_code in [202, 200]:
                mail.state = 'sent'
                _logger.info(f"[Graph API] Амжилттай илгээгдлээ → {mail.email_to}")
            else:
                mail.state = 'exception'
                _logger.error(f"[Graph API] Илгээхэд алдаа гарлаа: {response.text}")

        return True
