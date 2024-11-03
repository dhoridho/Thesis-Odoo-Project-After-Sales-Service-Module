# -*- coding: utf-8 -*-

from odoo import fields, models, api, _

class PosSaleReport(models.TransientModel):
    _inherit = 'pos.sale.report'


    def _report_data(self, session_ids):
        data = super(PosSaleReport, self)._report_data(session_ids)
        
        ids = session_ids.ids
        if ids:
            data['redeem_point_by_session_id'] = self.get_redeem_point_by_session_id(ids)
            data['deposit_used_by_session_id'] = self.get_deposit_used_by_session_id(ids)
            data['member_deposit_by_session_id'] = self.get_member_deposit_by_session_id(ids)
        return data

    def get_redeem_point_by_session_id(self, session_ids):
        values = {}
            
        query = '''
            SELECT
                po.session_id,
                SUM(
                    CASE WHEN l.type = 'redeem' THEN l.point ELSE 0 END
                ) AS redeem_point
            FROM pos_loyalty_point AS l
            INNER JOIN pos_order AS po ON po.id = l.order_id
            INNER JOIN pos_session AS ps ON ps.id = po.session_id
            WHERE po.session_id IN ({ids})
            GROUP BY po.session_id
        '''.format(ids=str(session_ids)[1:-1])
        self._cr.execute(query)
        results = self._cr.fetchall()
        for result in results:
            values[result[0]] = result[1] 

        return values

    def get_deposit_used_by_session_id(self, session_ids):
        values = {}
        deposit_used_query = '''
            SELECT 
                po.session_id,
                SUM(pp.amount)
            FROM pos_order AS po
            INNER JOIN pos_session AS ps ON ps.id = po.session_id
            INNER JOIN pos_payment AS pp ON pp.pos_order_id = po.id
            INNER JOIN pos_payment_method AS ppm ON ppm.id = pp.payment_method_id
            WHERE ppm.is_deposit_payment = 't'
                AND po.session_id IN ({ids})
            GROUP BY po.session_id
        '''.format(ids=str(session_ids)[1:-1])
        self._cr.execute(deposit_used_query)
        results = self._cr.fetchall()
        for result in results:
            values[result[0]] = result[1]
        return values
        

    def get_member_deposit_by_session_id(self, session_ids):
        values = {}
        query = '''
        
        SELECT 
            t.pos_session_id,
            t.payment_id,
            t.payment_name,
            SUM(t.total)
        FROM (

            SELECT 
                cd.create_from_session_id AS pos_session_id, 
                aj.id AS payment_id,
                aj.name AS payment_name, 
                COALESCE(cd.origin_create_amount, 0) AS total
            FROM customer_deposit AS cd
            INNER JOIN account_journal AS aj ON aj.id = cd.journal_id
            WHERE cd.create_from_session_id IN ({ids})

            UNION

            SELECT 
                am.create_from_session_id AS pos_session_id,
                am.deposit_account_journal_id AS payment_id,
                aj.name AS payment_name,
                SUM(am.amount_total_signed) AS total
            FROM account_move AS am
            INNER JOIN cust_deposit_history_rel AS c_rel ON c_rel.move_id = am.id
            INNER JOIN customer_deposit AS cd ON cd.id = c_rel.deposit_id
            INNER JOIN account_journal AS aj ON aj.id = am.deposit_account_journal_id

            WHERE am.create_from_session_id IN ({ids})
            GROUP BY am.create_from_session_id,
                am.deposit_account_journal_id,
                aj.name
        ) AS t
        GROUP BY pos_session_id, payment_id, payment_name

        '''.format(ids=str(session_ids)[1:-1])
        self._cr.execute(query)

        results = self._cr.fetchall()
        for result in results:
            session_id = result[0]
            payment_method_id = result[1]
            payment_method_name = result[2]
            amount = result[3]
            value = { 
                'total_amount': amount, 
                'payment_name': payment_method_name
            }
            if session_id not in values: 
                values[session_id] = [value]
            else:
                values[session_id] += [value]

        return values