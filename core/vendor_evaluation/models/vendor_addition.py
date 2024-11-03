# -*- coding:utf-8 -*-
from odoo import models, fields, api
from . import vendor_evaluation as ve


class VendorAddition(models.Model):
    _inherit = 'res.partner'

    visible_eval = fields.Selection(ve.VendorEvaluation.point, string="Last Evaluated",
                                    compute='_calculate_eval', readonly=True)

    @api.depends()
    def _calculate_eval(self):
        for rec in self:
            record = self.env['vendor.evaluation'].search([
                ('vendor', '=', rec.id),
                ('state', '=', 'approved')
            ])
            if record:
                rec.visible_eval = record.sorted('period_end', reverse=True)[0].final_rate
            else:
                rec.visible_eval = False

    def create_new_evaluation(self):
        self.ensure_one()
        action = self.env.ref('vendor_evaluation.vendor_evaluation_action').read()[0]
        res = self.env.ref('vendor_evaluation.vendor_evaluation_view_form', False)
        action['views'] = [(res and res.id or False, 'form')]
        action['context'] = {'default_vendor': self.id}
        return action


class PurchaseAddition(models.Model):
    _inherit = 'purchase.order'

    visible_eval = fields.Selection(ve.VendorEvaluation.point, string="Last Evaluated",
                                    compute='_calculate_eval', readonly=True)

    @api.depends('partner_id')
    def _calculate_eval(self):
        for rec in self:
            record = self.env['vendor.evaluation'].search([
                ('vendor', '=', rec.partner_id.id),
                ('state', '=', 'approved')
            ])
            if record:
                rec.visible_eval = record.sorted('period_end', reverse=True)[0].final_rate
            else:
                rec.visible_eval = False
