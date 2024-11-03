# -*- coding: utf-8 -*-
from odoo import _, fields, models, api
from odoo.exceptions import UserError


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    is_auto_sync = fields.Boolean(string="Auto Sync App")
    duration = fields.Integer(string="Duration")

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        params = self.env['ir.config_parameter'].sudo()
        is_auto_sync = params.get_param('is_auto_sync', default=False)
        duration = params.get_param('duration', default=0)
        res.update(is_auto_sync=is_auto_sync, duration=duration)
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        if self.is_auto_sync:
            if self.duration == 0:
                raise UserError(_('Please provide duration for auto sync process.'))
            duration = self.duration
        else:
            duration = 0
        self.env['ir.config_parameter'].sudo().set_param("is_auto_sync", self.is_auto_sync)
        self.env['ir.config_parameter'].sudo().set_param("duration", duration)


ResConfigSettings()


class IrConfigParameter(models.Model):
    _inherit = "ir.config_parameter"

    def get_dynamic_sync_settings(self):
        query = "SELECT value FROM ir_config_parameter WHERE key = 'is_auto_sync'"
        self.env.cr.execute(query)
        is_auto_sync = self.env.cr.fetchone()
        is_auto_sync = is_auto_sync and is_auto_sync[0] or False
        query = "SELECT value FROM ir_config_parameter WHERE key = 'duration'"
        self.env.cr.execute(query)
        duration = self.env.cr.fetchone()
        duration = duration and duration[0] or 0
        if is_auto_sync:
            return {
                'is_auto_sync': eval(is_auto_sync),
                'duration': int(duration),
            }
        else:
            return {
                'is_auto_sync': is_auto_sync,
                'duration': int(duration),
            }


IrConfigParameter()
