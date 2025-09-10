from odoo import models, api


class ConstMail(models.Model):
    _inherit = 'mailing.mailing'

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        res['email_from'] = 'NewsLetter <alert@gmobile.mn>'
        res['reply_to'] = 'NewsLetter <alert@gmobile.mn>'
        return res