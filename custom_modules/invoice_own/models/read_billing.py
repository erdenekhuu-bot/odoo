import logging

from odoo import api, fields, models
from odoo.exceptions import UserError
import psycopg2
import base64
from odoo.modules.module import get_module_resource
import os

_logger = logging.getLogger(__name__)

class ReadBilling(models.Model):
    _name = 'billing.read'
    _description = 'Read and write billing'

    acc_number = fields.Char('acc_number', required=True)
    email = fields.Char('email', required=True)
    bylling_cycle_id = fields.Char('bylling_cycle_id', required=True)
    period_start = fields.Date('period_start', required=True)
    period_end = fields.Date('period_end', required=True)
    items = fields.Json('items', required=True)
    state=fields.Char('state', required=False)

    @api.model
    def sync_billing(self):
        db_name = self.env['ir.config_parameter'].sudo().get_param("second.base")
        db_user = self.env['ir.config_parameter'].sudo().get_param("second.dbuser")
        db_pass = self.env['ir.config_parameter'].sudo().get_param("second.dbpassword")
        db_host = self.env['ir.config_parameter'].sudo().get_param("second.dbhost")

        if not all([db_name, db_user, db_pass, db_host]):
            raise UserError("Өгөгдлийн сангийн холболтын параметрүүд дутуу тохируулагдсан байна!")

        conn = None
        try:
            conn = psycopg2.connect(
                dbname=db_name, user=db_user, password=db_pass, host=db_host
            )
            cursor = conn.cursor()

            query = """
                SELECT 
                    an.acc_number,
                    an.email,
                    b.billing_cycle_id AS bylling_cycle_id,
                    b.period_start,
                    b.period_end,
                    json_agg(
                        json_build_object(
                            'item_type', bi.item_type,
                            'amount', bi.amount
                        )
                    ) AS items
                FROM bill_item bi
                LEFT JOIN bill b ON bi.bill_id = b.id
                LEFT JOIN acc_number an ON b.acc_number_id = an.id
                WHERE SUBSTR(an.acc_number, 1, 2) = '98'
                GROUP BY 
                    an.acc_number,
                    an.email,
                    b.billing_cycle_id,
                    b.period_start,
                    b.period_end
                ORDER BY an.acc_number
            """
            cursor.execute(query)
            results = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]

            vals_list = []
            for row in results:
                row_dict = dict(zip(columns, row))
                vals_list.append(row_dict)

            cursor.close()

            if vals_list:
                for vals in vals_list:
                    existing_record = self.search([
                        ('acc_number', '=', vals['acc_number']),
                        ('bylling_cycle_id', '=', vals['bylling_cycle_id'])
                    ], limit=1)

                    if existing_record:
                        existing_record.write(vals)
                    else:
                        self.create(vals)

        except psycopg2.Error as e:
            raise UserError(f"Гадаад өгөгдлийн сантай холбогдоход алдаа гарлаа: {e}")
        finally:
            if conn:
                conn.close()
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def execution_something(self):
        try:
            logo_b64 = self.get_image_base64('static/src/img/logo.png')
            app_b64 = self.get_image_base64('static/src/img/appstoreqr.png')
            qr_b64 = self.get_image_base64('static/src/img/playstoreqr.png')
            screen1_b64 = self.get_image_base64('static/src/img/whitescreen.png')
            screen2_b64 = self.get_image_base64('static/src/img/whitescreen2.png')
            screen3_b64 = self.get_image_base64('static/src/img/whitescreen3.png')
            agent = self.env['res.users'].search([('login', '=', 'bot@gmobile.mn')], limit=1)

            pdf_content, _ = self.env['ir.actions.report'].sudo().with_context(
                {
                    'logo_b64': logo_b64,
                    'app_b64': app_b64,
                    'qr_b64': qr_b64,
                    'screen1_b64': screen1_b64,
                    'screen2_b64': screen2_b64,
                    'screen3_b64': screen3_b64,
                 }
                )._render_qweb_pdf(
                'invoice_own.final_report_pdf',
                res_ids=self.ids
            )
            attachment = self.env['ir.attachment'].sudo().create({
                'name': 'invoice.pdf',
                'type': 'binary',
                'datas': base64.b64encode(pdf_content).decode('utf-8'),
                'res_model': self._name,
                'res_id': self.id,
                'mimetype': 'application/pdf',
            })
            contact_list = self.env['mailing.list'].search([], limit=1)
            email_campaign = self.env['mailing.mailing'].sudo().create({
                'name': 'Тест Нэхэмжлэх Захидал',
                'subject': 'Таны нэхэмжлэх бэлэн боллоо (Тест)',
                'body_html': '<p>Эрхэм хэрэглэгч танд энэ өдрийн мэнд хүргэе</p>',
                'mailing_type': 'mail',
                'attachment_ids': [(4, attachment.id)],
                'mailing_model_id': self.env.ref('mass_mailing.model_mailing_contact').id,
                'contact_list_ids': [(4, contact_list.id)] if contact_list else [],
                'reply_to': self.env['ir.config_parameter'].get_param('main.mail'),
                'user_id': agent.id if agent else self.env.user.id,
                'email_from': self.env['ir.config_parameter'].get_param('main.mail'),
            })
            email_campaign.action_put_in_queue()
            email_campaign.action_send_mail_cron()
            return True
        except Exception as e:
            raise UserError(f"PDF үүсгэж чадсангүй: {e}")

        # email_campaign.with_context(mass_mailing_test_addresses=[test_email]).action_send_mail()
        # mail = self.env['mail.mail'].create({
        #     'subject': 'Gmobile төлбөрийн нэхэмжлэл',
        #     'body_html': '<p>Эрхэм хэрэглэгч танд энэ өдрийн мэнд хүргэе</p>',
        #     'email_to': self.env['ir.config_parameter'].get_param('customer.customer.mail'),
        #     'email_from': self.env['ir.config_parameter'].get_param('main.mail'),
        #     'attachment_ids': [(4, attachment.id)],
        # })
        # mail.send()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}',
            'target': 'new',
        }


    def get_image_base64(self,relative_path):
        path = get_module_resource('invoice_own', relative_path)
        if path and os.path.exists(path):
            with open(path, 'rb') as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        return False

