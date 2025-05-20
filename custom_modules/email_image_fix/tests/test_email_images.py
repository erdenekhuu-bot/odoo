from odoo.tests import tagged, HttpCase

@tagged('post_install', '-at_install')
class TestEmailImages(HttpCase):
    def test_image_urls_in_emails(self):
        # Create a test email template
        template = self.env['mail.template'].create({
            'name': 'Test Template',
            'body_html': '<img src="/web/image/1"/> <img src="http://example.com/image.jpg"/>'
        })
        
        # Generate email
        email_values = template.generate_email([1])
        body = email_values['body_html']
        
        # Verify URLs are fixed
        self.assertIn('https://massmail.gmobile.mn/web/image/1', body)
        self.assertIn('https://example.com/image.jpg', body)