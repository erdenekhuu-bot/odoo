from odoo import models, api


class ConstMail(models.Model):
    _inherit = 'mailing.mailing'

   

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', 'https://massmail.gmobile.mn')
        res['email_from'] = 'NewsLetter <alert@gmobile.mn>'
        res['reply_to'] = 'NewsLetter <alert@gmobile.mn>'
        res['website_url'] = base_url
        return res