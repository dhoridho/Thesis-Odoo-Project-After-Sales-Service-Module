# -*- coding: utf-8 -*-

from odoo import models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    is_post_closing_cashbox_value_in_session = fields.Boolean(
        string='Post Closing Cashbox Value in Session', 
        related='company_id.is_post_closing_cashbox_value_in_session', readonly=False)
