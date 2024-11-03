from odoo import models


class PurchaseOrderLineQCInherit(models.Model):
    _inherit = 'purchase.order.line'

    def _prepare_stock_move_vals(self, picking, price_unit, product_uom_qty, product_uom):
        res = super(PurchaseOrderLineQCInherit, self)._prepare_stock_move_vals(picking, price_unit, product_uom_qty, product_uom)
        res.update({'remaining_checked_qty': product_uom_qty})
        return res
