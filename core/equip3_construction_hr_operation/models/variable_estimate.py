# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class LabourEstimationInherit(models.Model):
    _inherit = 'labour.variable'

    product_id = fields.Many2one('product.product', string='Product', 
                 domain="[('type', '=', 'labour'), ('group_of_product', '=', group_of_product)]",
                 check_company=True, required=True)
    