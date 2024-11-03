# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime, timedelta

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    config_elearning_zoom_integration = fields.Boolean(string="Enable Zoom Meetings", config_parameter='elearning_zoom_integration')
    config_elearning_zoom_api_key = fields.Char(string="Zoom API KEY", config_parameter='elearning_zoom_api_key')
    config_elearning_zoom_api_secret = fields.Char(string="Zoom API Secret", config_parameter='elearning_zoom_api_secret')