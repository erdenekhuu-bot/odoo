from odoo import models, fields

class DemoChart(models.Model):
    _name = 'demo.chart'
    _description = 'Demo Chart Model'

    name = fields.Char(string='Name', required=True)
    description = fields.Text(string='Description')
    is_active = fields.Boolean(string='Is Active', default=True)
