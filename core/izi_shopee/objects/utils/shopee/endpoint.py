# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah
# Revised August-2022 PT. HashMicro

import hashlib
import hmac
import time
import json


class ShopeeEndpoint(object):

    HOSTS = {
        'live': 'https://partner.shopeemobile.com',
        'base': 'https://partner.test-stable.shopeemobile.com'
    }

    ENDPOINTS = {
        'v1': {
            'get_awb_url': ('POST', '/api/v1/logistics/airway_bill/get_mass'),
            'get_my_income': ('POST', '/api/v1/orders/income'),
            'batch_ship_order': ('POST', '/api/v1/logistics/batch_init')
        },
        'v2': {
            'auth': ('POST', '/api/v2/shop/auth_partner'),
            'token_renew': ('POST', '/api/v2/auth/access_token/get'),
            'token_get': ('POST', '/api/v2/auth/token/get'),
            'shop_info': ('GET', '/api/v2/shop/get_shop_info'),
            'shop_address': ('GET', '/api/v2/logistics/get_address_list'),
            'profile_info': ('GET', '/api/v2/shop/get_profile'),
            'logistic_list': ('GET', '/api/v2/logistics/get_channel_list'),
            'product_list': ('GET', '/api/v2/product/get_item_list'),
            'product_info': ('GET', '/api/v2/product/get_item_base_info'),
            'product_variant_list': ('GET', '/api/v2/product/get_model_list'),
            'category_list': ('GET', '/api/v2/product/get_category'),
            'brand_list': ('GET', '/api/v2/product/get_brand_list'),
            'attribute_list': ('GET', '/api/v2/product/get_attributes'),
            'attribute_list_tree': ('GET', '/api/v2/product/get_attribute_tree'),

            # order management
            'order_list': ('GET', '/api/v2/order/get_order_list'),
            'order_detail': ('GET', '/api/v2/order/get_order_detail'),
            'batch_ship_order': ('POST', '/api/v2/logistics/batch_ship_order'),
            'reject_order': ('POST', '/api/v2/order/cancel_order'),
            'buyer_cancellation': ('POST', '/api/v2/order/handle_buyer_cancellation'),

            # logistic / shipping
            'shipping_doc_info': ('GET', '/api/v2/logistics/get_shipping_document_info'),
            'shipping_parameter': ('GET', '/api/v2/logistics/get_shipping_parameter'),
            'ship_order': ('POST', '/api/v2/logistics/ship_order'),
            'get_awb_num': ('GET', '/api/v2/logistics/get_tracking_number'),
            'get_tracking_number': ('GET', '/api/v2/logistics/get_tracking_number'),
            'download_shipping_document': ('POST', '/api/v2/logistics/download_shipping_document'),
            'create_shipping_document': ('POST', '/api/v2/logistics/create_shipping_document'),
            'get_shipping_document_status': ('POST', '/api/v2/logistics/get_shipping_document_result'),

            # order income
            'get_my_income': ('POST', '/api/v2/payment/get_escrow_detail'),

            # webhook
            'set_push_webhook': ('POST', '/api/v2/push/set_push_config'),

            # get wallet
            'wallet_transaction_list': ('GET', '/api/v2/payment/get_wallet_transaction_list'),

            # action product
            'add_new_product': ('POST', '/api/v2/product/add_item'),
            'set_product_price': ('POST', '/api/v2/product/update_price'),
            'set_product_stock': ('POST', '/api/v2/product/update_stock'),
            'set_product_unlist': ('POST', '/api/v2/product/unlist_item'),
            'set_product_detail': ('POST', '/api/v2/product/update_item'),
            'set_product_image': ('POST', '/api/v2/media_space/upload_image'),
            'add_new_variation': ('POST', '/api/v2/product/init_tier_variation'),

            # discount promotion
            'get_discount_list': ('GET', '/api/v2/discount/get_discount_list'),
            'get_discount': ('GET', '/api/v2/discount/get_discount'),
            'add_discount': ('POST', '/api/v2/discount/add_discount'),
            'add_discount_item': ('POST', '/api/v2/discount/add_discount_item'),
            'update_discount': ('POST', '/api/v2/discount/update_discount'),
            'update_discount_item': ('POST', '/api/v2/discount/update_discount_item'),
            'end_discount': ('POST', '/api/v2/discount/end_discount'),
            'delete_discount': ('POST', '/api/v2/discount/delete_discount'),
            'delete_discount_item': ('POST', '/api/v2/discount/delete_discount_item'),

            # voucher
            'add_voucher': ('POST', '/api/v2/voucher/add_voucher'),
            'delete_voucher': ('POST', '/api/v2/voucher/delete_voucher'),
            'end_voucher': ('POST', '/api/v2/voucher/end_voucher'),
            'update_voucher': ('POST', '/api/v2/voucher/update_voucher'),
            'get_voucher': ('GET', '/api/v2/voucher/get_voucher'),
            'get_voucher_list': ('GET', '/api/v2/voucher/get_voucher_list'),

            # bundle deal promotion
            'add_bundle': ('POST', '/api/v2/bundle_deal/add_bundle_deal'),
            'add_bundle_item': ('POST', '/api/v2/bundle_deal/add_bundle_deal_item'),
            'update_bundle': ('POST', '/api/v2/bundle_deal/update_bundle_deal'),
            'update_bundle_item': ('POST', '/api/v2/bundle_deal/update_bundle_deal_item'),
            'delete_bundle': ('POST', '/api/v2/bundle_deal/delete_bundle_deal'),
            'delete_bundle_item': ('POST', '/api/v2/bundle_deal/delete_bundle_deal_item'),
            'get_bundle_list': ('GET', '/api/v2/bundle_deal/get_bundle_deal_list'),
            'get_bundle': ('GET', '/api/v2/bundle_deal/get_bundle_deal'),
            'get_bundle_item': ('GET', '/api/v2/bundle_deal/get_bundle_deal_item'),
            'end_bundle': ('POST', '/api/v2/bundle_deal/end_bundle_deal'),

            # addon deal promotion
            'add_add_on_deal': ('POST', '/api/v2/add_on_deal/add_add_on_deal'),
            'add_add_on_deal_main_item': ('POST', '/api/v2/add_on_deal/add_add_on_deal_main_item'),
            'add_add_on_deal_sub_item': ('POST', '/api/v2/add_on_deal/add_add_on_deal_sub_item'),
            'update_add_on_deal': ('POST', '/api/v2/add_on_deal/update_add_on_deal'),
            'update_add_on_deal_main_item': ('POST', '/api/v2/add_on_deal/update_add_on_deal_main_item'),
            'update_add_on_deal_sub_item': ('POST', '/api/v2/add_on_deal/update_add_on_deal_sub_item'),
            'delete_add_on_deal': ('POST', '/api/v2/add_on_deal/delete_add_on_deal'),
            'delete_add_on_deal_main_item': ('POST', '/api/v2/add_on_deal/delete_add_on_deal_main_item'),
            'delete_add_on_deal_sub_item': ('POST', '/api/v2/add_on_deal/delete_add_on_deal_sub_item'),
            'get_add_on_deal_list': ('GET', '/api/v2/add_on_deal/get_add_on_deal_list'),
            'get_add_on_deal': ('GET', '/api/v2/add_on_deal/get_add_on_deal'),
            'get_add_on_deal_main_item': ('GET', '/api/v2/add_on_deal/get_add_on_deal_main_item'),
            'get_add_on_deal_sub_item': ('GET', '/api/v2/add_on_deal/get_add_on_deal_sub_item'),
            'end_add_on_deal': ('POST', '/api/v2/add_on_deal/end_add_on_deal'),

            # Return
            'return_list': ('GET', '/api/v2/returns/get_return_list'),
            'return_detail': ('GET', '/api/v2/returns/get_return_detail'),
        }
    }

    def __init__(self, sp_account, host="base", api_version="v2"):
        self.sp_account = sp_account
        self.host = host
        self.api_version = api_version

    def get_endpoints(self, endpoint_key=None):
        endpoints = self.ENDPOINTS.get(self.api_version)
        if endpoint_key:
            return endpoints.get(endpoint_key)
        return endpoints

    def get_url(self, endpoint_key, host="base"):
        if host == "live":
            self.host = "live"
        data = {
            'host': self.HOSTS[self.host],
            'endpoint': self.get_endpoints(endpoint_key)[1].format(**vars(self.sp_account))
        }
        return "{host}{endpoint}".format(**data)

    def timestamp(self):
        return(int(time.time()))

    def v1_sign(self, url, body, partner_key):
        bs = url + "|" + json.dumps(body)
        dig = hmac.new(partner_key.encode(), msg=bs.encode(), digestmod=hashlib.sha256).hexdigest()
        return dig

    def v2_sign(self, endpoint_key, partner_id, partner_key, shop_id, timeest, access_token=False):

        if not access_token:
            base_string = '%s%s%s%s' % (partner_id, self.get_endpoints(endpoint_key)[1], timeest, shop_id)
        else:
            base_string = '%s%s%s%s%s' % (partner_id,
                                          self.get_endpoints(endpoint_key)[1],
                                          timeest, access_token, shop_id)
        sign = hmac.new(partner_key.encode(), base_string.encode(), hashlib.sha256).hexdigest()

        return sign

    def v2_build_request(self, endpoint_key, partner_id, partner_key, shop_id, host="base", access_token=False, **kwargs):
        headers = dict({
            'Content-Length': '0',
            'User-Agent': 'PostmanRuntime/7.17.1',
            'Content-Type': 'application/json'
        }, **kwargs.get('headers', {}))

        timeest = self.timestamp()
        if not access_token:
            sign = self.v2_sign(endpoint_key, partner_id, partner_key, shop_id, timeest)
            params = dict({
                'partner_id': partner_id,
                'shop_id': shop_id,
                'timestamp': timeest,
                'sign': sign

            }, **kwargs.get('params', {}))
        else:
            sign = self.v2_sign(endpoint_key, partner_id, partner_key, shop_id, timeest, access_token)
            params = dict({
                'partner_id': partner_id,
                'shop_id': shop_id,
                'timestamp': timeest,
                'sign': sign,
                'access_token': access_token

            }, **kwargs.get('params', {}))
        prepared_request = {
            'method': self.get_endpoints(endpoint_key)[0],
            'url': self.get_url(endpoint_key, host),
            'params': params,
            'headers': headers
        }
        if 'data' in kwargs:
            prepared_request.update({'data': kwargs.get('data')})

        if 'json' in kwargs:
            prepared_request.update({'json': kwargs.get('json')})

        if 'files' in kwargs:
            prepared_request.update({'files': kwargs.get('files')})

        return prepared_request

    def v1_build_request(self, endpoint_key, partner_id, partner_key, shop_id, host="base", **kwargs):
        timeest = self.timestamp()
        body = {
            'partner_id': int(partner_id),
            'shopid': int(shop_id),
            'timestamp': timeest,
        }
        if 'json' in kwargs:
            body.update(kwargs.get('json'))

        sign = self.v1_sign(self.get_url(endpoint_key, host), body, partner_key)
        headers = dict({
            'Content-Length': '0',
            'User-Agent': 'PostmanRuntime/7.17.1',
            'Content-Type': 'application/json',
            'Authorization': sign
        }, **kwargs.get('headers', {}))

        prepared_request = {
            'method': self.get_endpoints(endpoint_key)[0],
            'url': self.get_url(endpoint_key, host),
            'headers': headers
        }

        if self.get_endpoints(endpoint_key)[0] in ["POST", "PUT", "PATH"]:
            prepared_request.update({'json': body})
        else:
            prepared_request.update({'params': body})

        if 'data' in kwargs:
            prepared_request.update({'data': kwargs.get('data')})

        if 'files' in kwargs:
            prepared_request.update({'files': kwargs.get('files')})

        return prepared_request
