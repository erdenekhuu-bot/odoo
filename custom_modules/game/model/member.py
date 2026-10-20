from odoo import models, fields, api

class Member(models.Model):
    _name = 'game.member'

    name = fields.Char(string="Name", required=True)
    phone = fields.Char(string="Phone", default="")
    score = fields.Integer(string="Score", required=True)

