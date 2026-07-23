from odoo import api, fields, models

class BillingGroup(models.Model):
    _name = 'billing.group'
    _description = 'Billing Group for test campaign'

    name = fields.Char(string='Billing Group Name')
    acc_number = fields.Char(string='Account Number')