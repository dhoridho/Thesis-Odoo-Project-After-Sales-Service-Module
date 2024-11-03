# -*- encoding: utf-8 -*-
from odoo import http
from odoo.http import request

class AcsWebcam(http.Controller):

    @http.route(['/acs/webcam/<string:model>/<int:record_id>','/acs/webcam/<string:model>/<int:record_id>/<string:image_field>'], type='http', auth="user", website=True)
    def acs_webcam(self, model, record_id, image_field='', **kw):
        record = request.env[model].sudo().search([('id', '=', record_id)])
        values = { 'record': record.id, 
            'model': model, 
            'record_name': record.display_name,
            'image_field': image_field,
            'action': record.acs_webcam_retrun_action(),
        }
        return request.render("acs_webcam.open_webcam", values)

    @http.route(['/acs/webcam/<string:model>/<int:record_id>/updateimage'], type="http", auth="public", methods=['post'], website=True)
    def acs_webcam_updateimage(self, model, record_id, **kwargs):
        record = request.env[model].sudo().browse([record_id])
        image_field = 'image_1920'
        if kwargs.get('image_field'):
            image_field = kwargs.get('image_field')
        record.write({image_field: kwargs.get('image_data')})

        redirect_url = '/web#model=%s&id=%s&action=%s&view_type=form' % (record._name, record.id, record.acs_webcam_retrun_action())
        return request.redirect(redirect_url)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: