
from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError
from odoo.tools import float_compare
from odoo.osv import expression

class ProductCancel(models.Model):
    _name = "product.cancel"
    _description = 'Product Cancel'
    _rec_name = 'order_ref'

    order_ref = fields.Char(string='Order Reference')
    product_id = fields.Many2one('product.product', string='Product')
    qty = fields.Float(string='Qty')
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure')
    src_location_id = fields.Many2one('stock.location', string='Source Location')
    cashier_id = fields.Many2one('res.users', string='Cashier')
    cancel_reason = fields.Text(string='Reason Cancel')
    pos_order_id = fields.Many2one('pos.order', string='POS Order', compute='_compute_pos_order_id')

    def _compute_pos_order_id(self):
        for record in self:
            pos_order_id = self.env['pos.order'].search([('pos_reference', '=', record.order_ref)], limit=1)
            record.pos_order_id = pos_order_id and pos_order_id.id or False
