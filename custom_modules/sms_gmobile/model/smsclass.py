import logging
import requests

from odoo.addons.sms.tools.sms_api import SmsApi

_logger = logging.getLogger(__name__)


class SMSHelperApi(SmsApi):

    def _send_sms_batch(self, messages, delivery_reports_url=False):
        _logger.warning(
            "===== CUSTOM SMSHelperApi._send_sms_batch CALLED ====="
        )
        _logger.info('Sending SMS batch')
        config = self.env['ir.config_parameter'].sudo()

        base_url = config.get_param('sms.provider_url')

        username = config.get_param('sms.provider_username')
        password = config.get_param('sms.provider_password')
        results = []

        for message in messages:
            content = message['content']

            for recipient in message['numbers']:
                number = recipient['number']
                uuid = recipient['uuid']

                try:
                    response = requests.get(
                        base_url,
                        params={
                            'username': username,
                            'password': password,
                            'to': number,
                            'text': content,
                            'from': '309'
                        },
                        timeout=15,
                    )

                    response.raise_for_status()

                    _logger.info(
                        "SMS sent: number=%s response=%s",
                        number,
                        response.text,
                    )

                    results.append({
                        'uuid': uuid,
                        'state': 'success',
                    })

                except requests.RequestException as e:
                    _logger.exception(
                        "SMS sending failed: number=%s error=%s",
                        number,
                        e,
                    )

                    results.append({
                        'uuid': uuid,
                        'state': 'server_error',
                    })

        return results

SmsApi._send_sms_batch = SMSHelperApi._send_sms_batch