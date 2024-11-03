# -*- coding: utf-8 -*-

from odoo.http import request
from odoo.exceptions import AccessDenied
from datetime import datetime, timedelta
from .helper import RestApi
import requests
from requests_oauthlib import OAuth1Session,OAuth1


class APIAuthentication(RestApi):
    def api_authenticate(self, database, body):
        base_url = request.env['ir.config_parameter'].sudo().get_param('restapi.api_url') + '/restapi/1.0/common/oauth1/request_token'
        if body.get('login', False) and body.get('password', False):
            try:
                obj_auth = 'auth.auth'
                uid = request.session.authenticate(database, body['login'], body['password'])
                user = request.env['res.users'].browse([uid])
                auth = request.env[obj_auth].sudo().search([('user_id','=',uid)],limit=1)
                if not auth:
                    return self.get_response(401, '401', {"code":401, "message": "User not permitted to access API!"})
                if not auth.consumer_key:
                    auth.update_key_secret()
                try:
                    oauth = OAuth1Session(auth.consumer_key, client_secret=auth.consumer_secret)
                    oauth.cookies.update(request.httprequest.cookies)
                    fetch_response = oauth.get(base_url).json()
                    
                except Exception as e:
                    return self.get_response(401, '401', {"code":401, "message":"Error fetching request token: {}".format(e)})
                
                fetch_response['consumer_key'] = auth.consumer_key
                fetch_response['consumer_secret'] = auth.consumer_secret
                
                return self.get_response(200, '200', {"code":200, "message": "Login Successful","token":fetch_response})
            except AccessDenied as e:
                return self.get_response(401, '401', {"code":401, "message": "Invalid Password"})
        else:
            return self.get_response(401, '400', {"code":400, "message": "Invalid Request"})
        
    def api_authenticate_v2(self, database, body):
        if body.get('login', False) and body.get('password', False):
            try:
                payload = {"login":body['login'], "password": body['password']}
                base_url = request.env['ir.config_parameter'].sudo().get_param('restapi.api_url')
                login = requests.post(f'{base_url}/api/v1/auth/login',json=payload)
                login_response = eval(login.content.decode("utf-8"))
                consumer_key = login_response['token']['consumer_key']
                consumer_secret = login_response['token']['consumer_secret']
                oauth_token = login_response['token']['oauth_token']
                oauth_token_secret = login_response['token']['oauth_token_secret']
                session_id = login.cookies.get_dict()['session_id']
                cookie = {'session_id': session_id}
                verifier =  requests.get(f"{base_url}/restapi/1.0/common/oauth1/authorize?oauth_consumer_key={consumer_key}&oauth_token={oauth_token}&oauth_token_secret={oauth_token_secret}",cookies=cookie)
                verifier_response =  eval(verifier.content.decode("utf-8"))
                oauth1 = OAuth1(client_key=consumer_key,
                                client_secret=consumer_secret,
                                resource_owner_key= verifier_response['oauth_token'],
                                resource_owner_secret = oauth_token_secret,
                                verifier= verifier_response['oauth_verifier']
                                )
                response_access_token = requests.post(base_url + "/restapi/1.0/common/oauth1/access_token", auth=oauth1)
                final_token = eval(response_access_token.content.decode("utf-8"))
                final_token['session_id'] = session_id
            except Exception as e:
                return self.get_response(500, '500', {"code":500, "message":e})

            return self.get_response(200, '200', {"code":200, "message": "Login Successful","token":final_token})
        else:
            return self.get_response(401, '400', {"code":400, "message": "Invalid Request"})