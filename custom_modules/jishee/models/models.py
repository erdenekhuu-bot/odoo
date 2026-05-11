from odoo import models, fields, api
import requests
import logging
from weasyprint import HTML
import base64

_logger = logging.getLogger(__name__)

class NewModule(models.Model):
    _name = 'jishee.table'
    _description = 'Zovhon jishee data oruulna'

    name=fields.Char(string='Name',required=True,max_length=10, index=True)
    description=fields.Char(string='Description')
    about=fields.Text(string='About',required=True,max_length=500)
    age=fields.Integer(string='Age',required=True)
    career=fields.Char(string='Career',required=True)
    profile=fields.Binary(string='Profile',required=True)
    start_date = fields.Datetime(string='Start Date', required=True)
    end_date = fields.Datetime(string='End Date')

    @api.model
    def fetch_items(self):
        url = "https://jsonplaceholder.typicode.com/todos"
        response = requests.get(url, timeout=20)
        response.raise_for_status()
        data = response.json()

        return {
            'items': data,
            'total': len(data),
        }

    @api.model
    def send_custom_page_mail(self):
        result = self.fetch_items()
        html_body = self.env['ir.qweb']._render(
            'jishee.sample_template',
            {
                'items': result.get('items', [])[:10],
                'total': result.get('total', 0),
            }
        )
        mail = self.env['mail.mail'].create({
            'subject': 'Gmobile Invoice Dashboard',
            'email_to': self.env['ir.config_parameter'].get_param('customer.customer.mail'),
            'email_from': self.env['ir.config_parameter'].get_param('main.mail'),
            'body_html': html_body,
        })
        _logger.info("Mail created: %s", mail.id)
        mail.send()
        return True

    @api.model
    def custom_demostration(self):
        base_url=self.env['ir.config_parameter'].get_param('web.base.url')
        html_content = self.env['ir.qweb']._render('jishee.attachment_pdf_invoice', {
            'base_url': base_url,
        })

        if isinstance(html_content, bytes):
            html_content = html_content.decode('utf-8')

        pdf_content = HTML(string=html_content,base_url=base_url).write_pdf()

        attachment = self.env['ir.attachment'].create({
            'name': 'dashboard_report.pdf',
            'type': 'binary',
            'datas': base64.b64encode(pdf_content),
            'mimetype': 'application/pdf',
        })
        contact = self.env['mailing.contact'].search([], limit=1)

        mass = self.env['mailing.mailing'].create({
            'subject': 'Gmobile Invoice Dashboard',
            'email_from': self.env['ir.config_parameter'].get_param('main.mail'),
            'mailing_type': 'bot',
            'body_html': html_content,
            'attachment_ids': [(6, 0, [attachment.id])],
            'contact_list_ids': [(6, 0, [contact.id])],

        })
        mass.action_send_mail()
        mailing_trace_id=mass.id
        html_body = "<p>Эрхэм хэрэглэгч танд энэ өдрийн мэнд хүргэе</p>"
        mail = self.env['mail.mail'].create({
            'subject': 'Gmobile төлбөрийн нэхэмжлэл',
            'email_to': self.env['ir.config_parameter'].get_param('customer.customer.mail'),
            'email_from': self.env['ir.config_parameter'].get_param('main.mail'),
            'body_html': html_body,
            'attachment_ids': [(4, attachment.id)],
            'mailing_trace_id': mailing_trace_id,
        })

        _logger.info("Mail created: %s", mail.id)
        mail.send()
        return True


