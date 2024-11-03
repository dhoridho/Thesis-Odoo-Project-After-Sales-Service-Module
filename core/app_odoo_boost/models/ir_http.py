# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo import models
from odoo.http import request


class Http(models.AbstractModel):
    _inherit = 'ir.http'

    def session_info(self):
        User = request.env['res.users']
        ir_config = self.env['ir.config_parameter'].sudo()

        app_stop_subscribe = True if ir_config.get_param('app_stop_subscribe', False) == "True" else False

        if User.has_group('app_odoo_boost.group_enable_discuss'):
            app_enable_discuss = True
        else:
            app_enable_discuss = False

        if User.has_group('app_odoo_boost.group_disable_poll'):
            app_disable_poll = True
        else:
            app_disable_poll = False


        result = super(Http, self).session_info()
        result['app_enable_discuss'] = app_enable_discuss
        result['app_disable_poll'] = app_disable_poll
        result['app_stop_subscribe'] = app_stop_subscribe
        # result['x'] = ICP.get_param('x')
        return result
