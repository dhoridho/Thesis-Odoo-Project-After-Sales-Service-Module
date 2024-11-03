# -*- coding: utf-8 -*
from odoo import api, fields, models, _

class ProductAtribute(models.Model):
    _inherit = 'product.attribute'

    multi_choice = fields.Boolean('Multi choose')