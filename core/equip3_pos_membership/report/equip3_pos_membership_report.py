# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools

class Equip3PosMembershipReport(models.Model):
    _name = "equip3.pos.membership.report"
    _description = "POS Membership Report"
    _auto = False
    _order = 'name asc'

    name = fields.Char(string='Name', readonly=True)
    member_code = fields.Char(string='Member Code', readonly=True) #BARCODE
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    date_joined = fields.Datetime(string='Date Joined', readonly=True)
    year_joined = fields.Char(string='Year Joined', readonly=True)
    member_point = fields.Float(string='Member Points', readonly=True)
    total_order = fields.Integer(string='Total Order', readonly=True)

    @property
    def _table_query(self):
        return '%s %s %s' % (self._select(), self._from(), self._where())

    @api.model
    def _select(self):
        return '''
            SELECT
            rp.id AS id,
            rp.name AS name,
            (
                SELECT value_text FROM ir_property 
                WHERE res_id = CONCAT('res.partner,', rp.id) AND name = 'barcode'
                LIMIT 1
            ) AS member_code,
            rp.company_id AS company_id,
    
            rp.create_date AS date_joined,
            to_char(rp.create_date, 'YYYY') AS year_joined,
            (
                COALESCE(rp.pos_loyalty_point_import, 0)
                +
                (SELECT COALESCE(SUM(p.point), 0) FROM pos_loyalty_point AS p 
                 WHERE p.type != 'redeem' AND p.partner_id = rp.id AND p.state = 'ready')
                -
                (SELECT COALESCE(SUM(p.point), 0) FROM pos_loyalty_point AS p 
                 WHERE p.type = 'redeem' AND p.partner_id = rp.id )
            ) AS member_point,
            (
                SELECT COUNT(id) FROM pos_order WHERE  partner_id = rp.id
            ) AS total_order
        '''

    @api.model
    def _from(self):
        return '''
            FROM res_partner AS rp
            '''

    @api.model
    def _where(self):
        return '''
            WHERE rp.is_pos_member = 't'
        '''