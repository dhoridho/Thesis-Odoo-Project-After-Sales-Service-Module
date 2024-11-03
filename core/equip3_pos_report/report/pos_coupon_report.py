# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools

class PosCouponReport(models.Model):
    _name = 'pos.coupon.report'
    _description = 'POS Coupon Report'
    _auto = False
    _order = 'name asc'

    name = fields.Char(string='Name', readonly=True)
    used_date = fields.Datetime(string='Order Date', readonly=True)
    number = fields.Char(string='Number', readonly=True)
    code = fields.Char(string='EAN13', readonly=True)
    pos_order_id = fields.Many2one('pos.order', string='Order ID', readonly=True)
    config_id = fields.Many2one('pos.config', string='POS', readonly=True)
    session_id = fields.Many2one('pos.session', string='Session', readonly=True)
    reward_type = fields.Selection([
        ('Discount','Discount'),
        ('Free Item','Free Item'),
    ], string='Reward', readonly=True)
    pos_branch_id = fields.Many2one('res.branch', string='Branch', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)


    @property
    def _table_query(self):
        return '%s %s %s' % (self._select(), self._from(), self._where())

    @api.model
    def _select(self):
        return '''
            SELECT
                ch.id AS id,
                c.name AS name,
                ch.used_date AS used_date, 
                c.number AS number,
                c.code AS code,
                c.reward_type AS reward_type,
                ch.pos_order_id AS pos_order_id,
                po.session_id AS session_id,
                ps.config_id AS config_id,
                po.pos_branch_id AS pos_branch_id,
                po.company_id AS company_id
        '''

    @api.model
    def _from(self):
        return '''
            FROM pos_coupon_use_history AS ch
                INNER JOIN pos_coupon AS c ON c.id = ch.coupon_id
                INNER JOIN pos_order AS po ON po.id = ch.pos_order_id
                INNER JOIN pos_session AS ps ON ps.id = po.session_id
            ''' 

    @api.model
    def _where(self):
        return '''

        '''