import logging

from odoo import models

_logger = logging.getLogger(__name__)


class SmsComposer(models.TransientModel):
    _inherit = 'sms.composer'

    def _action_send_sms_mass(self, records=None):
        sms_all = super()._action_send_sms_mass(records=records)

        if sms_all and not self.mass_force_send:
            cron = self.env.ref(
                'sms.ir_cron_sms_scheduler_action',
                raise_if_not_found=False,
            )

            if cron and cron.active:
                _logger.info(
                    "Triggering SMS Queue Manager for SMS ids=%s",
                    sms_all.ids,
                )
                cron._trigger()

        return sms_all