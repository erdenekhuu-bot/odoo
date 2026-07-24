from odoo import models,fields

class DefaultEmailContent(models.Model):
    _inherit = "mailing.mailing"

    email_from = fields.Char(readonly=True)
    reply_to_mode = fields.Selection(readonly=True)
    reply_to = fields.Char(readonly=True)

    def _get_system_mail_addresses(self):
        config = self.env["ir.config_parameter"].sudo()

        email_from = config.get_param("default.mail.from")
        reply_to = config.get_param("default.mail.reply_to")

        return email_from, reply_to
