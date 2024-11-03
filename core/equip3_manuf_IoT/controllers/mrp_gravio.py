# -*- coding: utf-8 -*-
from odoo import http, _
from odoo.http import request
from dateutil.parser import parse
from odoo.exceptions import AccessDenied

import json
import logging

_logger = logging.getLogger(__name__)

GRAVIO_FIELDS = [
    {
        'key': 'AreaId',
        'field': 'area_id',
        'model': 'mrp.gravio.area',
        'fields': [('gravio_id', 'AreaId'), ('name', 'AreaName')]
    },
    {
        'key': 'KindId',
        'field': 'kind_id',
        'model': 'mrp.gravio.kind',
        'fields': [('gravio_id', 'KindId'), ('name', 'KindName')]
    },
    {
        'key': 'LayerId',
        'field': 'layer_id',
        'model': 'mrp.gravio.layer',
        'fields': [('gravio_id', 'LayerId'), ('name', 'LayerName')]
    },
    {
        'key': 'PhysicalDeviceId',
        'field': 'physical_device_id',
        'model': 'mrp.gravio.physical',
        'fields': [('gravio_id', 'PhysicalDeviceId'), ('name', 'PhysicalDeviceName')]
    },
    {
        'key': 'VirtualDeviceId',
        'field': 'virtual_device_id',
        'model': 'mrp.gravio.virtual',
        'fields': [('gravio_id', 'VirtualDeviceId')]
    },
    {
        'key': 'DataId',
        'field': 'data_id',
        'model': 'mrp.gravio.data',
        'fields': [('gravio_id', 'DataId'), ('data', 'Data'), ('type', 'DataType')]
    }
]


class MrpGravioLogController(http.Controller):
    
    @http.route('/mrp_gravio/create', type='json', auth='none', csrf=False)
    def create_mrp_gravio_log(self, **kwargs):
        payload = json.loads(request.httprequest.data)

        db = payload.get('db', False)
        if db:
            request.session.db = db

        headers = request.httprequest.environ
        api_key = headers.get("HTTP_API_KEY")
        if not api_key:
            _logger.info('Please provide API KEY!')
            return {'success': False, 'message': _('Please provide API KEY!')}

        request.uid = 1
        try:
            auth_api_key = request.env["auth.api.key"]._retrieve_api_key(api_key)
        except Exception as err:
            _logger.info(str(err))
            return {'success': False, 'message': err}
        
        request._env = None
        request.uid = auth_api_key.user_id.id
        request.auth_api_key = api_key
        request.auth_api_key_id = auth_api_key.id

        try:
            record_id = request.env['mrp.gravio.record'].sudo().create({})
            log_ids = []
            for letter in 'xyz':
                if letter not in payload:
                    continue

                data = payload[letter]
                
                log_values = {'record_id': record_id.id}
                for gravio in GRAVIO_FIELDS:
                    gravio_id = data.get(gravio['key'], False)
                    if not gravio_id:
                        continue
                    obj_id = request.env[gravio['model']].sudo().search([('gravio_id', '=', gravio_id)])
                    if not obj_id:
                        obj_values = {}
                        for field_name, gravio_name in gravio['fields']:
                            obj_values[field_name] = data.get(gravio_name, False)
                        obj_id = request.env[gravio['model']].sudo().create(obj_values)
                    log_values[gravio['field']] = obj_id.id

                timestamp = data.get('Timestamp', False)
                if timestamp:
                    timestamp = parse(timestamp).replace(tzinfo=None)
                
                log_values['timestamp'] = timestamp
                log_values['json_data'] = json.dumps(data)
                log = request.env['mrp.gravio.log'].sudo().create(log_values)
                log_ids += [log.id]

            if not log_ids:
                record_id.unlink()
            else:
                record_id._assign_to_production_record()
                
            _logger.info('Success! logs: %s' % log_ids)
            return {'success': True, 'message': 'Success!', 'ids': log_ids}

        except Exception as err:
            _logger.info(str(err))
            return {'success': False, 'message': err}
