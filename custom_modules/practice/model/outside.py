from odoo import api, models, fields, exceptions
import logging

_logger = logging.getLogger(__name__)

class OutSide(models.Model):
    _name = 'outside.new.model'
    _description = 'Outside model'

    name = fields.Char(string="Name")
    email = fields.Char(string="Email")
    phone = fields.Char(string="Phone")
    address = fields.Char(string="Address")
    age = fields.Integer(string="Age")
    image = fields.Binary(string="Image")
    about=fields.Html(string="About")

    def action_download_custom_pdf(self):
        return self.env.ref('practice.demo_report').report_action(self)