from odoo import api, fields, models
import requests
from weasyprint import HTML
import base64

class GenerateInvoice(models.AbstractModel):
    _name = 'generate.invoice'

    @api.model
    def read_billing(self):
        url = "https://jsonplaceholder.typicode.com/todos"
        response = requests.get(url, timeout=20)
        response.raise_for_status()
        data = response.json()

        return {
            'items': data,
            'total': len(data),
        }

    def execution(self):
        result = self.read_billing()
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        agent=self.env['res.users'].filtered_domain('login','=','bot@gmobile.mn')
        html_body = self.env['ir.qweb']._render(
            'jishee.sample_template',
            {
                'items': result.get('items', [])[:10],
                'total': result.get('total', 0),
            }
        )
        return True