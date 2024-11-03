# -*- coding: utf-8 -*-

import json
import requests

from datetime import datetime, timedelta
from dateutil import parser

from odoo import api, fields, models
from odoo.exceptions import ValidationError

class PosOnlineOutletOrder(models.Model):
    _inherit = "pos.online.outlet.order"


    #Set New Order Ready Time
    ##Partners will call this GrabFood endpoint to inform GrabFood about the more accurate order ready time.
    def action_set_ready_time_grabfood_order(self):
        self.ensure_one()
        context = self._context
        ConfigParameter = self.env['ir.config_parameter'].sudo()
        environment = ConfigParameter.get_param('base_setup.grabfood_environment')
        order = self
        values = {}
        content = {}

        is_access_token, access_token = self.env['pos.online.outlet'].grabfood_get_access_token()
        if not is_access_token:
            raise ValidationError(access_token)

        if access_token:
            headers = { 'Authorization': 'Bearer %s' % access_token, }

            duration = context['duration'] 
            date1 = parser.parse(order.order_ready_est_time) #This is based on ISO_8601/RFC3339.
            new_order_ready_est_time = (date1 + timedelta(minutes=int(duration))).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            json_data = {
                'orderID': order.order_number,
                'newOrderReadyTime': new_order_ready_est_time,
            }
            if environment == 'sandbox':
                endpoint_url = f'https://partner-api.stg-myteksi.com/grabfood-sandbox/partner/v1/order/readytime'
            if environment == 'production':
                endpoint_url = f'https://partner-api.grab.com/grabfood/partner/v1/order/readytime'

            response = requests.put(endpoint_url, headers=headers, json=json_data)
            if response.status_code == 200:
                content['status'] = 'success'
                content['data'] = json.loads(response.text)
            elif response.status_code == 204:
                content['status'] = 'success'
                content['data'] = '' #Successful. No Content returned. 
            else:
                content['status'] = 'failed'
                content['message'] = json.loads(response.text)['message']
            if response.status_code in [200, 204]:
                self.write({
                    'order_ready_new_est_time': new_order_ready_est_time,
                })

            content['id'] = order.id

        values['content'] = content
        return values


    def action_accept_grabfood_order(self):
        self.ensure_one()
        ConfigParameter = self.env['ir.config_parameter'].sudo()
        environment = ConfigParameter.get_param('base_setup.grabfood_environment')
        order = self
        values = {}
        content = {}

        is_access_token, access_token = self.env['pos.online.outlet'].grabfood_get_access_token()
        if not is_access_token:
            raise ValidationError(access_token)

        if access_token:
            headers = { 'Authorization': 'Bearer %s' % access_token, }
            json_data = {
                'orderID': order.order_number,
                'toState': 'Accepted',
            }
            if environment == 'sandbox':
                endpoint_url = f'https://partner-api.stg-myteksi.com/grabfood-sandbox/partner/v1/order/prepare'
            if environment == 'production':
                endpoint_url = f'https://partner-api.grab.com/grabfood/partner/v1/order/prepare'

            response = requests.post(endpoint_url, headers=headers, json=json_data)
            if response.status_code == 200:
                content['status'] = 'success'
                content['data'] = json.loads(response.text)
            elif response.status_code == 204:
                content['status'] = 'success'
                content['data'] = '' #Successful. No Content returned. 
            else:
                content['status'] = 'failed'
                content['message'] = json.loads(response.text)['message']
                
            if response.status_code in [200, 204]:
                order.write({
                    'manual_action': 'accept',
                    'status': 'Accepted',
                    'state': 'to pay',
                })

            content['id'] = order.id

        values['content'] = content
        return values


    def action_reject_grabfood_order(self):
        self.ensure_one()
        ConfigParameter = self.env['ir.config_parameter'].sudo()
        environment = ConfigParameter.get_param('base_setup.grabfood_environment')
        order = self
        values = {}
        content = {}

        is_access_token, access_token = self.env['pos.online.outlet'].grabfood_get_access_token()
        if not is_access_token:
            raise ValidationError(access_token)

        if access_token:
            headers = { 'Authorization': 'Bearer %s' % access_token, }
            json_data = {
                'orderID': order.order_number,
                'toState': 'Rejected',
            }
            if environment == 'sandbox':
                endpoint_url = f'https://partner-api.stg-myteksi.com/grabfood-sandbox/partner/v1/order/prepare'
            if environment == 'production':
                endpoint_url = f'https://partner-api.grab.com/grabfood/partner/v1/order/prepare'

            response = requests.post(endpoint_url, headers=headers, json=json_data)
            if response.status_code == 200:
                content['status'] = 'success'
                content['data'] = json.loads(response.text)
            elif response.status_code == 204:
                content['status'] = 'success'
                content['data'] = '' #Successful. No Content returned.
            else:
                content['status'] = 'failed'
                content['message'] = json.loads(response.text)['message']

            if response.status_code in [200, 204]:
                order.write({
                    'manual_action': 'reject',
                    'status': 'Rejected',
                    'state': 'cancel',
                })

            content['id'] = order.id

        values['content'] = content
        return values


    def action_mark_ready_grabfood_order(self):
        self.ensure_one()
        ConfigParameter = self.env['ir.config_parameter'].sudo()
        environment = ConfigParameter.get_param('base_setup.grabfood_environment')
        order = self
        values = {}
        content = {} 

        is_access_token, access_token = self.env['pos.online.outlet'].grabfood_get_access_token()
        if not is_access_token:
            raise ValidationError(access_token)

        if access_token:
            headers = { 'Authorization': 'Bearer %s' % access_token, }
            json_data = {
                'orderID': order.order_number,
                'markStatus': 1,
            }
            if environment == 'sandbox':
                endpoint_url = f'https://partner-api.stg-myteksi.com/grabfood-sandbox/partner/v1/orders/mark'
            if environment == 'production':
                endpoint_url = f'https://partner-api.grab.com/grabfood/partner/v1/orders/mark'

            response = requests.post(endpoint_url, headers=headers, json=json_data)
            if response.status_code == 200:
                content['status'] = 'success'
                content['data'] = json.loads(response.text)
            elif response.status_code == 204:
                content['status'] = 'success'
                content['data'] = '' #Successful. No Content returned.
            else:
                content['status'] = 'failed'
                content['message'] = json.loads(response.text)['message']

            if response.status_code in [200, 204]:
                order.write({
                    'is_mark_order_ready': True,
                })

            content['id'] = order.id

        values['content'] = content
        return values