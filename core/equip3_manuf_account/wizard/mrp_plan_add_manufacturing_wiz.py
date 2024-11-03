# -*- coding: utf-8 -*-
from odoo import fields, models, api


class MrpProductionWizard(models.TransientModel):
    _inherit = 'mrp.production.wizard'

    def _post_production_create(self):
        res = super(MrpProductionWizard, self)._post_production_create()
        self.plan_id._get_estimated_cost()
        return res


class MrpProductionWizardLine(models.TransientModel):
    _inherit = 'mrp.production.wizard.line'

    def _prepare_order_values(self, bom_id, product_id, product_qty, uom_id, parent_id=False):
        values = super(MrpProductionWizardLine, self)._prepare_order_values(bom_id, product_id, product_qty, uom_id, parent_id=parent_id)
        plan_id = self.wizard_id.plan_id
        if plan_id.analytic_tag_ids:
            values['analytic_tag_ids'] = [(6, 0, plan_id.analytic_tag_ids.ids)]
        else:
            analytic_priority = self.env['analytic.priority'].sudo().search([], limit=1, order='priority')
            if analytic_priority:
                if analytic_priority.object_id == 'user' and self.env.user.analytic_tag_ids:
                    values['analytic_tag_ids'] = [(6, 0, self.env.user.analytic_tag_ids.ids)]
                elif analytic_priority.object_id == 'branch' and self.env.user.branch_id and self.env.user.branch_id.analytic_tag_ids:
                    values['analytic_tag_ids'] = [(6, 0, self.env.user.branch_id.analytic_tag_ids.ids)]
                elif analytic_priority.object_id == 'product_category':
                    search_product_category = self.env['product.category'].sudo().search([('analytic_tag_ids', '!=', False)], limit=1)
                    if search_product_category:
                        values['analytic_tag_ids'] = [(6, 0, search_product_category.analytic_tag_ids.ids)]

        return values

    def _post_production_create(self, order):
        res = super(MrpProductionWizardLine, self)._post_production_create(order)
        order._get_estimated_cost()
        return res
