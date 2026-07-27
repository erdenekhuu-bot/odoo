import psycopg2
from psycopg2.extras import RealDictCursor
from odoo import api, fields, models
from odoo.exceptions import UserError
import base64
from datetime import date, datetime
from odoo.tools import file_open
import logging

_logger = logging.getLogger(__name__)

selected_types = [
    'LOCAL_CALL', 'OTHER_NET_CALL', 'SPECIAL_CALL',
    'SMS_OWN', 'SMS_OTHER', 'INTERNET_USAGE_FEE',
    'EXTRA_DATA_FEE', 'OTHER_USAGE', 'CALLKEEPER', 'GTONE'
]

new_label = {
    'LOCAL_CALL': 'Сүлжээн дэх яриа',
    'OTHER_NET_CALL': 'Бусад сүлжээн дэх яриа',
    'SPECIAL_CALL': 'Тусгай дугаарын яриа',
    'SMS_OWN': 'Сүлжээн дэх мессеж',
    'SMS_OTHER': 'Бусад сүлжээн дэх мессеж',
    'INTERNET_USAGE_FEE': 'Дата',
    'EXTRA_DATA_FEE': 'Нэмэлт дата багц',
    'OTHER_USAGE': 'Бусад хэрэглээ',
    'CALLKEEPER': 'Дуудлага хадгалах үйлчилгээ',
    'GTONE': 'Gtone үйлчилгээ',
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
    email_title = fields.Char(string='Email Title', default="")

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
                an.subs_id, an.acct_id, an.acc_number, an.cust_name, an.email,
                b.bill_id, b.period_start, b.period_end, b.state, b.total_amount,
                p.package_name, p.data_limit, p.data_nemelt, p.sms_limit,
                p.own_network_limit, p.other_call_limit, p.all_call_limit,
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
                an.subs_id, an.acct_id, an.acc_number, an.cust_name, an.email,
                b.bill_id, b.period_start, b.period_end, b.state, b.total_amount,
                p.package_name, p.data_limit, p.data_nemelt, p.sms_limit,
                p.own_network_limit, p.other_call_limit, p.all_call_limit;
        """

        connection = None
        try:
            connection = self._get_connection()
            with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(sql_query, (acc_numbers, period_starts))
                existing_records = self.sudo().search([('bill_id', '!=', False)])
                existing_map = {rec.bill_id: rec for rec in existing_records}

                created_count = 0
                updated_count = 0
                batch_size = 500

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
                        }

                        if b_id in existing_map:
                            existing_map[b_id].write(vals)
                            updated_count += 1
                        else:
                            to_create_vals.append(vals)
                            created_count += 1

                    if to_create_vals:
                        new_recs = self.sudo().create(to_create_vals)
                        for rec in new_recs:
                            existing_map[rec.bill_id] = rec

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
        billing = self.env['billing.period'].search([
            ('acc_number_id', '=', account.id)],
            limit=1
        )
        bills = self.env['billing.read'].search([('acc_number', '=', self.acc_number), ('period_start', '=', billing.period_start)], limit=1)
        head_data = self.generate_head_data([bills.own_network_limit, bills.other_call_limit, bills.all_call_limit, bills.data_limit, bills.sms_limit], tagged_types)
        data = self.filter_items(bills.bill_items or [], selected_types, new_label)
        date_obj = datetime.strptime(self.period_start, '%Y-%m-%d')
        year = date_obj.year
        month = date_obj.month
        total_amount = bills.total_amount
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

    def filter_items(self, data: list[dict], item_types: list[str], labels: dict[str, str]) -> list[dict]:
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

    def generate_head_data(self, params: list[str], tag: list[str]) -> list[dict]:
        return [
            {
                'name': t,
                'description': '' if p is False else p,
                'amount': 0,
            }
            for p, t in zip(params, tag)
        ]

    def _generate_pdf_attachment_for_account(self, acc_number):
        """
        click_btn() функцтэй ижил өгөгдлөөр PDF үүсгэж,
        ir.attachment record буцаана.
        """

        acc_number = str(acc_number).strip()

        # 1. Account мэдээлэл
        account = self.env["billing.read.account"].sudo().search(
            [("acc_number", "=", acc_number)],
            limit=1,
        )
        if not account:
            _logger.warning(
                "billing.read.account олдсонгүй: acc_number=%s",
                acc_number,
            )
            return False

        # 2. Тухайн account-ийн хамгийн сүүлийн billing period
        billing = self.env["billing.period"].sudo().search(
            [("acc_number_id", "=", account.id)],
            order="period_start desc",limit=1)

        if not billing:
            _logger.warning(
                "billing.period олдсонгүй: acc_number=%s account_id=%s",
                acc_number,
                account.id,
            )
            return False
        today = fields.Date.context_today(self)
        current_period_start = "2026-06-01"
        # 3. Billing read record
        bills = self.sudo().search(
            [
                ("acc_number", "=", acc_number),
                ("period_start", "=", current_period_start),
            ],
            limit=1,
        )

        if not bills:
            _logger.warning(
                "billing.read олдсонгүй: acc_number=%s period_start=%s",
                acc_number,
                billing.period_start,
            )
            return False

        # 4. Report data
        head_data = self.generate_head_data(
            [
                bills.own_network_limit,
                bills.other_call_limit,
                bills.all_call_limit,
                bills.data_limit,
                bills.sms_limit,
            ],
            tagged_types,
        )

        data = self.filter_items(
            bills.bill_items or [],
            selected_types,
            new_label,
        )

        try:
            date_obj = datetime.strptime(
                bills.period_start,
                "%Y-%m-%d",
            )
        except (ValueError, TypeError):
            _logger.exception(
                "period_start формат буруу: billing_read_id=%s value=%s",
                bills.id,
                bills.period_start,
            )
            return False

        year = date_obj.year
        month = date_obj.month

        context_data = {
            "logo_b64": self.get_image_base64(
                "static/img/logo.png"
            ),
            "app_b64": self.get_image_base64(
                "static/img/appstoreqr.png"
            ),
            "qr_b64": self.get_image_base64(
                "static/img/playstoreqr.png"
            ),
            "screen1_b64": self.get_image_base64(
                "static/img/whitescreen.png"
            ),
            "screen2_b64": self.get_image_base64(
                "static/img/whitescreen2.png"
            ),
            "screen3_b64": self.get_image_base64(
                "static/img/whitescreen3.png"
            ),
            "datetimes": f"{year} ОНЫ {month}",
            "profile": account,
            "date_create": (
                f"{billing.period_start.replace('-', '/')}-"
                f"{billing.period_end.replace('-', '/')}"
            ),
            "period_start": billing.period_start.replace("-", "/"),
            "period_end": billing.period_end.replace("-", "/"),
            "head_data": head_data,
            "data": data,
            "total_amount": bills.total_amount,
        }

        try:
            pdf_content, _ = (
                self.env["ir.actions.report"]
                .sudo()
                .with_context(**context_data)
                ._render_qweb_pdf(
                    "business_company.final_report_pdf",
                    res_ids=[bills.id],
                )
            )
        except Exception:
            _logger.exception(
                "PDF render хийхэд алдаа гарлаа: "
                "acc_number=%s billing_read_id=%s",
                acc_number,
                bills.id,
            )
            return False

        if not pdf_content:
            _logger.error(
                "PDF content хоосон байна: acc_number=%s",
                acc_number,
            )
            return False

        # 5. Attachment үүсгэх
        attachment = self.env["ir.attachment"].sudo().create({
            "name": (
                f"Billing_{acc_number}_"
                f"{billing.period_start}.pdf"
            ),
            "type": "binary",
            "datas": base64.b64encode(pdf_content).decode("utf-8"),
            "res_model": "billing.read",
            "res_id": bills.id,
            "mimetype": "application/pdf",
            "public": False,
        })

        _logger.info(
            "PDF attachment үүслээ: "
            "attachment_id=%s acc_number=%s size=%s",
            attachment.id,
            acc_number,
            len(pdf_content),
        )

        return attachment

    def _email_campaign_bills(self, limit=None):
        config = self.env["ir.config_parameter"].sudo()
        MailingList = self.env["mailing.list"].sudo()
        MailingContact = self.env["mailing.contact"].sudo()
        MailingMailing = self.env["mailing.mailing"].sudo()
        BillingGroup = self.env["billing.group"].sudo()
        BillingRead = self.env["billing.read"].sudo()

        agent = self.env["res.users"].sudo().search(
            [("login", "=", "bot@gmobile.mn")],
            limit=1,
        )
        agent_user_id = agent.id

        mailing_list = MailingList.search([("name", "=", "Billing Customers Group")],limit=1)
        if not mailing_list:
            mailing_list = MailingList.create({
                "name": "Billing Customers Group",
                "is_public": False,
            })
        billing_reads = BillingRead.search(
            [],
            limit=1
        )

        created_mailings = 0
        skipped_count = 0

        for billing_rec in billing_reads:
            try:
                with self.env.cr.savepoint():
                    acc_number = (billing_rec.acc_number or "").strip()
                    year = billing_rec.period_start[:4]
                    month =billing_rec.period_start[5:7]

                    if not acc_number:
                        skipped_count += 1
                        _logger.warning(
                            "billing.read дээр acc_number хоосон: ID=%s",
                            billing_rec.id,
                        )
                        continue

                    # Тухайн account-ийн email-ийг billing.group-оос олно
                    group = BillingGroup.search([],limit=1)
                    if not group:
                        skipped_count += 1

                        _logger.warning(
                            "billing.group олдсонгүй: "
                            "billing_read_id=%s, acc_number=%s",
                            billing_rec.id,
                            acc_number,
                        )
                        continue

                    email = (group.name or "").strip().lower()
                    if not email or "@" not in email:
                        skipped_count += 1

                        _logger.warning(
                            "Email буруу байна: "
                            "group_id=%s, email=%s, acc_number=%s",
                            group.id,
                            email,
                            acc_number,
                        )
                        continue

                    contact = MailingContact.search(
                        [("email", "=ilike", email)],
                        limit=1,
                    )

                    if not contact:
                        contact = MailingContact.create({
                            "name": email,
                            "email": email,
                            "list_ids": [(4, mailing_list.id)],
                        })

                    elif mailing_list not in contact.list_ids:
                        contact.write({
                            "list_ids": [(4, mailing_list.id)]
                        })

                    attachment = (
                        self._generate_pdf_attachment_for_account(
                            acc_number
                        )
                    )

                    if not attachment:
                        skipped_count += 1

                        _logger.warning(
                            "PDF attachment үүссэнгүй: "
                            "billing_read_id=%s, acc_number=%s",
                            billing_rec.id,
                            acc_number,
                        )
                        continue
                    mailing = MailingMailing.create({
                        "subject": f"{config.get_param("mail.subject")}",
                        "body_html": (
                            f"<p>Таны {acc_number} дараа төлбөрт дугаарын {year} оны {month}-р сарын төлбөрийн нэхэмжлэхийг хавсралтаар илгээж байна нэхэмжлэл хавсралтаар очиж байна.</p>"
                        ),
                        "mailing_type": "mail",
                        "user_id": agent_user_id,
                        "mailing_model_id": (
                            self.env["ir.model"]._get_id(
                                "mailing.contact"
                            )
                        ),
                        "mailing_domain": repr([
                            ("id", "=", contact.id)
                        ]),
                        "attachment_ids": [
                            (4, attachment.id)
                        ],
                    })

                    mailing.action_put_in_queue()

                    created_mailings += 1

                    _logger.info(
                        "Mailing үүслээ: "
                        "mailing_id=%s, billing_read_id=%s, "
                        "email=%s, acc_number=%s",
                        mailing.id,
                        billing_rec.id,
                        email,
                        acc_number,
                    )

            except Exception:
                skipped_count += 1

                _logger.exception(
                    "Mailing боловсруулахад алдаа гарлаа: "
                    "billing_read_id=%s, acc_number=%s",
                    billing_rec.id,
                    billing_rec.acc_number,
                )

        return created_mailings, skipped_count

    def action_test_email_campaign_bills(self):
        created, skipped = self._email_campaign_bills(limit=1)

        if created:
            message = (
                f"{created} mailing амжилттай үүсэж queue-д орлоо."
            )
            notification_type = "success"
        else:
            message = (
                f"Mailing үүссэнгүй. Алгассан: {skipped}. "
                "Odoo log-ийг шалгана уу."
            )
            notification_type = "warning"

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Billing mailing test",
                "message": message,
                "type": notification_type,
                "sticky": True,
            },
        }


    def initiate_action_campaign_bills(self):
        created, skipped = self._email_campaign_bills()
        if created:
            message = (
                f"{created} mailing амжилттай үүсэж queue-д орлоо."
            )
            notification_type = "success"
        else:
            message = (
                f"Mailing үүссэнгүй. Алгассан: {skipped}. "
                "Odoo log-ийг шалгана уу."
            )
            notification_type = "warning"

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Billing mailing test",
                "message": message,
                "type": notification_type,
                "sticky": True,
            },
        }
