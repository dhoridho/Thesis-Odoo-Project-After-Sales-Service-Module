# -*- coding: utf-8 -*-

import json
import copy
from odoo import api, fields, models

class PosOrder(models.Model):
    _inherit = 'pos.order'

    line_details_ids = fields.One2many('pos.order.line.detail', 'order_id', string='Details')

    def _prepare_void_order_line_vals(self, order, line):
        values = super(PosOrder,self)._prepare_void_order_line_vals(order=order, line=line)
        values['bom_components'] = line.bom_components
        values['pos_combo_options'] = line.pos_combo_options
        return values

class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    line_details_ids = fields.One2many('pos.order.line.detail', 'pos_order_line_id', string='Details')
    bom_components = fields.Text('BOM Components Data', copy=False)
    pos_combo_options = fields.Text('POS Combo Option Data', copy=False)


class PosOrderLineDetail(models.Model):
    _name = 'pos.order.line.detail'
    _description = 'POS Order Line Detail'

    order_id = fields.Many2one('pos.order', 'POS Order')
    product_id = fields.Many2one('product.product', 'Product')
    product_component_id = fields.Many2one('product.product', 'Component')
    is_extra = fields.Boolean('Extra')
    price = fields.Float('Price')
    quantity = fields.Integer('Quantity')
    product_uom_id = fields.Many2one('uom.uom', 'Unit of Measure')
    pos_order_line_id = fields.Many2one('pos.order.line', 'POS Order Line')
