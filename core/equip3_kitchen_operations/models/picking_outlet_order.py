from odoo import models, fields, api, _


class PickingOutletOrder(models.Model):
    _inherit = 'stock.picking'

    @api.model
    def _default_analytic_tag_ids(self):
        user = self.env.user
        analytic_priority = self.env['analytic.priority'].sudo().search([], limit=1, order='priority')
        analytic_tag_ids = []
        if analytic_priority.object_id == 'user' and user.analytic_tag_ids:
            analytic_tag_ids = user.analytic_tag_ids.ids
        elif analytic_priority.object_id == 'branch' and user.branch_id and user.branch_id.analytic_tag_ids:
            analytic_tag_ids = user.branch_id.analytic_tag_ids.ids
        elif analytic_priority.object_id == 'product_category':
            product_category = self.env['product.category'].sudo().search([('analytic_tag_ids', '!=', False)], limit=1)
            analytic_tag_ids = product_category.analytic_tag_ids.ids
        return [(6, 0, analytic_tag_ids)]

    is_outlet_order = fields.Boolean(string='Is Outlet Order')

    kitchen_warehouse_id = fields.Many2one('stock.warehouse', string='Kitchen Warehouse', tracking=True)
    kitchen_outlet_warehouse_id = fields.Many2one('stock.warehouse', string='Kitchen Outlet Warehouse', tracking=True)
    kitchen_analytic_group_ids = fields.Many2many('account.analytic.tag', 'picking_analytic_tag_kitchen_rel', domain="[('company_id', '=', company_id)]", string="Kitchen Analytic Group", default=_default_analytic_tag_ids, tracking=True)
