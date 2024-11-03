
from odoo import models, fields, api, _


class SaleOrderRepair(models.TransientModel):
    _name = 'sale.order.repair'
    _description = 'Sale Order Repair'

    repair_type = fields.Selection([("customer_repair","Customer Repair"),("internal_repair","Internal Repair")], string='Repair Type', default='customer_repair')
    repair_line_ids = fields.One2many('sale.order.repair.line', 'repair_id', string="Repair Line", readonly=True)
    is_return_required = fields.Boolean('Return the repaired parts ')
    return_sale_order_id = fields.Many2one('dev.rma.rma')

    def action_confirm(self):
        for line in self.repair_line_ids:
            vals = {
                'product_id' : line.product_id.id,
                'product_uom' : line.product_id.uom_id.id,
                'product_qty' : line.quantity,
                'location_id' : line.location_id.id,
                'repair_type' : self.repair_type,
                'source_doc': self.return_sale_order_id.name,
            }
            repair_id = self.env['repair.order'].create(vals)
            if self.is_return_required:
                repair_id.address_id = self.return_sale_order_id.partner_id.id
                self.return_sale_order_id.is_return_order = self.is_return_required
            for move_line in self.return_sale_order_id.picking_id.move_line_ids_without_package:
                if move_line.product_id.id == line.product_id.id:
                    if move_line.lot_id:
                        repair_id.lot_id = move_line.lot_id.id
        return True

class SaleOrderRepairLine(models.TransientModel):
    _name = 'sale.order.repair.line'
    _description = 'Sale Order Repair Line'

    repair_id = fields.Many2one('sale.order.repair', string="Repair")
    product_id = fields.Many2one('product.product', string="Product")
    quantity = fields.Float(string="Quantity")
    location_id = fields.Many2one('stock.location', string="Location")
