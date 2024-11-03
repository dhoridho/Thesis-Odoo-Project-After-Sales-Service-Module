from odoo import api, fields, models, SUPERUSER_ID, tools, _
from odoo.addons.purchase_stock.models.stock import StockMove as PurchaseStockMove
from odoo.tools.float_utils import float_round

class StockMove(models.Model):
    _inherit = "stock.move"

    @api.model
    def create(self, vals):
        vals['sequence'] = self.env['ir.sequence'].next_by_code('increment.five.stock.move')
        res = super().create(vals)
        return res

    def _register_hook(self):
        PurchaseStockMove._patch_method('_get_price_unit', self.make_get_price_unit())
        return super(StockMove, self)._register_hook()

    def make_get_price_unit(self):
        def _get_price_unit(self):
            """ Returns the unit price for the move"""
            self.ensure_one()
            if self.purchase_line_id and self.product_id.id == self.purchase_line_id.product_id.id:
                price_unit_prec = self.env['decimal.precision'].precision_get('Product Price')
                line = self.purchase_line_id
                order = line.order_id
                price_unit = line.price_subtotal / line.product_qty
                if line.taxes_id:
                    qty = line.product_qty or 1
                    price_unit = line.taxes_id.with_context(round=False).compute_all(price_unit, currency=line.order_id.currency_id, quantity=qty)['total_void']
                    price_unit = float_round(price_unit / qty, precision_digits=price_unit_prec)
                if line.product_uom.id != line.product_id.uom_id.id:
                    price_unit *= line.product_uom.factor / line.product_id.uom_id.factor
                if order.currency_id != order.company_id.currency_id:
                    # The date must be today, and not the date of the move since the move move is still
                    # in assigned state. However, the move date is the scheduled date until move is
                    # done, then date of actual move processing. See:
                    # https://github.com/odoo/odoo/blob/2f789b6863407e63f90b3a2d4cc3be09815f7002/addons/stock/models/stock_move.py#L36
                    price_unit = order.currency_id._convert(
                        price_unit, order.company_id.currency_id, order.company_id, fields.Date.context_today(self), round=False)
                return price_unit
            return super(PurchaseStockMove, self)._get_price_unit()
        return _get_price_unit
