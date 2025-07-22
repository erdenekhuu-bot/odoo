import logging
from odoo import models
from .ms_graph_helper import get_ms_token, send_ms_email
import os

_logger = logging.getLogger(__name__)

# sender_email = 'no-reply@gmobile.mn'
sender_email = 'alert@gmobile.mn'

class MailingMailing(models.Model):
    _inherit = 'mailing.mailing'
    from_email=sender_email

    def action_test10(self):
        token=get_ms_token()
       
        _logger.info(f"Access token acquired successfully")

        for contact in self.mailing.mailing.search(['subject']):
            to_email=contact.email
            subject=self.subject
            body_html=self.body_html
            if not to_email:
                continue 
            _logger.info(f"Preparing to send email to {subject}")

            # status, message= send_ms_email(token, from_email, to_email, subject, body_html)
            # _logger.info(f"Email sent to {to_email} with status {status}")
            # if status >= 400:
            #     _logger.error(f"Failed to send email to {to_email}: {message}")
            # else:
            #     _logger.info(f"Email sent successfully to {to_email}")

        return True

    def action_test(self):
        token=get_ms_token()
        demo_mail=self.env['mailing.mailing'].browse([10])
        demo_contact=self.env['res.partner'].browse([43])
        
        send_ms_email(token, self.from_email, demo_contact.email, demo_mail.subject, demo_mail.body_html)
        _logger.info(f"**************** Test succed check your sundui.g@gmobile.mn ****************")
        return True

