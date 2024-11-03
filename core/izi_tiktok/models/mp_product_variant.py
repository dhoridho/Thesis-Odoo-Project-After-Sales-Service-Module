# -*- coding: utf-8 -*-
# Copyright 2023 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models



class MPProductVariant(models.Model):
    _inherit = 'mp.product.variant'

    tts_variant_id = fields.Char(string='Product Variant External ID')
    stock_ids = fields.One2many('mp.tiktok.warehouse.stock', 'mp_product_variant_id', string='Stock')
  