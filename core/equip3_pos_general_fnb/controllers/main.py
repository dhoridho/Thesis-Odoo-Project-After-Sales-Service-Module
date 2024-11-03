# -*- coding: utf-8 -*

import odoo
from odoo import http
from odoo.http import request
from odoo.addons.point_of_sale.controllers.main import PosController

class pos_fnb_controller(PosController):

    @http.route(['/pos/fnb/scanQrCode/'], type='http', auth='public')
    def scanQrOrder(self, order_id='', **k):
        """
        http://localhost:8069/pos/fnb/scanQrCode/?order_id=[ID: integer]&fields=['name']
        """
        try:
            id = int(order_id)
            order = request.env['pos.order'].sudo().search([('id','=',id)])
        except:
            return "Order not Found"
        config = None
        if not order:
            return "Order not Found"
        else:
            config = order.config_id
            
        fields = []
        fields_label_by_name = {}
        if config.pos_receipt_template_id:
            for label_qrcode in config.pos_receipt_template_id.qrcode_ids:
                fields.append(label_qrcode.field_id.name)
                fields_label_by_name[label_qrcode.field_id.name] = label_qrcode.name

        result = request.env['pos.order'].sudo().search_read([('id', '=', id)], fields)
        if len(result) == 1:
            detail_order = {}
            for field, value in result[0].items():
                if not value:
                    continue
                if fields_label_by_name.get(field, None):
                    detail_order[fields_label_by_name[field]] = value
                else:
                    detail_order[field] = value
            context = {
                'order': detail_order,
            }
            response = request.render('equip3_pos_masterdata.qrcode_order', context)
            response.headers['Cache-Control'] = 'no-store'
            return response
        else:
            return "Order not Found"
