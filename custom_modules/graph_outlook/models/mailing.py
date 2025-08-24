import logging
from odoo import models, fields, api
from .ms_graph_helper import get_ms_token, send_ms_email
import os

_logger = logging.getLogger(__name__)

# sender_email = 'no-reply@gmobile.mn'
sender_email = 'newsletter@gmobile.mn'


class TestCustom(models.Model):
    pass
class MailingMailing(models.Model):
    _inherit = 'mailing.mailing'
    from_email=sender_email

    def action_test(self):
        token=get_ms_token()
        _logger.info(f"**************** {token} ****************")
        return True

    def action_launch(self):
        _logger.info(f"**************** ACTION TRIGGERED *************************")
        return super().action_launch()
    
    
    def _action_send_mail(self, res_ids=None):
        token = get_ms_token()
        author_id = self.env.user.partner_id.id

        for mailing in self:
            mailing_res_ids = res_ids or mailing._get_remaining_recipients()

            _logger.info("********* MASS MAIL VIA GRAPH API *********")

            # Mass Mailing бүрийн хүлээн авагч бүрт илгээх.
            for partner_id in mailing_res_ids:
                
                partner = self.env['res.partner'].browse(partner_id)
                _logger.info(f"********* {partner} ***********")
                status, text = send_ms_email(
                    token,
                    from_email=self.from_email,
                    to_email=partner.email or '',
                    subject=mailing.subject or '',
                    html_content=mailing.body_html or ''
                )
                if status not in (200, 202):
                    _logger.error("Graph API send failed: %s", text)

            # Илгээсний дараа state update.
            mailing.write({
                'state': 'done',
                'sent_date': fields.Datetime.now(),
                'kpi_mail_required': not mailing.sent_date,
            })

        return True


    