import jwt
from functools import wraps
from odoo import http

SECRET = '35da85e290f0dea28b2369caa38716fb'

def jwt_verify(payload):
    try:
        decoded = jwt.decode(payload, SECRET, algorithm='HS256')
        if decoded:
            cek=http.request.env['res.partner'].sudo().search([('name', '=', decoded['name'])])
            if cek:
                return {
                    'message':'valid token',
                    'state':True
                }
            else:
               return {'message': 'Invalid  Token not found',
                 'state': False}
    # except jwt.InvalidTokenError:
    #     return {'message': 'Invalid  Token',
    #             'state': False}
    except jwt.exceptions.DecodeError:
        return {'message': 'Token error',
                'state': False}
    except jwt.exceptions.ExpiredSignatureError:
        return{'message': 'Token expired',
         'state': False}
    except jwt.exceptions.InvalidSignatureError:
        return{'message': 'Token invalid',
         'state': False}