import logging

from odoo import api, fields, models
from odoo.exceptions import UserError
import psycopg2
import requests
import base64
from weasyprint import HTML

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
    def create(self, vals):
        return super(ReadBilling, self).create(vals)

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
        html_content = self.env['ir.qweb']._render(
            'invoice_own.extendedbdftemplateattachment',

        )
        if isinstance(html_content, bytes):
            html_content = html_content.decode('utf-8')
        pdf_content = HTML(string=html_content).write_pdf()
        attachment = self.env['ir.attachment'].sudo().create({
            'name': f'invoice.pdf',
            'type': 'binary',
            'datas': base64.b64encode(pdf_content),
            'mimetype': 'application/pdf',
        })
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        download_url = f"/web/content/{attachment.id}?download=true"
        return {
            'type': 'ir.actions.act_url',
            'url': base_url + download_url,
            'target': 'new',
        }

