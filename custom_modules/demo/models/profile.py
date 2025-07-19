from odoo import models, tools, api, fields

class DemoProfile(models.Model):
    _name = 'demo.profile'
    _description = 'Demo Profile Model'

    name = fields.Char(string='Name', required=True)
    age = fields.Integer(string='Age')
    email = fields.Char(string='Email')
    is_active = fields.Boolean(string='Is Active', default=True)
