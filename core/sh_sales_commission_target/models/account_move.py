from typing import Collection
from odoo import models, fields, api, exceptions, _

class AccountMove(models.Model):
    _inherit = 'account.move'

    target_commission_id = fields.Many2one('sh.target.commision')
    commission_count = fields.Integer(compute ='compute_commission_count')
    # commission_ids = fields.Many2many('sh.target.commision',compute ='compute_commission_ids',)

    # def compute_commission_ids(self):
    #     self.commission_ids = False
    #     target_related_commissions = self.env['sh.target.commision'].search([('id', '=',self.target_commission_id.id)])
    #     if target_related_commissions:
    #         self.commission_ids = [(6,0,target_related_commissions.ids)]

    def open_commissions(self):
        [action] = self.env.ref('sh_sales_commission_target.sh_target_commision_action').read()
        action['domain'] = [('id', '=',self.target_commission_id.id)]
        return action

    def compute_commission_count(self):
        for rec in self:
            rec.commission_count = 0
            if rec.target_commission_id:
                rec.commission_count = 1