# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    app_default_superbar_lazy_search = fields.Boolean('Lazy Search in Sidebar', config_parameter='app_default_superbar_lazy_search')
