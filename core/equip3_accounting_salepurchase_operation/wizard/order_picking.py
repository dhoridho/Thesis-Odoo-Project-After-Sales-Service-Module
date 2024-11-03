
from odoo import api, fields, models


class OrderPicking(models.TransientModel):
    _name = 'order.picking'
    _description = 'Order Picking'

    move_id = fields.Many2one('account.move', string='Account Move')
    order_picking_line_ids = fields.One2many('order.picking.lines', 'order_id', string='Picking Lines')

    def action_confirm_order(self):
        self.ensure_one()
        self.move_id.line_ids.unlink()
        self.move_id.invoice_line_ids.unlink()
        if self.move_id.sale_order_ids:
            line_ids = self.move_id.sale_order_ids.order_line.filtered(lambda r: r.product_id.invoice_policy == 'order')
            data = []
            for line in line_ids:
                data.append((0, 0, {
                    'product_id': line.product_id.id,
                    'quantity': line.product_uom_qty,
                    'product_uom_id': line.product_uom.id,
                    'price_unit': line.price_unit,
                    'tax_ids': [(6, 0, line.tax_id.ids)],
                }))
            self.move_id.invoice_line_ids = data
        elif self.move_id.purchase_order_ids:
            line_ids = self.move_id.purchase_order_ids.order_line.filtered(lambda r: r.product_id.purchase_method == 'purchase')
            data = []
            for line in line_ids:
                data.append((0, 0, {
                    'product_id': line.product_id.id,
                    'quantity': line.product_qty,
                    'product_uom_id': line.product_uom.id,
                    'price_unit': line.price_unit,
                    'tax_ids': [(6, 0, line.taxes_id.ids)],
                }))
            self.move_id.invoice_line_ids = data

class OrderPickingLines(models.TransientModel):
    _name = 'order.picking.lines'
    _description = 'Order Picking Lines'

    order_id = fields.Many2one('order.picking', string='Order Picking')
    product_id = fields.Many2one('product.product', string='Product')
    quantity = fields.Float(string='Quantity')
    unit_price = fields.Float(string='Price')
    subtotal = fields.Float(string='Subtotal')
    picking_id = fields.Many2one('stock.picking', string='Delivery Order')
    state = fields.Selection(related='picking_id.state', string='Delivery Order Status')
    move_type = fields.Selection(related='order_id.move_id.move_type', string='Move Type')
