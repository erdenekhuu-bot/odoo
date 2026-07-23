import psycopg2
from psycopg2.extras import RealDictCursor
from odoo import api, fields, models
from odoo.exceptions import UserError


class ReadAccount(models.Model):
    _name = "billing.read.account"
    _description = "Read account"

    acc_number = fields.Char(string="Account Number", required=True, index=True)
    subs_id = fields.Char(string="Subscription ID")
    acc_id = fields.Char(string="Account ID")
    cust_name = fields.Char(string="Customer Name")
    email = fields.Char(string="Email", index=True)
    time_created = fields.Char(string="Time")

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
    def sync_billing_account(self):
        connection = None

        try:
            connection = self._get_connection()

            with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT 
                        acc_number,
                        subs_id,
                        acct_id,
                        cust_name,
                        email,
                        time_created
                    FROM public.acc_number
                """)
                rows = cursor.fetchall()

            if not rows:
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": "Sync Notice",
                        "message": "Шинэчлэх дансны мэдээлэл олдсонгүй.",
                        "type": "warning",
                        "sticky": False,
                    },
                }

            # ---------------------------------------------------------
            # Odoo-д байгаа одоогийн данснуудыг acc_number-аар нь Dictionary болгоно
            # ---------------------------------------------------------
            existing_records = self.sudo().search([('acc_number', '!=', False)])
            existing_map = {rec.acc_number: rec for rec in existing_records}

            to_create_vals = []
            created_count = 0
            updated_count = 0

            for row in rows:
                raw_acc_num = row.get("acc_number")

                # acc_number хоосон эсвэл None бол алгасна
                if raw_acc_num is None or raw_acc_num == "":
                    continue

                acc_num_str = str(raw_acc_num)

                # Утгуудыг бэлтгэх (None ирвэл Odoo стандартын дагуу False болгоно)
                vals = {
                    "acc_number": acc_num_str,
                    "subs_id": str(row["subs_id"]) if row.get("subs_id") is not None else False,
                    "acc_id": str(row["acct_id"]) if row.get("acct_id") is not None else False,
                    "cust_name": str(row["cust_name"]) if row.get("cust_name") is not None else False,
                    "email": str(row["email"]) if row.get("email") is not None else False,
                    "time_created": str(row["time_created"]) if row.get("time_created") is not None else False,
                }

                # Хэрэв acc_number байвал UPDATE, байхгүй бол БАГЦАД НЭМНЭ (CREATE)
                if acc_num_str in existing_map:
                    existing_map[acc_num_str].write(vals)
                    updated_count += 1
                else:
                    to_create_vals.append(vals)
                    created_count += 1

            # Шинэ бичлэгүүдийг бөөнд нь нэг дор үүсгэнэ (Хурдыг эрс нэмэгдүүлнэ)
            if to_create_vals:
                self.sudo().create(to_create_vals)

            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Sync Completed",
                    "message": f"Амжилттай дууслаа: {created_count} шинэ данс үүсч, {updated_count} данс шинэчлэгдлээ.",
                    "type": "success",
                    "sticky": False,
                },
            }

        except psycopg2.Error as error:
            raise UserError(f"PostgreSQL error:\n{str(error)}") from error

        finally:
            if connection:
                connection.close()