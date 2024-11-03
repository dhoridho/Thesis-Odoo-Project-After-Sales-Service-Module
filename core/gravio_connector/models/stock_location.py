# -*- coding: utf-8 -*-

from email.policy import default

# from numpy import product
from odoo import api, models, fields
from odoo.http import request

class StockLocation(models.Model):
    _inherit = 'stock.location'

    layer_label = fields.Char(string="Layer Label")