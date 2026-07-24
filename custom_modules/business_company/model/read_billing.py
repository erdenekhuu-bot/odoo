import psycopg2
from psycopg2.extras import RealDictCursor
from odoo import api, fields, models
from odoo.exceptions import UserError
import base64
from datetime import date,datetime
from odoo.tools import file_open
import logging

_logger = logging.getLogger(__name__)

selected_types = [
            'LOCAL_CALL',
            'OTHER_NET_CALL',
            'SPECIAL_CALL',
            'SMS_OWN',
            'SMS_OTHER',
            'INTERNET_USAGE_FEE',
            'EXTRA_DATA_FEE',
            'OTHER_USAGE',
            'CALLKEEPER',
            'GTONE'
    ]

new_label = {
    'LOCAL_CALL':'Сүлжээн дэх яриа',
    'OTHER_NET_CALL':'Бусад сүлжээн дэх яриа',
    'SPECIAL_CALL':'Тусгай дугаарын яриа',
    'SMS_OWN':'Сүлжээн дэх мессеж',
    'SMS_OTHER':'Бусад сүлжээн дэх мессеж',
    'INTERNET_USAGE_FEE':'Дата',
    'EXTRA_DATA_FEE':'Нэмэлт дата багц',
    'OTHER_USAGE':'Бусад хэрэглээ',
    'CALLKEEPER':'Дуудлага хадгалах үйлчилгээ',
    'GTONE':'Gtone үйлчилгээ',
}

tagged_types = [
    'Сүлжээдээ ярих',
    'Бусад сүлжээнд ярих',
    'Сүлжээ хоорондын яриа',
    'Дата',
    'Мессеж'
]

class ReadBilling(models.Model):
    _name = 'billing.read'
    _description = 'Read billing'

    acc_number = fields.Char(string='Account Number', required=True, index=True)
    bill_id = fields.Char(string='Bill ID', required=True, index=True)
    period_start = fields.Char(string='Period Start', required=True)
    period_end = fields.Char(string='Period End')
    state = fields.Char(string='State')
    total_amount = fields.Float(string='Total Amount')

    package_name = fields.Char(string='Package Name')
    data_limit = fields.Char(string='Data Limit')
    data_nemelt = fields.Char(string='Data Nemelt')
    sms_limit = fields.Char(string='SMS Limit')
    own_network_limit = fields.Char(string='Own Network Limit')
    other_call_limit = fields.Char(string='Other Call Limit')
    all_call_limit = fields.Char(string='All Call Limit')
    bill_items = fields.Json(string='Bill Items')
    email_title=fields.Char(string='Email Title',default="")

    def _get_connection(self):
        config = self.env["ir.config_parameter"].sudo()
        return psycopg2.connect(
            dbname=config.get_param("second.base"),
            user=config.get_param("second.dbuser"),
            password=config.get_param("second.dbpassword"),
            host=config.get_param("second.dbhost"),
            port=int(config.get_param("second.dbport", 5432)),
            connect_timeout=10,
        )

    @api.model
    def sync_billing_read(self):
        # 1. Odoo-д байгаа дансны дугаар болон хугацаануудыг авна
        accounts = self.env['billing.read.account'].sudo().search([('acc_number', '!=', False)])
        periods = self.env['billing.period'].sudo().search([('period_start', '!=', False)])

        acc_numbers = tuple(set(acc.acc_number for acc in accounts if acc.acc_number))
        period_starts = tuple(set(p.period_start for p in periods if p.period_start))

        if not acc_numbers or not period_starts:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Sync Notice",
                    "message": "billing.read.account эсвэл billing.period дээр шүүх дата олдсонгүй.",
                    "type": "warning",
                },
            }

        sql_query = """
            SELECT
                an.subs_id,
                an.acct_id,
                an.acc_number,
                an.cust_name,
                an.email,

                b.bill_id,
                b.period_start,
                b.period_end,
                b.state,
                b.total_amount,

                p.package_name,
                p.data_limit,
                p.data_nemelt,
                p.sms_limit,
                p.own_network_limit,
                p.other_call_limit,
                p.all_call_limit,

                json_agg(
                    json_build_object(
                        'item_group_type', bi.item_group_type,
                        'item_type', bi.item_type,
                        'limit', bi.limit,
                        'amount', bi.amount,
                        'charge', bi.charge,
                        'description', bi.description
                    )
                    ORDER BY bi.item_group_type, bi.item_type
                ) AS bill_items

            FROM acc_number an
            JOIN bill b ON b.acc_number_id = an.id
            JOIN bill_item bi ON bi.bill_id = b.id
            JOIN packages p ON an.acc_number::text = p.acc_number::text

            WHERE an.acc_number::text IN %s
              AND b.period_start::text IN %s

            GROUP BY
                an.subs_id,
                an.acct_id,
                an.acc_number,
                an.cust_name,
                an.email,
                b.bill_id,
                b.period_start,
                b.period_end,
                b.state,
                b.total_amount,
                p.package_name,
                p.data_limit,
                p.data_nemelt,
                p.sms_limit,
                p.own_network_limit,
                p.other_call_limit,
                p.all_call_limit;
        """

        connection = None
        try:
            connection = self._get_connection()
            with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(sql_query, (acc_numbers, period_starts))

                # Odoo-д байгаа одоогийн датаг Map болгох
                existing_records = self.sudo().search([('bill_id', '!=', False)])
                existing_map = {rec.bill_id: rec for rec in existing_records}

                created_count = 0
                updated_count = 0
                batch_size = 500  # 500 мөр тутамд санах ойг суллана (Flush)

                while True:
                    rows = cursor.fetchmany(batch_size)
                    if not rows:
                        break

                    to_create_vals = []

                    for row in rows:
                        raw_bill_id = row.get("bill_id")
                        if raw_bill_id is None or raw_bill_id == "":
                            continue

                        b_id = str(raw_bill_id)

                        vals = {
                            "acc_number": str(row["acc_number"]) if row.get("acc_number") is not None else False,
                            "bill_id": b_id,
                            "period_start": str(row["period_start"]) if row.get("period_start") is not None else False,
                            "period_end": str(row["period_end"]) if row.get("period_end") is not None else False,
                            "state": str(row["state"]) if row.get("state") is not None else False,
                            "total_amount": float(row["total_amount"]) if row.get("total_amount") is not None else 0.0,

                            "package_name": str(row["package_name"]) if row.get("package_name") is not None else False,
                            "data_limit": str(row["data_limit"]) if row.get("data_limit") is not None else False,
                            "data_nemelt": str(row["data_nemelt"]) if row.get("data_nemelt") is not None else False,
                            "sms_limit": str(row["sms_limit"]) if row.get("sms_limit") is not None else False,
                            "own_network_limit": str(row["own_network_limit"]) if row.get("own_network_limit") is not None else False,
                            "other_call_limit": str(row["other_call_limit"]) if row.get("other_call_limit") is not None else False,
                            "all_call_limit": str(row["all_call_limit"]) if row.get("all_call_limit") is not None else False,

                            "bill_items": row.get("bill_items") if row.get("bill_items") is not None else False,
                            "state":row.get("state") if row.get("state") is not None else False,
                        }

                        if b_id in existing_map:
                            existing_map[b_id].write(vals)
                            updated_count += 1
                        else:
                            to_create_vals.append(vals)
                            created_count += 1

                    # 500 тутамд Odoo санах ойд нэг дор хадгалах
                    if to_create_vals:
                        new_recs = self.sudo().create(to_create_vals)
                        # Шинэ үүссэн рекордуудыг map-д нэмэх
                        for rec in new_recs:
                            existing_map[rec.bill_id] = rec

                    # Cache арилгаж RAM-ийг суллах
                    self.env.invalidate_all()

            if created_count == 0 and updated_count == 0:
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": "Sync Notice",
                        "message": "Татах шаардлагатай нэхэмжлэх олдсонгүй.",
                        "type": "warning",
                    },
                }

            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Sync Completed",
                    "message": f"Амжилттай дууслаа: {created_count} шинээр үүсч, {updated_count} шинэчлэгдэв.",
                    "type": "success",
                },
            }

        except psycopg2.Error as error:
            raise UserError(f"PostgreSQL error:\n{str(error)}") from error

        finally:
            if connection:
                connection.close()

    def click_btn(self):
        self.ensure_one()
        account = self.env['billing.read.account'].search(
            [('acc_number', '=', self.acc_number)],
            limit=1
        )
        billing=self.env['billing.period'].search([
            ('acc_number_id', '=', account.id)],
            limit=1
        )
        bills=self.env['billing.read'].search([('acc_number', '=', self.acc_number),('period_start','=',billing.period_start)],limit=1)
        head_data=self.generate_head_data([bills.own_network_limit,bills.other_call_limit,bills.all_call_limit,bills.data_limit,bills.sms_limit],tagged_types)
        data=self.filter_items(bills.bill_items or [],selected_types,new_label)
        date_obj = datetime.strptime(self.period_start, '%Y-%m-%d')
        year = date_obj.year
        month = date_obj.month
        total_amount=bills.total_amount
        pdf_content, _ = self.env['ir.actions.report'].sudo().with_context(
            {
                'logo_b64': self.get_image_base64('static/img/logo.png'),
                'app_b64': self.get_image_base64('static/img/appstoreqr.png'),
                'qr_b64': self.get_image_base64('static/img/playstoreqr.png'),
                'screen1_b64': self.get_image_base64('static/img/whitescreen.png'),
                'screen2_b64': self.get_image_base64('static/img/whitescreen2.png'),
                'screen3_b64': self.get_image_base64('static/img/whitescreen3.png'),
                'datetimes': f"{year} ОНЫ {month}",
                'profile': account,
                'date_create': f"{billing.period_start.replace('-', '/')}-{billing.period_end.replace('-', '/')}",
                'period_start': f"{billing.period_start.replace('-', '/')}",
                'period_end': f"{billing.period_end.replace('-', '/')}",
                'head_data': head_data,
                'data': data,
                'total_amount': total_amount,
            }
        )._render_qweb_pdf(
            'business_company.final_report_pdf',
            res_ids=self.ids
        )
        attachment = self.env['ir.attachment'].sudo().create({
            'name': 'invoice.pdf',
            'type': 'binary',
            'datas': base64.b64encode(pdf_content).decode('utf-8'),
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/pdf',
            'public': True,
        })


        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=false',
            'target': 'new',
        }

    def get_image_base64(self, relative_path):
        resource_path = f"business_company/{relative_path}"
        try:
            with file_open(resource_path, 'rb') as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except FileNotFoundError:
            return False

    def filter_items(self,data: list[dict],item_types: list[str],labels: dict[str, str]) -> list[dict]:
        return [
            {
                **item,
                'item_type_code': item.get('item_type'),
                'item_type': labels.get(
                    item.get('item_type'),
                    item.get('item_type', '')
                ),
            }
            for item in data
            if item.get('item_type') in item_types
        ]

    def generate_head_data(self, params: list[str],tag:list[str]) -> list[dict]:
        return [
            {
                'name': t,
                'description': '' if p==False else p,
                'amount': 0,
            }
            for p,t in zip(params, tag)
        ]

    def email_campaign_bills(self):
        agent=self.env['res.users'].search([('login', '=', 'bot@gmobile.mn')])
        billing_list=self.env['billing.read'].search([],limit=10)
        mail_group = self.env['billing.group'].search([])
        mailing_list = self.env["mailing.list"].sudo().search(
            [("name", "=", "Billing Group")],
            limit=1,
        )
        if not mailing_list:
            mailing_list = self.env["mailing.list"].sudo().create({
                "name": "Billing Customers",
                "is_public": False,
            })

        return True

    def generate_qweb(self,id):
        return True

    @api.model
    def signToSent(self):
        return True

    @api.model
    def email_campaign_bills(self):
        """ Scheduled action-аар дуудагдаж, хэрэглэгч бүрт PDF нэхэмжлэл бүхий Email Mailing илгээнэ """

        MailingList = self.env["mailing.list"].sudo()
        MailingContact = self.env["mailing.contact"].sudo()
        MailingMailing = self.env["mailing.mailing"].sudo()
        BillingGroup = self.env["billing.group"].sudo()

        # 1. Mailing List сонгох эсвэл шинээр үүсгэх
        list_name = "Billing Customers"
        mailing_list = MailingList.search([("name", "=", list_name)], limit=1)
        if not mailing_list:
            mailing_list = MailingList.create({
                "name": list_name,
                "is_public": False,
            })

        # 2. Идэвхтэй billing.group бичлэгүүдийг авах
        mail_groups = BillingGroup.search([("name", "!=", False)])

        created_mailings = 0
        skipped_count = 0

        for group in mail_groups:
            email = (group.name or "").strip().lower()
            acc_number = group.acc_number

            # Email форматыг энгийнээр шалгах
            if not email or "@" not in email or not acc_number:
                skipped_count += 1
                _logger.warning("Хүчингүй email эсвэл acc_number skipped: ID=%s, Name=%s", group.id, group.name)
                continue

            # 3. Mailing Contact үүсгэх/холбох
            contact = MailingContact.search([("email", "=ilike", email)], limit=1)
            if not contact:
                contact = MailingContact.create({
                    "name": email,
                    "email": email,
                    "list_ids": [(4, mailing_list.id)],
                })
            elif mailing_list not in contact.list_ids:
                contact.write({"list_ids": [(4, mailing_list.id)]})

            # 4. Тухайн Account-д зориулсан PDF тайлан үүсгэх
            try:
                attachment = self._generate_pdf_attachment_for_account(acc_number)
            except Exception as e:
                _logger.error("PDF үүсгэхэд алдаа гарлаа (acc_number: %s): %s", acc_number, str(e))
                continue

            if not attachment:
                _logger.warning("Биллингийн мэдээлэл олдсонгүй (acc_number: %s)", acc_number)
                continue

            # 5. Тухайн хэрэглэгчид зориулсан бие даасан mailing.mailing үүсгэх
            # Odoo 18 дээр mail_state/state талбаруудыг тохируулж байна
            mailing = MailingMailing.create({
                'subject': f'Нэхэмжлэлийн мэдээлэл - Данс: {acc_number}',
                'body_html': f'<p>Сайн байна уу,</p><p>Таны дансны ({acc_number}) сарын нэхэмжлэл хавсралтаар очиж байна.</p>',
                'mailing_type': 'mail',
                'mailing_model_id': self.env['ir.model']._get_id('mailing.contact'),
                'mailing_domain': [('id', '=', contact.id)],  # Зөвхөн энэ контактад илгээнэ
                'attachment_ids': [(4, attachment.id)],  # PDF-ийг хавсаргах
            })

            # 6. Имэйлийг шууд одоо илгээх рүү шилжүүлэх
            mailing.action_put_in_queue()
            # Оруулсан даруйд нь шууд замын имэйлүүдийг илгээх
            mailing.action_send_mail()

            created_mailings += 1

        _logger.info("Cron биллоос Имэйл кампанит ажил амжилттай дууслаа: Илгээсэн=%s, Алгассан=%s", created_mailings,
                     skipped_count)
        return True

    def _generate_pdf_attachment_for_account(self, acc_number):
        """ Дансны дугаараар нэхэмжлэлийн PDF файл бэлтгэж attachment үүсгэх туслах функц """
        account = self.env['billing.read.account'].search([('acc_number', '=', acc_number)], limit=1)
        if not account:
            return False

        billing = self.env['billing.period'].search([('acc_number_id', '=', account.id)], limit=1)
        if not billing:
            return False

        bills = self.search([
            ('acc_number', '=', acc_number),
            ('period_start', '=', billing.period_start)
        ], limit=1)

        if not bills:
            return False

        # Тэгшитгэсэн төрлүүдийн тохиргоо (Шаардлагатай тогтмолуудаа тодорхойлно уу)
        tagged_types = {}
        selected_types = []
        new_label = ""

        head_data = self.generate_head_data(
            [bills.own_network_limit, bills.other_call_limit, bills.all_call_limit, bills.data_limit, bills.sms_limit],
            tagged_types
        )
        data = self.filter_items(bills.bill_items or [], selected_types, new_label)

        date_obj = datetime.strptime(bills.period_start, '%Y-%m-%d')
        year = date_obj.year
        month = date_obj.month

        # QWeb-ээр PDF-ийг render хийх
        pdf_content, _ = self.env['ir.actions.report'].sudo().with_context(
            {
                'logo_b64': self.get_image_base64('static/img/logo.png'),
                'app_b64': self.get_image_base64('static/img/appstoreqr.png'),
                'qr_b64': self.get_image_base64('static/img/playstoreqr.png'),
                'screen1_b64': self.get_image_base64('static/img/whitescreen.png'),
                'screen2_b64': self.get_image_base64('static/img/whitescreen2.png'),
                'screen3_b64': self.get_image_base64('static/img/whitescreen3.png'),
                'datetimes': f"{year} ОНЫ {month}",
                'profile': account,
                'date_create': f"{billing.period_start.replace('-', '/')}-{billing.period_end.replace('-', '/')}",
                'period_start': f"{billing.period_start.replace('-', '/')}",
                'period_end': f"{billing.period_end.replace('-', '/')}",
                'head_data': head_data,
                'data': data,
                'total_amount': bills.total_amount,
            }
        )._render_qweb_pdf(
            'business_company.final_report_pdf',
            res_ids=bills.ids
        )

        # Файлыг ir.attachment болгон хадгалах
        attachment = self.env['ir.attachment'].sudo().create({
            'name': f'invoice_{acc_number}.pdf',
            'type': 'binary',
            'datas': base64.b64encode(pdf_content).decode('utf-8'),
            'res_model': 'billing.read',
            'res_id': bills.id,
            'mimetype': 'application/pdf',
            'public': True,
        })

        return attachment

