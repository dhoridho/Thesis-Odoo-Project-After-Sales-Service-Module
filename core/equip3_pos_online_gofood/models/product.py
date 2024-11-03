# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    is_available_in_outlet_gofood = fields.Boolean('Available in GoFood')