import logging
import requests
from odoo import models, api

_logger = logging.getLogger(__name__)


class SmsSmsCustom(models.Model):
    _inherit = 'sms.sms'

    def _send(self, unlink_failed=False, unlink_sent=True, raise_exception=False):
        """
        Override the main sending engine for sms.sms queue/marketing elements
        to bypass Odoo IAP and use a custom gateway directly.
        """
        config = self.env['ir.config_parameter'].sudo()
        base_url = config.get_param('sms.provider_url')
        username = config.get_param('sms.provider_username')
        password = config.get_param('sms.provider_password')
        sender_id = config.get_param('sms.provider_sender', '309')

        for record in self:
            try:
                # Make HTTP request to your custom gateway provider
                response = requests.get(
                    base_url,
                    params={
                        'username': username,
                        'password': password,
                        'to': record.number,
                        'text': record.body,
                        'from': sender_id
                    },
                    timeout=15,
                )
                response.raise_for_status()

                _logger.info("Custom SMS sent successfully to %s", record.number)

                # Update Odoo record state to 'sent'
                record.write({
                    'state': 'sent',
                    'failure_type': False,
                })

                if unlink_sent:
                    record.unlink()

            except Exception as e:
                _logger.exception("Failed to send custom SMS to %s: %s", record.number, e)

                # Update Odoo record state to 'error'
                record.write({
                    'state': 'error',
                    'failure_type': 'unknown',
                })

                if unlink_failed:
                    record.unlink()

                if raise_exception:
                    raise

        return True