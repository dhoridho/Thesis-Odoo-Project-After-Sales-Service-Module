# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools

class PosVoucherReport(models.Model):
    _name = 'pos.voucher.report'
    _description = 'POS Voucher Report'
    _auto = False
    _order = 'name asc'

    name = fields.Char(string='Name/Number', readonly=True)
    used_date = fields.Datetime(string='Order Date', readonly=True)
    number = fields.Char(string='Number', readonly=True)
    code = fields.Char(string='EAN13', readonly=True)
    pos_order_id = fields.Many2one('pos.order', string='Order ID', readonly=True)
    config_id = fields.Many2one('pos.config', string='POS', readonly=True)
    session_id = fields.Many2one('pos.session', string='Session', readonly=True)
    apply_type = fields.Selection([
        ('fixed_amount', 'Fixed amount'),
        ('percent', 'Percent (%)'),
    ], string='Apply', readonly=True)
    amount = fields.Float(string='Amount', readonly=True)
    pos_branch_id = fields.Many2one('res.branch', string='Branch', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)


    @property
    def _table_query(self):
        return '%s %s %s' % (self._select(), self._from(), self._where())

    @api.model
    def _select(self):
        return '''
            SELECT
                vh.id AS id,
                v.number AS name,
                vh.used_date AS used_date, 
                v.number AS number,
                v.code AS code,
                v.apply_type AS apply_type,
                vh.pos_order_id AS pos_order_id,
                po.session_id AS session_id,
                ps.config_id AS config_id,
                po.pos_branch_id AS pos_branch_id,
                po.company_id AS company_id,
                po.voucher_amount AS amount
        '''

    @api.model
    def _from(self):
        return '''
            FROM pos_voucher_use_history AS vh
                INNER JOIN pos_voucher AS v ON v.id = vh.voucher_id
                INNER JOIN pos_order AS po ON po.id = vh.pos_order_id
                INNER JOIN pos_session AS ps ON ps.id = po.session_id 
            ''' 

    @api.model
    def _where(self):
        return '''

        '''