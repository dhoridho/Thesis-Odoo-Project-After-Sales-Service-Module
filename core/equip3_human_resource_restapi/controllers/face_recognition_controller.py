
from datetime import datetime, timedelta
from itertools import count
from odoo.http import route,request
from ...restapi.controllers.helper import RestApi
import pytz
import json


class Equip3HumanResourceRestApiFaceRecognition(RestApi):
    @route('/api/user/create/face_recognition',auth='user', type='json', methods=['POST'])
    def create_face_recognition(self,**kw):
        request_data = request.jsonrequest
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        request_param = {"vals":{'name':request_data.get('name'),
                                 'image':request_data.get('image'),
                                 'image_detection':request_data.get('image_detection'),
                                 'descriptor':request_data.get('descriptor'),
                                 'res_user_id':request.env.user.id,
                                 'is_cropped':request_data.get('is_cropped')
                                 }}
        read_record = self.perform_request('res.users.image',kwargs=request_param, user=user)
        response_data = json.loads(read_record.data)
        if not 'res.users.image' in response_data:
            return self.update_create_failed()
        return self.get_response(200, '200', {"code":200, 
                                              "message":"Create Face Recognition Successful"
                                              })
        
    @route(['/api/user/update/face_recognition/<int:id>'],auth='user', type='json', methods=['put'])
    def update_face_recognition(self,id=None,**kw):
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        request_param = {"vals":{}}
        if kw.get('image'):
            request_param['vals']['image'] = kw.get('image')
        if kw.get('image_detection'):
            request_param['vals']['image_detection'] = kw.get('image_detection')
        if kw.get('descriptor'):
            request_param['vals']['descriptor'] = kw.get('descriptor')
        read_record = self.perform_request('res.users.image',id=id, kwargs=request_param, user=user)
        response_data = json.loads(read_record.data)
        if not 'res.users.image' in response_data:
            return self.update_create_failed()
        return self.get_response(200, '200', {"code":200, 
                                              "message":"Update Successful"
                                              })