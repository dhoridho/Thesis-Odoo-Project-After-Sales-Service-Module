# -*- coding: utf-8 -*-
from .exceptions import ValidationError, UserError
import requests
import hashlib
import hmac
import time
import json


class CeisaEndpoint(object):

    HOSTS = {
        'development': 'https://apisdev-gw.beacukai.go.id',
        'production': 'https://apis-gw.beacukai.go.id'
    }

    ENDPOINTS = {
        'register': ('POST', '/api/v1/logistics/airway_bill/get_mass'),
        'access_token': ('POST', '/openapi/token'),
        'refresh_token': ('POST', '/auth-amws/v1/user/update-token'),
        'login': ('POST', '/auth-amws/v1/user/login'),
        # Pabean
        'send_document': ('POST', '/openapi/document'),
        'status_document': ('POST', '/openapi/status/{nomor_aju}'),
        'get_kurs': ('GET', '/openapi/kurs/{kodeValuta'),
        
    }

    def __init__(self, ceisa_account, host="development"):
        self.ceisa_account = ceisa_account
        self.host = host

    def get_endpoints(self, endpoint_key=None):
        endpoints = self.ENDPOINTS.get()
        if endpoint_key:
            return endpoints.get(endpoint_key)
        return endpoints

    def get_url(self, endpoint_key):
        data = {
            'host': self.HOSTS[self.host],
            'endpoint': self.get_endpoints(endpoint_key)[1].format(**vars(self.ceisa_account))
        }
        return "{host}{endpoint}".format(**data)

    def build_request(self, endpoint_key, partner_id, partner_key, shop_id, access_token=False, **kwargs):
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
            }, **kwargs.get('params', {}))
        else:
            sign = self.v2_sign(endpoint_key, partner_id, partner_key, shop_id, timeest, access_token)
            params = dict({
                'partner_id': partner_id,
                'shop_id': shop_id,
                'access_token': access_token
            }, **kwargs.get('params', {}))

        prepared_request = {
            'method': self.get_endpoints(endpoint_key)[0],
            'url': self.get_url(endpoint_key),
            'headers': headers
        }

        # if self.get_endpoints(endpoint_key)[0] in ["POST", "PUT", "PATH"]:
        #     prepared_request.update({'json': body})
        # else:
        #     prepared_request.update({'params': body})

        if 'data' in kwargs:
            prepared_request.update({'data': kwargs.get('data')})

        if 'json' in kwargs:
            prepared_request.update({'json': kwargs.get('json')})

        if 'files' in kwargs:
            prepared_request.update({'files': kwargs.get('files')})

        # try:
        #     auth_user = requests.post(f'http://apisdev-gw.beacukai.go.id/auth-amws/v1/user/login', data=payload,verify=True)
        #     response_data_auth = json.loads(auth_user.content)
        # except (ValueError, requests.exceptions.ConnectionError, requests.exceptions.MissingSchema, requests.exceptions.Timeout, requests.exceptions.HTTPError):
        #     raise ValidationError('connection_error',
        #         _('The url that this service requested returned an error.'))
        # if 'errors' in response_data_auth:
        #     raise ValidationError('%s' % (response_data_auth['errors']))

        return prepared_request

    def login(self, username, password, host='development'):
        users = self.env['res.users'].browse(self.env.user.id)
        company = self.env['res.company'].browse(self.env.user.company_id.id)
        header = {
            'Content-Type': 'application/json'
        }
        payload = {'username': username,
                   'password': password
        }
        data = json.dumps(payload)
        response_data_auth = []
        try:
            auth_user = requests.post(f'https://apisdev-gw.beacukai.go.id/auth-amws/v1/user/login', data=data, headers=header, timeout=40, verify=True)
            response_data_auth = json.loads(auth_user.content)
        except requests.exceptions.SSLError as _err:
            self.log_request_error(['SSLError'])
            raise UserError(_('Error! Could not connect to Ceisa server. '
                              'Please in the connector settings, set the '
                              'parameter "Verify" to false by unchecking it and try again.'))
        except requests.exceptions.ConnectTimeout as _err:
            self.log_request_error(['ConnectTimeout'])
            raise UserError(_('Timeout error. Try again...'))
        except (requests.exceptions.HTTPError,
                requests.exceptions.RequestException,
                requests.exceptions.ConnectionError) as _err:
            self.log_request_error(['requests'])
            ex_type, _ex_value, _ex_traceback = sys.exc_info()
            raise UserError(_('Error! Could not connect to Ceisa account.\n%s') % ex_type)

        if 'errors' in response_data_auth:
            raise ValidationError('%s' % (response_data_auth['errors']))
        elif 'Exception' in response_data_auth:
            raise ValidationError('%s' % (response_data_auth['Exception']))