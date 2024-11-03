# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale
from datetime import date, timedelta, datetime
from odoo.exceptions import UserError, ValidationError
import logging
_logger = logging.getLogger(__name__)
import json

class GravioLogController(http.Controller):
    
    
    @http.route('/log/create', type='json', auth='api_key')
    def create_log(self, **rec):
        print("recccccccccccccc", rec)
        if request.jsonrequest:
            print("rec", rec)
            data = json.loads(request.httprequest.data)
            vals = {
                'data': data,
                'area': data.get('AreaName'),
                'log': data.get('Data'),
                'layer': data.get('LayerName'),
                'timestamp': data.get('Timestamp')
            }
            log = request.env['gravio.log'].sudo().create(vals)
            args = {'success': True, 'message': 'Success', 'id': log.id, 'data': rec}
        return args

    # @http.route('/log/create', type='json', auth='api_key')
    # def create_log(self, **rec):
    #     if request.jsonrequest:
    #         print("rec", rec)
    #         # data = {'uuid':'Ec:FA;Bc:23:OF:E5','temperature':'29.60','humidity':'85.00'}
    #         if rec['sensor_id']:
    #             vals = {
    #                 'button_pressed': rec['button_pressed'],
    #                 'distance': rec['distance'],
    #                 'sensor_id': rec['sensor_id'],
    #                 'length': rec['length'],
    #                 'width': rec['width'],
    #                 'height': rec['height'],
    #             }
    #             log = request.env['gravio.log'].sudo().create(vals)
    #             args = {'success': True, 'message': 'Success', 'id': log.id}
    #     return args

    @http.route('/log/list', type='json', auth='user')
    def get_logs(self):
        logs = request.env['lot.log'].search([], order="id asc")
        data = {'status': 200, 'count': len(logs), 'response': logs, 'message': ('total {} data found').format(len(logs))}
        return data