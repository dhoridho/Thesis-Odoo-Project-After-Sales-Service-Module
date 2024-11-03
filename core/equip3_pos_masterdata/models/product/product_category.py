# -*- coding: utf-8 -*
from odoo import api, fields, models, _

class ProductCategory(models.Model):
    _inherit = 'product.category'

    product_limit = fields.Selection(
        [('no_limit', "Don't Limit"), ('limit_per', 'Limit by Precentage %'), ('limit_amount', 'Limit by Amount'),
         ('str_rule', 'Strictly Limit by Purchase Order')],
        string='Receiving Limit', tracking=True, default='no_limit')