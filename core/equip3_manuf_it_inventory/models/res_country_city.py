# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import UserError


class ResCountry(models.Model):
    _inherit = 'res.country'
    _description = 'Country'

    ceisa_state = fields.Boolean('CEISA Status', default=False)

