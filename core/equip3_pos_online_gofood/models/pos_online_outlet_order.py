# -*- coding: utf-8 -*-

import json
import requests

from datetime import datetime, timedelta
from dateutil import parser

from odoo import api, fields, models
from odoo.exceptions import ValidationError

class PosOnlineOutletOrder(models.Model):
    _inherit = "pos.online.outlet.order"


    def action_accept_gofood_order(self):
        self.ensure_one()
        ConfigParameter = self.env['ir.config_parameter'].sudo()
        environment = ConfigParameter.get_param('base_setup.grabfood_environment')
        OnlineOutlet = self.env['pos.online.outlet']
        order = self
        values = {}
        content = {}

        
        is_access_token, access_token = OnlineOutlet.gobiz_get_access_token(scope='gofood:order:write')
        if not is_access_token:
            raise ValidationError(access_token)

        if access_token:
            headers = { 'Authorization': 'Bearer %s' % access_token, }
            base_url = '#'

            outlet = order.online_outlet_id
            outlet_id = outlet.gofood_merchant_id
            order_id = order.order_number
            order_type = 'delivery' #The order type, either delivery or pickup

            json_data = {
                'country_code': outlet.country_code,
            }
            if environment == 'sandbox':
                base_url = f'https://api.sandbox.gobiz.co.id'
            if environment == 'production':
                base_url = f'https://api.gobiz.co.id'
            endpoint_url = f'{base_url}/integrations/gofood/outlets/{outlet_id}/v1/orders/{order_type}/{order_id}/accepted'

            response = requests.put(endpoint_url, headers=headers, json=json_data)
            if response.status_code == 200:
                content['status'] = 'success'
                content['data'] = response.text
            elif response.status_code == 204:
                content['status'] = 'success'
                content['data'] = '' #Successful. No Content returned.
            else:
                content['status'] = 'failed'
                content['message'] = response.text

            if response.status_code in [200, 204]:
                order.write({
                    'manual_action': 'accept',
                    'status': 'Accepted',
                    'state': 'to pay',
                })

        content['id'] = order.id
        values['content'] = content
        return values


    def action_reject_gofood_order(self):
        self.ensure_one()
        ConfigParameter = self.env['ir.config_parameter'].sudo()
        environment = ConfigParameter.get_param('base_setup.grabfood_environment')
        OnlineOutlet = self.env['pos.online.outlet']
        order = self
        values = {}
        content = {}

        is_access_token, access_token = OnlineOutlet.gobiz_get_access_token(scope='gofood:order:write')
        if not is_access_token:
            raise ValidationError(access_token)

        if access_token:
            headers = { 'Authorization': 'Bearer %s' % access_token, }
            base_url = '#'

            outlet = order.online_outlet_id
            outlet_id = outlet.gofood_merchant_id
            order_id = order.order_number
            order_type = 'delivery' #The order type, either delivery or pickup

            json_data = {
                'country_code': outlet.country_code,
            }
            if environment == 'sandbox':
                base_url = f'https://api.sandbox.gobiz.co.id'
            if environment == 'production':
                base_url = f'https://api.gobiz.co.id'
            endpoint_url = f'{base_url}/integrations/gofood/outlets/{outlet_id}/v1/orders/{order_type}/{order_id}/cancelled'

            response = requests.put(endpoint_url, headers=headers, json=json_data)
            if response.status_code == 200:
                content['status'] = 'success'
                content['data'] = response.text
            elif response.status_code == 204:
                content['status'] = 'success'
                content['data'] = '' #Successful. No Content returned.
            else:
                content['status'] = 'failed'
                content['message'] = response.text

            if response.status_code in [200, 204]:
                order.write({
                    'manual_action': 'reject',
                    'status': 'Rejected',
                    'state': 'cancel',
                })

        content['id'] = order.id
        values['content'] = content
        return values

    def action_mark_ready_gofood_order(self):
        self.ensure_one()
        ConfigParameter = self.env['ir.config_parameter'].sudo()
        environment = ConfigParameter.get_param('base_setup.gobiz_environment')
        OnlineOutlet = self.env['pos.online.outlet']
        
        order = self
        values = {}
        content = {}

        is_access_token, access_token = OnlineOutlet.gobiz_get_access_token(scope='gofood:order:write')
        if not is_access_token:
            raise ValidationError(access_token)

        if access_token:
            headers = { 'Authorization': 'Bearer %s' % access_token, }
            base_url = '#'

            outlet = order.online_outlet_id
            outlet_id = outlet.gofood_merchant_id
            order_id = order.order_number
            order_type = 'delivery' #The order type, either delivery or pickup

            json_data = {
                'country_code': outlet.country_code,
            }
            if environment == 'sandbox':
                base_url = f'https://api.sandbox.gobiz.co.id'
            if environment == 'production':
                base_url = f'https://api.gobiz.co.id'
            endpoint_url = f'{base_url}/integrations/gofood/outlets/{outlet_id}/v1/orders/{order_type}/{order_id}/food-prepared'

            response = requests.put(endpoint_url, headers=headers, json=json_data)
            if response.status_code == 200:
                content['status'] = 'success'
                content['data'] = response.text
            elif response.status_code == 204:
                content['status'] = 'success'
                content['data'] = '' #Successful. No Content returned.
            else:
                content['status'] = 'failed'
                content['message'] = response.text

            if response.status_code in [200, 204]:
                order.write({
                    'is_mark_order_ready': True,
                })

            content['id'] = order.id

        values['content'] = content
        return values