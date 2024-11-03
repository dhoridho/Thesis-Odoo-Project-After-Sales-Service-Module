# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import UserError


class ResCountryCity(models.Model):
    _inherit = 'res.country.city'
    _description = 'Country CIty'

    # ceisa_id = fields.Integer('CEISA Document ID')
