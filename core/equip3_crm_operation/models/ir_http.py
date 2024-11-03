# -*- coding: utf-8 -*-

import hashlib
import json

from odoo import api, models
from odoo.http import request
from odoo.tools import ustr

class Http(models.AbstractModel):
    _inherit = 'ir.http'

    def webclient_rendering_context(self):
        rendering_context = super(Http, self).webclient_rendering_context()
        rendering_context['google_maps_api_key'] = request.env['ir.config_parameter'].sudo().get_param('google_maps_api_key')
        return rendering_context
