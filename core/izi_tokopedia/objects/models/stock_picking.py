# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def tokopedia_request_pickup(self):
        for rec in self:
            if rec.state == 'done':
                rec.sale_id.tokopedia_request_pickup()
            else:
                raise ValidationError('Please Validate DO before Request Pickup ..')

    def tokopedia_confirm_shipping(self):
        for rec in self:
            if rec.state == 'done':
                confirm_shipping = rec.sale_id.tokopedia_confirm_shipping()
                return confirm_shipping
            else:
                raise ValidationError('Please Validate DO before Confirm Shipping ..')

    def tokopedia_print_label(self):
        so_ids = self.env['sale.order']
        for rec in self:
            so_ids |= rec.sale_id
        label = so_ids.tokopedia_print_label()
        return label
