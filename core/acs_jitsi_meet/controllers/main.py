# -*- encoding: utf-8 -*-
from odoo import http
from odoo.http import request

class AcsVideoCall(http.Controller):

    @http.route(['/videocall/<string:meeting_name>'], type='http', auth="public", website=True)
    def acs_videocall(self, meeting_name, **kw):
        videocall_server_url = request.env['ir.config_parameter'].sudo().get_param('acs_jitsi_meet.video_call_server_url')
        site_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
        meeting = request.env['acs.video.call'].sudo().search([('meeting_code','=',meeting_name)], limit=1)
        values = { 
            'meeting_name': meeting_name,
            'server_name': videocall_server_url.split("//")[1],
            'site_url': site_url,
            'meeting': meeting,
        }
        return request.render("acs_jitsi_meet.acs_videocall", values)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
