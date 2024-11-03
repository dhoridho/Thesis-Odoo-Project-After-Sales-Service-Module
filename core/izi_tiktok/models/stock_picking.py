# -*- coding: utf-8 -*-
# Copyright 2023 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def tiktok_print_label(self):
        so_ids = self.env['sale.order']
        for rec in self:
            so_ids |= rec.sale_id
        label = so_ids.tiktok_print_label()
        return label