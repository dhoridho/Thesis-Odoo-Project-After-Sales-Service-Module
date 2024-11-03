# -*- coding: utf-8 -*-

from odoo import api, fields, models

class PosConfig(models.Model):
    _inherit = "pos.config"

    customize_bom = fields.Boolean('Customize BoM')