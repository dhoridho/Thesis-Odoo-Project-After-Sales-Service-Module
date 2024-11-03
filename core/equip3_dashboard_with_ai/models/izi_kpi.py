# -*- coding: utf-8 -*-
from odoo import models, fields, api


class IZIKPI(models.Model):
    _inherit = 'izi.kpi'

    calculation_method = fields.Selection(
        selection_add=[
            ('model', 'Model'),
        ])