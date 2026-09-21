from odoo import models, fields, api
from odoo.exceptions import UserError
from email import message_from_bytes
from email.header import decode_header
from email.message import EmailMessage
from email.utils import parseaddr
import imaplib
import smtplib

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
    reply_body = fields.Html(string="Reply Text")
    mail_message_id = fields.Char(string="Message-ID", index=True, readonly=True)
    in_reply_to = fields.Char(string="In-Reply-To", readonly=True)

    _sql_constraints = [
        ('mail_message_id_uniq', 'unique(mail_message_id)',
         'This email was already received.'),
    ]


    # @api.model
    # def message_new(self, msg_dict, custom_values=None):
    #     values = {
    #         'email_from': msg_dict.get('from'),
    #         'subject': msg_dict.get('subject'),
    #         'body_preview': msg_dict.get('body'),
    #         'received_date': fields.Datetime.now(),
    #     }
    #     if custom_values:
    #         values.update(custom_values)
    #     return self.create(values)
    @api.model
    def message_new(self, msg_dict, custom_values=None):
        values = {
            'email_from': msg_dict.get('email_from') or msg_dict.get('from'),
            'subject': msg_dict.get('subject'),
            'body_preview': msg_dict.get('body'),
            'received_date': fields.Datetime.now(),
            'mail_message_id': msg_dict.get('message_id'),
            'in_reply_to': msg_dict.get('in_reply_to'),
        }
        if custom_values:
            values.update(custom_values)
        return super().message_new(msg_dict, custom_values=values)

    def action_reply_to_customer(self):
        self.ensure_one()
        config = self.env["ir.config_parameter"].sudo()
        imap = imaplib.IMAP4_SSL(
            config.get_param("IMAP.SERVER"),
            config.get_param("IMAP.PORT")
        )
        imap.login(
            config.get_param("USERNAME"),
            config.get_param("PASSWORD"),
        )
        imap.select("INBOX")

        if not self.email_from:
            raise UserError("No customer email address")
        if not self.reply_body:
            raise UserError("Please write a reply before sending.")

        mail = self.env['mail.mail'].sudo().create({
            'email_from': config.get_param("main.mail"),
            'email_to': self.email_from,
            'subject': f"Re: {self.subject or ''}",
            'body_html': self.reply_body,
            'model': self._name,
            'res_id': self.id,
            'auto_delete': True,
            'state': 'outgoing',
        })
        return {
            'name': 'Reply back',
            'type': 'ir.actions.act_window',
            'res_model': 'mail.mail',
            'res_id': mail.id,
            'view_mode': 'form',
            'view_id': self.env.ref('mail.view_mail_form').id,
            'target': 'new',
            'context': {'create': False},
        }