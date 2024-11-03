# -*- coding: utf-8 -*-
# Copyright 2022 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models

class SaleOutlet(models.Model):
    _name = 'sale.outlet'
    _description = 'Sale Outlet'
    
    name = fields.Char(string='Name', required=True)
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse', required=True)
    partner_id = fields.Many2one('res.partner', 'Partner')