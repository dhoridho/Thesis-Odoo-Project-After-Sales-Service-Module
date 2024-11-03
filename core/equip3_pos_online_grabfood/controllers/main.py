# -*- coding: utf-8 -*-

import base64
import math
import json
from datetime import datetime, timedelta
from dateutil import parser

import odoo
from odoo import http
from odoo.http import request

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

class GrabFoodRestAPI(RestApi):

    # Partner: Oauth Token API, GrabFood uses this partner endpoint
    @http.route(['/api-grabfood/oauth/token'], type='json', auth='public', csrf=False, methods=['GET','POST'])
    def grabfood_oauth_token(self, **kw):
        Settings = request.env['res.config.settings']
        headers = {'Content-Type': 'application/json'}
        data = kw 
        if not data:
            data = json.loads(request.httprequest.data)

        pass_check = check_params(data, ['client_id','client_secret'])
        if not pass_check:
            response = {
                "message": "Missing required field client or secret"
            }
            return self.get_response(401, '401', response)

        if pass_check:
            is_allow_access = Settings._olo_check_user_secret(data.get('client_id'),  data.get('client_secret'))
            if is_allow_access:
                access_token = Settings._olo_generate_access_token()
                response = {
                    "access_token": access_token,
                    "token_type": "Bearer",
                    "expires_in": 604799 #Hardcode 7 days, this just follows GrabFood standard response
                }
            else:
                response = {
                    "message": "Unauthorized"
                }
                return self.get_response(401, '401', response)

        return self.get_response(200, '200', response)


    # Partner: Get Food Menu API, GrabFood uses this partner endpoint 
    @http.route(['/api-grabfood/merchant/menu'], type='http', auth='public', csrf=False, methods=['GET','POST'])
    def grabfood_merchant_menu(self, **kw):
        Settings = request.env['res.config.settings']
        SellingTime = request.env['pos.online.outlet.selling.time']
        data = kw
        request_headers = request.httprequest.headers
        is_allow_access = Settings._olo_check_access_token(request_headers.get('Authorization'))
        if not is_allow_access:
            response = { "message": "Unauthorized" }
            response = request.make_response(json.dumps(response), headers=[('Content-Type', 'application/json')])
            response.status_code = 401
            return response

        headers = {'Content-Type': 'application/json'}
        response = { }
        merchantID = data.get('merchantID')
        if not merchantID:
            response = { "message": "Missing required field merchantID" }
            response = request.make_response(json.dumps(response), headers=[('Content-Type', 'application/json')])
            response.status_code = 401
            return response

        domain = [('grabfood_merchant_id','=', merchantID)]
        outlet = request.env['pos.online.outlet'].sudo().search(domain)
        if not outlet:
            response = { "message": "merchantID is not found" }
            response = request.make_response(json.dumps(response), headers=[('Content-Type', 'application/json')])
            response.status_code = 401
            return response

        # outlet_exponent = outlet.exponent
        outlet_exponent = outlet.currency_id.decimal_places
        exponent = 10 ** outlet_exponent

        used_selling_times = []
        categories = [] 
        line_category_ids = filter(lambda c: c['available_in_grabfood'] == True, outlet.categ_ids)
        for category_sequence, line_category in enumerate(line_category_ids):
            category = line_category.pos_categ_id
            items = []
            for product_sequence, line_product in enumerate(line_category.line_product_ids):
                product = line_product.product_tmpl_id
                if not product.available_in_pos:
                    continue
                if not product.product_variant_id:
                    continue

                modifierGroups = []
                for line_option in product.oloutlet_product_option_ids:
                    modifiers = []
                    for product_option_sequence, product_option in enumerate(line_option.product_tmpl_ids):
                        if not product_option.available_in_pos:
                            continue
                        if not product_option.product_variant_id:
                            continue

                        modifiers += [{
                            "id": 'MODIFIER-' + str(product_option.id),
                            "name": product_option.name,
                            "sequence": product_option.oloutlet_sequence,
                            "availableStatus": product_option.oloutlet_stock_available and 'AVAILABLE' or 'UNAVAILABLE',
                            "price": int(normal_round(product_option.list_price)) * exponent,
                        }]

                    if modifiers:
                        modifierGroups += [{
                            "id": 'MODIFIERGROUP-' + str(line_option.id),
                            "name": line_option.name,
                            "sequence": line_option.sequence,
                            "availableStatus": 'AVAILABLE',
                            "selectionRangeMin": line_option.min_selection,
                            "selectionRangeMax": len(modifiers),
                            "modifiers": modifiers,
                        }]

                items_values = {
                    "id": 'ITEM-' + str(product.id),
                    "name": product.name or "",
                    "sequence": line_product.sequence,
                    "availableStatus": line_product.is_available and 'AVAILABLE' or 'UNAVAILABLE',
                    "price": int(normal_round(product.list_price,0)) * exponent,
                    "description": product.oloutlet_description or "",
                    "photos": [ product.oloutlet_product_image_url, ],
                }
                items_selling_time = "operationalHourID-%s" % str(outlet.id)
                if not category.is_use_outlet_operational_hours:
                    items_selling_time = ''
                if not product.is_use_outlet_operational_hours:
                    items_selling_time = "sellingTimeID-%s" % str(product.selling_time_id.id)
                if items_selling_time:
                    items_values['sellingTimeID'] = items_selling_time
                    used_selling_times += [items_selling_time]

                items_values['modifierGroups'] = modifierGroups
                items += [items_values]

            if items:
                categories_values = {
                    "id": 'CATEGORY-' + str(category.id),
                    "name": category.name or "",
                    "sequence": line_category.sequence,
                    "availableStatus": 'AVAILABLE',
                    "items": items,
                    "sellingTimeID": "operationalHourID-%s" % str(outlet.id),
                }
                if not category.is_use_outlet_operational_hours:
                    categories_values['sellingTimeID'] = "sellingTimeID-%s" % str(category.selling_time_id.id)
                used_selling_times += [categories_values['sellingTimeID']]

                categories += [categories_values]

        currency_id = outlet.currency_id
        currency = {
            "code": currency_id.name,
            "symbol": currency_id.symbol, # "Rp",
            "exponent": outlet_exponent #exponent: Log base 10 of the number of times we have to multiply the major unit to get the minor unit. Should be 0 for VN and 2 for others countries (SG/MY/ID/TH/PH/KH)
        }

        used_selling_times = list(set(used_selling_times))
        selling_times = []
        selling_times += [outlet.get_outlet_selling_time()]
        selling_times += SellingTime.get_selling_times()
        selling_times = [s for s in selling_times if s['id'] in used_selling_times]

        response = {
            "merchantID": outlet.grabfood_merchant_id,
            "partnerMerchantID": outlet.grabfood_partner_merchant_id,
            "currency": currency,
            "sellingTimes": selling_times,
        }
        if categories:
            response['categories'] = categories
            
        headers = [('Content-Type', 'application/json')]
        return request.make_response(json.dumps(response), headers=headers)


    # Partner: Orders API, GrabFood uses this partner endpoint
    @http.route(['/api-grabfood/orders'], type='json', auth='public', csrf=False, methods=['GET','POST']) 
    def grabfood_api_orders(self, **kw):
        Settings = request.env['res.config.settings']
        data = json.loads(request.httprequest.data) 

        request_headers = request.httprequest.headers
        is_allow_access = Settings._olo_check_access_token(request_headers.get('Authorization'))
        if not is_allow_access:
            response = {
                "message": "Unauthorized",
            }
            return self.get_response(401, '401', response) 

        _message = 'Order Received'
        domain = [
            ('online_outlet_id.grabfood_merchant_id','=',data['merchantID']), 
            ('online_outlet_id.grabfood_partner_merchant_id','=',data['partnerMerchantID']),
            ('order_number','=',data['orderID']),
            ('order_from','=','grabfood')
        ]
        order = request.env['pos.online.outlet.order'].search(domain, limit=10) #check duplicate
        if not order:
            domain = [('grabfood_merchant_id','=',data['merchantID']), 
                ('grabfood_partner_merchant_id','=',data['partnerMerchantID'])]
            outlets = request.env['pos.online.outlet'].search(domain)
            outlet_ids = []
            for outlet in outlets:
                if outlet.id not in outlet_ids:
                    order_details = self.grabfood_prepare_order(outlet, data)
                    request.env['pos.online.outlet.order'].create(order_details)
                    outlet_ids += [outlet.id]

            if not outlets:        
                _message += "\n Outlet don\'t exist in the System."
        if order:
            _message += "\n Order already exist."

        headers = {'Content-Type': 'application/json'}
        response = {'message': _message}
        return self.get_response(200, '200', response)

    def grabfood_prepare_order(self, outlet, data):
        ProductTemplate = request.env['product.template'].sudo()
        order_date = parser.parse(data['orderTime']).strftime('%Y-%m-%d %H:%M:%S') #This is based on ISO_8601/RFC3339.
        outlet_exponent = data['currency']['exponent']
        exponent = 10 ** outlet_exponent
        values = {
            'online_outlet_id': outlet.id,
            'order_number': data['orderID'],
            'info': data['shortOrderNumber'],
            'order_from': 'grabfood',
            'status': 'New',
            'state': 'new',
            'order_data': json.dumps(data),
            'amount_total_order': data['price']['eaterPayment'] / exponent,
            'order_date': order_date,
            'order_date_str': data['orderTime'],
            'payment_type': data.get('paymentType','').lower(),
            'exponent': outlet_exponent,
        }

        order_type = data['featureFlags']['orderType']
        values['order_type'] = order_type
        if order_type == 'TakeAway':
            values['order_type'] = 'self-pickup'
        if order_type in ['DeliveredByGrab']:
            values['order_type'] = 'grab-delivery'
        if order_type in ['DeliveredByRestaurant']:
            values['order_type'] = 'outlet-delivery'
        if order_type in ['DineIn']:
            values['order_type'] = 'dine-in'

        if data['featureFlags']['orderAcceptedType'].lower() == 'auto':
            values['status'] = 'Accepted'
            values['state'] = 'to pay'

        if data.get('orderReadyEstimation'):
            values['order_ready_est_allow_change'] = data['orderReadyEstimation']['allowChange']
            values['order_ready_est_time'] = data['orderReadyEstimation']['estimatedOrderReadyTime']
            values['order_ready_est_max_time'] = data['orderReadyEstimation']['maxOrderReadyTime']

        lines = []
        count_sequence = 1
        for item in data['items']:
            domain = [('id', '=', int(item['id'].replace('ITEM-','')))] 
            product = ProductTemplate.with_context(active_test=False).search(domain, limit=1)
            if not product.available_in_pos:
                product.write({ 'available_in_pos': True })

            lines += [(0,0, {
                'sequence': count_sequence,
                'product_id': product.product_variant_id.id,
                'qty': item['quantity'],
                'price': item['price'] / exponent,
                'note': item['specifications'],
                'is_main_product': True,
            })]
            count_sequence += 1
            if item['modifiers']:
                for modifier in item['modifiers']:
                    domain = [('id', '=', int(modifier['id'].replace('MODIFIER-','')))] 
                    product = ProductTemplate.with_context(active_test=False).search(domain, limit=1)
                    lines += [(0,0, {
                        'sequence': count_sequence,
                        'product_id': product.product_variant_id.id,
                        'qty': modifier['quantity'],
                        'price': 0 / exponent, # Modifiers price already calculate in the main item
                        'is_option_product': True,
                    })]
                    count_sequence += 1

        amount_promo = 0
        if data['price'].get('merchantFundPromo'):
            amount_promo += data['price']['merchantFundPromo'] / exponent
        if data['price'].get('grabFundPromo'):
            amount_promo += data['price']['grabFundPromo'] / exponent
        if amount_promo:
            lines += [(0,0, {
                'sequence': 511,
                'product_id': request.env.ref('equip3_pos_online_outlet.product_template_promo').sudo().product_variant_id.id,
                'qty': 1,
                'price': -1 * amount_promo,
            })]

        values['line_ids'] = lines
        return values

    # Partner: Order State API, GrabFood uses this partner endpoint
    @http.route(['/api-grabfood/order/state'], type='json', auth='public', csrf=False, methods=['GET','POST', 'PUT'])
    def grabfood_api_order_state(self, **kw):
        Settings = request.env['res.config.settings']
        data = json.loads(request.httprequest.data)

        request_headers = request.httprequest.headers
        is_allow_access = Settings._olo_check_access_token(request_headers.get('Authorization'))
        if not is_allow_access:
            response = {
                "message": "Unauthorized",
            }
            return self.get_response(401, '401', response)

        domain = [
            ('online_outlet_id.grabfood_merchant_id','=',data['merchantID']), 
            ('online_outlet_id.grabfood_partner_merchant_id','=',data['partnerMerchantID']),
            ('order_number','=',data['orderID']),
            ('order_from','=','grabfood')
        ]
        orders = request.env['pos.online.outlet.order'].search(domain)
        for order in orders:
            order.write({ 'status': data['state'] })

        headers = {'Content-Type': 'application/json'}
        response = {'message': 'Order State Received'}   
        return self.get_response(200, '200', response)