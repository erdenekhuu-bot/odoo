import psycopg2
from psycopg2.extras import RealDictCursor
from odoo import api, fields, models
from odoo.exceptions import UserError


class BillingPeriod(models.Model):
    _name = "billing.period"
    _description = "Read billing period"

    acc_number_id = fields.Char(string='Account Number')
    billing_cycle_id = fields.Char(string='Bill Cycle')
    bill_id = fields.Char(string='Bill ID', required=True, index=True)
    period_start = fields.Char(string='Period Start')
    period_end = fields.Char(string='Period End')
    email = fields.Char(string='Email', index=True)
    state = fields.Char(string='State')
    total_amount = fields.Float(string='Total Amount')

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

    def sync_billing_period(self):
        connection = None

        try:
            connection = self._get_connection()

            with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT 
                        acc_number_id,
                        billing_cycle_id,
                        bill_id,
                        period_start,
                        period_end,
                        email,
                        state,
                        total_amount
                    FROM public.bill
                """)
                rows = cursor.fetchall()

            if not rows:
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": "Sync Notice",
                        "message": "Шинэчлэх дата олдсонгүй.",
                        "type": "warning",
                        "sticky": False,
                    },
                }

            # ---------------------------------------------------------
            # Баазад байгаа датаг Dict болгож бэлдэх
            # ---------------------------------------------------------
            existing_records = self.sudo().search([('bill_id', '!=', False)])
            existing_map = {rec.bill_id: rec for rec in existing_records}

            to_create_vals = []
            created_count = 0
            updated_count = 0

            for row in rows:
                raw_bill_id = row.get("bill_id")
                # bill_id байхгүй бол алгасна
                if raw_bill_id is None or raw_bill_id == "":
                    continue

                bill_id_str = str(raw_bill_id)

                # Утгуудыг бэлтгэх (None/NULL ирвэл False болгож Odoo-д тохируулна)
                vals = {
                    "acc_number_id": str(row["acc_number_id"]) if row.get("acc_number_id") is not None else False,
                    "billing_cycle_id": str(row["billing_cycle_id"]) if row.get("billing_cycle_id") is not None else False,
                    "bill_id": bill_id_str,
                    "period_start": str(row["period_start"]) if row.get("period_start") is not None else False,
                    "period_end": str(row["period_end"]) if row.get("period_end") is not None else False,
                    "email": str(row["email"]) if row.get("email") is not None else False,
                    "state": str(row["state"]) if row.get("state") is not None else False,
                    "total_amount": float(row["total_amount"]) if row.get("total_amount") is not None else 0.0,
                }

                # Хэрэв байвал ШИНЭЧЛЭХ (Write), байхгүй бол ШИНЭЭР ҮҮСГЭХ
                if bill_id_str in existing_map:
                    existing_map[bill_id_str].write(vals)
                    updated_count += 1
                else:
                    to_create_vals.append(vals)
                    created_count += 1

            # Шинэ бичлэгүүдийг бөөнд нь нэг дор үүсгэнэ (Performance сайжруулна)
            if to_create_vals:
                self.sudo().create(to_create_vals)

            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Sync Completed",
                    "message": f"Амжилттай дууслаа: {created_count} шинээр үүсч, {updated_count} шинэчлэгдэв.",
                    "type": "success",
                    "sticky": False,
                },
            }

        except psycopg2.Error as error:
            raise UserError(f"PostgreSQL error:\n{str(error)}") from error

        finally:
            if connection:
                connection.close()