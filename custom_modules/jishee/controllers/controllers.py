from odoo import http
from odoo.http import request, Response
import json

class JisheeController(http.Controller):
    @http.route('/invoice_mail', type='http', auth='user', website=True)
    def index(self, **kwargs):
        data = request.env['jishee.table'].fetch_items()
        return request.render('jishee.sample_template',{
                'items': data.get('items', [])[:10],
                'total': data.get('total', 0),
            })