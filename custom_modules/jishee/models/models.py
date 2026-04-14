from odoo import models, fields, api
import requests
import logging

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
            'email_to': self.env['ir.config_parameter'].sudo().get_param('customer.customer.mail'),
            'email_from': 'alert@gmobile.mn',
            'body_html': html_body,
        })
        _logger.info("Mail created: %s", mail.id)
        mail.send()
        return True


