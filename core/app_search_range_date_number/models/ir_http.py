# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import models
from odoo.http import request


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    def session_info(self):
        result = super(IrHttp, self).session_info()
        config_parameter = request.env['ir.config_parameter'].sudo()
        result['app_search_range_date_show'] = True if config_parameter.get_param('app_search_range_date_show', 'True') else False
        result['app_search_range_number_show'] = True if config_parameter.get_param('app_search_range_number_show', 'True') else False
        return result
