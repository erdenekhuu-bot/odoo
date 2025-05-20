from odoo import models, api

class IrQWeb(models.AbstractModel):
    _inherit = 'ir.qweb'

    @api.model
    def _render_image(self, record, field_name, **options):
        original_url = super()._render_image(record, field_name, **options)
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        
        # Force HTTPS and correct domain
        if original_url.startswith(('http://', '/')):
            secure_url = base_url.replace('http://', 'https://')
            
            if original_url.startswith('/'):
                return f"{secure_url}{original_url}"
            elif original_url.startswith('http://'):
                return original_url.replace('http://', 'https://')
        
        return original_url