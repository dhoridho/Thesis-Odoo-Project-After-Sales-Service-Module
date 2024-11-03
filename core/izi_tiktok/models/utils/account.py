# -*- coding: utf-8 -*-
# Added August-2022 PT. HashMicro
import requests
from base64 import b64encode

from .tools import validate_response
from .endpoint import TiktokEndpoint


class TiktokAccount(object):

    def __init__(self, app_key, app_secret, api_version="v2", **kwargs):
        self.app_key = app_key
        self.app_secret = app_secret
        self.shop_id = kwargs.get('shop_id', None)
        self.access_token = kwargs.get('access_token', None)
        self.refresh_token = kwargs.get('refresh_token', None)
        self.expired_date = kwargs.get('expired_date', None)
        self.auth_code = kwargs.get('auth_code', None)
        self.shop_cipher = kwargs.get('shop_cipher', None)
        self.api_version = api_version
        self.endpoints = TiktokEndpoint(self, host="base_auth", api_version=api_version)

    def get_auth(self, token=False):
        if token:
            auth = 'Basic %s' % b64encode('{}:{}'.format(self.client_id, self.client_secret).encode()).decode()
        else:
            # auth = '%s %s' % (self.token_type, self.access_token)
            auth = '%s' % (self.access_token)
        return auth

    def tts_authenticate(self, code=None):
        params = {
            'app_key': self.app_key,
            'app_secret': self.app_secret,
            'auth_code': code,
            'grant_type': 'authorized_code'
        }

        prepared_request = self.endpoints.build_request('token', **{
            'params': params
        })
        response = validate_response(requests.request(**prepared_request))
        return response.json()

    def refresh_token(self):
        params = {
            'app_key': self.app_key,
            'app_secret': self.app_secret,
            'refresh_token': self.refresh_token,
            'grant_type': 'authorized_code'
        }

        prepared_request = self.endpoints.build_request('refresh_token', **{
            'params': params
        })
        response = validate_response(requests.request(**prepared_request))
        return response.json()
