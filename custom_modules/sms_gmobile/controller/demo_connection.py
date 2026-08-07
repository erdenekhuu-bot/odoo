from odoo import http

class DemoConnection(http.Controller):
    @http.route('/custom_modules/d1/custom_modules/d1', auth='public')
    def index(self, **kw):
        return "Hello, world"

