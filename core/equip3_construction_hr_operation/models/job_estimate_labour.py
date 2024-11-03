# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class LabourEstimateInherits(models.Model):
    _inherit = "labour.estimate"
    
    product_id = fields.Many2one('product.product', string='Product', required=True, domain="[('type', '=', 'labour'), ('group_of_product', '=', group_of_product)]")
    
