# -*- coding: utf-8 -*-

from datetime import datetime
import json
import logging

import requests
from werkzeug import urls

from odoo import api, fields, models, registry, _
from odoo.exceptions import UserError
from odoo.http import request


_logger = logging.getLogger(__name__)

TIMEOUT = 20

GOOGLE_AUTH_ENDPOINT = 'https://accounts.google.com/o/oauth2/auth'
GOOGLE_TOKEN_ENDPOINT = 'https://accounts.google.com/o/oauth2/token'
GOOGLE_API_BASE_URL = 'https://www.googleapis.com'


class GoogleService(models.AbstractModel):
    _inherit = 'google.service'

    @api.model
    def generate_refresh_token(self, service, authorization_code):
        """ Call Google API to refresh the token, with the given authorization code
            :param service : the name of the google service to actualize
            :param authorization_code : the code to exchange against the new refresh token
            :returns the new refresh token
        """
        Parameters = self.env['ir.config_parameter'].sudo()
        client_id = self.env.user.cal_client_id
        client_secret = self.env.user.cal_client_secret
        redirect_uri = Parameters.get_param('google_redirect_uri')

        # Get the Refresh Token From Google And store it in ir.config_parameter
        headers = {"Content-type": "application/x-www-form-urlencoded"}
        data = {
            'code': authorization_code,
            'client_id': client_id,
            'client_secret': client_secret,
            'redirect_uri': redirect_uri,
            'grant_type': "authorization_code"
        }
        try:
            req = requests.post(GOOGLE_TOKEN_ENDPOINT, data=data, headers=headers, timeout=TIMEOUT)
            req.raise_for_status()
            content = req.json()
        except IOError:
            error_msg = _(
                "Something went wrong during your token generation. Maybe your Authorization Code is invalid or already expired")
            raise self.env['res.config.settings'].get_config_warning(error_msg)

        return content.get('refresh_token')

    @api.model
    def _get_google_token_uri(self, service, scope):
        get_param = self.env['ir.config_parameter'].sudo().get_param
        encoded_params = urls.url_encode({
            'scope': scope,
            'redirect_uri': get_param('google_redirect_uri'),
            'client_id': self.env.user.cal_client_id,
            'response_type': 'code',
        })
        return '%s?%s' % (GOOGLE_AUTH_ENDPOINT, encoded_params)


    @api.model
    def _get_authorize_uri(self, from_url, service, scope=False):
        """ This method return the url needed to allow this instance of Odoo to access to the scope
            of gmail specified as parameters
        """
        state = {
            'd': self.env.cr.dbname,
            's': service,
            'f': from_url
        }

        get_param = self.env['ir.config_parameter'].sudo().get_param
        base_url = get_param('web.base.url', default='http://www.hashmicro.com?NoBaseUrl')
        client_id = self.env.user.cal_client_id

        encoded_params = urls.url_encode({
            'response_type': 'code',
            'client_id': client_id,
            'state': json.dumps(state),
            'scope': scope or '%s/auth/%s' % (GOOGLE_API_BASE_URL, service),  # If no scope is passed, we use service by default to get a default scope
            'redirect_uri': base_url + '/google_account/authentication',
            'approval_prompt': 'force',
            'access_type': 'offline'
        })
        return "%s?%s" % (GOOGLE_AUTH_ENDPOINT, encoded_params)
    

    
    @api.model
    def _get_google_tokens(self, authorize_code, service):
        """ Call Google API to exchange authorization code against token, with POST request, to
            not be redirected.
        """
        get_param = self.env['ir.config_parameter'].sudo().get_param
        base_url = get_param('web.base.url', default='http://www.hashmicro.com?NoBaseUrl')
        client_id = self.env.user.cal_client_id
        client_secret = self.env.user.cal_client_secret

        headers = {"content-type": "application/x-www-form-urlencoded"}
        data = {
            'code': authorize_code,
            'client_id': client_id,
            'client_secret': client_secret,
            'grant_type': 'authorization_code',
            'redirect_uri': base_url + '/google_account/authentication'
        }
        try:
            dummy, response, dummy = self._do_request(GOOGLE_TOKEN_ENDPOINT, params=data, headers=headers, method='POST', preuri='')
            access_token = response.get('access_token')
            refresh_token = response.get('refresh_token')
            ttl = response.get('expires_in')
            return access_token, refresh_token, ttl
        except requests.HTTPError:
            error_msg = _("Something went wrong during your token generation. Maybe your Authorization Code is invalid")
            raise self.env['res.config.settings'].get_config_warning(error_msg)
        
    
    