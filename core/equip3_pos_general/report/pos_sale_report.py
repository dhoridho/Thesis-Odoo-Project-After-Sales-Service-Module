# -*- coding: utf-8 -*-

import pytz
from pytz import timezone

from odoo import fields, models, api, _


class pos_sale_report_template(models.AbstractModel):
    _name = 'report.equip3_pos_general.pos_sale_report_template'
    _description = "Template Report of sale"

    @api.model
    def _get_report_values(self, doc_ids, data=None):
        report = self.env['ir.actions.report']._get_report_from_name('equip3_pos_general.pos_sale_report_template')
        return {
            'doc_ids': doc_ids or data['form']['session_ids'],
            'doc_model': report.model,
            'docs': self.env['pos.session'].browse(doc_ids or data['form']['session_ids']),
            'data': data,
        }


class pos_sale_report(models.TransientModel):
    _name = 'pos.sale.report'
    _description = "Z-Report Backend"

    @api.model
    def _get_report_values(self, docids, data=None):
        if self.env.user and self.env.user.tz:
            tz = self.env.user.tz
            tz = timezone(tz)
        else:
            tz = pytz.utc
        report = self.env['ir.actions.report']._get_report_from_name('equip3_pos_general.pos_sale_report_template')
        return {
            'doc_ids': self.env['pos.sale.report'].browse(data['ids']),
            'doc_model': report.model,
            'docs': self.env['pos.session'].browse(data['form']['session_ids']),
            'data': data,
            'tz': tz,
        }

    def get_receivable_by_session_id(self, session_ids): 
        values = {}

        query = '''
            SELECT 
                po.session_id,
                SUM(pp.amount)
            FROM pos_order AS po
            INNER JOIN pos_session AS ps ON ps.id = po.session_id
            INNER JOIN pos_payment AS pp ON pp.pos_order_id = po.id
            INNER JOIN pos_payment_method AS ppm ON ppm.id = pp.payment_method_id
            WHERE ppm.is_receivables = 't'
                AND po.session_id IN ({ids})
            GROUP BY po.session_id
        '''.format(ids=str(session_ids)[1:-1])
        self._cr.execute(query)
        results = self._cr.fetchall()
        for result in results:
            values[result[0]] = result[1]

        return values

    def get_payment_receivable_by_session_id(self, session_ids):
        values = {}
        query = '''
        SELECT
            t.session_id,
            t.payment_method_id,
            t.payment_method_name,
            -- t.payment_date,
            -- t.payment_date_for_receivable,
            SUM(t.payment_amount)
        FROM(
            SELECT  
                po.session_id AS session_id, 
                pp.amount AS payment_amount,
                ppm.id AS payment_method_id,
                ppm.name  AS payment_method_name,
                (
                    SELECT b_ppm.is_receivables
                    FROM pos_payment AS b_pp 
                    INNER JOIN pos_payment_method AS b_ppm ON b_ppm.id = b_pp.payment_method_id
                    WHERE b_pp.pos_order_id = po.id AND b_ppm.is_receivables = 't'
                    LIMIT 1
                ) AS is_payment_for_receivable, -- Check if payment using payment method Receivables

                pp.payment_date AS payment_date,
                (
                    SELECT b_pp.payment_date
                    FROM pos_payment AS b_pp
                    INNER JOIN pos_payment_method AS b_ppm ON b_ppm.id = b_pp.payment_method_id
                    WHERE b_pp.pos_order_id = po.id AND b_ppm.is_receivables = 't'
                    LIMIT 1
                ) AS payment_date_for_receivable -- Get if payment_date using payment method Receivables

            FROM pos_order AS po
            INNER JOIN pos_session AS ps ON ps.id = po.session_id
            INNER JOIN pos_payment AS pp ON pp.pos_order_id = po.id
            INNER JOIN pos_payment_method AS ppm ON ppm.id = pp.payment_method_id
            WHERE po.session_id IN ({ids})
                AND (ppm.is_receivables IS NULL OR ppm.is_receivables = 'f') -- don't count payment with Receivables
                AND (ppm.is_deposit_payment IS NULL OR ppm.is_deposit_payment = 'f') -- don't count payment with Member Deposit
        ) AS t
        WHERE t.is_payment_for_receivable = 't'
            AND t.payment_date != t.payment_date_for_receivable -- don't count if payment with multi payment in POS Screen
        GROUP BY t.session_id, t.payment_method_id, t.payment_method_name
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


    def _report_data(self, session_ids):
        data = {}
        ids = session_ids.ids
        if ids:
            data['receivable_by_session_id'] = self.get_receivable_by_session_id(ids)
            data['payment_receivable_by_session_id'] = self.get_payment_receivable_by_session_id(ids)
        return data

    def print_receipt(self):
        data = {
            'ids': self._ids,
            'form': self.read()[0],
            'model': 'pos.sale.report',
        }
        return self.env.ref('equip3_pos_general.report_pos_sales_pdf').report_action(self, data=data)

    session_ids = fields.Many2many('pos.session', 'pos_sale_report_session_rel', 'wizard_id', 'session_id',
                                   string="Session(s) need Report")
    report_type = fields.Selection([('thermal', 'Thermal'),
                                    ('pdf', 'PDF')], default='pdf', readonly=True, string="Report Type")
    branch_id = fields.Many2one('res.branch', string='Branch', default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, domain=lambda self: [('id', 'in', self.env.branches.ids)])
    company_id = fields.Many2one('res.company', string='Company',default=lambda self: self.env.company.id)
