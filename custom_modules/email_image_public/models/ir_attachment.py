from odoo import models, fields, api

class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    @api.model
    def create(self, vals):
        # Check if it's an image and related to mail
        if vals.get('mimetype', '').startswith('image/') and not vals.get('public', False):
            if 'mail.compose.message' in vals.get('res_model', '') or 'mail.template' in vals.get('res_model', ''):
                vals['public'] = True
        return super(IrAttachment, self).create(vals)
