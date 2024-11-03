# -*- coding: utf-8 -*-

from odoo.http import request
from odoo.exceptions import AccessDenied
from datetime import datetime, timedelta
from .helpers import *
from .encryption import APIJSONWebToken


class APIAuthentication(APIJSONWebToken):
    status_code = 200
    token = False
    message = ""

    def set_status_code(self, response_status_code):
        self.status_code = response_status_code
        self.message = STATUS_CODE[response_status_code]

    def set_token(self, uid):
        """
        Function for making JWT tokens. Token is created based on uid.
        @param: uid
        """
        user_id = request.env['res.users'].browse(int(uid))
        # Add some other data in following dictionary related to user
        dt = datetime.now() + timedelta(seconds=60)
        user_data = {
            'name': user_id.name,
            'exp':dt

        }
        token = self.jwt_encode(user_data)
        self.token = token

    def get_response(self, token=True):
        """
        Set the token=True if you want to enter the token into the response result.
        """
        if token:
            response = {
                'status_code': self.status_code,
                'message': self.message,
                'token': self.token,
            }
        else:
            response = {
                'status_code': self.status_code,
                'message': self.message,
            }
        return response

    def api_authenticate(self, database, body):
        if body.get('login', False) and body.get('password', False):
            try:

                uid = request.session.authenticate(database, body['login'], body['password'])
                self.set_token(uid)
                self.set_status_code(200)
                return self.get_response()
            except AccessDenied as e:
                self.set_status_code(401)
                return self.get_response()
        else:
            self.set_status_code(400)
            return self.get_response()
