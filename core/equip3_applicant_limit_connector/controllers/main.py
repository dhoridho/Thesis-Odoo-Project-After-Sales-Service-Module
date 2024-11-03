# -*- coding: utf-8 -*-
from werkzeug.wrappers import Response
from odoo.http import Controller, request, route
from .authentication import APIAuthentication
from .data_processing import *
from .esa_jwt import jwt_verify


class Equip3APIAuthentication(Controller, APIAuthentication):
    @route('/api/v1/auth/login', auth='none', type='json', methods=['POST'])
    def auth_login(self, **kw):
        """
            @request:
            {'login': 'username', 'password': 'password'}
        """
        return self.api_authenticate(request.session.db, request.jsonrequest)

    @route('/api/v1/auth/logout', auth='none', type='json', methods=['POST'])
    def auth_logout(self, **kw):
        """
            @request:
            {}
        """
        return request.session.logout(keep_db=True)


class EQUIP3APIApllicantLimitEndpoints(Controller, APIApplicantLimit):
    @route('/api/v1/update/applicant', auth='none',type='json', methods=['POST'])
    def applicant_limit(self, **kw):
        return self.update_applicant(request.jsonrequest)


#     @route('/api/create/timeoff', type='json', methods=['POST'])
#     def timeoff(self,**kw):
#         x = request.httprequest.headers['Authorization']
#         y = x.split()
#         cek = jwt_verify(y[1])
#         if cek['state'] == False:
#             return cek
#         else:
#             return self.create_timeoff()
