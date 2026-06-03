import logging

from odoo import api, fields, models
from odoo.exceptions import UserError
import psycopg2
import base64
import pdfkit
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
                LIMIT 100
            """
            cursor.execute(query)
            results = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]

            vals_list = []
            for row in results:
                row_dict = dict(zip(columns, row))
                vals_list.append(row_dict)

            cursor.close()

            # --- UPSERT (CREATE OR UPDATE) ЛОГИК ЭНД ЭХЭЛНЭ ---
            if vals_list:
                for vals in vals_list:
                    # Давтагдахгүй байх түлхүүр: acc_number болон bylling_cycle_id хоёроор хайж шалгана
                    existing_record = self.search([
                        ('acc_number', '=', vals['acc_number']),
                        ('bylling_cycle_id', '=', vals['bylling_cycle_id'])
                    ], limit=1)

                    if existing_record:
                        # Хэрэв өгөгдлийн санд байвал write() ашиглан шинэчилнэ (Update)
                        existing_record.write(vals)
                    else:
                        # Байхгүй бол шинээр үүсгэнэ (Create)
                        self.create(vals)

        except psycopg2.Error as e:
            raise UserError(f"Гадаад өгөгдлийн сантай холбогдоход алдаа гарлаа: {e}")
        finally:
            if conn:
                conn.close()

        # Амжилттай болсны дараа Odoo-гийн хуудсыг автоматаар шинэчилнэ (Refresh)
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def execution_something(self):
        _logger.info("Clicked")
        logo_b64 = self.get_image_base64('static/src/img/logo.png')

        html_content = self.env['ir.qweb']._render(
            'invoice_own.pdfbody',
            {'logo_b64 ': logo_b64}
        )

        if isinstance(html_content, bytes):
            html_content = html_content.decode('utf-8')

        # [ЗАСВАР 1]: from_file биш from_string ашиглах ёстой
        # [ЗАСВАР 2]: Монгол үсэг алдаагүй гаргахын тулд encoding тохируулна
        options = {
            'encoding': "UTF-8",
            'enable-local-file-access': None,
            'load-error-handling': 'ignore',
            'load-media-error-handling': 'ignore',
            'exit-status-to-ignore': '1',
        }

        try:
            pdf_content = pdfkit.from_string(html_content, False, options=options)
        except Exception as e:
            _logger.warning("PDFKit үүсгэх явцад анхааруулга гарлаа: %s", str(e))
            # Хэрэв ямар нэгэн байдлаар гацвал pdf_content үүссэн эсэхийг баталгаажуулах
            if 'pdf_content' not in locals():
                raise IOError(f"PDF файл үүсгэж чадсангүй: {e}")

        attachment = self.env['ir.attachment'].sudo().create({
            'name': 'invoice.pdf',
            'type': 'binary',
            'datas': base64.b64encode(pdf_content).decode('utf-8'),
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/pdf',
        })

        # email_campaign = self.env['mailing.mailing'].sudo().create({
        #     'name': 'Тест Нэхэмжлэх Захидал',
        #     'subject': 'Таны нэхэмжлэх бэлэн боллоо (Тест)',
        #     'body_html': html_content,
        #     'mailing_type': 'mail',
        #     'attachment_ids': [(4, attachment.id)],
        #     'mailing_model_id': self.env.ref('mass_mailing.model_mailing_contact').id,
        #     'reply_to': self.env.company.email or test_email,
        # })
        # email_campaign.with_context(mass_mailing_test_addresses=[test_email]).action_send_mail()
        mail = self.env['mail.mail'].create({
            'subject': 'Gmobile төлбөрийн нэхэмжлэл',
            'email_to': self.env['ir.config_parameter'].get_param('customer.customer.mail'),
            'email_from': self.env['ir.config_parameter'].get_param('main.mail'),
            'body_html': html_content,
            'attachment_ids': [(4, attachment.id)],
        })
        mail.send()
        _logger.info("********** Executed without error *********", exc_info=True)
        return {
            'type': 'ir.actions.act_url',
            # 'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new',
        }

    def get_image_base64(self,relative_path):
        path = get_module_resource('invoice_own', relative_path)
        if path and os.path.exists(path):
            with open(path, 'rb') as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        return False

