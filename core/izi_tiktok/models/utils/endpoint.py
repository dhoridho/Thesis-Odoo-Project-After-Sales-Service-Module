# -*- coding: utf-8 -*-
# Added August-2022 PT. HashMicro
import hmac
import hashlib
import time


auth_state = 'HMTIKTOKSHOP'


class TiktokEndpoint(object):
    HOSTS = {
        'base': 'https://open-api.tiktokglobalshop.com',
        'auth': 'https://auth.tiktok-shops.com/oauth/authorize',
        'base_auth': 'https://auth.tiktok-shops.com'
    }

    ENDPOINTS = {
        # api_version: {endpoint_key: (http_method, endpoint_url)}
        'v2': {
            # authorize
            'token': ('GET', '/api/v2/token/get'),
            'refresh_token': ('GET', '/api/v2/token/refresh'),
            'auth_shop': ('GET', '/authorization/202309/shops'),
            # warehouse & logistic
            'get_warehouse_list': ('GET', '/logistics/202309/warehouses'),
            'get_warehouse_logistic': ('GET', '/logistics/202309/warehouses/{warehouse_id}/delivery_options'),
            'get_logistic_info': ('GET', '/logistics/202309/delivery_options/{delivery_option_id}/shipping_providers'),
            # products
            'create_product': ('POST', '/api/products'),
            'product_brand': ('GET', '/api/products/brands'),
            'custom_brand': ('POST', '/api/products/brand'),
            'product_category': ('GET', '/api/products/categories'),
            'ccategory_rule': ('GET', '/api/products/categories/rules'),
            'product_attribute': ('GET', '/api/products/attributes'),
            'upload_image': ('POST', '/api/products/upload_imgs'),
            'edit_product': ('PUT', '/product/202309/products/{product_id}'),
            'update_inventory': ('POST', '/product/202309/products/{product_id}/inventory/update'),
            'update_price': ('PUT', '/api/products/prices'),
            'activate_product': ('POST', '/product/202309/products/activate'),
            'deactivate_product': ('POST', '/product/202309/products/deactivate'),
            'delete_product': ('DEL', '/api/products'),
            'product_list': ('POST', '/api/products/search'),
            'product_detail': ('POST', '/api/products/details'),
            # orders
            ## promotion legacy (old version)
            # 'get_promotion_list': ('POST', '/api/promotion/activity/list'),
            # 'get_promotion_detail': ('GET', '/api/promotion/activity/get'),
            ## promotion new version
            'get_promotion_list': ('POST', '/promotion/202309/activities/search'),
            'get_promotion_detail': ('GET', '/promotion/202309/activities/{activity_id}'),
            'get_coupon_list': ('POST', '/promotion/202406/coupons/search'),
            'get_coupon_detail': ('GET', '/promotion/202406/coupons/{coupon_id}'),
            # wallet
            'finance_settlements': ('POST', '/api/finance/settlements/search'),
        },
    }

    def __init__(self, tts_account, host="base", api_version="v2"):
        self.tts_account = tts_account
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
            'endpoint': self.get_endpoints(endpoint_key)[1].format(**vars(self.tts_account))
        }
        return "{host}{endpoint}".format(**data)

    def build_request(self, endpoint_key, **kwargs):
        headers = dict({
            'Content-Length': '0',
            'User-Agent': 'PostmanRuntime/7.17.1',
            'Content-Type': 'application/json',
            'x-tts-access-token': self.tts_account.access_token or ''
        }, **kwargs.get('headers', {}))
        # headers = {
        #     'Content-Length': '0',
        #     'User-Agent': 'PostmanRuntime/7.17.1',
        #     'Content-Type': 'application/json',
        #     'x-tts-access-token': self.tts_account.access_token or ''
        # }
        timestamp = int(time.time())
        endpoint_path = self.get_endpoints(endpoint_key)[1]
        if kwargs.get('force_params'):
            params = kwargs.get('params', {})
        else:
            if not 'token' in endpoint_key and not 'auth_shop' in endpoint_key:
                params = dict({
                    'app_key': self.tts_account.app_key,
                    'shop_cipher': self.tts_account.shop_cipher
                }, **kwargs.get('params', {}))
            else:
                params = dict({
                    'app_key': self.tts_account.app_key,
                }, **kwargs.get('params', {}))
            sign, timecreate = self.tts_generate_sign(endpoint_path, params)
            params.update({
                'sign': sign,
                'timestamp': timecreate
            })
        # params = dict(params, **kwargs.get('params', {}))
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

    def tts_generate_sign(self, path, params, data=None):
        params = params.copy()
        if 'sign' in params:
            del params['sign']
        if 'access_token' in params:
            del params['access_token']
        timestamp = int(time.time())
        params.update({
            'timestamp': timestamp
        })
        signstring = ''
        for key in params:
            signstring += (key + str(params[key]))

        if data:
            signstring = '%s%s' % (signstring, data)

        signstring = '%s%s%s%s' % (
            self.tts_account.app_secret, path, signstring, self.tts_account.app_secret)

        sign = hmac.new(self.tts_account.app_secret.encode(), msg=signstring.encode(), digestmod=hashlib.sha256).hexdigest()
        return sign, timestamp
