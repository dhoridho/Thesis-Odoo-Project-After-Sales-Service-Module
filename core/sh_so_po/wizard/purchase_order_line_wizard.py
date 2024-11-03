# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import models, fields, api


class PurchaseOrder(models.TransientModel):
    _name = 'purchase.order.line.wizard'
    _description = "Purchase Order line Wizard"

    @api.depends('product_qty', 'price_unit')
    def _compute_amount(self):
        if self:
            for rec in self:
                rec.price_subtotal = rec.product_qty * rec.price_unit

    name = fields.Text(string='Description')
    wizard_id = fields.Many2one('purchase.order.wizard')
    product_id = fields.Many2one('product.product', string='Product')
    product_qty = fields.Float(string='Quantity', default=1)
    price_unit = fields.Float(string='Unit Price')
    product_uom = fields.Many2one('uom.uom', string='Product Unit of Measure')
    price_subtotal = fields.Float(compute='_compute_amount', string='Subtotal')

    @api.onchange('product_id')
    def get_unit_price(self):
        if self:
            for rec in self:
                if rec and rec.product_id:
                    # this code is for assign unit price automatic
                    product_obj = self.env['product.product']
                    product_id = product_obj.search(
                        [('id', '=', rec.product_id.id)], limit=1)
                    if product_id:
                        self.price_unit = product_id.standard_price
                        self.name = product_id.name
                        if product_id.uom_po_id:
                            self.product_uom = product_id.uom_po_id.id
