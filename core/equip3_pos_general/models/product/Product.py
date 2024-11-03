# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class ProductTemplate(models.Model):
    _inherit = 'product.template' 
    
    not_returnable = fields.Boolean('Not Returnable')

