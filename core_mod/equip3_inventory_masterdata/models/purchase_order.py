from odoo import models, api


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    @api.depends('product_uom', 'product_qty', 'product_id.uom_id')
    def _compute_product_uom_qty(self):
        super(PurchaseOrderLine, self)._compute_product_uom_qty()
        lines_to_update = self.filtered(lambda line: line.product_uom.is_custom_uom or line.product_id.uom_id.is_custom_uom)
        for line in lines_to_update:
            line.product_uom_qty = line.product_uom._compute_quantity_custom(line.product_id, line.product_qty, line.product_id.uom_id)

    def _prepare_stock_move_vals(self, picking, price_unit, product_uom_qty, product_uom):
        res = super(PurchaseOrderLine, self)._prepare_stock_move_vals(picking, price_unit, product_uom_qty, product_uom)
        if (not self.product_uom.is_custom_uom and not product_uom.is_custom_uom) or self.product_uom == product_uom:
            return res
        res['product_uom_qty'] = self.product_uom._compute_quantity_custom(self.product_id, self.product_qty, product_uom)
        return res
