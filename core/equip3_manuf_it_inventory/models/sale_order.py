from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        anything = super(SaleOrder, self).action_confirm()
        for record in self:
            record.picking_ids.write({
                'is_it_inventory_warehouse': record.warehouse_id.is_it_inventory_warehouse
            })
        return anything
