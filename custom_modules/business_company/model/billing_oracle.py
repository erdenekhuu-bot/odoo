# import logging
# import os
# from contextlib import closing
#
# import oracledb
# from odoo import models, fields, api
# from odoo.exceptions import UserError
#
# _logger = logging.getLogger(__name__)
#
# _ORACLE_INITIALIZED = False
#
#
# def _ensure_oracle_client():
#     """Initialize the Oracle thick client exactly once per process.
#
#     Odoo forks workers; calling init_oracle_client() again in the same
#     process raises DPY-2019, and calling it at import time is unsafe.
#     """
#     global _ORACLE_INITIALIZED
#     if _ORACLE_INITIALIZED:
#         return
#     if not oracledb.is_thin_mode():
#         _ORACLE_INITIALIZED = True
#         return
#     lib_dir = os.environ.get("ORACLE_CLIENT_LIB") or r"C:\instantclient_23_26"
#     try:
#         oracledb.init_oracle_client(lib_dir=lib_dir)
#         _logger.info("Oracle thick client initialized from %s", lib_dir)
#     except Exception as e:
#         # DPY-2019 means someone else already initialized it — that's fine.
#         if "DPY-2019" not in str(e):
#             _logger.warning("Oracle client init failed: %s", e)
#     finally:
#         _ORACLE_INITIALIZED = True
#
#
# class BillingOracle(models.Model):
#     _name = 'billing.oracle'
#     _description = 'Billing query synced from Oracle (GMobile)'
#     _rec_name = 'bill_id'
#     _order = 'billing_cycle_id desc, phonenum'
#
#     # -- identifiers / period --
#     bill_id = fields.Char(string='Bill ID', index=True)
#     billperiod = fields.Char(string='Bill Period')
#     due_date = fields.Char(string='Due Date')
#     debt_date = fields.Char(string='Debt Date')
#     custname = fields.Char(string='Customer Name')
#     acct_id = fields.Char(string='Account ID', index=True)
#     phonenum = fields.Char(string='Phone Number', index=True)
#
#     # -- monthly fees --
#     fixedmonthfee = fields.Float(string='Fixed Month Fee')
#     other_usage = fields.Float(string='Other Usage')
#     data_nemelt_une = fields.Float(string='Data Nemelt Price')
#     callkeeper = fields.Float(string='Call Keeper')
#     crbt = fields.Float(string='CRBT')
#     sms_own = fields.Float(string='SMS Own')
#     sms_other = fields.Float(string='SMS Other')
#     totalcharge = fields.Float(string='Total Charge')
#     additional_usage = fields.Float(string='Additional Usage')
#     internetusagefee = fields.Float(string='Internet Usage Fee')
#     vat = fields.Float(string='VAT')
#     monthly_total = fields.Float(string='Monthly Total')
#     prebalancecharge = fields.Float(string='Pre-Balance Charge')
#     granttotal = fields.Float(string='Grand Total')
#
#     # -- usage --
#     duration_other_call = fields.Char(string='Duration Other Call')
#     sum_charge_other_call = fields.Float(string='Sum Charge Other Call')
#     duration_own_network = fields.Char(string='Duration Own Network')
#     sum_charge_own_network = fields.Float(string='Sum Charge Own Network')
#     count_sms_own_network = fields.Integer(string='Count SMS Own Network')
#     count_sms_other = fields.Integer(string='Count SMS Other')
#     duration_special_call = fields.Char(string='Duration Special Call')
#     sum_charge_special_call = fields.Float(string='Sum Charge Special Call')
#     download_upload = fields.Char(string='Download/Upload')
#
#     # -- plan limits --
#     data_limit = fields.Char(string='Data Limit')
#     data_nemelt = fields.Char(string='Data Nemelt')
#     own_network_limit = fields.Char(string='Own Network Limit')
#     sms_limit = fields.Char(string='SMS Limit')
#     other_network_call_limit = fields.Char(string='Other Network Call Limit')
#     all_network_call_limit = fields.Char(string='All Network Call Limit')
#
#     # -- sync metadata --
#     billing_cycle_id = fields.Integer(string='Billing Cycle ID', index=True)
#
#     _sql_constraints = [
#         ('bill_id_cycle_uniq', 'unique(bill_id, billing_cycle_id)',
#          'A bill row for this cycle already exists.'),
#     ]
#
#     # ---------------------------------------------------------------
#     # Oracle connection
#     # ---------------------------------------------------------------
#     def _get_oracle_connection(self):
#         _ensure_oracle_client()
#
#         icp = self.env['ir.config_parameter'].sudo()
#         user = icp.get_param('gmobile_oracle.user','cc_post_bill')
#         password = icp.get_param('gmobile_oracle.password','m8#K2qL9$vP6zR')
#         host = icp.get_param('gmobile_oracle.host', '10.10.11.112')
#         port = int(icp.get_param('gmobile_oracle.port', '1521'))
#         sid = icp.get_param('gmobile_oracle.sid', 'cc')
#
#         if not user or not password:
#             raise UserError(
#                 "Oracle credentials not set in System Parameters "
#                 "(gmobile_oracle.user / gmobile_oracle.password)."
#             )
#
#         dsn = oracledb.makedsn(host, port, sid=sid)
#         conn = oracledb.connect(user=user, password=password, dsn=dsn)
#         conn.call_timeout = 30 * 60 * 1000  # 30 min per round-trip
#         return conn
#
#     # ---------------------------------------------------------------
#     # Query builder — cycle_id is interpolated into DB-link table names
#     # (Oracle can't bind object names), so it MUST be int-cast first.
#     # ---------------------------------------------------------------
#     def _build_query(self, cycle_id):
#         cycle_id = int(cycle_id)
#         return f"""
#             WITH cycle_dates AS (
#                 SELECT cycle_begin_date, cycle_end_date, billing_cycle_id, DEBT_DATE
#                   FROM cc.billing_cycle
#                  WHERE billing_cycle_id = :cycle_id
#             ),
#             packinfo_prep AS (
#                 SELECT s.subs_id, s.acct_id, s.acc_nbr, s.cust_id,
#                        pp.price_plan_name, sui.price_plan_id AS main_plan_id,
#                        sui.subs_upp_inst_id,
#                        MAX(CASE WHEN sui1.price_plan_id IN (2322,2320,2321,2400,2340) THEN sui1.price_plan_id END) AS perfect_plan,
#                        MAX(CASE WHEN sui1.price_plan_id IN (4782,4899,6344) THEN sui1.price_plan_id END) AS nemelt_plan,
#                        MAX(CASE WHEN suiv.attr_id = 1766 THEN suiv.value END) AS val_1766,
#                        MAX(CASE WHEN suiv.attr_id = 2185 THEN suiv.value END) AS val_2185,
#                        MAX(CASE WHEN suiv.attr_id = 1768 THEN suiv.value END) AS val_1768
#                   FROM cc.subs s
#                  CROSS JOIN cycle_dates cd
#                  INNER JOIN cc.prod pr
#                     ON s.subs_id = pr.prod_id
#                    AND (pr.prod_state <> 'B'
#                         OR (pr.prod_state = 'B'
#                             AND pr.prod_state_date > cd.cycle_begin_date))
#                  INNER JOIN cc.subs_upp_inst sui ON s.subs_id = sui.subs_id
#                  INNER JOIN cc.price_plan pp ON sui.price_plan_id = pp.price_plan_id
#                   LEFT JOIN cc.subs_upp_inst sui1
#                     ON s.subs_id = sui1.subs_id
#                    AND sui1.price_plan_id IN (4782,4899,6344,2322,2320,2321,2400,2340)
#                    AND (sui1.exp_date >= cd.cycle_end_date OR sui1.exp_date IS NULL)
#                    AND sui1.eff_date < cd.cycle_end_date
#                   LEFT JOIN cc.subs_upp_inst_value suiv
#                     ON sui.subs_upp_inst_id = suiv.subs_upp_inst_id
#                    AND suiv.attr_id IN (1766, 2185, 1768)
#                  WHERE s.acc_nbr NOT LIKE '48%'
#                    AND LENGTH(s.acc_nbr) = 8
#                    AND sui.price_plan_id IN (602,601,600,421,2360,2300,4120,4328,603,607,
#                                               1900,1920,4580,4800,4801,4937,4938,4939,6596,6597,6637)
#                    AND (sui.exp_date >= cd.cycle_end_date OR sui.exp_date IS NULL)
#                    AND sui.eff_date < cd.cycle_end_date
#                  GROUP BY s.subs_id, s.acct_id, s.acc_nbr, pp.price_plan_name,
#                           sui.price_plan_id, sui.subs_upp_inst_id, s.cust_id
#             ),
#             ai_stuff AS (
#                 SELECT ai.acct_id,
#                        nvl(SUM(CASE WHEN ait.parent_id = 2 AND ait.acct_item_type_id NOT IN (110,205,211,231,263,201) THEN ai.charge END)/100,0) AS FIXEDMONTHFEE,
#                        nvl(SUM(CASE WHEN (ait.acct_item_type_name LIKE 'Roaming%' OR ait.acct_item_type_id IN (205,261,201)) THEN ai.charge END)/100,0) AS OTHER_USAGE,
#                        nvl(SUM(CASE WHEN ait.acct_item_type_id IN (211,231,263) THEN ai.charge END)/100,0) AS DATA_NEMELT_UNE,
#                        nvl(SUM(CASE WHEN ait.acct_item_type_id = 110 THEN ai.charge END)/100,0) AS CALLKEEPER,
#                        nvl(SUM(CASE WHEN ait.acct_item_type_id IN (38,101) THEN ai.charge END)/100,0) AS CRBT,
#                        nvl(SUM(CASE WHEN ait.parent_id = 5 AND ait.acct_item_type_id = 22 THEN ai.charge END)/100,0) AS SMS_OWN,
#                        nvl(SUM(CASE WHEN ait.parent_id = 5 AND ait.acct_item_type_id <> 22 THEN ai.charge END)/100,0) AS SMS_OTHER,
#                        nvl(SUM(CASE WHEN ait.acct_item_type_name NOT LIKE 'VAT%' THEN ai.charge END)/100,0) AS TOTALCHARGE,
#                        nvl(SUM(CASE WHEN ait.acct_item_type_name NOT LIKE 'VAT%' AND ait.acct_item_type_id <> 71
#                                     AND (ait.parent_id <> 2 OR ait.parent_id IS NULL OR ait.acct_item_type_id = 110) THEN ai.charge END)/100,0) AS ADDITIONAL_USAGE,
#                        nvl(SUM(CASE WHEN ait.acct_item_type_id = 19 THEN ai.charge END)/100,0) AS INTERNETUSAGEFEE,
#                        nvl(SUM(CASE WHEN ait.acct_item_type_name LIKE 'VAT%' THEN ai.charge END)/100,0) AS VAT
#                   FROM cc.acct_item ai
#                  INNER JOIN cc.acct_item_type ait ON ai.acct_item_type_id = ait.acct_item_type_id
#                  INNER JOIN cycle_dates cd ON ai.billing_cycle_id = cd.billing_cycle_id
#                  WHERE ai.acct_id IN (SELECT acct_id FROM packinfo_prep)
#                  GROUP BY ai.acct_id
#             ),
#             usagevs AS (
#                 SELECT t.subs_id,
#                        SUM(CASE WHEN t.re_id IN ('1044','1046','1077','1079','960','962') AND t.duration>0 THEN t.duration END) DURATION_OWN_NETWORK,
#                        SUM(CASE WHEN t.re_id IN ('1044','1046','1077','1079','960','962') AND t.duration>0 THEN t.charge1/100 END) SUM_CHARGE_OWN_NETWORK,
#                        SUM(CASE WHEN t.re_id NOT IN ('1233','1449','1951','1953','1950','1452','1453','1239','1707','1045','1235','1708','1078','1124','1874','1129','1719',
#                                                       '1919','1856','1123','1130','1127','1131','1667','1109','1875','1115','1718','1920','1857','1118','1116','1112','1117',
#                                                       '1668','1735','1905','1906','1044','1079','1046','962','960','1077','1091','1058','1007','1080','966','2098','2099','2188','2191')
#                                 AND t.duration>0 THEN t.duration END) duration_other_call,
#                        SUM(CASE WHEN t.re_id NOT IN ('1233','1449','1951','1953','1950','1452','1453','1239','1707','1045','1235','1708','1078','1124','1874','1129','1719',
#                                                       '1919','1856','1123','1130','1127','1131','1667','1109','1875','1115','1718','1920','1857','1118','1116','1112','1117',
#                                                       '1668','1735','1905','1906','1044','1079','1046','962','960','1077','1091','1058','1007','1080','966','2098','2099','2188','2191')
#                                 AND t.duration>0 THEN t.charge1/100 END) sum_charge_other_call,
#                        SUM(CASE WHEN t.re_id IN ('1091','1058','1007','1080','966') AND t.duration>0 THEN t.duration END) duration_special_call,
#                        SUM(CASE WHEN t.re_id IN ('1091','1058','1007','1080','966') AND t.duration>0 THEN t.charge1/100 END) sum_charge_special_call,
#                        COUNT(CASE WHEN t.re_id IN ('1123','1118') AND t.duration = 0 THEN t.re_id END) count_sms_own_network,
#                        COUNT(CASE WHEN t.re_id IN ('1124','1874','1129','1719','1919','1856','1130','1127','1131','1667','1109','1875','1115','1718','1920',
#                                                     '1857','1116','1112','1117','1668','1735','1905','1906','2098','2099','2188','2191') AND t.duration=0 THEN t.re_id END) count_sms_other
#                   FROM rb.EVENT_USAGE_{cycle_id}@link_rb t
#                  WHERE t.subs_id IN (SELECT subs_id FROM packinfo_prep)
#                  GROUP BY t.subs_id
#             ),
#             usagedata AS (
#                 SELECT t.subs_id, ROUND(SUM(t.byte_up+t.byte_down)/1024/1024,2)||' MB' AS download_upload
#                   FROM rb.EVENT_USAGE_C_{cycle_id}@link_rb t
#                  WHERE subs_id IN (SELECT subs_id FROM packinfo_prep)
#                  GROUP BY subs_id
#             )
#             SELECT bill.bill_id,
#                    to_char(cd.CYCLE_BEGIN_DATE,'yyyy/mm/dd')||'-'||to_char(cd.CYCLE_END_DATE,'yyyy/mm/dd') BILLPERIOD,
#                    to_char(cd.DEBT_DATE-12,'yyyy/mm/dd') DUE_DATE,
#                    to_char(cd.DEBT_DATE,'yyyy/mm/dd') DEBT_DATE,
#                    cu.cust_name CUSTNAME,
#                    p_info.acct_id, p_info.acc_nbr PHONENUM,
#                    ais.FIXEDMONTHFEE, ais.OTHER_USAGE, ais.DATA_NEMELT_UNE, ais.CALLKEEPER, ais.CRBT,
#                    ais.SMS_OWN, ais.SMS_OTHER, ais.TOTALCHARGE, ais.ADDITIONAL_USAGE, ais.INTERNETUSAGEFEE, ais.VAT,
#                    ais.TOTALCHARGE + ais.VAT MONTHLY_TOTAL,
#                    bill.recv_charge + (nvl(bill.PRE_BALANCE,0)+nvl(bill.ADJUST_CHARGE,0)) PREBALANCECHARGE,
#                    (bill.DUE + nvl(bill.CHARGE_BE_ADJUSTED,0) + nvl(bill.Dispute_Charge,0) + nvl(bill.RECV_CHARGE,0)
#                     + (nvl(bill.PRE_BALANCE,0)+nvl(bill.ADJUST_CHARGE,0))) GRANTTOTAL,
#                    TO_CHAR(TRUNC(uvs.duration_other_call/3600),'FM9900')||':'||TO_CHAR(TRUNC(MOD(uvs.duration_other_call,3600)/60),'FM00')||':'||TO_CHAR(MOD(uvs.duration_other_call,60),'FM00') duration_other_call,
#                    uvs.sum_charge_other_call,
#                    TO_CHAR(TRUNC(uvs.DURATION_OWN_NETWORK/3600),'FM9900')||':'||TO_CHAR(TRUNC(MOD(uvs.DURATION_OWN_NETWORK,3600)/60),'FM00')||':'||TO_CHAR(MOD(uvs.DURATION_OWN_NETWORK,60),'FM00') DURATION_OWN_NETWORK,
#                    uvs.SUM_CHARGE_OWN_NETWORK, uvs.count_sms_own_network, uvs.count_sms_other,
#                    TO_CHAR(TRUNC(uvs.duration_special_call/3600),'FM9900')||':'||TO_CHAR(TRUNC(MOD(uvs.duration_special_call,3600)/60),'FM00')||':'||TO_CHAR(MOD(uvs.duration_special_call,60),'FM00') duration_special_call,
#                    uvs.sum_charge_special_call, ud.download_upload,
#                    CASE WHEN p_info.main_plan_id = 421 THEN N'200MB'
#                         WHEN p_info.main_plan_id IN (603) THEN N'1GB'
#                         WHEN p_info.main_plan_id IN (600,1900) THEN N'2GB'
#                         WHEN p_info.main_plan_id IN (4937) THEN N'3GB'
#                         WHEN p_info.main_plan_id IN (601,1920) THEN N'5GB'
#                         WHEN p_info.main_plan_id IN (4938) THEN N'8GB'
#                         WHEN p_info.main_plan_id IN (602) THEN N'10GB'
#                         WHEN p_info.main_plan_id IN (4939) THEN N'15GB'
#                         WHEN p_info.main_plan_id IN (6637) THEN N'30GB'
#                         WHEN p_info.main_plan_id IN (2300,2360) THEN
#                              CASE p_info.perfect_plan WHEN 2322 THEN N'10GB' WHEN 2320 THEN N'2GB' WHEN 2321 THEN N'5GB'
#                                   WHEN 2400 THEN N'хязгааргүй' WHEN 2340 THEN N'хязгааргүй' ELSE NULL END
#                         WHEN p_info.main_plan_id IN (4328,4120) THEN
#                              CASE p_info.val_2185 WHEN '2' THEN N'1GB' WHEN '3' THEN N'20GB' WHEN '4' THEN N'5GB'
#                                   WHEN '5' THEN N'10GB' WHEN '6' THEN N'5GB' WHEN '7' THEN N'40GB' WHEN '8' THEN N'20GB'
#                                   WHEN '9' THEN N'10GB' WHEN '10' THEN N'30GB' WHEN '11' THEN N'60GB' WHEN '12' THEN N'хязгааргүй'
#                                   WHEN '13' THEN N'10GB' WHEN '14' THEN N'5GB' WHEN '15' THEN N'25GB' WHEN '22' THEN N'1GB' ELSE NULL END
#                         WHEN p_info.main_plan_id IN (6596,6597) THEN
#                              CASE p_info.val_2185 WHEN '24' THEN N'10GB' WHEN '25' THEN N'1GB' WHEN '16' THEN N'10GB'
#                                   WHEN '17' THEN N'15GB' WHEN '18' THEN N'20GB' WHEN '19' THEN N'30GB' WHEN '20' THEN N'60GB'
#                                   WHEN '21' THEN N'хязгааргүй' WHEN '23' THEN N'25GB' ELSE NULL END
#                    ELSE NULL END AS DATA_LIMIT,
#                    CASE p_info.nemelt_plan WHEN 4782 THEN N'5GB' WHEN 4899 THEN N'10GB' WHEN 6344 THEN N'2GB' ELSE NULL END AS DATA_NEMELT,
#                    CASE WHEN p_info.main_plan_id IN (602,600,601,1920,4580,4800,4801,4937,4938,4939) THEN N'хязгааргүй'
#                         WHEN p_info.main_plan_id IN (2300,2360) AND p_info.val_1766 IN ('1','3') THEN N'хязгааргүй'
#                         WHEN p_info.main_plan_id IN (4328,4120) AND p_info.val_2185 IN ('2','5','6','8','9','14','15') THEN N'хязгааргүй'
#                         WHEN p_info.main_plan_id IN (6596,6597) AND p_info.val_2185 IN ('25','16','17') THEN N'хязгааргүй'
#                         WHEN p_info.main_plan_id IN (6596,6597) AND p_info.val_2185 IN ('24') THEN N'100'
#                    ELSE NULL END AS OWN_NETWORK_LIMIT,
#                    CASE WHEN p_info.main_plan_id = 421 THEN N'50' WHEN p_info.main_plan_id = 4937 THEN N'30'
#                         WHEN p_info.main_plan_id IN (600,1920) THEN N'200' WHEN p_info.main_plan_id = 6637 THEN N'300'
#                         WHEN p_info.main_plan_id = 601 THEN N'500' WHEN p_info.main_plan_id IN (602,4938,4939) THEN N'хязгааргүй'
#                         WHEN p_info.main_plan_id IN (2300,2360) THEN
#                              CASE p_info.val_1768 WHEN '1' THEN N'сүлжээндээ хязгааргүй' WHEN '2' THEN N'хязгааргүй' ELSE NULL END
#                         WHEN p_info.main_plan_id IN (4328,4120) THEN
#                              CASE WHEN p_info.val_2185 IN ('3','4','5','6') THEN N'100'
#                                   WHEN p_info.val_2185 IN ('7','8','9') THEN N'300'
#                                   WHEN p_info.val_2185 IN ('10','11','12') THEN N'хязгааргүй' ELSE NULL END
#                         WHEN p_info.main_plan_id IN (6596,6597) THEN
#                              CASE WHEN p_info.val_2185 = '17' THEN N'100' WHEN p_info.val_2185 = '18' THEN N'150'
#                                   WHEN p_info.val_2185 = '19' THEN N'300' WHEN p_info.val_2185 = '20' THEN N'500'
#                                   WHEN p_info.val_2185 = '21' THEN N'хязгааргүй' ELSE NULL END
#                    ELSE NULL END AS SMS_LIMIT,
#                    CASE WHEN p_info.main_plan_id IN (4800) THEN N'100 минут'
#                         WHEN p_info.main_plan_id IN (421,4939) THEN N'150 минут'
#                         WHEN p_info.main_plan_id = 4937 THEN N'30 минут' WHEN p_info.main_plan_id = 4938 THEN N'30 минут'
#                         WHEN p_info.main_plan_id IN (600,1920) THEN N'200 минут' WHEN p_info.main_plan_id IN (601,4801) THEN N'500 минут'
#                         WHEN p_info.main_plan_id IN (602) THEN N'1000 минут'
#                         WHEN p_info.main_plan_id IN (2300,2360) AND p_info.val_1766 = '3' THEN N'250 минут'
#                         WHEN p_info.main_plan_id IN (4328,4120) THEN
#                              CASE WHEN p_info.val_2185 IN ('6','8') THEN N'200 минут' WHEN p_info.val_2185 = '9' THEN N'500 минут' ELSE NULL END
#                         WHEN p_info.main_plan_id IN (6596,6597) THEN
#                              CASE WHEN p_info.val_2185 = '24' THEN N'20 минут' WHEN p_info.val_2185 = '25' THEN N'25 минут'
#                                   WHEN p_info.val_2185 = '16' THEN N'50 минут' WHEN p_info.val_2185 = '17' THEN N'500 минут' ELSE NULL END
#                    ELSE NULL END AS OTHER_NETWORK_CALL_LIMIT,
#                    CASE WHEN p_info.main_plan_id IN (603) THEN N'100 минут' WHEN p_info.main_plan_id IN (607,1900) THEN N'200 минут'
#                         WHEN p_info.main_plan_id = 6637 THEN N'хязгааргүй'
#                         WHEN p_info.main_plan_id IN (2300,2360) AND p_info.val_1766 = '2' THEN N'хязгааргүй'
#                         WHEN p_info.main_plan_id IN (4328,4120) THEN
#                              CASE WHEN p_info.val_2185 = '1' THEN N'250 минут' WHEN p_info.val_2185 = '4' THEN N'500 минут'
#                                   WHEN p_info.val_2185 IN ('10','11','12') THEN N'хязгааргүй' ELSE NULL END
#                         WHEN p_info.main_plan_id IN (6596,6597) THEN
#                              CASE WHEN p_info.val_2185 = '23' THEN N'25 минут'
#                                   WHEN p_info.val_2185 IN ('18','19','20','21') THEN N'хязгааргүй' ELSE NULL END
#                    ELSE NULL END AS ALL_NETWORK_CALL_LIMIT
#               FROM packinfo_prep p_info
#              CROSS JOIN cycle_dates cd
#              INNER JOIN cc.acct ac ON p_info.acct_id = ac.acct_id AND ac.postpaid = 'Y'
#              INNER JOIN cc.prod p ON p.prod_id = p_info.subs_id
#               LEFT JOIN ai_stuff ais ON p_info.acct_id = ais.acct_id
#              INNER JOIN cc.bill bill ON p_info.acct_id = bill.acct_id AND bill.billing_cycle_id = cd.billing_cycle_id
#              INNER JOIN cc.cust cu ON p_info.cust_id = cu.cust_id
#               LEFT JOIN usagevs uvs ON p_info.subs_id = uvs.subs_id
#               LEFT JOIN usagedata ud ON p_info.subs_id = ud.subs_id
#              WHERE (p.prod_state <> 'B' OR (p.prod_state = 'B' AND p.prod_state_date > cd.cycle_begin_date))
#         """
#
#     # ---------------------------------------------------------------
#     # Row mapping
#     # ---------------------------------------------------------------
#     def _row_to_vals(self, col_index, row, cycle_id):
#         def g(col):
#             return row[col_index[col]]
#
#         return {
#             'bill_id': g('BILL_ID'),
#             'billperiod': g('BILLPERIOD'),
#             'due_date': g('DUE_DATE'),
#             'debt_date': g('DEBT_DATE'),
#             'custname': g('CUSTNAME'),
#             'acct_id': g('ACCT_ID'),
#             'phonenum': g('PHONENUM'),
#             'fixedmonthfee': g('FIXEDMONTHFEE') or 0,
#             'other_usage': g('OTHER_USAGE') or 0,
#             'data_nemelt_une': g('DATA_NEMELT_UNE') or 0,
#             'callkeeper': g('CALLKEEPER') or 0,
#             'crbt': g('CRBT') or 0,
#             'sms_own': g('SMS_OWN') or 0,
#             'sms_other': g('SMS_OTHER') or 0,
#             'totalcharge': g('TOTALCHARGE') or 0,
#             'additional_usage': g('ADDITIONAL_USAGE') or 0,
#             'internetusagefee': g('INTERNETUSAGEFEE') or 0,
#             'vat': g('VAT') or 0,
#             'monthly_total': g('MONTHLY_TOTAL') or 0,
#             'prebalancecharge': g('PREBALANCECHARGE') or 0,
#             'granttotal': g('GRANTTOTAL') or 0,
#             'duration_other_call': g('DURATION_OTHER_CALL'),
#             'sum_charge_other_call': g('SUM_CHARGE_OTHER_CALL') or 0,
#             'duration_own_network': g('DURATION_OWN_NETWORK'),
#             'sum_charge_own_network': g('SUM_CHARGE_OWN_NETWORK') or 0,
#             'count_sms_own_network': g('COUNT_SMS_OWN_NETWORK') or 0,
#             'count_sms_other': g('COUNT_SMS_OTHER') or 0,
#             'duration_special_call': g('DURATION_SPECIAL_CALL'),
#             'sum_charge_special_call': g('SUM_CHARGE_SPECIAL_CALL') or 0,
#             'download_upload': g('DOWNLOAD_UPLOAD'),
#             'data_limit': g('DATA_LIMIT'),
#             'data_nemelt': g('DATA_NEMELT'),
#             'own_network_limit': g('OWN_NETWORK_LIMIT'),
#             'sms_limit': g('SMS_LIMIT'),
#             'other_network_call_limit': g('OTHER_NETWORK_CALL_LIMIT'),
#             'all_network_call_limit': g('ALL_NETWORK_CALL_LIMIT'),
#             'billing_cycle_id': cycle_id,
#         }
#
#     # ---------------------------------------------------------------
#     # Write to local Odoo table (upsert per batch)
#     # ---------------------------------------------------------------
#     def _write_batch(self, columns, rows, cycle_id):
#         col_index = {name.upper(): i for i, name in enumerate(columns)}
#         bill_ids = [str(row[col_index['BILL_ID']]) for row in rows]
#
#         existing = self.search_read(
#             [('billing_cycle_id', '=', cycle_id), ('bill_id', 'in', bill_ids)],
#             ['bill_id'],
#         )
#         existing_map = {r['bill_id']: r['id'] for r in existing}
#
#         to_create = []
#         for row in rows:
#             vals = self._row_to_vals(col_index, row, cycle_id)
#             bill_id = vals['bill_id']
#             if bill_id in existing_map:
#                 self.browse(existing_map[bill_id]).write(vals)
#             else:
#                 to_create.append(vals)
#         if to_create:
#             self.create(to_create)
#
#     # ---------------------------------------------------------------
#     # Sync entry points
#     # ---------------------------------------------------------------
#     def _sync_for_cycle(self, cycle_id, batch_size=2000):
#         cycle_id = int(cycle_id)
#         query = self._build_query(cycle_id)
#         total = 0
#
#         try:
#             # closing() guarantees the connection is closed.
#             # Odoo commits the Odoo transaction; the Oracle side is read-only.
#             with closing(self._get_oracle_connection()) as conn:
#                 with conn.cursor() as cur:
#                     cur.arraysize = batch_size
#                     cur.execute(query, cycle_id=cycle_id)
#                     columns = [c[0] for c in cur.description]
#
#                     while True:
#                         rows = cur.fetchmany(batch_size)
#                         if not rows:
#                             break
#                         self._write_batch(columns, rows, cycle_id)
#                         total += len(rows)
#                         _logger.info("Synced %s rows so far for cycle %s",
#                                      total, cycle_id)
#                 # No need to commit: we only read from Oracle.
#         except oracledb.Error as e:
#             _logger.exception("Oracle billing query failed for cycle %s", cycle_id)
#             raise UserError(f"Oracle query failed: {e}")
#
#         _logger.info("Finished sync: %s total rows for cycle %s", total, cycle_id)
#         return total
#
#     def action_manual_sync(self):
#         self.ensure_one()
#         if not self.billing_cycle_id:
#             raise UserError("Set a Billing Cycle ID before syncing.")
#         count = self._sync_for_cycle(self.billing_cycle_id)
#         return {
#             'type': 'ir.actions.client',
#             'tag': 'display_notification',
#             'params': {
#                 'title': 'Oracle Sync Complete',
#                 'message': f'{count} rows synced for cycle {self.billing_cycle_id}.',
#                 'sticky': False,
#             },
#         }
#
#     @api.model
#     def sync_cycle(self, cycle_id):
#         return self._sync_for_cycle(cycle_id)
#
#     @api.model
#     def cron_sync_billing(self):
#         icp = self.env['ir.config_parameter'].sudo()
#         cycle_id = int(icp.get_param('gmobile_oracle.default_cycle_id', 587))
#         if not cycle_id:
#             _logger.warning("cron_sync_billing: default_cycle_id not set, skipping")
#             return
#         self._sync_for_cycle(cycle_id)
import logging
import oracledb
from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Only needed for thick-mode client. If python-oracledb thin mode works for
# your DB-link queries, remove this block and the lib_dir entirely.
try:
    oracledb.init_oracle_client(lib_dir=r"C:\instantclient_23_26")
except Exception as e:
    _logger.warning("Oracle client init skipped/failed: %s", e)


class BillingOracle(models.Model):
    _name = 'billing.oracle'
    _description = 'Billing query synced from Oracle (GMobile)'
    _rec_name = 'bill_id'

    # -- identifiers / period --
    bill_id = fields.Char(string='Bill ID', index=True)
    billperiod = fields.Char(string='Bill Period')
    due_date = fields.Char(string='Due Date')
    debt_date = fields.Char(string='Debt Date')
    custname = fields.Char(string='Customer Name')
    acct_id = fields.Char(string='Account ID')
    phonenum = fields.Char(string='Phone Number')

    # -- monthly fees --
    fixedmonthfee = fields.Float(string='Fixed Month Fee')
    other_usage = fields.Float(string='Other Usage')
    data_nemelt_une = fields.Float(string='Data Nemelt Price')
    callkeeper = fields.Float(string='Call Keeper')
    crbt = fields.Float(string='CRBT')
    sms_own = fields.Float(string='SMS Own')
    sms_other = fields.Float(string='SMS Other')
    totalcharge = fields.Float(string='Total Charge')
    additional_usage = fields.Float(string='Additional Usage')
    internetusagefee = fields.Float(string='Internet Usage Fee')
    vat = fields.Float(string='VAT')
    monthly_total = fields.Float(string='Monthly Total')
    prebalancecharge = fields.Float(string='Pre-Balance Charge')
    granttotal = fields.Float(string='Grand Total')

    # -- usage --
    duration_other_call = fields.Char(string='Duration Other Call')
    sum_charge_other_call = fields.Float(string='Sum Charge Other Call')
    duration_own_network = fields.Char(string='Duration Own Network')
    sum_charge_own_network = fields.Float(string='Sum Charge Own Network')
    count_sms_own_network = fields.Integer(string='Count SMS Own Network')
    count_sms_other = fields.Integer(string='Count SMS Other')
    duration_special_call = fields.Char(string='Duration Special Call')
    sum_charge_special_call = fields.Float(string='Sum Charge Special Call')
    download_upload = fields.Char(string='Download/Upload')

    # -- plan limits --
    data_limit = fields.Char(string='Data Limit')
    data_nemelt = fields.Char(string='Data Nemelt')
    own_network_limit = fields.Char(string='Own Network Limit')
    sms_limit = fields.Char(string='SMS Limit')
    other_network_call_limit = fields.Char(string='Other Network Call Limit')
    all_network_call_limit = fields.Char(string='All Network Call Limit')

    # -- sync metadata --
    billing_cycle_id = fields.Integer(string='Billing Cycle ID', index=True)

    _sql_constraints = [
        ('bill_id_cycle_uniq', 'unique(bill_id, billing_cycle_id)',
         'A bill row for this cycle already exists.'),
    ]

    # ---------------------------------------------------------------
    # Oracle connection
    # ---------------------------------------------------------------
    def _get_oracle_connection(self):
        icp = self.env['ir.config_parameter'].sudo()
        user = icp.get_param('gmobile_oracle.user','cc_post_bill')
        password = icp.get_param('gmobile_oracle.password','m8#K2qL9$vP6zR')
        host = icp.get_param('gmobile_oracle.host', '10.10.11.112')
        port = int(icp.get_param('gmobile_oracle.port', '1521'))
        sid = icp.get_param('gmobile_oracle.sid', 'cc')

        if not user or not password:
            raise UserError(
                "Oracle credentials are not set in System Parameters "
                "(gmobile_oracle.user / gmobile_oracle.password)."
            )

        dsn = oracledb.makedsn(host, port, sid=sid)
        conn = oracledb.connect(user=user, password=password, dsn=dsn)
        conn.call_timeout = 120 * 60 * 1000  # 120 min guard against runaway queries
        return conn

    # ---------------------------------------------------------------
    # Query builder
    # ---------------------------------------------------------------
    def _build_query(self, cycle_id):
        """cycle_id is interpolated into DB-link table names (Oracle can't bind
        object names), so it MUST be int-cast before this runs."""
        cycle_id = int(cycle_id)
        return f"""
            WITH cycle_dates AS (
                SELECT cycle_begin_date, cycle_end_date, billing_cycle_id, DEBT_DATE
                  FROM cc.billing_cycle
                 WHERE billing_cycle_id = :cycle_id
            ),
            packinfo_prep AS (
                SELECT s.subs_id, s.acct_id, s.acc_nbr, s.cust_id,
                       pp.price_plan_name, sui.price_plan_id AS main_plan_id,
                       sui.subs_upp_inst_id,
                       MAX(CASE WHEN sui1.price_plan_id IN (2322,2320,2321,2400,2340) THEN sui1.price_plan_id END) AS perfect_plan,
                       MAX(CASE WHEN sui1.price_plan_id IN (4782,4899,6344) THEN sui1.price_plan_id END) AS nemelt_plan,
                       MAX(CASE WHEN suiv.attr_id = 1766 THEN suiv.value END) AS val_1766,
                       MAX(CASE WHEN suiv.attr_id = 2185 THEN suiv.value END) AS val_2185,
                       MAX(CASE WHEN suiv.attr_id = 1768 THEN suiv.value END) AS val_1768
                  FROM cc.subs s
                 CROSS JOIN cycle_dates cd
                 INNER JOIN cc.prod pr ON s.subs_id = pr.prod_id
                        AND pr.prod_state <> 'B' OR (pr.prod_state = 'B' AND pr.prod_state_date > cd.cycle_begin_date)
                 INNER JOIN cc.subs_upp_inst sui ON s.subs_id = sui.subs_id
                 INNER JOIN cc.price_plan pp ON sui.price_plan_id = pp.price_plan_id
                  LEFT JOIN cc.subs_upp_inst sui1 ON s.subs_id = sui1.subs_id
                        AND sui1.price_plan_id IN (4782,4899,6344,2322,2320,2321,2400,2340)
                        AND (sui1.exp_date >= cd.cycle_end_date OR sui1.exp_date IS NULL)
                        AND sui1.eff_date < cd.cycle_end_date
                  LEFT JOIN cc.subs_upp_inst_value suiv ON sui.subs_upp_inst_id = suiv.subs_upp_inst_id
                        AND suiv.attr_id IN (1766, 2185, 1768)
                 WHERE s.acc_nbr NOT LIKE '48%'
                   AND LENGTH(s.acc_nbr) = 8
                   AND sui.price_plan_id IN (602,601,600,421,2360,2300,4120,4328,603,607,
                                              1900,1920,4580,4800,4801,4937,4938,4939,6596,6597,6637)
                   AND (sui.exp_date >= cd.cycle_end_date OR sui.exp_date IS NULL)
                   AND sui.eff_date < cd.cycle_end_date
                 GROUP BY s.subs_id, s.acct_id, s.acc_nbr, pp.price_plan_name,
                          sui.price_plan_id, sui.subs_upp_inst_id, s.cust_id
            ),
            ai_stuff AS (
                SELECT ai.acct_id,
                       nvl(SUM(CASE WHEN ait.parent_id = 2 AND ait.acct_item_type_id NOT IN (110,205,211,231,263,201) THEN ai.charge END)/100,0) AS FIXEDMONTHFEE,
                       nvl(SUM(CASE WHEN (ait.acct_item_type_name LIKE 'Roaming%' OR ait.acct_item_type_id IN (205,261,201)) THEN ai.charge END)/100,0) AS OTHER_USAGE,
                       nvl(SUM(CASE WHEN ait.acct_item_type_id IN (211,231,263) THEN ai.charge END)/100,0) AS DATA_NEMELT_UNE,
                       nvl(SUM(CASE WHEN ait.acct_item_type_id = 110 THEN ai.charge END)/100,0) AS CALLKEEPER,
                       nvl(SUM(CASE WHEN ait.acct_item_type_id IN (38,101) THEN ai.charge END)/100,0) AS CRBT,
                       nvl(SUM(CASE WHEN ait.parent_id = 5 AND ait.acct_item_type_id = 22 THEN ai.charge END)/100,0) AS SMS_OWN,
                       nvl(SUM(CASE WHEN ait.parent_id = 5 AND ait.acct_item_type_id <> 22 THEN ai.charge END)/100,0) AS SMS_OTHER,
                       nvl(SUM(CASE WHEN ait.acct_item_type_name NOT LIKE 'VAT%' THEN ai.charge END)/100,0) AS TOTALCHARGE,
                       nvl(SUM(CASE WHEN ait.acct_item_type_name NOT LIKE 'VAT%' AND ait.acct_item_type_id <> 71
                                    AND (ait.parent_id <> 2 OR ait.parent_id IS NULL OR ait.acct_item_type_id = 110) THEN ai.charge END)/100,0) AS ADDITIONAL_USAGE,
                       nvl(SUM(CASE WHEN ait.acct_item_type_id = 19 THEN ai.charge END)/100,0) AS INTERNETUSAGEFEE,
                       nvl(SUM(CASE WHEN ait.acct_item_type_name LIKE 'VAT%' THEN ai.charge END)/100,0) AS VAT
                  FROM cc.acct_item ai
                 INNER JOIN cc.acct_item_type ait ON ai.acct_item_type_id = ait.acct_item_type_id
                 INNER JOIN cycle_dates cd ON ai.billing_cycle_id = cd.billing_cycle_id
                 WHERE ai.acct_id IN (SELECT acct_id FROM packinfo_prep)
                 GROUP BY ai.acct_id
            ),
            usagevs AS (
                SELECT t.subs_id,
                       SUM(CASE WHEN t.re_id IN ('1044','1046','1077','1079','960','962') AND t.duration>0 THEN t.duration END) DURATION_OWN_NETWORK,
                       SUM(CASE WHEN t.re_id IN ('1044','1046','1077','1079','960','962') AND t.duration>0 THEN t.charge1/100 END) SUM_CHARGE_OWN_NETWORK,
                       SUM(CASE WHEN t.re_id NOT IN ('1233','1449','1951','1953','1950','1452','1453','1239','1707','1045','1235','1708','1078','1124','1874','1129','1719',
                                                      '1919','1856','1123','1130','1127','1131','1667','1109','1875','1115','1718','1920','1857','1118','1116','1112','1117',
                                                      '1668','1735','1905','1906','1044','1079','1046','962','960','1077','1091','1058','1007','1080','966','2098','2099','2188','2191')
                                AND t.duration>0 THEN t.duration END) duration_other_call,
                       SUM(CASE WHEN t.re_id NOT IN ('1233','1449','1951','1953','1950','1452','1453','1239','1707','1045','1235','1708','1078','1124','1874','1129','1719',
                                                      '1919','1856','1123','1130','1127','1131','1667','1109','1875','1115','1718','1920','1857','1118','1116','1112','1117',
                                                      '1668','1735','1905','1906','1044','1079','1046','962','960','1077','1091','1058','1007','1080','966','2098','2099','2188','2191')
                                AND t.duration>0 THEN t.charge1/100 END) sum_charge_other_call,
                       SUM(CASE WHEN t.re_id IN ('1091','1058','1007','1080','966') AND t.duration>0 THEN t.duration END) duration_special_call,
                       SUM(CASE WHEN t.re_id IN ('1091','1058','1007','1080','966') AND t.duration>0 THEN t.charge1/100 END) sum_charge_special_call,
                       COUNT(CASE WHEN t.re_id IN ('1123','1118') AND t.duration = 0 THEN t.re_id END) count_sms_own_network,
                       COUNT(CASE WHEN t.re_id IN ('1124','1874','1129','1719','1919','1856','1130','1127','1131','1667','1109','1875','1115','1718','1920',
                                                    '1857','1116','1112','1117','1668','1735','1905','1906','2098','2099','2188','2191') AND t.duration=0 THEN t.re_id END) count_sms_other
                  FROM rb.EVENT_USAGE_{cycle_id}@link_rb t
                 WHERE t.subs_id IN (SELECT subs_id FROM packinfo_prep)
                 GROUP BY t.subs_id
            ),
            usagedata AS (
                SELECT t.subs_id, ROUND(SUM(t.byte_up+t.byte_down)/1024/1024,2)||' MB' AS download_upload
                  FROM rb.EVENT_USAGE_C_{cycle_id}@link_rb t
                 WHERE subs_id IN (SELECT subs_id FROM packinfo_prep)
                 GROUP BY subs_id
            )
            SELECT bill.bill_id,
                   to_char(cd.CYCLE_BEGIN_DATE,'yyyy/mm/dd')||'-'||to_char(cd.CYCLE_END_DATE,'yyyy/mm/dd') BILLPERIOD,
                   to_char(cd.DEBT_DATE-12,'yyyy/mm/dd') DUE_DATE,
                   to_char(cd.DEBT_DATE,'yyyy/mm/dd') DEBT_DATE,
                   cu.cust_name CUSTNAME,
                   p_info.acct_id, p_info.acc_nbr PHONENUM,
                   ais.FIXEDMONTHFEE, ais.OTHER_USAGE, ais.DATA_NEMELT_UNE, ais.CALLKEEPER, ais.CRBT,
                   ais.SMS_OWN, ais.SMS_OTHER, ais.TOTALCHARGE, ais.ADDITIONAL_USAGE, ais.INTERNETUSAGEFEE, ais.VAT,
                   ais.TOTALCHARGE + ais.VAT MONTHLY_TOTAL,
                   bill.recv_charge + (nvl(bill.PRE_BALANCE,0)+nvl(bill.ADJUST_CHARGE,0)) PREBALANCECHARGE,
                   (bill.DUE + nvl(bill.CHARGE_BE_ADJUSTED,0) + nvl(bill.Dispute_Charge,0) + nvl(bill.RECV_CHARGE,0)
                    + (nvl(bill.PRE_BALANCE,0)+nvl(bill.ADJUST_CHARGE,0))) GRANTTOTAL,
                   TO_CHAR(TRUNC(uvs.duration_other_call/3600),'FM9900')||':'||TO_CHAR(TRUNC(MOD(uvs.duration_other_call,3600)/60),'FM00')||':'||TO_CHAR(MOD(uvs.duration_other_call,60),'FM00') duration_other_call,
                   uvs.sum_charge_other_call,
                   TO_CHAR(TRUNC(uvs.DURATION_OWN_NETWORK/3600),'FM9900')||':'||TO_CHAR(TRUNC(MOD(uvs.DURATION_OWN_NETWORK,3600)/60),'FM00')||':'||TO_CHAR(MOD(uvs.DURATION_OWN_NETWORK,60),'FM00') DURATION_OWN_NETWORK,
                   uvs.SUM_CHARGE_OWN_NETWORK, uvs.count_sms_own_network, uvs.count_sms_other,
                   TO_CHAR(TRUNC(uvs.duration_special_call/3600),'FM9900')||':'||TO_CHAR(TRUNC(MOD(uvs.duration_special_call,3600)/60),'FM00')||':'||TO_CHAR(MOD(uvs.duration_special_call,60),'FM00') duration_special_call,
                   uvs.sum_charge_special_call, ud.download_upload,
                   CASE WHEN p_info.main_plan_id = 421 THEN N'200MB'
                        WHEN p_info.main_plan_id IN (603) THEN N'1GB'
                        WHEN p_info.main_plan_id IN (600,1900) THEN N'2GB'
                        WHEN p_info.main_plan_id IN (4937) THEN N'3GB'
                        WHEN p_info.main_plan_id IN (601,1920) THEN N'5GB'
                        WHEN p_info.main_plan_id IN (4938) THEN N'8GB'
                        WHEN p_info.main_plan_id IN (602) THEN N'10GB'
                        WHEN p_info.main_plan_id IN (4939) THEN N'15GB'
                        WHEN p_info.main_plan_id IN (6637) THEN N'30GB'
                        WHEN p_info.main_plan_id IN (2300,2360) THEN
                             CASE p_info.perfect_plan WHEN 2322 THEN N'10GB' WHEN 2320 THEN N'2GB' WHEN 2321 THEN N'5GB'
                                  WHEN 2400 THEN N'хязгааргүй' WHEN 2340 THEN N'хязгааргүй' ELSE NULL END
                        WHEN p_info.main_plan_id IN (4328,4120) THEN
                             CASE p_info.val_2185 WHEN '2' THEN N'1GB' WHEN '3' THEN N'20GB' WHEN '4' THEN N'5GB'
                                  WHEN '5' THEN N'10GB' WHEN '6' THEN N'5GB' WHEN '7' THEN N'40GB' WHEN '8' THEN N'20GB'
                                  WHEN '9' THEN N'10GB' WHEN '10' THEN N'30GB' WHEN '11' THEN N'60GB' WHEN '12' THEN N'хязгааргүй'
                                  WHEN '13' THEN N'10GB' WHEN '14' THEN N'5GB' WHEN '15' THEN N'25GB' WHEN '22' THEN N'1GB' ELSE NULL END
                        WHEN p_info.main_plan_id IN (6596,6597) THEN
                             CASE p_info.val_2185 WHEN '24' THEN N'10GB' WHEN '25' THEN N'1GB' WHEN '16' THEN N'10GB'
                                  WHEN '17' THEN N'15GB' WHEN '18' THEN N'20GB' WHEN '19' THEN N'30GB' WHEN '20' THEN N'60GB'
                                  WHEN '21' THEN N'хязгааргүй' WHEN '23' THEN N'25GB' ELSE NULL END
                   ELSE NULL END AS DATA_LIMIT,
                   CASE p_info.nemelt_plan WHEN 4782 THEN N'5GB' WHEN 4899 THEN N'10GB' WHEN 6344 THEN N'2GB' ELSE NULL END AS DATA_NEMELT,
                   CASE WHEN p_info.main_plan_id IN (602,600,601,1920,4580,4800,4801,4937,4938,4939) THEN N'хязгааргүй'
                        WHEN p_info.main_plan_id IN (2300,2360) AND p_info.val_1766 IN ('1','3') THEN N'хязгааргүй'
                        WHEN p_info.main_plan_id IN (4328,4120) AND p_info.val_2185 IN ('2','5','6','8','9','14','15') THEN N'хязгааргүй'
                        WHEN p_info.main_plan_id IN (6596,6597) AND p_info.val_2185 IN ('25','16','17') THEN N'хязгааргүй'
                        WHEN p_info.main_plan_id IN (6596,6597) AND p_info.val_2185 IN ('24') THEN N'100'
                   ELSE NULL END AS OWN_NETWORK_LIMIT,
                   CASE WHEN p_info.main_plan_id = 421 THEN N'50' WHEN p_info.main_plan_id = 4937 THEN N'30'
                        WHEN p_info.main_plan_id IN (600,1920) THEN N'200' WHEN p_info.main_plan_id = 6637 THEN N'300'
                        WHEN p_info.main_plan_id = 601 THEN N'500' WHEN p_info.main_plan_id IN (602,4938,4939) THEN N'хязгааргүй'
                        WHEN p_info.main_plan_id IN (2300,2360) THEN
                             CASE p_info.val_1768 WHEN '1' THEN N'сүлжээндээ хязгааргүй' WHEN '2' THEN N'хязгааргүй' ELSE NULL END
                        WHEN p_info.main_plan_id IN (4328,4120) THEN
                             CASE WHEN p_info.val_2185 IN ('3','4','5','6') THEN N'100'
                                  WHEN p_info.val_2185 IN ('7','8','9') THEN N'300'
                                  WHEN p_info.val_2185 IN ('10','11','12') THEN N'хязгааргүй' ELSE NULL END
                        WHEN p_info.main_plan_id IN (6596,6597) THEN
                             CASE WHEN p_info.val_2185 = '17' THEN N'100' WHEN p_info.val_2185 = '18' THEN N'150'
                                  WHEN p_info.val_2185 = '19' THEN N'300' WHEN p_info.val_2185 = '20' THEN N'500'
                                  WHEN p_info.val_2185 = '21' THEN N'хязгааргүй' ELSE NULL END
                   ELSE NULL END AS SMS_LIMIT,
                   CASE WHEN p_info.main_plan_id IN (4800) THEN N'100 минут'
                        WHEN p_info.main_plan_id IN (421,4939) THEN N'150 минут'
                        WHEN p_info.main_plan_id = 4937 THEN N'30 минут' WHEN p_info.main_plan_id = 4938 THEN N'30 минут'
                        WHEN p_info.main_plan_id IN (600,1920) THEN N'200 минут' WHEN p_info.main_plan_id IN (601,4801) THEN N'500 минут'
                        WHEN p_info.main_plan_id IN (602) THEN N'1000 минут'
                        WHEN p_info.main_plan_id IN (2300,2360) AND p_info.val_1766 = '3' THEN N'250 минут'
                        WHEN p_info.main_plan_id IN (4328,4120) THEN
                             CASE WHEN p_info.val_2185 IN ('6','8') THEN N'200 минут' WHEN p_info.val_2185 = '9' THEN N'500 минут' ELSE NULL END
                        WHEN p_info.main_plan_id IN (6596,6597) THEN
                             CASE WHEN p_info.val_2185 = '24' THEN N'20 минут' WHEN p_info.val_2185 = '25' THEN N'25 минут'
                                  WHEN p_info.val_2185 = '16' THEN N'50 минут' WHEN p_info.val_2185 = '17' THEN N'500 минут' ELSE NULL END
                   ELSE NULL END AS OTHER_NETWORK_CALL_LIMIT,
                   CASE WHEN p_info.main_plan_id IN (603) THEN N'100 минут' WHEN p_info.main_plan_id IN (607,1900) THEN N'200 минут'
                        WHEN p_info.main_plan_id = 6637 THEN N'хязгааргүй'
                        WHEN p_info.main_plan_id IN (2300,2360) AND p_info.val_1766 = '2' THEN N'хязгааргүй'
                        WHEN p_info.main_plan_id IN (4328,4120) THEN
                             CASE WHEN p_info.val_2185 = '1' THEN N'250 минут' WHEN p_info.val_2185 = '4' THEN N'500 минут'
                                  WHEN p_info.val_2185 IN ('10','11','12') THEN N'хязгааргүй' ELSE NULL END
                        WHEN p_info.main_plan_id IN (6596,6597) THEN
                             CASE WHEN p_info.val_2185 = '23' THEN N'25 минут'
                                  WHEN p_info.val_2185 IN ('18','19','20','21') THEN N'хязгааргүй' ELSE NULL END
                   ELSE NULL END AS ALL_NETWORK_CALL_LIMIT
              FROM packinfo_prep p_info
             CROSS JOIN cycle_dates cd
             INNER JOIN cc.acct ac ON p_info.acct_id = ac.acct_id AND ac.postpaid = 'Y'
             INNER JOIN cc.prod p ON p.prod_id = p_info.subs_id
              LEFT JOIN ai_stuff ais ON p_info.acct_id = ais.acct_id
             INNER JOIN cc.bill bill ON p_info.acct_id = bill.acct_id AND bill.billing_cycle_id = cd.billing_cycle_id
             INNER JOIN cc.cust cu ON p_info.cust_id = cu.cust_id
              LEFT JOIN usagevs uvs ON p_info.subs_id = uvs.subs_id
              LEFT JOIN usagedata ud ON p_info.subs_id = ud.subs_id
             WHERE (p.prod_state <> 'B' OR (p.prod_state = 'B' AND p.prod_state_date > cd.cycle_begin_date))
        """

    # ---------------------------------------------------------------
    # Row mapping
    # ---------------------------------------------------------------
    def _row_to_vals(self, col_index, row, cycle_id):
        def g(col):
            return row[col_index[col]]

        return {
            'bill_id': g('BILL_ID'),
            'billperiod': g('BILLPERIOD'),
            'due_date': g('DUE_DATE'),
            'debt_date': g('DEBT_DATE'),
            'custname': g('CUSTNAME'),
            'acct_id': g('ACCT_ID'),
            'phonenum': g('PHONENUM'),
            'fixedmonthfee': g('FIXEDMONTHFEE') or 0,
            'other_usage': g('OTHER_USAGE') or 0,
            'data_nemelt_une': g('DATA_NEMELT_UNE') or 0,
            'callkeeper': g('CALLKEEPER') or 0,
            'crbt': g('CRBT') or 0,
            'sms_own': g('SMS_OWN') or 0,
            'sms_other': g('SMS_OTHER') or 0,
            'totalcharge': g('TOTALCHARGE') or 0,
            'additional_usage': g('ADDITIONAL_USAGE') or 0,
            'internetusagefee': g('INTERNETUSAGEFEE') or 0,
            'vat': g('VAT') or 0,
            'monthly_total': g('MONTHLY_TOTAL') or 0,
            'prebalancecharge': g('PREBALANCECHARGE') or 0,
            'granttotal': g('GRANTTOTAL') or 0,
            'duration_other_call': g('DURATION_OTHER_CALL'),
            'sum_charge_other_call': g('SUM_CHARGE_OTHER_CALL') or 0,
            'duration_own_network': g('DURATION_OWN_NETWORK'),
            'sum_charge_own_network': g('SUM_CHARGE_OWN_NETWORK') or 0,
            'count_sms_own_network': g('COUNT_SMS_OWN_NETWORK') or 0,
            'count_sms_other': g('COUNT_SMS_OTHER') or 0,
            'duration_special_call': g('DURATION_SPECIAL_CALL'),
            'sum_charge_special_call': g('SUM_CHARGE_SPECIAL_CALL') or 0,
            'download_upload': g('DOWNLOAD_UPLOAD'),
            'data_limit': g('DATA_LIMIT'),
            'data_nemelt': g('DATA_NEMELT'),
            'own_network_limit': g('OWN_NETWORK_LIMIT'),
            'sms_limit': g('SMS_LIMIT'),
            'other_network_call_limit': g('OTHER_NETWORK_CALL_LIMIT'),
            'all_network_call_limit': g('ALL_NETWORK_CALL_LIMIT'),
            'billing_cycle_id': cycle_id,
        }

    def _write_batch(self, columns, rows, cycle_id, verbose=False):
        col_index = {name.upper(): i for i, name in enumerate(columns)}
        bill_ids = [str(row[col_index['BILL_ID']]) for row in rows]

        existing = self.search_read(
            [('billing_cycle_id', '=', cycle_id), ('bill_id', 'in', bill_ids)],
            ['bill_id'],
        )
        existing_map = {r['bill_id']: r['id'] for r in existing}

        to_create = []
        for row in rows:
            vals = self._row_to_vals(col_index, row, cycle_id)
            bill_id = vals['bill_id']

            if verbose:
                _logger.info(
                    "[cycle %s] bill_id=%s acct_id=%s phone=%s cust=%s total=%s grand_total=%s -> %s",
                    cycle_id, bill_id, vals['acct_id'], vals['phonenum'], vals['custname'],
                    vals['totalcharge'], vals['granttotal'],
                    'UPDATE' if bill_id in existing_map else 'CREATE',
                )

            if bill_id in existing_map:
                self.browse(existing_map[bill_id]).write(vals)
            else:
                to_create.append(vals)
        if to_create:
            self.create(to_create)

    # ---------------------------------------------------------------
    # Sync entry points
    # ---------------------------------------------------------------
    def _sync_for_cycle(self, cycle_id, batch_size=2000, verbose=False):
        cycle_id = int(cycle_id)
        query = self._build_query(cycle_id)
        total = 0

        try:
            with self._get_oracle_connection() as conn:
                with conn.cursor() as cur:
                    cur.arraysize = batch_size
                    cur.execute(query, cycle_id=cycle_id)
                    columns = [c[0] for c in cur.description]

                    if verbose:
                        _logger.info("[cycle %s] columns returned: %s", cycle_id, columns)

                    while True:
                        rows = cur.fetchmany(batch_size)
                        if not rows:
                            break

                        if verbose:
                            _logger.info("[cycle %s] fetched batch of %s rows", cycle_id, len(rows))

                        self._write_batch(columns, rows, cycle_id, verbose=verbose)
                        total += len(rows)
                        self.env.cr.commit()
                        _logger.info("[cycle %s] progress: %s rows synced so far", cycle_id, total)
        except oracledb.Error as e:
            _logger.exception("Oracle billing query failed for cycle %s", cycle_id)
            raise UserError(f"Oracle query failed: {e}")

        _logger.info("[cycle %s] sync finished: %s total rows", cycle_id, total)
        return total

    def action_manual_sync(self):
        """Button action. Manual runs default to verbose=True so you can watch
        row-by-row activity in the Odoo server log while testing."""
        self.ensure_one()
        if not self.billing_cycle_id:
            raise UserError("Set a Billing Cycle ID before syncing.")
        count = self._sync_for_cycle(self.billing_cycle_id, verbose=True)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Oracle Sync Complete',
                'message': f'{count} rows synced for cycle {self.billing_cycle_id}.',
                'sticky': False,
            },
        }

    @api.model
    def sync_cycle(self, cycle_id, verbose=True):
        """Convenience entry point, e.g. from shell:
        self.env['billing.oracle'].sync_cycle(587)"""
        return self._sync_for_cycle(cycle_id, verbose=verbose)

    @api.model
    def cron_sync_billing(self):
        icp = self.env['ir.config_parameter'].sudo()
        cycle_id = int(icp.get_param('gmobile_oracle.default_cycle_id', 587))
        if not cycle_id:
            _logger.warning("cron_sync_billing: gmobile_oracle.default_cycle_id not set, skipping")
            return
        # Cron runs quiet by default — flip this System Parameter to '1' if you
        # want per-row logging on scheduled runs too (noisy for large cycles).
        verbose = icp.get_param('gmobile_oracle.verbose_sync', '0') == '1'
        self._sync_for_cycle(cycle_id, verbose=verbose)