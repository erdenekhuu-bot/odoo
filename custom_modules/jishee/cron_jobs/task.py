from odoo import  models, api

class Task(models.AbstractModel):
    _inherit = 'task'

    @api.model
    def init_task(self):
        pass