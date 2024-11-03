from odoo import models, fields, api, _
from odoo.exceptions import UserError


class MrpReserveLine(models.Model):
    _name = 'mrp.reserve.line'
    _description = 'MRP Reserve Line'

    move_id = fields.Many2one('stock.move', string='Stock Move', required=True, ondelete='cascade')

    company_id = fields.Many2one('res.company', string='Company', readonly=True, required=True, index=True)
    product_id = fields.Many2one('product.product', 'Product', ondelete="cascade", check_company=True, domain="[('type', '!=', 'service'), '|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    product_uom_id = fields.Many2one('uom.uom', 'Unit of Measure', required=True, domain="[('category_id', '=', product_uom_category_id)]")
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id')

    lot_id = fields.Many2one('stock.production.lot', 'Lot/Serial Number', domain="[('product_id', '=', product_id), ('company_id', '=', company_id)]", check_company=True)
    tracking = fields.Selection(related='product_id.tracking', readonly=True)

    product_qty = fields.Float('Real Reserved Quantity', digits=0, compute='_compute_product_qty', inverse='_set_product_qty', store=True)
    product_uom_qty = fields.Float('Reserved', default=1.0, digits='Product Unit of Measure', required=True)
    sequence = fields.Integer(string='No')

    @api.depends('product_id', 'product_uom_id', 'product_uom_qty')
    def _compute_product_qty(self):
        for line in self:
            line.product_qty = line.product_uom_id._compute_quantity(line.product_uom_qty, line.product_id.uom_id, rounding_method='HALF-UP')

    def _set_product_qty(self):
        """ The meaning of product_qty field changed lately and is now a functional field computing the quantity
        in the default product UoM. This code has been added to raise an error if a write is made given a value
        for `product_qty`, where the same write should set the `product_uom_qty` field instead, in order to
        detect errors. """
        raise UserError(_('The requested operation cannot be processed because of a programming error setting the `product_qty` field instead of the `product_uom_qty`.'))
