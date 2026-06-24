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

    acc_number = fields.Char('Account Number', required=True)
    email = fields.Char('Email', required=True)
    bylling_cycle_id = fields.Char('Billing Cycle ID', required=True)
    period_start = fields.Date('Period Start', required=True)
    period_end = fields.Date('Period End', required=True)
    items = fields.Json('Items', required=True)
    state = fields.Char('State', required=False)
    subject_title=fields.Char('Subject Title', required=False)

    _sql_constraints = [
        (
            'billing_read_unique_acc_cycle',
            'unique(acc_number, bylling_cycle_id)',
            'Энэ хэрэглэгчийн тухайн billing cycle аль хэдийн бүртгэгдсэн байна!'
        )
    ]

    @api.model
    def sync_billing(self):
        config = self.env['ir.config_parameter'].sudo()

        db_name = config.get_param("second.base")
        db_user = config.get_param("second.dbuser")
        db_pass = config.get_param("second.dbpassword")
        db_host = config.get_param("second.dbhost")
        db_port = config.get_param("second.dbport") or 5432

        if not all([db_name, db_user, db_pass, db_host]):
            raise UserError("Өгөгдлийн сангийн холболтын параметрүүд дутуу тохируулагдсан байна!")

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

        conn = None

        try:
            _logger.warning("Sync initiated ...")

            conn = psycopg2.connect(
                dbname=db_name,
                user=db_user,
                password=db_pass,
                host=db_host,
                port=db_port,
                connect_timeout=10,
            )

            with conn.cursor() as cursor:
                cursor.execute(query)
                results = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]

        except psycopg2.Error as e:
            raise UserError(f"Гадаад өгөгдлийн сантай холбогдох эсвэл query ажиллуулах үед алдаа гарлаа: {e}")

        finally:
            if conn:
                conn.close()

        vals_list = []

        for row in results:
            vals = dict(zip(columns, row))

            vals['acc_number'] = str(vals['acc_number']) if vals.get('acc_number') else False
            vals['bylling_cycle_id'] = str(vals['bylling_cycle_id']) if vals.get('bylling_cycle_id') else False

            vals_list.append(vals)

        if not vals_list:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Sync',
                    'message': 'Татах өгөгдөл олдсонгүй.',
                    'type': 'warning',
                    'sticky': False,
                }
            }

        acc_numbers = list(set(v['acc_number'] for v in vals_list if v['acc_number']))
        cycle_ids = list(set(v['bylling_cycle_id'] for v in vals_list if v['bylling_cycle_id']))

        existing_records = self.search([
            ('acc_number', 'in', acc_numbers),
            ('bylling_cycle_id', 'in', cycle_ids),
        ])

        existing_map = {
            (rec.acc_number, rec.bylling_cycle_id): rec
            for rec in existing_records
        }

        created_count = 0
        updated_count = 0

        for vals in vals_list:
            key = (vals['acc_number'], vals['bylling_cycle_id'])
            record = existing_map.get(key)

            if record:
                record.write(vals)
                updated_count += 1
            else:
                new_record = self.create(vals)
                existing_map[key] = new_record
                created_count += 1

        _logger.warning(
            "Sync ended. Created: %s, Updated: %s",
            created_count,
            updated_count
        )

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Sync амжилттай',
                'message': f'Шинээр үүссэн: {created_count}, шинэчлэгдсэн: {updated_count}',
                'type': 'success',
                'sticky': False,
            }
        }

    def execution_something(self):
        try:
            self.ensure_one()
            logo_b64 = self.get_image_base64('static/src/img/logo.png')
            app_b64 = self.get_image_base64('static/src/img/appstoreqr.png')
            qr_b64 = self.get_image_base64('static/src/img/playstoreqr.png')
            screen1_b64 = self.get_image_base64('static/src/img/whitescreen.png')
            screen2_b64 = self.get_image_base64('static/src/img/whitescreen2.png')
            screen3_b64 = self.get_image_base64('static/src/img/whitescreen3.png')

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
            agent = self.env['res.users'].search([('login', '=', 'bot@gmobile.mn')], limit=1)
            contact_list = self.env['mailing.list'].search([], limit=1)
            mail = self.env['mail.mail'].create({
                'subject': 'Gmobile төлбөрийн нэхэмжлэл',
                'body_html': '<p>Эрхэм хэрэглэгч танд энэ өдрийн мэнд хүргэе</p>',
                'email_to': self.env['ir.config_parameter'].get_param('customer.customer.mail'),
                'email_from': self.env['ir.config_parameter'].get_param('main.mail'),
                'attachment_ids': [(4, attachment.id)],

            })
            mail.send()
            return {
                'type': 'ir.actions.act_url',
                'url': f'/web/content/{attachment.id}',
                'target': 'new',
            }
        except Exception as e:
            _logger.error("Failed to execute execution: %s", e)
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

    @api.model
    def email_campaign_billing(self):
        # Зөвхөн эдгээр email рүү илгээнэ
        target_emails = [
            'erdenekhuu.e@gmobile.mn',
            # 'second.person@gmobile.mn',
            # 'third.person@gmobile.mn',
        ]

        MailingContact = self.env['mailing.contact'].sudo()
        contacts = MailingContact.browse()

        missing_emails = []

        # Email бүрээс зөвхөн нэг contact сонгоно
        for email in target_emails:
            contact = MailingContact.search([
                ('email', '=ilike', email.strip()),
                ('is_blacklisted', '=', False),
            ], limit=1)

            if contact:
                contacts |= contact
            else:
                missing_emails.append(email)

        if missing_emails:
            raise UserError(
                'Дараах email хаягтай Mailing Contact олдсонгүй '
                'эсвэл blacklist-д байна:\n%s'
                % '\n'.join(missing_emails)
            )

        if not contacts:
            raise UserError('Илгээх Mailing Contact сонгогдоогүй байна.')

        agent = self.env['res.users'].sudo().search([
            ('login', '=', 'bot@gmobile.mn')
        ], limit=1)

        # Recipient model: mailing.contact
        mailing_model = self.env['ir.model']._get('mailing.contact')

        # Өмнө queue-д орсон эсвэл илгээгдсэн record-ийг дахин сонгохгүй
        billing = self.search([
            ('state', 'not in', ['queued', 'sent'])
        ], order='id desc', limit=1)

        if not billing:
            raise UserError(
                'PDF үүсгэх, илгээх боломжтой billing record олдсонгүй.'
            )

        logo_b64 = self.get_image_base64(
            'static/src/img/logo.png'
        )
        app_b64 = self.get_image_base64(
            'static/src/img/appstoreqr.png'
        )
        qr_b64 = self.get_image_base64(
            'static/src/img/playstoreqr.png'
        )
        screen1_b64 = self.get_image_base64(
            'static/src/img/whitescreen.png'
        )
        screen2_b64 = self.get_image_base64(
            'static/src/img/whitescreen2.png'
        )
        screen3_b64 = self.get_image_base64(
            'static/src/img/whitescreen3.png'
        )

        pdf_content, _ = (
            self.env['ir.actions.report']
            .sudo()
            .with_context(
                logo_b64=logo_b64,
                app_b64=app_b64,
                qr_b64=qr_b64,
                screen1_b64=screen1_b64,
                screen2_b64=screen2_b64,
                screen3_b64=screen3_b64,
            )
            ._render_qweb_pdf(
                'invoice_own.final_report_pdf',
                res_ids=billing.ids,
            )
        )

        attachment = self.env['ir.attachment'].sudo().create({
            'name': 'invoice.pdf',
            'type': 'binary',
            'datas': base64.b64encode(
                pdf_content
            ).decode('utf-8'),
            'res_model': billing._name,
            'res_id': billing.id,
            'mimetype': 'application/pdf',
        })

        mailing_campaign = self.env[
            'mailing.mailing'
        ].sudo().create({
            'name': 'Billing sent',

            'subject': (
                    billing.subject_title
                    or 'Gmobile төлбөрийн нэхэмжлэл'
            ),

            'mailing_model_id': mailing_model.id,

            # Зөвхөн дээр сонгосон contact record-ууд
            'mailing_domain': repr([
                ('id', 'in', contacts.ids),
                ('is_blacklisted', '=', False),
            ]),

            'body_html': """
                <p>Сайн байна уу?</p>
                <p>
                    Төлбөрийн нэхэмжлэлийг хавсралтаар
                    хүргүүлж байна.
                </p>
            """,

            'user_id': agent.id or self.env.user.id,

            'attachment_ids': [
                (4, attachment.id)
            ],
        })

        # Нэг mailing.mailing record queue-д оруулна
        mailing_campaign.action_put_in_queue()

        # Cron дахин ажиллах үед ижил billing-ийг дахин илгээхгүй
        billing.write({
            'state': 'queued'
        })

        _logger.info(
            'Billing campaign queue-д орлоо. '
            'Campaign ID: %s, Contact IDs: %s, Emails: %s',
            mailing_campaign.id,
            contacts.ids,
            ', '.join(contacts.mapped('email')),
        )

        return True