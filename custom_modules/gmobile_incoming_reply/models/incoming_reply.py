from odoo import models, fields, api
from odoo.exceptions import UserError
from email.header import decode_header
from email.message import EmailMessage
from email.utils import parseaddr
import smtplib
import logging
from odoo.tools import html2plaintext

_logger = logging.getLogger(__name__)

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
    references = fields.Text(string="References",readonly=True)
    mail_template = fields.Many2one('mailing.mailing',string="Mailing Template")

    _sql_constraints = [
        ('mail_message_id_uniq', 'unique(mail_message_id)',
         'This email was already received.'),
    ]

    @api.model
    def message_new(self, msg_dict, custom_values=None):
        values = {
            'email_from': msg_dict.get('email_from') or msg_dict.get('from'),
            'subject': msg_dict.get('subject'),
            'body_preview': msg_dict.get('body'),
            'received_date': fields.Datetime.now(),
            'mail_message_id': msg_dict.get('message_id'),
            'in_reply_to': msg_dict.get('in_reply_to'),
            'references': msg_dict.get('references'),
        }
        if custom_values:
            values.update(custom_values)
        return super().message_new(msg_dict, custom_values=values)

    def action_back_reply(self):
        self.ensure_one()
        config = self.env["ir.config_parameter"].sudo()
        smtp_server = config.get_param("mail.smtp.server")
        smtp_port = int(config.get_param("mail.smtp.port","587"))
        smtp_username = config.get_param("smtp.USERNAME")
        smtp_password = config.get_param("smtp.PASSWORD")
        from_address = config.get_param("main.mail")
        _logger.info(self.email_from,self.mail_message_id)

        if not self.email_from or not self.mail_message_id:
            raise UserError("Хариу бичих боломжгүй")


        if not smtp_server:
            raise UserError(
                "SMTP server тохируулаагүй байна."
            )

        if not from_address:
            raise UserError(
                "Хариу илгээгч тохируулаагүй байна."
            )

        # Name <email@gmail.com> байвал
        # зөвхөн email address-ийг салгаж авна.
        customer_address = parseaddr(
            self.email_from
        )[1]

        if not customer_address:
            customer_address = self.email_from

        # -----------------------------------------
        # Reply message
        # -----------------------------------------

        reply = EmailMessage()

        reply["From"] = from_address
        reply["To"] = customer_address

        original_subject = (
                self.subject or ""
        ).strip()

        if original_subject.lower().startswith(
                "re:"
        ):
            reply["Subject"] = (
                original_subject
            )
        else:
            reply["Subject"] = (
                f"Re: {original_subject}"
            )

        # =========================================
        # ХАМГИЙН ЧУХАЛ
        # Incoming customer mail-ийн Message-ID
        # =========================================

        reply["In-Reply-To"] = (
            self.mail_message_id
        )

        # =========================================
        # Thread References
        # =========================================

        references = []

        if self.references:
            references.append(
                self.references.strip()
            )

        references.append(
            self.mail_message_id.strip()
        )

        reply["References"] = " ".join(
            references
        )

        # -----------------------------------------
        # Reply body
        # -----------------------------------------

        if not self.reply_body:
            raise UserError(
                "Заавал хариугаа бичээрэй."
            )
        reply_text_html = str(self.reply_body or "")
        template_html = ""
        if self.mail_template:
            template_html = str(
                self.mail_template.body_html or ""
            )

        if not html2plaintext(reply_text_html).strip() and not template_html:
            raise UserError(
                "Хариу текст бичих эсвэл мэйл template сонгоно уу."
            )
        base_url = config.get_param("web.base.url")
        combined_html = f"""
        <div>
            {reply_text_html}
        </div>

        {template_html}
        """
        combined_html = self.env["mail.render.mixin"]._replace_local_links(
            combined_html, base_url=base_url
        )

        # Plain text fallback
        plain_body = html2plaintext(
            combined_html
        ).strip()

        reply.set_content(
            plain_body
        )
        reply.add_alternative(
            combined_html,
            subtype="html"
        )
        # -----------------------------------------
        # SMTP
        # -----------------------------------------

        try:
            with smtplib.SMTP(smtp_server,smtp_port,timeout=30) as smtp:
                smtp.ehlo()
                smtp.starttls()
                smtp.ehlo()
                smtp.login(smtp_username,smtp_password)
                smtp.send_message(reply)

        except Exception as e:
            raise UserError(
                f"Email илгээхэд алдаа гарлаа: {e}"
            )

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Амжилттай",
                "message": f"{customer_address} хаяг руу хариу амжилттай илгээгдлээ.",
                "type": "success",
                "sticky": False,
            },
        }

    @staticmethod
    def decode_mime_header(value):
        if not value:
            return ""

        decoded_parts = decode_header(value)

        result = ""

        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                result += part.decode(
                    encoding or "utf-8",
                    errors="replace"
                )
            else:
                result += part

        return result