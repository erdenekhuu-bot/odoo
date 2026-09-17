from odoo import models, fields, api
from odoo.exceptions import UserError

class IncomingReply(models.Model):
    _name = 'gmobile.incoming.reply'
    _inherit = ['mail.thread']
    _description = 'Incoming Reply Log'
    _rec_name = 'subject'
    _order = 'received_date desc'

    email_from = fields.Char(string="From", tracking=True)
    subject = fields.Char(string="Subject")
    body_preview = fields.Html(string="Body")
    received_date = fields.Datetime(string="Received", default=fields.Datetime.now)

    @api.model
    def message_new(self, msg_dict, custom_values=None):
        values = {
            'email_from': msg_dict.get('from'),
            'subject': msg_dict.get('subject'),
            'body_preview': msg_dict.get('body'),
            'received_date': fields.Datetime.now(),
        }
        if custom_values:
            values.update(custom_values)
        return super().message_new(msg_dict, values)

    def action_reply_to_customer(self):
        self.ensure_one()
        config = self.env["ir.config_parameter"].sudo()
        if not self.email_from:
            raise UserError("No customer email address to reply to.")

        # mail = self.env['mail.mail'].sudo().create({
        #     'email_from': config.get_param("main.mail"),
        #     'email_to': self.email_from,
        #     'subject': f"Re: {self.subject or ''}",
        #     'body_html': self.body_preview or '',
        #     'model': self._name,
        #     'res_id': self.id,
        #     'auto_delete': True,
        #     'state': 'outgoing',
        # })
        return {
            'name': 'Select Mail to Reply',
            'type': 'ir.actions.act_window',
            'res_model': 'mail.mail',
            'view_mode': 'list,form',
            'views': [(self.env.ref('mail.view_mail_tree').id, 'list'),
                      (self.env.ref('mail.view_mail_form').id, 'form')],
            'domain': [('email_to', '=', self.email_from)],
            'target': 'new',
            'context': {
                'default_email_to': self.email_from,
                'default_email_from': config.get_param("main.mail"),
                'default_subject': f"Re: {self.subject or ''}",
                'default_model': self._name,
                'default_res_id': self.id,
            },
        }