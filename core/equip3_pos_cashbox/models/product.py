# -*- coding: utf-8 -*-

from odoo import fields, models

class ProductTemplate(models.Model):
    _inherit = 'product.template'
 
    is_for_cash_management = fields.Boolean('Cash Management')