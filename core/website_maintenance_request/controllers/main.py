# -*- coding: utf-8 -*-

from odoo import http, _
import base64
from odoo.http import request

class MaintenanceRequest(http.Controller):

    @http.route(['/website_maintenance_request/maintenance_request_create/'], auth='public', website=True, csrf=True)
    def maintenance_request_create(self, **kw):
        maintenance_team = 1
        if kw.get('maintenance_team_id', False):
            maintenance_team = kw.get('maintenance_team_id', False)
            print("=====================maintenance_team============================",maintenance_team)
        maintenance_request =  request.env['maintenance.request'].sudo().create({
                                                        'name': kw['name'],
                                                        'owner_user_id': request.env.user.id,
                                                        'equipment_id': int(kw['equipment_id']),
                                                        'priority': kw['priority'],
                                                        'description': kw['description'],
                                                        'maintenance_team_id': int(maintenance_team),
                                                         })
        print("======================maintenance_request=========================",maintenance_request)
        maintenance_template = request.env.ref('website_maintenance_request.email_template_maintenance_create_custom')
        maintenance_template.sudo().send_mail(maintenance_request.id, force_send=True)
        company = maintenance_request.company_id.name
        user = maintenance_request.owner_user_id.name
        vals = {
            'company':company,
            'user':user,
        }
        attachment_list = request.httprequest.files.getlist('attachment')
        for image in attachment_list:
                if kw.get('attachment'):
                    attachments = {
                               'res_name': image.filename,
                               'res_model': 'maintenance.request',
                               'res_id': maintenance_request.id,
                               'datas': base64.encodestring(image.read()),
                               'type': 'binary',
                               'name': image.filename,
                           }
                    attachment_obj = http.request.env['ir.attachment']
                    attach = attachment_obj.sudo().create(attachments)
        if len(attachment_list) > 0:
            group_msg = _('Customer has sent %s attachments to this Maintenance Request. Name of attachments are: ') % (len(attachment_list))
            for attach in attachment_list:
                group_msg = group_msg + '\n' + attach.filename
                group_msg = group_msg + '\n'  +  '. You can see top attachment menu to download attachments.'
                maintenance_request.sudo().message_post(body=group_msg,message_type='comment')
        return request.render('website_maintenance_request.thanks_maintenance_request_probc',vals)

    @http.route(['/page/maintenance_request/'], auth='user', website=True, csrf=True)
    def maintenance_request(self, **kw):
        Team_obj = request.env['maintenance.team']
        Teams = Team_obj.sudo().search([])
        
        Equipment_obj = request.env['maintenance.equipment']
        Equipments = Equipment_obj.sudo().search([])
        values = {
            'team_ids': Teams,
            'equipment_ids': Equipments,
        }
        
        return request.render('website_maintenance_request.maintenance_request_create_probc',values)
        
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
