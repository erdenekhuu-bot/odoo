from odoo import http
from odoo.http import request, Response
import json


class ReadBase(http.Controller):
    @http.route('/invoice/read', type='http', auth="public", website=True)
    def index(self, **kw):
        call_self = request.env["generate.invoice"].read_base()
        return Response(
            json.dumps(call_self),
            content_type='application/json;charset=utf-8',
            status=200
        )