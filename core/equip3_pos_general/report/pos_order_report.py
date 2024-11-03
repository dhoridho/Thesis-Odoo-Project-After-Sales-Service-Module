# -*- coding: utf-8 -*-

from odoo import models, fields

class ReportPosOrder(models.Model):
    _inherit = "report.pos.order"

    pos_branch_id = fields.Many2one('res.branch', 'Branch')
    promotion_count = fields.Integer(string='Promotion Count', readonly=1)
    promotion_id = fields.Many2one('pos.promotion', string='Promotion', readonly=1)
    # seller_id = fields.Many2one('res.users', 'Sale Man')
    hour_group_id = fields.Many2one('hour.group', string='Hour Group')
    zone_id = fields.Many2one('pos.zone', string='Zone')

    voucher_id = fields.Many2one('pos.voucher', string='Voucher', readonly=1)
    voucher_count = fields.Integer(string='Voucher Count', readonly=1)
    voucher_value = fields.Float(string='Voucher Value', readonly=1)

    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        'Analytic Account'
    )

    cashier_id = fields.Many2one('res.users', string='Cashier', readonly=True)


    def _select(self):
        _select = '''
            ,
            l.promotion_id as promotion_id,
            l.zone_id as zone_id,
            l.pos_branch_id as pos_branch_id,
            s.hour_group_id as hour_group_id,
            l.analytic_account_id as analytic_account_id,
            COUNT(l.promotion_id) AS promotion_count,
            ( 
                SELECT pvh.voucher_id 
                FROM pos_voucher_use_history pvh 
                WHERE pvh.pos_order_id=s.id LIMIT 1
            ) as voucher_id,
            (   
                SELECT SUM(pvh.value) 
                FROM pos_voucher_use_history pvh 
                WHERE pvh.pos_order_id=s.id 
            ) as voucher_value,
            (   
                SELECT COUNT(pvh.voucher_id) 
                FROM pos_voucher_use_history pvh 
                WHERE pvh.pos_order_id=s.id 
            ) as voucher_count,
            s.cashier_id AS cashier_id
        '''
        return super(ReportPosOrder, self)._select() + _select

    def _group_by(self):
        _group_by = '''
            ,
            l.promotion_id,
            l.zone_id,
            l.pos_branch_id,
            l.user_id,
            l.analytic_account_id,
            s.id,
            s.hour_group_id,
            s.cashier_id
        '''
        return super(ReportPosOrder, self)._group_by() + _group_by

    def _from(self):
        _from = '''

        '''
        return super(ReportPosOrder, self)._from() + _from