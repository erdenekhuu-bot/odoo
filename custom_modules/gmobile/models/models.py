# -*- coding: utf-8 -*-
from odoo import models, fields, api
import requests
import logging
import base64

_logger = logging.getLogger(__name__)

class gmobile(models.AbstractModel):
    _name = 'gmobile.invoice.service'
    _description = 'GMobile Invoice Service'

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
            'gmobile.gmobile_invoice_email_body',
            {
                'items': result.get('items', [])[:10],
                'total': result.get('total', 0),
            }
        )
        pdf_content = b"Test attachment content"
        attachment = self.env['ir.attachment'].create({
            'name': 'dashboard_report.pdf',
            'type': 'binary',
            'datas': base64.b64encode(pdf_content),
            'mimetype': 'application/pdf',
        })

        if isinstance(html_body, bytes):
            html_body = html_body.decode('utf-8')

        mail = self.env['mail.mail'].sudo().create({
            'subject': 'Gmobile Invoice Dashboard',
            'email_to': 'erdenekhuu.e@gmobile.mn',
            'email_from': 'alert@gmobile.mn',
            'body_html': html_body,
            'attachment_ids': [(4, attachment.id)],
        })

        # html_body = """
        #         <div style="font-family: Arial, sans-serif; padding: 20px;">
        #             <h2>Gmobile Invoice Dashboard</h2>
        #             <p>Энэ бол тест email.</p>
        #             <ul>
        #                 <li>Invoice A</li>
        #                 <li>Invoice B</li>
        #                 <li>Invoice C</li>
        #             </ul>
        #         </div>
        #         """
        #
        # mail = self.env['mail.mail'].sudo().create({
        #     'subject': 'Simple HTML Mail',
        #     'email_to': 'nvipree441@gmail.com',
        #     'email_from': 'alert@gmobile.mn',
        #     'body_html': html_body,
        # })
        _logger.info("Mail created: %s", mail.id)
        mail.send()
        return True
