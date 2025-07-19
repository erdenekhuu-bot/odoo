from odoo import models, fields

class Addons(models.Model):
    _name='shine.addon'

    addons_name=fields.Char(string='addon name')
    addons_description=fields.Char(string='addon description')
    addons_category=fields.Char(string='addon category')