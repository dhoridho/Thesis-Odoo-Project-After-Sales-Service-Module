# -*- coding: utf-8 -*-

from odoo import fields, models, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    acs_video_call_server_url = fields.Char(
        string='Jisti Server URL',
        config_parameter='acs_jitsi_meet.video_call_server_url')
    acs_video_call_on_own_site = fields.Char(
        string='On Own Site',
        config_parameter='acs_jitsi_meet.call_on_own_site')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: