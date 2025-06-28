from odoo import models, fields

class AttachMailCustom(models.Model):
    _inherit='mail.mail'
    mailing_list_id=fields.Many2one('mailing.list', string='Mailing List')
    mailing_contact_id=fields.Many2one('mailing.contact', string='Mailing Contact')
