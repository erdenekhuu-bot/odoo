from odoo import models, fields, api, _

class ResPartner(models.Model):
    _inherit = 'res.partner'
    segment_contract_ids = fields.One2many('segment.contract','partner_id')

class SegmentContract(models.Model):
    _name = 'segment.contract'
    name = fields.Char(string="Contract Reference")
    partner_id = fields.Many2one('res.partner', ondelete='cascade')