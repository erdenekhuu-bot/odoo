from odoo import http
from odoo.http import request, Response
import json
import datetime

class ReadBase(http.Controller):
    @http.route('/invoice/read', type='http', auth="public", website=True)
    def index(self, **kw):
        invoices = request.env["generate.invoice"].read_base()
        invoice_date=datetime.date.today().strftime("%Y/%m/%d")
        return request.render("invoice_own.extendedbdftemplate",{"invoices": invoices,"invoice_date":invoice_date})
        # return Response(
        #     json.dumps(invoices),
        #     content_type='application/json;charset=utf-8',
        #     status=200
        # )


class TemplateController(http.Controller):
    @http.route('/invoice/get', type='http', auth="public", website=True)
    def index(self, **kw):
        return request.render('invoice_own.extendedbdftemplate',)
