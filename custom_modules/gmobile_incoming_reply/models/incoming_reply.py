from odoo import models, fields, api
from odoo.exceptions import UserError
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class IncomingReply(models.Model):
    _name = 'gmobile.incoming.reply'
    # _inherit = ['mail.thread']
    _description = 'Incoming Reply Log'
    _rec_name = 'subject'
    _order = 'received_date desc'

    email_from = fields.Char(string="From", tracking=True)
    subject = fields.Char(string="Subject")
    body_preview = fields.Html(string="Body")
    received_date = fields.Datetime(string="Received", default=fields.Datetime.now)
    reply_body = fields.Html(string="Reply Text")

    def action_back_reply(self):
        self.ensure_one()
        config = self.env["ir.config_parameter"].sudo()
        if not self.email_from:
            raise UserError("No recipient email address found.")
        if not self.reply_body:
            raise UserError("Please write a reply before sending.")

        smtp_user = config.get_param("smtp.user")
        smtp_pass = config.get_param("smtp.pass")
        if not smtp_user or not smtp_pass:
            raise UserError("No SMTP credentials configured.")

        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = self.email_from
        msg['Subject'] = f"Re: {self.subject or ''}"
        msg.add_header('Reply-To', 'alert@gmobile.mn')
        msg.attach(MIMEText(self.reply_body, 'html'))

        try:
            smtp_server = smtplib.SMTP('mail.gmobile.mn', 587)
            smtp_server.starttls()
            smtp_server.login(smtp_user, smtp_pass)
            smtp_server.sendmail(smtp_user, [self.email_from], msg.as_string())
            smtp_server.quit()
        except smtplib.SMTPException as e:
            raise UserError(str(e))

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
    #     return super().message_new(msg_dict, values)

    # def action_reply_to_customer(self):
    #     self.ensure_one()
    #     config = self.env["ir.config_parameter"].sudo()
    #     if not self.email_from:
    #         raise UserError("No customer email address")
    #     if not self.reply_body:
    #         raise UserError("Please write a reply before sending.")
    #
    #     mail = self.env['mail.mail'].sudo().create({
    #         'email_from': config.get_param("main.mail"),
    #         'email_to': self.email_from,
    #         'subject': f"Re: {self.subject or ''}",
    #         'body_html': self.reply_body,
    #         'model': self._name,
    #         'res_id': self.id,
    #         'auto_delete': True,
    #         'state': 'outgoing',
    #     })
    #     return {
    #         'name': 'Reply back',
    #         'type': 'ir.actions.act_window',
    #         'res_model': 'mail.mail',
    #         'res_id': mail.id,
    #         'view_mode': 'form',
    #         'view_id': self.env.ref('mail.view_mail_form').id,
    #         'target': 'new',
    #         'context': {'create': False},
    #     }