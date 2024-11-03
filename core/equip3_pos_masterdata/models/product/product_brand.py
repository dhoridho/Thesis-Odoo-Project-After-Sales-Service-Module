# -*- coding: utf-8 -*
from odoo import api, fields, models, _



class ProductBrand(models.Model):
    _inherit = 'product.brand'
    
    active = fields.Boolean('Active',default=True)
    
