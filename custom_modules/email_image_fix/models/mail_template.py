from odoo import models

class MailTemplate(models.Model):
    _inherit = 'mail.template'

    def _replace_image_urls(self, html):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        secure_url = base_url.replace('http://', 'https://')
        
        # Replace relative and HTTP URLs
        html = html.replace('src="/', f'src="{secure_url}/')
        html = html.replace('src="http://', 'src="https://')
        return html

    def generate_email(self, res_ids, fields=None):
        email_values = super().generate_email(res_ids, fields=fields)
        if email_values.get('body_html'):
            email_values['body_html'] = self._replace_image_urls(email_values['body_html'])
        return email_values