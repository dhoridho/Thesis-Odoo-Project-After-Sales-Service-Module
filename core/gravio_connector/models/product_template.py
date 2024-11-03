# -*- coding: utf-8 -*-

from email.policy import default

# from numpy import product
from odoo import api, models, fields
from odoo.http import request
    
class ProductTemplate(models.Model):
    _inherit = 'product.template'

    rfid_label = fields.Char(string="RFID Label")