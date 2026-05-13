from odoo import api, fields, models
import psycopg2
import logging

logger = logging.getLogger(__name__)

class GenerateInvoice(models.AbstractModel):
    _name = 'generate.invoice'

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
                select an.acc_number, b.billing_cycle_id, b.period_start, b.period_end, bi.item_type, bi.amount,an.email
                from bill_item bi
                left join bill b on bi.bill_id = b.id
                left join acc_number an on b.acc_number_id = an.id
                where substr(an.acc_number, 1, 2) = '98'
                order by an.acc_number limit 500
            """
        cursor.execute(query)
        results = cursor.fetchall()

        data = []
        for row in results:
            partner = self.env['res.partner'].search([('complete_name', '=', row[0])], limit=1).exists()
            if partner:
                logger.info("partner found: %s", partner.id)
            else:
                logger.info("partner not found: %s", row[0])
            data.append({
                'acc_number': row[0],
                'billing_cycle_id': row[1],
                'period_start': str(row[2]) if row[2] else None,
                'period_end': str(row[3]) if row[3] else None,
                'item_type': row[4],
                'amount': float(row[5]) if row[5] else 0.0,
                'email': str(row[6]) if row[6] else None,
                'partner_id': partner.id,
            })

        cursor.close()
        conn.close()
        logger.info("Task Ended")
        return data

    @api.model
    def read_billing(self):
        return True

    def execution(self):
        result = self.read_billing()
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        agent=self.env['res.users'].filtered_domain('login','=','bot@gmobile.mn')
        html_body = self.env['ir.qweb']._render(
            'jishee.sample_template',
            {
                'items': result.get('items', [])[:10],
                'total': result.get('total', 0),
            }
        )
        return True