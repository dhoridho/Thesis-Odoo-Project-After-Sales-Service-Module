# -*- coding: utf-8 -*-
# Copyright 2021 IZI PT Solusi Usaha Mudah

class TokopediaEndpoint(object):
    HOSTS = {
        'base': 'https://fs.tokopedia.net',
        'accounts': 'https://accounts.tokopedia.com',
        'seller': 'https://seller.tokopedia.com',
        'image': 'https://ecs7.tokopedia.net'
    }

    ENDPOINTS = {
        # api_version: {endpoint_key: (http_method, endpoint_url)}
        'url': {
            'order_shipping_label': ('GET', '/shipping-label'),
        },
        'v1': {
            'token': ('POST', '/token?grant_type=client_credentials'),
            'register_key': ('POST', '/v1/fs/{fs_id}/register'),
            'shop_info': ('GET', '/v1/shop/fs/{fs_id}/shop-info'),
            'product_info': ('GET', '/inventory/v1/fs/{fs_id}/product/info'),
            'logistic_active_info': ('GET', '/v1/logistic/fs/{fs_id}/active-info'),
            # category
            'product_category': ('GET', '/inventory/v1/fs/{fs_id}/product/category'),
            'get_attributes': ('GET', '/v1/fs/{fs_id}/product/annotation'),

            # order action
            'order_accept': ('POST', '/v1/order/{order_id}/fs/{fs_id}/ack'),
            'order_reject': ('POST', '/v1/order/{order_id}/fs/{fs_id}/nack'),
            'order_shipping_label': ('GET', '/v1/order/{order_id}/fs/{fs_id}/shipping-label'),
            'fulfillment_order': ('GET', '/v1/fs/{fs_id}/fulfillment_order'),
            'confirm_shipping': ('POST ', '/v1/order/{order_id}/fs/{fs_id}/status'),
            'request_pickup': ('POST ', '/inventory/v1/fs/{fs_id}/pick-up'),
            'update_shipping_number': ('POST', '/v1/order/:order_id/fs/:fs_id/status'),

            # webhook
            'register_webhook': ('POST', '/v1/fs/{fs_id}/register'),

            # wallet
            'saldo_history': ('GET', '/v1/fs/{fs_id}/shop/{shop_id}/saldo-history'),

            # product action
            'set_product_price': ('POST', '/inventory/v1/fs/{fs_id}/price/update?shop_id={shop_id}'),
            'set_product_stock': ('POST', '/inventory/v1/fs/{fs_id}/stock/update?shop_id={shop_id}'),
            'set_product_active': ('POST', '/v1/products/fs/{fs_id}/active?shop_id={shop_id}'),
            'set_product_inactive': ('POST', '/v1/products/fs/{fs_id}/inactive?shop_id={shop_id}'),
            'set_product_detail': ('PATCH', '/v3/products/fs/{fs_id}/edit?shop_id={shop_id}'),

            # campaign
            'add_slash_price': ('POST', '/v1/slash-price/fs/{fs_id}/add'),
            'update_slash_price': ('POST', '/v1/slash-price/fs/{fs_id}/update'),
            'cancel_slash_price': ('POST', '/v1/slash-price/fs/{fs_id}/cancel'),
            'get_bundle_list': ('GET', '/v1/products/bundle/fs/{fs_id}/list'),
            'get_bundle_info': ('GET', '/v1/products/bundle/fs/{fs_id}/info'),
            'add_bundle': ('POST', '/v1/products/bundle/fs/{fs_id}/create'),
            'cancel_bundle': ('PATCH', '/v1/products/bundle/fs/{fs_id}/edit'),
        },
        'v2': {
            'logistic_info': ('GET', '/v2/logistic/fs/{fs_id}/info'),
            'order_list': ('GET', '/v2/order/list'),
            'order_detail': ('GET', '/v2/fs/{fs_id}/order'),

            # campaign
            'get_slash_price': ('GET', '/v2/slash-price/fs/{fs_id}/view'),

            # variant
            'get_variants': ('GET', '/inventory/v2/fs/{fs_id}/category/get_variant'),
            'create_product': ('POST', '/v2/products/fs/{fs_id}/create')
        },
        'v3': {
            'create_product': ('POST', '/v3/products/fs/{fs_id}/create'),
            'update_product': ('PATCH', '/v3/products/fs/{fs_id}/edit'),
            'delete_product': ('POST', '/v3/products/fs/{fs_id}/delete'),
            'upload_images': ('POST', '/img/cache/700/product-1'),
        }
    }

    def __init__(self, tp_account, host="base", api_version="v1"):
        self.tp_account = tp_account
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
            'endpoint': self.get_endpoints(endpoint_key)[1].format(**vars(self.tp_account))
        }
        return "{host}{endpoint}".format(**data)

    def build_request(self, endpoint_key, **kwargs):
        headers = dict({
            'Authorization': self.tp_account.get_auth(),
            'Content-Length': '0',
            'User-Agent': 'PostmanRuntime/7.17.1'
        }, **kwargs.get('headers', {}))

        if kwargs.get('force_params'):
            params = kwargs.get('params', {})
        else:
            params = dict({
                'page': 1,
                'per_page': 50
            }, **kwargs.get('params', {}))

        prepared_request = {
            'method': self.get_endpoints(endpoint_key)[0],
            'url': self.get_url(endpoint_key),
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
