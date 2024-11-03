# -*- coding: utf-8 -*

from odoo import api, fields, models
from datetime import datetime


class PosPromotion(models.Model):
    _inherit = "pos.promotion"

    no_of_usage = fields.Integer("No Of Usage", default=0, help='This shows how many times the promotion can be used. If 0 = unlimited')
    no_of_used = fields.Integer("No Of Used", compute='get_total_number_used')
    active = fields.Boolean('Active', compute=False, store=True, default=True) # Previously field Compute
    is_priority = fields.Boolean('Priority')
    note = field_name = fields.Text('Note')

    def write(self, vals):
        if 'active' in vals:
            vals['state'] = 'active' if vals['active'] else 'disable'
        res = super(PosPromotion, self).write(vals)
        return res
    
    def get_total_number_used(self):
        result = {}
        if self and self[0].ids:
            self.env.cr.execute('''
                SELECT t.promotion_id, COUNT(t.order_id)
                FROM (
                    SELECT  DISTINCT pol.promotion_id, pol.order_id
                    FROM pos_order AS po
                    LEFT JOIN pos_order_line AS pol ON pol.order_id = po.id
                    WHERE pol.promotion_id IN (%s)
                ) AS t
                GROUP BY t.promotion_id
            ''' % ( str(self.ids)[1:-1] ))
            result = dict(self.env.cr.fetchall())

        for rec in self:
            if self[0].ids:
                rec.no_of_used = result.get(rec.id, 0)
            else:
                rec.no_of_used = 0

    def disable_expired_promotion_cron(self):
        domain = [('active','=',True), ('state','=','active'), ('end_date','<', datetime.now())]
        promotions = self.env['pos.promotion'].search(domain)
        promotions.write({ 'active': False, 'state': 'disable' })