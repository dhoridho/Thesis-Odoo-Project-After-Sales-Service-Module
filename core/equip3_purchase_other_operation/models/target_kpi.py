from odoo import models, fields, api, _


class TargetKPIInherit(models.Model):
    _inherit = 'target.kpi'

    current_achievement = fields.Float(string='Current Achievement', compute="_compute_current_achievement")

    @api.depends('main_target','target_on','target_based_on_ids')
    def _compute_current_achievement(self):
        for i in self:
            codes = ''
            total_cost_saving = count_purchase_order_lines = current_achievement = 0
            if i.state == 'confirm' or i.state == 'expired' or i.state == 'failed' or i.state == 'succeed':
                if i.target_based_on_ids:
                    codes = i.target_based_on_ids.mapped('code')
                if 'purchase_order_line' in codes:
                    purchase_order_lines = self.env['purchase.order.line'].search([
                        ('agreement_id','=',False),
                        ('purchase_line_cost_saving','>',0),
                    ])
                    purchase_order_lines = purchase_order_lines.filtered(lambda p:p.order_id and p.order_id.user_id and p.order_id.user_id.id == i.user_id.id and p.order_id.state1 == 'purchase' and p.order_id.date_approve.date() >= i.from_date and p.order_id.date_approve.date() <= i.to_date)
                    total_cost_saving += sum(purchase_order_lines.mapped('total_cost_saving'))
                    count_purchase_order_lines += len(purchase_order_lines)
                if 'purchase_tender' in codes:
                    purchase_order_lines = self.env['purchase.order.line'].search([
                        ('agreement_id','!=',False),
                        ('total_cost_saving','>',0)
                    ])
                    purchase_order_lines = purchase_order_lines.filtered(lambda p:p.order_id and p.order_id.user_id and p.order_id.user_id.id == i.user_id.id and p.order_id.state1 == 'purchase' and p.order_id.date_approve.date() >= i.from_date and p.order_id.date_approve.date() <= i.to_date)
                    total_cost_saving += sum(purchase_order_lines.mapped('total_cost_saving'))
                    count_purchase_order_lines += len(purchase_order_lines)
                if i.target_on == 'amount':
                    current_achievement = total_cost_saving
                elif i.target_on == 'qty':
                    current_achievement = count_purchase_order_lines
            i.current_achievement = current_achievement