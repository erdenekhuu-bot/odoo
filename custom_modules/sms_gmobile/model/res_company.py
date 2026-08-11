from odoo import models

from smsclass import SMSHelperApi


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _get_sms_api_class(self):
        self.ensure_one()
        return SMSHelperApi