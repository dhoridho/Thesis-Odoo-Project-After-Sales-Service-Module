from odoo import models, api, fields
from odoo.tools import float_round, float_compare


class StockMove(models.Model):
    _inherit = 'stock.move'

    uom_cache = dict()

    @api.onchange('product_uom_qty')
    def _set_cache_product_uom_qty(self):
        if self.uom_cache.get('qty_updated') is not True:
            self.uom_cache['product_uom_qty'] = self.product_uom_qty
        else:
            self.uom_cache['qty_updated'] = False

    @api.onchange('product_uom')
    def _set_cache_product_uom(self):
        if self.product_uom:
            uom_id = self.uom_cache.get('product_uom', self.product_id and self.product_id.id or False)
            uom_qty = self.uom_cache.get('product_uom_qty', self.product_uom_qty)

            origin_uom = self.env['uom.uom'].browse(uom_id)
            if origin_uom:
                uom_qty = origin_uom._compute_quantity(uom_qty, self.product_uom, round=False)
                precision_qty = float_round(uom_qty, precision_rounding=1, rounding_method='HALF-UP')
                if not float_compare(uom_qty, precision_qty, precision_digits=1):
                    product_uom_qty = precision_qty
                else:
                    product_uom_qty = float_round(uom_qty, precision_rounding=self.product_uom.rounding, rounding_method='HALF-UP')
                self.product_uom_qty = product_uom_qty
                self.uom_cache['product_uom_qty'] = uom_qty
                self.uom_cache['qty_updated'] = True
        self.uom_cache['product_uom'] = self.product_uom.id
