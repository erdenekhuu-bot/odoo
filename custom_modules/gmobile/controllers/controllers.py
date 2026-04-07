# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request, Response
import json

class GmobileController(http.Controller):
    @http.route('/gmobile/controller', type='http', auth='public')
    def index(self,**kwargs):
        return "Gmobile"

class MyDashboard(http.Controller):
    @http.route('/gmobile/invoice/template', type='http', auth='user')
    def index(self, **kwargs):
        data = request.env['gmobile.invoice.service'].fetch_items()
        return Response(
            json.dumps(data),
            content_type='application/json;charset=utf-8',
            status=200,
        )
