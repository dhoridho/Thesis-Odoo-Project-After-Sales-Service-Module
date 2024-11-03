# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools


class PosPaymentReport(models.Model):
    _name = 'pos.payment.report'
    _description = 'POS Payment Report'
    _auto = False
    _order = 'date desc'

    date = fields.Datetime(string='Order Date', readonly=True)
    payment_date = fields.Datetime(string='Payment Date', readonly=True)
    payment_method_id = fields.Many2one('pos.payment.method', string='Payment Method', readonly=True)
    config_id = fields.Many2one('pos.config', string='Point of Sale', readonly=True)
    order_id = fields.Many2one('pos.order', string='Order', readonly=True)
    session_id = fields.Many2one('pos.session', string='Session', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    pos_branch_id = fields.Many2one('res.branch', string='Branch', readonly=True)
    amount = fields.Float(string='Amount', readonly=True)
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Customer', readonly=True)

    def _select(self):
        return '''
            SELECT
	            MIN(p.id) AS id,
				po.date_order AS date,
				p.payment_date AS payment_date,
				p.payment_method_id AS payment_method_id,
				ps.config_id AS config_id,
				po.id AS order_id,
				po.session_id AS session_id,
				po.company_id AS company_id,
				p.pos_branch_id AS pos_branch_id,
				p.amount AS amount,
				po.currency_id AS currency_id,
				po.partner_id AS partner_id
        '''

    def _from(self):
        return '''
            FROM pos_payment AS p
				INNER JOIN pos_order AS po ON po.id = p.pos_order_id
				LEFT JOIN pos_session AS ps ON ps.id = po.session_id
        '''

    def _group_by(self):
        return '''
            GROUP BY
                po.date_order,
				p.payment_date,
				p.payment_method_id,
				ps.config_id,
				po.id,
				po.session_id,
				po.company_id,
				p.pos_branch_id,
				p.amount,
				po.currency_id,
				po.partner_id
        '''

    def init(self):
        tools.drop_view_if_exists(self._cr, self._table)
        self._cr.execute('''
            CREATE OR REPLACE VIEW %s AS (
                %s
                %s
                %s
            )
        ''' % (self._table, self._select(), self._from(), self._group_by())
        )
