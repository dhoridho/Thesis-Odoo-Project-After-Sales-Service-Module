from odoo import models, fields, api

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    picking_count = fields.Integer(
        string="Picking Count",
        compute="_compute_picking_count"
    )

    @api.depends('picking_ids')
    def _compute_picking_count(self):
        for order in self:
            order.picking_count = len(order.picking_ids)

    def action_view_pickings(self):
        self.ensure_one()
        action = self.env.ref('stock.action_picking_tree_all').read()[0]
        action['domain'] = [('origin', '=', self.name)]
        action['context'] = {'default_origin': self.name}
        return action