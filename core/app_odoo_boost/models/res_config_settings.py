# -*- coding: utf-8 -*-

import logging

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    group_enable_discuss = fields.Boolean('Enable Discuss',
                                          help="Uncheck to Disable odoo IM(instant message). Uncheck to make odoo speed up.",
                                          implied_group='app_odoo_boost.group_enable_discuss')
    group_disable_poll = fields.Boolean('Disable odoo bus for poll',
                                        help="Check to Disable poll, so you can not receive push message. Check to make odoo speed up.",
                                        implied_group='app_odoo_boost.group_disable_poll')
    app_stop_subscribe = fields.Boolean('Stop Odoo Subscribe', help="Check to stop subscribe and follow. Check to make odoo speed up.")

    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        ir_config = self.env['ir.config_parameter'].sudo()

        app_stop_subscribe = False if ir_config.get_param('app_stop_subscribe') == "False" else True

        res.update(
            app_stop_subscribe=app_stop_subscribe,
        )
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        ir_config = self.env['ir.config_parameter'].sudo()
        ir_config.set_param("app_stop_subscribe", self.app_stop_subscribe or "False")
        # 设置 discuss 菜单可见性
        group_enable_discuss = ResConfigSettings.group_enable_discuss
        if not group_enable_discuss:
            self.env.ref('mail.menu_root_discuss').write({'active': group_enable_discuss})

