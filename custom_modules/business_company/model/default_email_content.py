from odoo import models,fields,api

class DefaultEmailContent(models.Model):
    _inherit = "mailing.mailing"

    email_from = fields.Char(readonly=True)
    reply_to_mode = fields.Selection(readonly=True)
    reply_to = fields.Char(readonly=True)

    def _get_system_mail_addresses(self):
        config = self.env["ir.config_parameter"].sudo()

        email_from = config.get_param("main.mail")
        reply_to = config.get_param("main.mail")

        return email_from, reply_to

    @api.depends("mail_server_id", "create_uid")
    def _compute_email_from(self):
        email_from, _ = self._get_system_mail_addresses()

        for mailing in self:
            mailing.email_from = email_from

    @api.depends("mailing_model_id")
    def _compute_reply_to_mode(self):
        for mailing in self:
            mailing.reply_to_mode = "new"

    @api.depends("reply_to_mode")
    def _compute_reply_to(self):
        _, reply_to = self._get_system_mail_addresses()

        for mailing in self:
            mailing.reply_to = reply_to
