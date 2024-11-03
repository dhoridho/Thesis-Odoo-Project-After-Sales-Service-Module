# -*- coding: utf-8 -*-

from odoo import api, fields, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    is_product_grid_view = fields.Boolean(string='Product View',default=False)
