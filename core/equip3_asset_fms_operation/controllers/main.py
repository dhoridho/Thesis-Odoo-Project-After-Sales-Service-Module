# -*- coding: utf-8 -*-

from odoo import http, _
from odoo.http import request
import base64
from odoo.addons.website_maintenance_request.controllers.main import MaintenanceRequest  # Import the class

class InheritMaintenanceRequest(MaintenanceRequest):

    @http.route(['/website_maintenance_request/maintenance_request_create/'], auth='public', website=True, csrf=True)
    def maintenance_request_create(self, **kw):

        maintenance_facilities_area = 1
        if kw.get('facility_area', False):
            maintenance_facilities_area = kw.get('facility_area', False)
        if kw.get('equipment_id'):
            equipment_id = int(kw.get('equipment_id'))
        else:
            equipment_id = False
            
        if kw.get('description'):
            description = kw.get('description')
        else:
            description = False
        
        maintenance_request =  request.env['maintenance.request'].sudo().create({
                                                        'facility_area': int(maintenance_facilities_area),
                                                        'owner_user_id': request.env.user.id,
                                                        'equipment_id': equipment_id,
                                                        'priority': kw['priority'],
                                                        'remarks': description,
                                                         })
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
        
    @http.route(['/page/maintenance_request/'], auth='public', website=True, csrf=True)
    def maintenance_request(self, **kw):
        FacilityArea = request.env['maintenance.facilities.area']
        selected_facility_area = FacilityArea.sudo().search([('id', '=', kw.get('facility_area'))])
        facility_area_ids = FacilityArea.sudo().search([('id', 'child_of', selected_facility_area.id)])
        
        if not facility_area_ids:
            facility_area_ids = FacilityArea.sudo().search([('id', '=', kw.get('facility_area'))])

        Equipment = request.env['maintenance.equipment']
        MaintenanceRequest = request.env['maintenance.request']
        
        equipment_ids = Equipment.sudo().search([])
        maintenance_request_ids = MaintenanceRequest.sudo().search([])

        values = {
            'selected_facility_area_id': int(kw.get('facility_area')) if kw.get('facility_area') else "",
            'selected_equipment_id': int(kw.get('asset')) if kw.get('asset') else "",
            'facility_area_ids': facility_area_ids,
            'equipment_ids': equipment_ids,
            'maintenance_request_ids': maintenance_request_ids,
            'from_scan': kw.get('from_scan') if kw.get('from_scan') else ""
        }
        return request.render('website_maintenance_request.maintenance_request_create_probc', values)


    @http.route(['/page/asset_information/'], auth='public', website=True, csrf=False)
    def asset_information(self, **kw):
        equipment_id = request.env['maintenance.equipment'].sudo().browse([int(kw.get('asset'))])
        values = {
            'equipment_id': equipment_id,
            'from_scan':True
        }
        return request.render('equip3_asset_fms_operation.assets_information',values)



