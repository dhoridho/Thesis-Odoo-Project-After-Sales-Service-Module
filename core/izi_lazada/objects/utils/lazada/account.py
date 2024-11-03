# -*- coding: utf-8 -*-
# Copyright 2022 IZI PT Solusi Usaha Mudah
import pytz

# noinspection PyCompatibility
from urllib.parse import urlencode

from .lazop import LazopClient
from .endpoint import LazadaEndpoint


class LazadaAccount(object):

    def __init__(self, host, app_name, app_key, app_secret, api_version="v2", **kwargs):
        self.app_name = app_name
        self.app_key = app_key
        self.app_secret = app_secret
        self.tid = kwargs.get('tid')
        self.country = kwargs.get('country', 'id')
        self.base_url = kwargs.get('base_url', None)
        self.mp_id = kwargs.get('mp_id', None)
        self.code = kwargs.get('code', None)
        self.refresh_token = kwargs.get('refresh_token', None)
        self.access_token = kwargs.get('access_token', None)
        self.api_version = api_version
        self.endpoints = LazadaEndpoint(self, host=host, api_version=api_version)
        self.lz_client = LazopClient(self.endpoints.HOSTS[host], self.app_key, self.app_secret)
        self.api_tz = pytz.timezone(kwargs.get('tz', 'Asia/Jakarta'))

    def get_redirect_url(self):
        url = '%s/api/user/auth/lazada/%s'
        return url % (self.base_url, self.mp_id)

    def get_auth_url(self):
        return getattr(self, '%s_get_auth_url' % self.api_version)()

    def v2_get_auth_url(self):
        qs_params = {
            'response_type': 'code',
            'force_auth': 'true',
            'redirect_uri': self.get_redirect_url(),
            'client_id': self.app_key,
            'country': self.country
        }
        qs = urlencode(qs_params)
        return '%s?%s' % (self.endpoints.get_url('oauth'), qs)

    def get_token(self):
        if self.code:
            params = {'code': self.code}
            api_code = 'token'
        elif self.refresh_token:
            params = {'refresh_token': self.refresh_token}
            api_code = 'refresh_token'
        lz_request = self.endpoints.build_lz_request(api_code, params=params)
        lz_response = self.lz_client.execute(lz_request)
        return lz_response
