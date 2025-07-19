from odoo import models, fields

class AttachMailCustom(models.Model):
    _inherit='mailing.list'
    email=fields.Char(string='email')  
