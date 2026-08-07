from odoo import api, fields, models
import requests
import json
import time

class SMSclass(models.TransientModel):
    _name = 'sms.class'
    _description = 'SMS third party pool'

    def _connection_sms(self):
        pass

    @api.model
    def initiate_sms(self):
        pass