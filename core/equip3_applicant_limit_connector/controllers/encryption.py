# -*- coding: utf-8 -*-

import jwt
from .response import APIResponse
from odoo.http import request,Response



class APIJSONWebToken():
    # TODO: This key should be not in file
    SECRET = '35da85e290f0dea28b2369caa38716fb'
    # SECRET = request.env['ir.config_parameter'].sudo().get_param('api.jwt.secret')

    def jwt_encode(self, payload):
        encoded = jwt.encode(payload, self.SECRET, algorithm='HS256')
        return encoded

    # def jwt_decode(self, payload):
    #     try:
    #         decoded = jwt.decode(payload, self.SECRET, algorithm='HS256')
    #         return decoded
    #     except jwt.InvalidTokenError:
    #          Response({'message':'Invalid  Token',
    #                 'state':False})
    #          Response.status('400')
    #          return Response
    #
    #     except jwt.exceptions.DecodeError:
    #         return {'message': 'Token error',
    #                 'state': False}

    # def tokenjwt(func):
    #     def jwt_verify():
    #             payload=request.httprequest.headers['Authorization']
    #             if payload is None:
    #                 return {"message":"token is null"}
    #             return func()
    #     return jwt_verify()