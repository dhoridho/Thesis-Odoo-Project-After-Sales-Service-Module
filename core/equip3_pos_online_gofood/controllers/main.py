# -*- coding: utf-8 -*-

import math
import json
from datetime import datetime, timedelta

import odoo
from odoo import http
from odoo.http import request,  Response

from ...restapi.controllers.helper import RestApi


def format24hour(hours):
    td = timedelta(hours=hours)
    dt = datetime.min + td
    return "{:%H:%M}".format(dt)

def normal_round(n, decimals=0):
    expoN = n * 10 ** decimals
    if abs(expoN) - abs(math.floor(expoN)) < 0.5:
        return math.floor(expoN) / 10 ** decimals
    return math.ceil(expoN) / 10 ** decimals

def check_params(data, req_fields):
    for field in req_fields:
        if field not in data:
            return False
    return True

class GoFoodRestApi(RestApi):

    """
    GoFood Awaiting Merchant Acceptance Event
    GoFood Driver Arrived Event
    GoFood Order Cancelled Event
    GoFood Driver Pickup Event (OTW Pickup)
    GoFood Order Completed Event
    GoFood Order Created Event
    GoFood Merchant Accepted Event
    """
    @http.route(['/api-gofood/orders'], type='json', auth='public', csrf=False, methods=['GET','POST']) 
    def gofood_api_orders(self, **kw): 
        data = json.loads(request.httprequest.data) 
        OnlineOutletOrder = request.env['pos.online.outlet.order']
        request_headers = request.httprequest.headers
        data_header = data['header']
        data_body = data['body']
        event_name = data_header['event_name']

        events = ['gofood.order.created','gofood.order.awaiting_merchant_acceptance', 'gofood.order.merchant_accepted', 'gofood.order.driver_otw_pickup', 'gofood.order.driver_arrived', 'gofood.order.completed', 'gofood.order.cancelled']
        if event_name not in events:
            response = {
                "message": "Unknown event name: %s" % (str(event_name))
            }
            return self.get_response(401, '401', response)

        domain = [
            ('online_outlet_id.gofood_merchant_id','=',data_body['outlet']['id']), 
            ('order_number','=',data_body['order']['order_number']),
            ('order_from','=','gofood')
        ]

        response = {'message': 'Failed Receive Order'}

        orders = OnlineOutletOrder.search(domain)
        if not orders:
            response['message'] = response['message'] + ': outlet not found'
            outlet_domain = [('gofood_merchant_id','=',data_body['outlet']['id'])]
            outlets = request.env['pos.online.outlet'].search(outlet_domain, limit=1)
            for outlet in outlets:
                order_details = self.gofood_prepare_order(outlet, data)
                OnlineOutletOrder.create(order_details)
                response = {'message': 'Orders Received'}

        if orders:
            status = data_body['order']['status']
            for order in orders:
                values = {
                    'status': status
                }
                if status.lower() == 'merchant accepted':
                    if order.state == 'new':
                        values['state'] = 'to pay'
                if status.lower() == 'cancelled':
                    values['state'] = 'cancel'

                order.write(values)
                response = {'message': 'Orders status changed'}

        return self.get_response(200, '200', response)

    def gofood_prepare_order(self, outlet, data):
        ProductTemplate = request.env['product.template'].sudo()
        data_header = data['header']
        data_body = data['body']
        order = data_body['order']
        values = {
            'online_outlet_id': outlet.id,
            'order_number': order['order_number'],
            'order_from': 'gofood',
            'status': 'New',
            'state': 'new',
            'order_data': json.dumps(data),
            'amount_total': order['order_total'],
            'order_date': order['created_at'][:19].replace('T',' '),
        }
        if data_body.get('customer'):
            values['info'] = data_body['customer']['name']
        order_type = str(data_body['service_type']).lower()
        values['order_type'] = order_type
        if order_type in ['gofood_pickup', 'pickup']:
            values['order_type'] = 'self-pickup'
        if order_type in ['gofood', 'delivery']:
            values['order_type'] = 'outlet-delivery'

        values['status'] = order['status']
        if values['status'].lower() == 'created':
            values['status'] = 'NEW'
            values['state'] = 'to pay' # auto accept order

        lines = []
        count_sequence = 1
        for item in order['order_items']:
            item_external_id = item['external_id']
            domain = [('id', '=', int(item_external_id.replace('ITEM-','')))]
            product = ProductTemplate.search(domain, limit=1)

            lines += [(0,0, {
                'sequence': count_sequence,
                'product_id': product.product_variant_id.id,
                'qty': item['quantity'],
                'price': item['price'],
                'note': item['notes'],
                'is_main_product': True,
            })]
            count_sequence += 1
            if item.get('variants'):
                for variant in item['variants']:
                    variant_external_id = variant['external_id']
                    domain = [('id', '=', int(variant_external_id.replace('V-','')))]
                    product = ProductTemplate.search(domain, limit=1)
                    lines += [(0,0, {
                        'sequence': count_sequence,
                        'product_id': product.product_variant_id.id,
                        'qty': 1,
                        'price': 0, #
                        'is_option_product': True,
                    })]
                    count_sequence += 1

        # Takeaway charges
        if order.get('takeaway_charges'):
            lines += [(0,0, {
                'sequence': 500,
                'product_id': request.env.ref('equip3_pos_online_outlet.product_template_takeaway_charges').sudo().product_variant_id.id,
                'qty': 1,
                'price': order['takeaway_charges'],
            })]

        values['line_ids'] = lines
        return values


        