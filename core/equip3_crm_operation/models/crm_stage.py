# -*- coding: utf-8 -*-
from odoo import api, fields, models


class CrmStage(models.Model):
    _inherit = 'crm.stage'

    change_probability = fields.Boolean(string='Change Probability', default=False)
    probability = fields.Float(string='Probability')
    is_lost = fields.Boolean('Is Lost Stage ?')