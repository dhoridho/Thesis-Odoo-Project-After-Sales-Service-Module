# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import models, fields, _



class ResPartner(models.Model):
    _inherit = "res.partner"

    vendor_products = fields.Text('Products')
    vendor_product_categ_ids = fields.Many2many('product.category',string='Product Categories')
    