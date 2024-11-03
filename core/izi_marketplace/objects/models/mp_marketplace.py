# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models, tools

class MPMarketplace(models.Model):
    _name = 'mp.marketplace'
    _description = 'Marketplace'

    name = fields.Char(string="Name", index=True, required=True)
