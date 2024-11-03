# -*- coding: utf-8 -*-
# Copyright 2022 IZI PT Solusi Usaha Mudah

from .lazop import LazopClient, LazopRequest


class LazadaEndpoint(object):
    HOSTS = {
        'oauth': 'https://auth.lazada.com',
        'auth': 'https://auth.lazada.com/rest',
        'all': 'https://api.lazada.com/rest',
        'id': 'https://api.lazada.co.id/rest'
    }

    ENDPOINTS = {
        # api_version: {endpoint_key: (http_method, endpoint_url)}
        'v2': {
            'oauth': ('GET', '/oauth/authorize'),
            'token': ('POST', '/auth/token/create'),
            'refresh_token': ('POST', '/auth/token/refresh'),

            # Datamoat
            'datamoat_login': ('POST', '/datamoat/login'),
            'datamoat_compute_risk': ('POST', '/datamoat/compute_risk'),

            # Seller API
            'seller_info': ('GET', '/seller/get'),

            # Shipping API
            'shipping_info': ('GET', '/shipment/providers/get'),

            # Product
            'product_list': ('GET', '/products/get'),
            'product_detail': ('GET', '/product/item/get'),
            'product_price_qty': ('POST', '/product/price_quantity/update'),

            # Order
            'order_list': ('GET', '/orders/get'),
            'order_item': ('GET', '/order/items/get'),
            'orders_item': ('GET', '/orders/items/get'),
            'order_detail': ('GET', '/order/get'),
            'pack_order': ('POST', '/order/pack'),
            'set_invoice': ('POST', '/order/invoice_number/set'),
            'ready_to_ship': ('POST', '/order/rts'),
            'repack_order': ('POST', '/order/repack'),
            'set_delivery': ('POST', '/order/sof/delivered'),
            'print_label': ('GET', '/order/document/awb/pdf/get'),

            # Finance
            'payout_status': ('GET', '/finance/payout/status/get'),
            'transaction_details': ('GET', '/finance/transaction/details/get'),
        }
    }

    def __init__(self, lz_account, host="all", api_version="v2"):
        self.lz_account = lz_account
        self.host = host
        self.api_version = api_version

    def get_endpoints(self, endpoint_key=None):
        endpoints = self.ENDPOINTS.get(self.api_version)
        if endpoint_key:
            return endpoints.get(endpoint_key)
        return endpoints

    def get_url(self, endpoint_key):
        data = {
            'host': self.HOSTS[self.host],
            'endpoint': self.get_endpoints(endpoint_key)[1].format(**vars(self.lz_account))
        }
        return "{host}{endpoint}".format(**data)

    def build_lz_request(self, endpoint_key, **kwargs):
        endpoint = self.get_endpoints(endpoint_key)
        if kwargs.get('force_params'):
            params = kwargs.get('params', {})
        else:
            params = dict({}, **kwargs.get('params', {}))

        lz_request = LazopRequest(**{
            'api_pame': endpoint[1].format(**vars(self.lz_account)),
            'http_method': endpoint[0]
        })
        for key, value in params.items():
            lz_request.add_api_param(key, value)

        return lz_request
