from odoo import api, fields, models
import psycopg2
import logging
import threading
from weasyprint import HTML
import datetime
import base64

_logger = logging.getLogger(__name__)

class GenerateInvoice(models.AbstractModel):
    _name = 'generate.invoice'

    ITEM_TYPE_NAMES = {
        'LOCAL_CALL': 'Сүлжээдээ ярих',
        'OTHER_NET_CALL': 'Бусад сүлжээнд ярих',
        'SPECIAL_CALL': 'Тусгай дугаарын яриа',
        'SMS_OWN': 'Сүлжээн дахь мессеж',
        'SMS_OTHER': 'Бусад сүлжээн дахь мессеж',
        'OTHER_USAGE': 'Бусад хэрэглээ',
        'CALLKEEPER': 'Дуудлага хадгалах үйлчилгээ',
        'GTONE': 'Gtone үйлчилгээ'
    }

    @api.model
    def read_base(self):
        conn = psycopg2.connect(
            dbname=self.env['ir.config_parameter'].get_param("second.base"),
            user=self.env['ir.config_parameter'].get_param("second.dbuser"),
            password=self.env["ir.config_parameter"].get_param("second.dbpassword"),
            host=self.env["ir.config_parameter"].get_param("second.dbhost"),
        )

        cursor = conn.cursor()
        query = """
               SELECT 
                    an.acc_number,
                    an.email,
                    b.billing_cycle_id,
                    b.period_start,
                    b.period_end,
                    an.email,
                    json_agg(
                        json_build_object(
                            'item_type', bi.item_type,
                            'amount', bi.amount
                        )
                    ) AS items
               FROM bill_item bi
               LEFT JOIN bill b ON bi.bill_id = b.id
               LEFT JOIN acc_number an ON b.acc_number_id = an.id
                    WHERE substr(an.acc_number, 1, 2) = '98' and an.acc_number='98100327'
            GROUP BY 
                an.acc_number,
                b.billing_cycle_id,
                b.period_start,
                b.period_end,
                an.email
            ORDER BY an.acc_number
            LIMIT 1
            """
        cursor.execute(query)
        results = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]

        data=[]
        for row in results:
            row_dict = dict(zip(columns, row))
            acc_number = row_dict.get('acc_number')

            for f in row_dict.get('items', []):
                f['item_type'] = self.ITEM_TYPE_NAMES.get(f['item_type'], '')

            contact_result = self.create_mailing_contact(data=row_dict)

            mailing_id = False

            if contact_result:
                mailing_id = self.create_mailing(
                    contact_result["contact_id"],
                    contact_result["attachment_id"]
                )

            data.append({
                'email': row_dict.get('email'),
                'acc_number': acc_number,
                'items': row_dict.get('items', []),
                'contact_result': contact_result,
                'mailing_id': mailing_id,
            })

        cursor.close()
        conn.close()
        _logger.info("Query Ended")
        return data

    @api.model
    def create_mailing_contact(self, data: dict):
        acc_number = data.get('acc_number')
        email = data.get('email')
        invoice_date = datetime.date.today().strftime("%Y/%m/%d")

        if not email:
            return False

        partner = self.env['res.partner'].sudo().search([
            '|',
            ('email', '=', email),
            ('complete_name', '=', acc_number),
        ], limit=1)

        if not partner:
            return False

        html_content = self.env['ir.qweb']._render(
            'invoice_own.extendedbdftemplate',
            {
                "invoices": [data],
                "invoice_date": invoice_date,
            }
        )

        if isinstance(html_content, bytes):
            html_content = html_content.decode('utf-8')

        pdf_content = HTML(string=html_content).write_pdf()

        attachment = self.env['ir.attachment'].sudo().create({
            'name': f'invoice_{acc_number}.pdf',
            'type': 'binary',
            'datas': base64.b64encode(pdf_content),
            'mimetype': 'application/pdf',
        })

        contact = self.env['mailing.contact'].sudo().search([
            ('email', '=', email)
        ], limit=1)

        if not contact:
            contact = self.env['mailing.contact'].sudo().create({
                'name': partner.complete_name or partner.name or acc_number,
                'email': email,
            })

        return {
            "contact_id": contact.id,
            "attachment_id": attachment.id,
        }

    @api.model
    def create_mailing(self, contact_id, attachment_id):
        contact = self.env['mailing.contact'].sudo().browse(contact_id).exists()
        attachment = self.env['ir.attachment'].sudo().browse(attachment_id).exists()
        agent = self.env['res.users'].search([('login', '=', 'bot@gmobile.mn')], limit=1)

        if not contact or not attachment:
            return False

        mailing_list = self.env['mailing.list'].sudo().search([
            ('name', '=', 'Invoice Customers')
        ], limit=1)

        if not mailing_list:
            mailing_list = self.env['mailing.list'].sudo().create({
                'name': 'Invoice Customers',
            })

        mailing_list.sudo().write({
            'contact_ids': [(4, contact.id)]
        })

        mailing = self.env['mailing.mailing'].sudo().create({
            'subject': 'Төлбөрийн мэдээлэл',
            'body_html': '<p>Эрхэм хэрэглэгч танд энэ өдрийн мэнд хүргэе</p>',
            'mailing_model_id': self.env.ref('mass_mailing.model_mailing_contact').id,
            'contact_list_ids': [(6, 0, [mailing_list.id])],
            'attachment_ids': [(4, attachment.id)],
            'user_id':agent.id,
            'email_from': self.env['ir.config_parameter'].get_param('main.mail'),
        })
        mailing.action_send_mail()
        _logger.info("Mail sent: %s",mailing.id)
        return True

