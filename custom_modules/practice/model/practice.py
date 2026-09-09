from odoo import models, fields, api

class Practice(models.Model):
    _name = 'practice.odoo.model'
    _description = 'Practice'

    name = fields.Char(required=True)
    description = fields.Char(required=True)