from odoo import http
from odoo.http import request, Response
import json
import datetime
import os
from odoo.modules.module import get_module_resource
import base64

def get_image_base64(self, relative_path):
    path = get_module_resource('invoice_own', relative_path)
    if path and os.path.exists(path):
        with open(path, 'rb') as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    return False

class ReadBase(http.Controller):
    @http.route('/invoice/read', type='http', auth="public", website=True)
    def index(self, **kw):
        invoices = request.env["generate.invoice"].read_base()
        invoice_date=datetime.date.today().strftime("%Y/%m/%d")
        return request.render("invoice_own.demo_custom_template",{"invoices": invoices,"invoice_date":invoice_date})
        # return Response(
        #     json.dumps(invoices),
        #     content_type='application/json;charset=utf-8',
        #     status=200
        #)


class TemplateController(http.Controller):
    @http.route('/invoice/get', type='http', auth="public", website=True)
    def index(self, **kw):
        return request.render('invoice_own.pdfbody',)