# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SaleOrderLine(models.Model):
    _name = 'sale.order.line'
    _inherit = ['sale.order.line', 'mp.base']

    mp_account_id = fields.Many2one(required=False)
    is_insurance = fields.Boolean(string="Is a Insurance", default=False)
    is_global_discount = fields.Boolean(string="Is a Global Discount", default=False)
    is_adjustment = fields.Boolean(string="Is a Adjustment", default=False)
    is_services = fields.Boolean(string="Is a Services", default=False)
    product_type = fields.Selection(related='product_id.type')
    mp_product_name = fields.Char(string='Marketplace Product Name')
    mp_product_sku = fields.Char(string='Marketplace Product SKU')
    normal_price = fields.Float(string='Normal Price')

    @api.model
    def create(self, vals):
        if 'order_id' in vals:
            order_id = vals.get('order_id')
            sale_order = self.env['sale.order'].sudo().search([('id', '=', order_id)], limit=1)
            # vals['delivery_address_id'] = sale_order.partner_id.id
            vals['line_warehouse_id'] = sale_order.warehouse_id.id
            if 'marketplace' in vals:
                if sale_order.mp_pickup_done_time:
                    vals['multiple_do_date'] = sale_order.mp_pickup_done_time
                    vals['multiple_do_date_new'] = sale_order.mp_pickup_done_time
                else:
                    if sale_order.mp_shipping_deadline:
                        vals['multiple_do_date'] = sale_order.mp_shipping_deadline
                        vals['multiple_do_date_new'] = sale_order.mp_shipping_deadline
                    elif sale_order.mp_pickup_time_slot:
                        vals['multiple_do_date'] = sale_order.mp_pickup_time_slot
                        vals['multiple_do_date_new'] = sale_order.mp_pickup_time_slot

        if 'is_delivery' in vals and vals.get('is_delivery') == True:
            order_id = vals.get('order_id')
            sale_order = self.env['sale.order'].sudo().search([('id', '=', order_id)], limit=1)
            vals['line_warehouse_id'] = sale_order.warehouse_id.id
            if 'marketplace' in vals:
                if sale_order.mp_pickup_done_time:
                    vals['multiple_do_date'] = sale_order.mp_pickup_done_time
                    vals['multiple_do_date_new'] = sale_order.mp_pickup_done_time
                else:
                    if sale_order.mp_shipping_deadline:
                        vals['multiple_do_date'] = sale_order.mp_shipping_deadline
                        vals['multiple_do_date_new'] = sale_order.mp_shipping_deadline
                    elif sale_order.mp_pickup_time_slot:
                        vals['multiple_do_date'] = sale_order.mp_pickup_time_slot
                        vals['multiple_do_date_new'] = sale_order.mp_pickup_time_slot
        res = super(SaleOrderLine, self).create(vals)
        return res

    @api.model
    def _finish_mapping_raw_data(self, sanitized_data, values):
        sanitized_data, values = super(SaleOrderLine, self)._finish_mapping_raw_data(sanitized_data, values)
        if not values.get('product_id') and self._context.get('final', False):
            err_msg = 'Could not find matched record for MP Product "%s", please make sure this MP Product is mapped!'
            raise ValidationError(err_msg % values['mp_product_name'])

        return sanitized_data, values
