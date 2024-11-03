# -*- coding: utf-8 -*-
from odoo import models, fields, api


class IZIAnalysisFilterOperatorDBOdoo(models.Model):
    _inherit = 'izi.analysis.filter.operator'

    source_type = fields.Selection(
        selection_add=[
            ('db_odoo', 'Database Hashmicro'),
        ])