# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class AcsVideoCall(models.Model):
    _inherit = 'acs.video.call'

    def _get_meeting_link(self):
        on_own_site = self.env['ir.config_parameter'].sudo().get_param('acs_jitsi_meet.call_on_own_site')
        if on_own_site:
            server_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url') + '/videocall'
        else:
            server_url = self.env['ir.config_parameter'].sudo().get_param('acs_jitsi_meet.video_call_server_url')
        for rec in self:
            rec.meeting_link = server_url + '/' + rec.meeting_code

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
