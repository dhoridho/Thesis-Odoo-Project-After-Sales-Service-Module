# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class ProductTemplate(models.Model):
    _inherit = "product.template"

    ph_vat_type = fields.Selection([('VATable', 'VATable'),('VAT zero rate', 'VAT zero rate'),('VAT exempt', 'VAT exempt'),
        ], string="PH VAT Type",default="VATable",required=True)