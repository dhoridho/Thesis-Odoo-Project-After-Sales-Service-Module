# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class SaleOrderlabourLineInherit(models.Model):
    _inherit= 'sale.order.labour.line'
    
    product_id = fields.Many2one('product.product', string='Product', required=True, domain="[('type', '=', 'labour'), ('group_of_product', '=', group_of_product)]")
    
