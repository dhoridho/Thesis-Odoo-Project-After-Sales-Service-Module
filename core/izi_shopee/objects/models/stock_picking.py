# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def shopee_drop_off(self):
        for rec in self:
            if rec.state == 'done':
                rec.sale_id.shopee_drop_off()
            else:
                raise ValidationError('Please Validate DO before Drop Off ..')

    def shopee_request_pickup(self):
        for rec in self:
            if rec.state == 'done':
                rec.sale_id.shopee_request_pickup()
            else:
                raise ValidationError('Please Validate DO before Request Pickup ..')

    def shopee_print_label(self):
        so_ids = self.env['sale.order']
        for rec in self:
            so_ids |= rec.sale_id
        label = so_ids.shopee_print_label()
        return label

    def shopee_get_awb_num(self):
        for rec in self:
            if rec.state == 'done':
                rec.sale_id.shopee_get_awb_num()
            else:
                raise ValidationError('Please Validate DO Get AWB Number ..')

    def shopee_download_shipping_label(self):
        so_ids = self.env['sale.order']
        for rec in self:
            so_ids |= rec.sale_id
        label = so_ids.shopee_download_shipping_label()
        return label