# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import route,request
import requests
import json

class Equip3GeneralApi(http.Controller):
    @route('/api/get_data', auth='public',type='json')
    def general_api_get_data(self, **kw):
        request_data = request.jsonrequest
        session = requests.Session()
        cookie = {'session_id': request_data.get('id')}
        session.cookies.update(cookie)
        base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
        data =  request_data.get('request')
        rpc_request =  session.get(f"{base_url}{request_data.get('url')}",cookies=cookie,json=data)
        response_data = rpc_request.json()
        if 'error' in response_data:
            return response_data['error']

        return response_data['result']


