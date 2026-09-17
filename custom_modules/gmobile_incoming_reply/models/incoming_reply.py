from odoo import models, fields, api


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
        compose_ctx = {
            'default_model': self._name,
            'default_res_ids': [self.id],
            'default_composition_mode': 'comment',
            'default_subject': f"Re: {self.subject or ''}",
            'default_partner_ids': [],
            'default_email_to': self.email_from,
            'default_body': '',
        }
        return {
            'type': 'ir.actions.act_window',
            'name': 'Reply to Customer',
            'res_model': 'mail.compose.message',
            'view_mode': 'form',
            'target': 'current',
            'context': compose_ctx,
        }