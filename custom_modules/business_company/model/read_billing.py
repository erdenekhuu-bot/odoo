import psycopg2
from dateutil.relativedelta import relativedelta
from psycopg2.extras import RealDictCursor
from odoo import api, fields, models
from odoo.exceptions import UserError
import base64
from datetime import datetime,date
from odoo.tools import file_open
import logging
import time
import calendar

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
        conn = psycopg2.connect(
            dbname=config.get_param("second.base"),
            user=config.get_param("second.dbuser"),
            password=config.get_param("second.dbpassword"),
            host=config.get_param("second.dbhost"),
            port=int(config.get_param("second.dbport", 5432)),
            connect_timeout=10,
        )
        with conn.cursor() as c:
            c.execute("SET statement_timeout = '300000';")
        conn.commit()
        return conn

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

    def click_btn(self):
        self.ensure_one()
        target_year = datetime.today().year
        target_month = datetime.today().month
        start_date = f"{target_year}-{target_month:02d}-01"
        last_day = calendar.monthrange(target_year, target_month)[1]
        end_date = f"{target_year}-{target_month:02d}-{last_day} 23:59:59"

        account=self.env['billing.read.account'].search([('acc_number', '=', self.acc_number)],limit=1)
        bills = self.env['billing.read'].search([
            ('acc_number', '=', self.acc_number),
            ('period_start', '=', self.period_start),
        ], limit=1)
        head_data = self.generate_head_data([bills.own_network_limit, bills.other_call_limit, bills.all_call_limit, bills.data_limit, bills.sms_limit], tagged_types)
        data = self.filter_items(bills.bill_items, selected_types, new_label)
        period_start=datetime.strptime(bills.period_start, '%Y-%m-%d').date()
        period_end=datetime.strptime(bills.period_end, '%Y-%m-%d').date()
        year = period_start.year
        month = period_start.month
        total_amount = bills.total_amount
        pdf_content, _ = self.env['ir.actions.report'].sudo().with_context(
            {
                'logo_b64': self.get_image_base64('static/img/logo.png'),
                'app_b64': self.get_image_base64('static/img/appstoreqr.png'),
                'qr_b64': self.get_image_base64('static/img/playstoreqr.png'),
                'screen1_b64': self.get_image_base64('static/img/whitescreen.png'),
                'screen2_b64': self.get_image_base64('static/img/whitescreen2.png'),
                'screen3_b64': self.get_image_base64('static/img/whitescreen3.png'),
                'datetimes': f"{year} ОНЫ {month}-Р",
                'profile': account,
                'date_create': f"{str(period_start).replace('-', '/')}-{str(period_end).replace('-', '/')}",
                'period_start': f"{str(period_start).replace('-', '/')}",
                'period_end': f"{str(period_end).replace('-', '/')}",
                'head_data': head_data,
                'data': data,
                'total_amount': total_amount,
            }
        )._render_qweb_pdf('business_company.final_report_pdf',res_ids=self.ids)

        # attachment = self.env['ir.attachment'].sudo().create({
        #     'name': 'invoice.pdf',
        #     'type': 'binary',
        #     'datas': base64.b64encode(pdf_content).decode('utf-8'),
        #     'res_model': self._name,
        #     'res_id': self.id,
        #     'mimetype': 'application/pdf',
        #     'public': True,
        # })
        attachment = self._generate_pdf_attachment_for_account(account.acc_number,'2026-06-01')

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=false',
            'target': 'new',
        }



    def _generate_pdf_attachment_for_account(self, acc_number,period_starts):
        target_year = datetime.today().year
        target_month = datetime.today().month
        start_date = f"{target_year}-{target_month:02d}-01"
        last_day = calendar.monthrange(target_year, target_month)[1]
        end_date = f"{target_year}-{target_month:02d}-{last_day} 23:59:59"
        account = self.env['billing.read.account'].search([('acc_number', '=', acc_number)], limit=1)
        _logger.info('account: %s', account)
        bills = self.env['billing.read'].search([
            ('acc_number', '=', acc_number),
            ('period_start', '=', period_starts),
        ], limit=1)
        _logger.info('bills: %s', bills)
        head_data = self.generate_head_data(
            [bills.own_network_limit, bills.other_call_limit, bills.all_call_limit, bills.data_limit, bills.sms_limit],
            tagged_types)
        data = self.filter_items(bills.bill_items, selected_types, new_label)
        period_start = datetime.strptime(bills.period_start, '%Y-%m-%d').date()
        period_end = datetime.strptime(bills.period_end, '%Y-%m-%d').date()
        year = period_start.year
        month = period_start.month
        total_amount = bills.total_amount

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
            "date_create": f"{str(period_start).replace('-', '/')}-{str(period_end).replace('-', '/')}",
            'period_start': f"{str(period_start).replace('-', '/')}",
            'period_end': f"{str(period_end).replace('-', '/')}",
            "head_data": head_data,
            "data": data,
            'total_amount': total_amount,
        }

        try:
            pdf_content, _ = (self.env["ir.actions.report"].sudo()
                .with_context(**context_data)
                ._render_qweb_pdf("business_company.final_report_pdf",res_ids=[bills.id])
            )
        except Exception:
            _logger.exception(
                "PDF render хийхэд алдаа гарлаа: "
                "acc_number=%s billing_read=%s",
                acc_number,
                bills.id,
            )
            return False

        attachment = self.env["ir.attachment"].sudo().create({
            "name": f"Billing_{acc_number}_{bills.period_start}.pdf",
            "type": "binary",
            "datas": base64.b64encode(pdf_content).decode("utf-8"),
            "res_model": "billing.read",
            "res_id": bills.id,
            "mimetype": "application/pdf",
            "public": True,
        })

        _logger.info(
            "PDF attachment үүслээ: "
            "attachment_id=%s acc_number=%s size=%s",
            attachment.id,
            acc_number,
            len(pdf_content),
        )
        return attachment

    def _test_email_campaign(self):
        MailingList = self.env["mailing.list"].sudo()
        MailingContact = self.env["mailing.contact"].sudo()
        MailingMailing = self.env["mailing.mailing"].sudo()
        BillingRead = self.env["billing.read"].sudo()
        BillingGroup = self.env["billing.group"].sudo()

        today = fields.Date.context_today(self)
        target_year, target_month = today.year, today.month
        start_date = date(target_year, target_month, 1)
        end_date = start_date + relativedelta(months=1)

        list_name = f"{target_year}_{target_month:02d}_mails"
        mailing_list = MailingList.search([("name", "=", list_name)], limit=1)
        if not mailing_list:
            mailing_list = MailingList.create({
                "name": list_name,
                "is_public": False,
            })

        # bills = BillingRead.search([
        #     ("acc_number", "like", "9810"),
        #     ("period_start", ">=", start_date),
        #     ("period_start", "<", end_date),
        #     ("email", "!=", False),
        # ])
        groups = BillingGroup.search([])

        # contacts = MailingContact.create([{
        #     "name": bill.acc_number,
        #     "email": bill.email,
        #     "list_ids": [(4, mailing_list.id)],
        # } for bill in bills])
        contacts=MailingContact.create([{
            'name': group.acc_number,
            'email':group.name,
            'list_ids': [(4, mailing_list.id)],
        } for group in groups])

        if not contacts:
            return 0, len(groups)

        skipped = 0
        mails_to_create = []
        email_from = self.env.company.email or self.env.user.email
        subject = f"Billing notice {target_year}-{target_month:02d}"

        for group in groups:
            try:
                pdf_attachment = self._generate_pdf_attachment_for_account(group.acc_number,'2026-06-01')
                print(pdf_attachment)
            except Exception:
                _logger.exception("PDF үүссэнгүй %s <-дээр", group.acc_number)
                skipped += 1
                continue

            mails_to_create.append({
                "subject": subject,
                "email_from": email_from,
                "email_to": group.name,
                "body_html": "<p>Your monthly billing notice.</p>",
                "attachment_ids": [(6, 0, [pdf_attachment.id])],
                "auto_delete": True,
            })

            if len(mails_to_create) >= 100:
                MailingMailing.create(mails_to_create)
                self.env.cr.commit()
                mails_to_create = []

        if mails_to_create:
            MailingMailing.create(mails_to_create)

        sent_count = len(groups) - skipped
        _logger.info("Mail жагсаалт үүслээ: sent=%s skipped=%s", sent_count, skipped)
        return len(contacts), skipped

    def initiate_action_campaign_bills(self):
        created, skipped = self._test_email_campaign()
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

    @api.model
    def read_all(self):
        connection = None
        synced = 0
        errors = 0
        dupes_seen = 0
        start = time.time()

        try:
            connection = self._get_connection()
            QUERY = """
                SELECT
                    an.subs_id, an.acct_id, an.acc_number, an.cust_name, an.email,
                    b.bill_id, b.period_start, b.period_end, b.total_amount,
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
                JOIN packages p ON an.acc_number = p.acc_number
                GROUP BY
                    an.subs_id, an.acct_id, an.acc_number, an.cust_name, an.email,
                    b.bill_id, b.period_start, b.period_end, b.state, b.total_amount,
                    p.package_name, p.data_limit, p.data_nemelt, p.sms_limit,
                    p.own_network_limit, p.other_call_limit, p.all_call_limit;
            """

            cur = connection.cursor("billing_sync_cursor", cursor_factory=psycopg2.extras.RealDictCursor)
            cur.itersize = 5000
            cur.execute(QUERY)

            Billing = self.env['billing.read'].sudo()

            self.env.cr.execute("SELECT id, acc_number, bill_id FROM billing_read")
            existing_map = {(r[1], r[2]): r[0] for r in self.env.cr.fetchall()}
            _logger.info("Preloaded %d existing keys", len(existing_map))

            to_create = []  # vals dicts queued for create() in this batch
            to_create_keys = []  # parallel keys, so created ids can be mapped back
            pending_index = {}  # key -> index into to_create, for same-batch dupes
            to_update = []  # (existing_id, vals) tuples
            BATCH = 2000

            def flush():
                nonlocal to_create, to_create_keys, to_update, pending_index, synced
                if to_create:
                    created = Billing.create(to_create)
                    for key, rec in zip(to_create_keys, created):
                        existing_map[key] = rec.id
                    synced += len(to_create)
                    to_create = []
                    to_create_keys = []
                    pending_index = {}
                if to_update:
                    for rec_id, vals in to_update:
                        try:
                            Billing.browse(rec_id).write(vals)
                        except Exception:
                            _logger.exception("write failed for id=%s", rec_id)
                    synced += len(to_update)
                    to_update = []
                self.env.cr.commit()

            for row in cur:
                bill_id = row.get("bill_id")
                acc_number = row.get("acc_number")
                if not bill_id or not acc_number:
                    errors += 1
                    continue

                if not row.get("period_start"):
                    # required field on the model -- skip rather than let create()/write() blow up the batch
                    errors += 1
                    _logger.warning(
                        "Skipping acc_number=%s bill_id=%s: missing period_start",
                        acc_number, bill_id
                    )
                    continue

                vals = {
                    "acc_number": acc_number,
                    "bill_id": str(bill_id),
                    "period_start": str(row["period_start"]),
                    "period_end": str(row["period_end"]) if row["period_end"] else False,
                    "total_amount": row["total_amount"] or 0.0,
                    "package_name": row["package_name"],
                    "data_limit": row["data_limit"],
                    "data_nemelt": row["data_nemelt"],
                    "sms_limit": row["sms_limit"],
                    "own_network_limit": row["own_network_limit"],
                    "other_call_limit": row["other_call_limit"],
                    "all_call_limit": row["all_call_limit"],
                    "bill_items": row["bill_items"],
                    'email_title': row["email"],
                }

                key = (acc_number, str(bill_id))
                existing_id = existing_map.get(key)

                if key in pending_index:
                    # same-batch duplicate of a not-yet-created row -> overwrite the queued payload
                    to_create[pending_index[key]] = vals
                    dupes_seen += 1
                elif existing_id:
                    to_update.append((existing_id, vals))
                else:
                    to_create.append(vals)
                    to_create_keys.append(key)
                    pending_index[key] = len(to_create) - 1

                if len(to_create) + len(to_update) >= BATCH:
                    flush()
                    elapsed = time.time() - start
                    rate = synced / elapsed if elapsed else 0
                    _logger.info(
                        "...%d synced, %d dupes (%.1fs elapsed, %.0f rows/sec)",
                        synced, dupes_seen, elapsed, rate
                    )

            flush()
            cur.close()

        except psycopg2.Error as error:
            raise UserError(f"PostgreSQL error:\n{str(error)}") from error
        finally:
            if connection:
                connection.close()

        self.env.cr.commit()
        _logger.info(
            "Done. %d synced, %d errors, %d dupes seen, %.1fs total",
            synced, errors, dupes_seen, time.time() - start
        )
        return True