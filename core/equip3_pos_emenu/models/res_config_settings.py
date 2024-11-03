# -*- coding: utf-8 -*-

from odoo import fields, models, api

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    pos_emenu_domain = fields.Char('E-Menu Domain', config_parameter='base_setup.pos_emenu_domain')
    pos_emenu_base_url = fields.Char('E-Menu Base URL', config_parameter='web.base.url.pos_emenu')
