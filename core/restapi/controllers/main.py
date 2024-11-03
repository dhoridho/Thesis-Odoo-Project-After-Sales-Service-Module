
from collections import defaultdict
from crypt import methods
import itertools
import string
from odoo.http import Controller, request, route
from .authentication import APIAuthentication
from random import randint
from pytz import timezone
from datetime import datetime,timedelta
import random
from odoo.exceptions import AccessDenied
import json
from ...equip3_general_features.models.email_wa_parameter import waParam
from .helper import *



fmt = "%Y-%m-%dT%H:%M:%S%Z"

class HashmicroApiAuthentication(APIAuthentication):
    @route('/api/v1/auth/login', auth='none', type='json', methods=['POST'])
    def auth_login(self, **kw):
        return self.api_authenticate(request.session.db, request.jsonrequest)
    
    @route('/api/v2/auth/login', auth='none', type='json', methods=['POST'])
    def auth_login_v2(self, **kw):
        return self.api_authenticate_v2(request.session.db, request.jsonrequest)

    @route('/api/v1/auth/logout', auth='user', type='json', methods=['POST'])
    def auth_logout(self, **kw):
        obj_auth = 'auth.auth'
        uid = request.env.user.id
        user = request.env['res.users'].browse([uid])
        auth = request.env[obj_auth].sudo().search([('user_id','=',uid)],limit=1)
        if auth:
            auth.revoke_access()
        logout = request.session.logout(keep_db=True)
        return self.get_response(200, '200', {"code":200, "message": "Logout Successful"})
        
    @route('/send/email/otp',auth='none',type='json',methods=['POST'])
    def send_email_otp(self, **kw):
        body = request.jsonrequest
        otp = randint(111111, 999999)
        token = ''.join(random.choices(string.ascii_uppercase + string.digits, k=20))
        context = request.env.context = dict(request.env.context)
        user = request.env['res.users'].sudo().search([('login','=',body.get('email'))])
        if user:
            user_sender = request.env['res.users'].sudo().search([('id','=',1),('active','=',False)])
            expire = datetime.now(timezone(user_sender.sudo().tz if user_sender.sudo().tz else 'UTC') ) + timedelta(hours=1)
            expire_store = expire.replace(tzinfo=None)
            otp_obj = request.env['otp.email'].sudo().create({'opt_code':str(otp),'email':body.get('email'),'expire':expire_store,'company_id':user_sender.company_id.id,'token':token})
            context.update({'email_to':body.get('email'),
                            'name':user.name,
                            'otp':otp_obj.opt_code,
                            'email_from':user_sender.sudo().partner_id.email})
            template = request.env.ref('restapi.mail_template_send_otp').sudo()
            template.send_mail(otp_obj.id, force_send=True)
            template.with_context(context)
            return self.get_response(200, '200', {"code":200, "message": "Email OTP sended check inbox ",'expire':otp_obj.expire.strftime('%d-%m-%Y %H:%M:%S')})
        else:
            return self.get_response(400, '400', {"code":400, "message": "User not found"})
        
    @route('/send/whatsapp/otp',auth='none',type='json',methods=['POST'])
    def send_whatsapp_otp(self, **kw):
        body = request.jsonrequest
        otp = randint(111111, 999999)
        token = ''.join(random.choices(string.ascii_uppercase + string.digits, k=20))
        context = request.env.context = dict(request.env.context)
        employee = request.env['hr.employee'].sudo().search([('mobile_phone','=',body.get('phone'))])
        if employee:
            user_sender = request.env['res.users'].sudo().search([('id','=',1),('active','=',False)])
            expire = datetime.now(timezone(user_sender.sudo().tz if user_sender.sudo().tz else 'UTC') ) + timedelta(hours=1)
            expire_store = expire.replace(tzinfo=None)
            otp_obj = request.env['otp.phone'].sudo().create({'opt_code':str(otp),'phone':body.get('phone'),'expire':expire_store,'company_id':user_sender.company_id.id,'token':token})
            wa_sender = waParam()
            template = f"""Reset your password? If you request a password reset for {employee.name} use the confirmation code below to complete the process. If you did not make this request, please ignore this Message. OTP:{otp_obj.opt_code} You get a lot of password reset whatsapp? You can change your account settings to request personal information in order to reset your password."""""
            wa_sender.set_wa_string(template)
            wa_sender.send_wa(body.get('phone'))
            return self.get_response(200, '200', {"code":200, "message": "WhatsApp OTP sended check messages ",'expire':otp_obj.expire.strftime('%d-%m-%Y %H:%M:%S')})
        else:
            return self.get_response(400, '400', {"code":400, "message": "User not found"})
        
    @route('/check/otp',auth='none',type='json',methods=['POST'])
    def check_otp(self, **kw):
        user_sender = request.env['res.users'].sudo().search([('id','=',1),('active','=',False)])
        now = datetime.now(timezone(user_sender.sudo().tz if user_sender.sudo().tz else 'UTC') )
        body = request.jsonrequest
        if body.get('email'):
            otp_check = request.env['otp.email'].sudo().search([('opt_code','=',str(body.get('otp'))),('email','=',body.get('email')),('expire','>=',now),('is_use','=',False)])
        if body.get('phone'):
            otp_check = request.env['otp.phone'].sudo().search([('opt_code','=',str(body.get('otp'))),('phone','=',body.get('phone')),('expire','>=',now),('is_use','=',False)])
        if otp_check:
            otp_check.is_use =True
            return self.get_response(200, '200', {"code":200,'token_reset':otp_check.token})
        else:
            return self.get_response(400, '400', {"code":400,'message':"OTP Not valid !"})
            
        
    @route('/reset/password/user',auth='none',type='json',methods=['POST'])
    def reset_password_user(self, **kw):
        body = request.jsonrequest
        password = str(body.get('password')).encode('utf-8')
        if body.get('email'):
            token_check = request.env['otp.email'].sudo().search([('token','=',body.get('token')),('email','=',body.get('email')),('is_use_reset','=',False)])
            if token_check:
                token_check.is_use_reset = True
                user = request.env['res.users'].sudo().search([('login','=',body.get('email'))])
                if user:
                    user.update({'password':password})
                    return self.get_response(200, '200', {"code":200, "message": "Password Successfully Reset"})
                else:
                    return self.get_response(400, '400', {"code":400, "message": "User not found"})    
        if body.get('phone'):
            token_check = request.env['otp.phone'].sudo().search([('token','=',body.get('token')),('phone','=',body.get('phone')),('is_use_reset','=',False)])
            if token_check:
                token_check.is_use_reset = True
                employee = request.env['hr.employee'].sudo().search([('mobile_phone','=',body.get('phone'))])
                if employee:
                    employee.user_id.password = password
                    return self.get_response(200, '200', {"code":200, "message": "Password Successfully Reset"})
                else:
                    return self.get_response(400, '400', {"code":400, "message": "User not found"})
        return self.get_response(400, '400', {"code":400, "message": "Token Not valid"})
    
    
    @route('/user/change/password',auth='user',type='json',methods=['PUT'])
    def change_password_user(self, **kw):
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        try:
            body = request.jsonrequest
            uid = request.session.authenticate(request.session.db, request.env.user.login, body['old_password'])
            user = request.env['res.users'].browse([uid])
            user.password = body['new_password']
            return self.get_response(200, '200', {"code":200, "message": "Change Password Successful"})
        except AccessDenied as e:
                return self.get_response(401, '401', {"code":401, "message": "Invalid old password !"})
            
    @route('/api/user/update/image',auth='user', type='json', methods=['put'])
    def update_image(self,**kw):
        id = request.env.user.id
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        request_param = {"vals":{}}
        if kw.get('image_1920'):
            request_param['vals']['image_1920'] = kw.get('image_1920')
        read_record = self.perform_request('res.users',id=id, kwargs=request_param, user=user)
        response_data = json.loads(read_record.data)
        if not 'res.users' in response_data:
            return self.record_not_found()
        return self.get_response(200, '200', {"code":200, 
                                              "message":"Update Successful"
                                              })
        
    @route('/api/user/update/digital_signature',auth='user', type='json', methods=['put'])
    def update_digital_signature(self,**kw):
        id = request.env.user.id
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        request_param = {"vals":{}}
        if kw.get('digital_signature'):
            request_param['vals']['digital_signature'] = kw.get('digital_signature')
        read_record = self.perform_request('res.users',id=id, kwargs=request_param, user=user)
        response_data = json.loads(read_record.data)
        if not 'res.users' in response_data:
            return self.record_not_found()
        return self.get_response(200, '200', {"code":200, 
                                              "message":"Update Successful"
                                              })
        
    @route('/api/user/access_right',auth='user', type='http', methods=['get'])
    @authenticate   
    def user_access_right(self,**kw):       
        category_hr = request.env.ref('base.module_category_human_resources')            
        hr_role = [{"module":data.name,"role_ids":self.get_group(data.xml_id)} for data in category_hr.sudo().child_ids if self.get_group(data.xml_id)]
        access_right = {
            'human_resource_role':hr_role
             
        }
        return self.get_response(200, '200', access_right)
        
        
    @route('/api/user/profile',auth='user', type='http', methods=['get'])
    @authenticate
    def user_profile(self,**kw):
        attendance_hours_sum = 0
        query = """
        select ha.id from hr_attendance ha WHERE ha.create_date  > current_date - interval '30' day and ha.employee_id = %s
        """
        request._cr.execute(query, [request.env.user.employee_id.id])
        attendance = request.env.cr.dictfetchall()
        if attendance:
            attendance_ids =  [data['id'] for data in attendance]
            attendance_hours =  request.env['hr.attendance'].browse(attendance_ids)
            if attendance_hours:
                attendance_hours_sum =  sum([data.worked_hours for data in attendance_hours])        
        env = request.env         
        return self.get_response(200, '200', {"code":200, 
                                              "id":env.user.id,
                                              "fcm_token":env.user.firebase_token,
                                              "employee_image":env.user.employee_id.image_1920.decode("utf-8") if env.user.employee_id.image_1920 else '-',
                                              "name":env.user.name,
                                              "job_position":env.user.job_title,
                                              "job_position_id":env.user.employee_id.job_id.id,
                                              "department":env.user.employee_id.department_id.name,
                                              "work_email":env.user.employee_id.work_email,
                                              "attendance_hours":attendance_hours_sum,
                                              "allocation_display":env.user.allocation_display,
                                              "work_mobile":env.user.mobile_phone,
                                              "work_phone":env.user.work_phone,
                                              "work_email":env.user.work_email,
                                              "work_location":env.user.work_location,
                                              "allow_offline_attendance":env.user.employee_id.allow_offline_attendance,
                                              "auto_submit_data_record":env.user.employee_id.auto_submit_data_record,
                                              "user_delegation_id":
                                                  {
                                                      "id":env.user.user_delegation_id.id,
                                                      "name":env.user.user_delegation_id.name
                                                      
                                                      
                                                  },
                                              "manager_id":{"id":env.user.employee_parent_id.id,
                                                            "name":env.user.employee_parent_id.name
                                                            
                                                            },
                                              "coach_id":{"id":env.user.coach_id.id,
                                                          "name":env.user.coach_id.name},
                                              "notification":env.user.notification_type,
                                              "email":env.user.email,
                                              "language":env.user.lang,
                                              "timezone":env.user.tz,
                                              "online_chat_name":env.user.livechat_username,
                                              "digital_signature":env.user.digital_signature.decode("utf-8") if env.user.digital_signature else "-",
                                              "face_emotion":env.user.face_emotion,
                                              "face_gender":env.user.face_gender,
                                              "face_age":env.user.face_age
                                               
                                              })
        
    @route(['/api/user/get_currency'],auth='user', type='http', methods=['get'])
    def get_currency(self,id=None,**kw):
        offset =  self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1)
        obj = 'res.currency'
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        domain = []
        if kw.get("search"):
            domain.append(('name','ilike',kw.get("search")))
            
        data_ids = request.env[obj].sudo().search(domain)
        if not data_ids:
            return self.record_not_found()
        
        request_param = {"ids":','.join(str(data.id) for data in data_ids),"fields":['name'],
                         "offset":offset,
                         "limit":PAGE_DATA_LIMIT
                             }
        read_record = self.perform_request(obj,id=id, kwargs=request_param, user=user)
        response_data = json.loads(read_record.data)
        if not obj in response_data:
            return self.record_not_found()
        page_total  = self.get_total_page(len(data_ids),PAGE_DATA_LIMIT)
        return self.get_response(200, '200', {"code":200,
                                              "data":response_data[obj],
                                              "page_total":page_total if not id else 0
                                              })
        
        
    @route(['/api/user/get_country'],auth='user', type='http', methods=['get'])
    def get_country(self,id=None,**kw):
        offset =  self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1)
        obj = 'res.country'
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        domain = []
        if kw.get("search"):
            domain.append(('name','ilike',kw.get("search")))
            
        data_ids = request.env[obj].sudo().search(domain)
        if not data_ids:
            return self.record_not_found()
        
        request_param = {"ids":','.join(str(data.id) for data in data_ids),"fields":['name'],
                         "offset":offset,
                         "limit":PAGE_DATA_LIMIT
                             }
        read_record = self.perform_request(obj,id=id, kwargs=request_param, user=user)
        response_data = json.loads(read_record.data)
        if not obj in response_data:
            return self.record_not_found()
        page_total  = self.get_total_page(len(data_ids),PAGE_DATA_LIMIT)
        return self.get_response(200, '200', {"code":200,
                                              "data":response_data[obj],
                                              "page_total":page_total if not id else 0
                                              })
        
    @route(['/api/user/country_domicile_code'],auth='user', type='http', methods=['get'])
    def get_country_domicile_code(self,id=None,**kw):
        offset =  self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1)
        obj = 'country.domicile.code'
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        domain = []
        if kw.get("search"):
            domain.append(('name','ilike',kw.get("search")))
            
        if kw.get("country_id"):
            domain.append(('country_id','=',int(kw.get("country_id"))))
            
        data_ids = request.env[obj].sudo().search(domain)
        if not data_ids:
            return self.record_not_found()
        
        request_param = {"ids":','.join(str(data.id) for data in data_ids),"fields":['name','country_id'],
                         "offset":offset,
                         "limit":PAGE_DATA_LIMIT
                             }
        read_record = self.perform_request(obj,id=id, kwargs=request_param, user=user)
        response_data = json.loads(read_record.data)
        if not obj in response_data:
            return self.record_not_found()
        page_total  = self.get_total_page(len(data_ids),PAGE_DATA_LIMIT)
        return self.get_response(200, '200', {"code":200,
                                              "data":response_data[obj],
                                              "page_total":page_total if not id else 0
                                              })
        
        
    @route(['/api/user/get_country_state'],auth='user', type='http', methods=['get'])
    def get_country_state(self,id=None,**kw):
        offset =  self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1)
        obj = 'res.country.state'
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        domain = []
        if kw.get("search"):
            domain.append(('name','ilike',kw.get("search")))
            
        if kw.get("country_id"):
            domain.append(('country_id','=',int(kw.get("country_id"))))
            
        data_ids = request.env[obj].sudo().search(domain)
        if not data_ids:
            return self.record_not_found()
        
        request_param = {"ids":','.join(str(data.id) for data in data_ids),"fields":['name'],
                         "offset":offset,
                         "limit":PAGE_DATA_LIMIT
                             }
        read_record = self.perform_request(obj,id=id, kwargs=request_param, user=user)
        response_data = json.loads(read_record.data)
        if not obj in response_data:
            return self.record_not_found()
        page_total  = self.get_total_page(len(data_ids),PAGE_DATA_LIMIT)
        return self.get_response(200, '200', {"code":200,
                                              "data":response_data[obj],
                                              "page_total":page_total if not id else 0
                                              })
        
        
    @route(['/api/user/get_partner'],auth='user', type='http', methods=['get'])
    def get_get_partner(self,id=None,**kw):
        offset =  self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1)
        obj = 'res.partner'
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        domain = []
        if kw.get("search"):
            domain.append(('name','ilike',kw.get("search")))
            
        data_ids = request.env[obj].sudo().search(domain)
        if not data_ids:
            return self.record_not_found()
        
        request_param = {"ids":','.join(str(data.id) for data in data_ids),"fields":['name'],
                         "offset":offset,
                         "limit":PAGE_DATA_LIMIT
                             }
        read_record = self.perform_request(obj,id=id, kwargs=request_param, user=user)
        response_data = json.loads(read_record.data)
        if not obj in response_data:
            return self.record_not_found()
        page_total  = self.get_total_page(len(data_ids),PAGE_DATA_LIMIT)
        return self.get_response(200, '200', {"code":200,
                                              "data":response_data[obj],
                                              "page_total":page_total if not id else 0
                                              })
        
    @route(['/api/user/get_bank'],auth='user', type='http', methods=['get'])
    def get_get_bank(self,id=None,**kw):
        offset =  self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1)
        obj = 'res.bank'
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        domain = []
        if kw.get("search"):
            domain.append(('name','ilike',kw.get("search")))
            
        data_ids = request.env[obj].sudo().search(domain)
        if not data_ids:
            return self.record_not_found()
        
        request_param = {"ids":','.join(str(data.id) for data in data_ids),"fields":['name','bic'],
                         "offset":offset,
                         "limit":PAGE_DATA_LIMIT
                             }
        read_record = self.perform_request(obj,id=id, kwargs=request_param, user=user)
        response_data = json.loads(read_record.data)
        if not obj in response_data:
            return self.record_not_found()
        page_total  = self.get_total_page(len(data_ids),PAGE_DATA_LIMIT)
        return self.get_response(200, '200', {"code":200,
                                              "data":response_data[obj],
                                              "page_total":page_total if not id else 0
                                              })
        
    @route(['/api/user/get_uom'],auth='user', type='http', methods=['get'])
    def get_get_uom(self,id=None,**kw):
        offset =  self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1)
        obj = 'uom.uom'
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        domain = []
        if kw.get("search"):
            domain.append(('name','ilike',kw.get("search")))
            
        data_ids = request.env[obj].sudo().search(domain)
        if not data_ids:
            return self.record_not_found()
        
        request_param = {"ids":','.join(str(data.id) for data in data_ids),"fields":['name'],
                         "offset":offset,
                         "limit":PAGE_DATA_LIMIT
                             }
        read_record = self.perform_request(obj,id=id, kwargs=request_param, user=user)
        response_data = json.loads(read_record.data)
        if not obj in response_data:
            return self.record_not_found()
        page_total  = self.get_total_page(len(data_ids),PAGE_DATA_LIMIT)
        return self.get_response(200, '200', {"code":200,
                                              "data":response_data[obj],
                                              "page_total":page_total if not id else 0
                                              })
        
    @http.route(['/api/user/create_attachment/<string:object_model>/<int:id>',],type="json", auth="user")
    def create_attachment_api(self, object_model, id, **kwargs):
        request_data = request.jsonrequest
        auth, user, invalid = self.valid_authentication(kwargs)
        if not user or invalid:
            return self.get_response(401, '401', {'code': 401, 'message': 'Authentication required'})
        
        attachment = request.env['ir.attachment'].sudo().create({'name':request_data.get("file_name"),
                                                                 'res_model':object_model,
                                                                 'res_id':id,
                                                                 'type': 'binary',
                                                                 'datas':request_data.get('datas')})
        return self.get_response(200, '200', {"code":200,
                                              "id":attachment.id,
                                              "data":"Create Attachment Successful"
                                              })
        
           
    @http.route(['/api/user/get_attachment/<string:object_model>/<int:id>',],type="http", auth="user",methods=['GET'])
    def get_attachment_api(self, object_model, id, **kwargs):
        auth, user, invalid = self.valid_authentication(kwargs)
        if not user or invalid:
            return self.get_response(401, '401', {'code': 401, 'message': 'Authentication required'})
        attachment = request.env['ir.attachment'].sudo().search([('res_model','=',object_model),('res_id','=',id)])
        if not attachment:
            return self.record_not_found()
        data = []
        for record in attachment:
            data.append({'name':record.name,
                         'datas':record.datas.decode('utf-8')
                         })
        return self.get_response(200, '200', {"code":200,
                                              "data":data
                                              })
        
        
    @http.route(['/api/user/update_attachment/<int:id>',],type="json", auth="user",methods=['PUT'])
    def update_attachment_api(self, id, **kwargs):
        request_data = request.jsonrequest
        auth, user, invalid = self.valid_authentication(kwargs)
        if not user or invalid:
            return self.get_response(401, '401', {'code': 401, 'message': 'Authentication required'})
        
        attachment = request.env['ir.attachment'].sudo().search([('id','=',id)])
        if not attachment:
            return self.record_not_found()
        
        attachment.write({'name':request_data.get("file_name"),
                          'datas':request_data.get('datas')})
        return self.get_response(200, '200', {"code":200,
                                              "id":attachment.id,
                                              "data":"Update Attachment Successful"
                                              })
    
    @http.route(['/api/user/contract_type',],type="http", auth="user",methods=['get'])
    def get_contract_type(self, **kw):
        offset =  self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1)
        obj = 'hr.contract.type'
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        domain = []
        if kw.get("search"):
            domain.append(('name','ilike',kw.get("search")))
            
        data_ids = request.env[obj].sudo().search(domain)
        if not data_ids:
            return self.record_not_found()
        
        request_param = {"ids":','.join(str(data.id) for data in data_ids),"fields":['name'],
                         "offset":offset,
                         "limit":PAGE_DATA_LIMIT
                         }
        read_record = self.perform_request(obj,id=None, kwargs=request_param, user=user)
        response_data = json.loads(read_record.data)
        if not obj in response_data:
            return self.record_not_found()
        
        page_total  = self.get_total_page(len(data_ids),PAGE_DATA_LIMIT)
        return self.get_response(200, '200', {"code":200,
                                              "data":response_data[obj],
                                              "page_total":page_total if not id else 0
                                              })
    
    @http.route(['/api/user/company',],type="http", auth="user",methods=['get'])
    def get_user_company(self, **kw):
        offset =  self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1)
        obj = 'res.company'
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        domain = [('id','in',request.env.user.company_ids.ids)]
        if kw.get("search"):
            domain.append(('name','ilike',kw.get("search")))
            
        data_ids = request.env[obj].sudo().search(domain)
        if not data_ids:
            return self.record_not_found()
        
        request_param = {"ids":','.join(str(data.id) for data in data_ids),"fields":['name'],
                         "offset":offset,
                         "limit":PAGE_DATA_LIMIT
                         }
        read_record = self.perform_request(obj,id=None, kwargs=request_param, user=user)
        response_data = json.loads(read_record.data)
        if not obj in response_data:
            return self.record_not_found()
        
        page_total  = self.get_total_page(len(data_ids),PAGE_DATA_LIMIT)
        return self.get_response(200, '200', {"code":200,
                                              "data":response_data[obj],
                                              "page_total":page_total if not id else 0
                                              })
            
    @http.route(['/api/user/work_location',],type="http", auth="user",methods=['get'])
    def get_work_location(self, **kw):
        offset =  self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1)
        obj = 'work.location.object'
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        domain = []
        if kw.get("search"):
            domain.append(('name','ilike',kw.get("search")))
            
        data_ids = request.env[obj].sudo().search(domain)
        if not data_ids:
            return self.record_not_found()
        
        request_param = {"ids":','.join(str(data.id) for data in data_ids),"fields":['name'],
                         "offset":offset,
                         "limit":PAGE_DATA_LIMIT
                         }
        read_record = self.perform_request(obj,id=None, kwargs=request_param, user=user)
        response_data = json.loads(read_record.data)
        if not obj in response_data:
            return self.record_not_found()
        
        page_total  = self.get_total_page(len(data_ids),PAGE_DATA_LIMIT)
        return self.get_response(200, '200', {"code":200,
                                              "data":response_data[obj],
                                              "page_total":page_total if not id else 0
                                              })
           
    @http.route(['/api/user/department'],type="http", auth="user",methods=['get'])
    def get_department(self, **kw):
        limit = int(kw.get('limit')) if 'limit' in kw else False
        offset =  self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1,limit=limit)
        obj = 'hr.department'
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        domain = []
        if kw.get("search"):
            domain.append(('name','ilike',kw.get("search")))
            
        data_ids = request.env[obj].sudo().search(domain)
        if not data_ids:
            return self.record_not_found()
        
        request_param = {"ids":','.join(str(data.id) for data in data_ids),"fields":['name'],
                         "offset":offset,
                         "limit":PAGE_DATA_LIMIT if not limit else limit
                         }
        read_record = self.perform_request(obj,id=None, kwargs=request_param, user=user)
        response_data = json.loads(read_record.data)
        if not obj in response_data:
            return self.record_not_found()
        for data in response_data[obj]:
            job_count = request.env['hr.job'].search_count([('department_id','=',data['id'])])
            data['job_count'] = job_count
        page_total  = self.get_total_page(len(data_ids),PAGE_DATA_LIMIT if not limit else limit)
        return self.get_response(200, '200', {"code":200,
                                              "data":response_data[obj],
                                              "page_total":page_total
                                              })
        
   

    @http.route(['/api/user/grade'],type="http", auth="user",methods=['get'])
    def get_grade(self, **kw):
        offset =  self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1)
        obj = 'employee.grade'
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        domain = []
        if kw.get("search"):
            domain.append(('name','ilike',kw.get("search")))
            
        data_ids = request.env[obj].sudo().search(domain)
        if not data_ids:
            return self.record_not_found()
        
        request_param = {"ids":','.join(str(data.id) for data in data_ids),"fields":['name'],
                         "offset":offset,
                         "limit":PAGE_DATA_LIMIT
                         }
        read_record = self.perform_request(obj,id=None, kwargs=request_param, user=user)
        response_data = json.loads(read_record.data)
        if not obj in response_data:
            return self.record_not_found()
        
        page_total  = self.get_total_page(len(data_ids),PAGE_DATA_LIMIT)
        return self.get_response(200, '200', {"code":200,
                                              "data":response_data[obj],
                                              "page_total":page_total if not id else 0
                                              })
    
    
    @http.route(['/api/user/religion'],type="http", auth="user",methods=['get'])
    def get_religion(self, **kw):
        offset =  self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1)
        obj = 'employee.religion'
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        domain = []
        if kw.get("search"):
            domain.append(('name','ilike',kw.get("search")))
            
        data_ids = request.env[obj].sudo().search(domain)
        if not data_ids:
            return self.record_not_found()
        
        request_param = {"ids":','.join(str(data.id) for data in data_ids),"fields":['name'],
                         "offset":offset,
                         "limit":PAGE_DATA_LIMIT
                         }
        read_record = self.perform_request(obj,id=None, kwargs=request_param, user=user)
        response_data = json.loads(read_record.data)
        if not obj in response_data:
            return self.record_not_found()
        
        page_total  = self.get_total_page(len(data_ids),PAGE_DATA_LIMIT)
        return self.get_response(200, '200', {"code":200,
                                              "data":response_data[obj],
                                              "page_total":page_total if not id else 0
                                              })
        
    @http.route(['/api/user/race'],type="http", auth="user",methods=['get'])
    def get_race(self, **kw):
        offset =  self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1)
        obj = 'employee.race'
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        domain = []
        if kw.get("search"):
            domain.append(('name','ilike',kw.get("search")))
            
        data_ids = request.env[obj].sudo().search(domain)
        if not data_ids:
            return self.record_not_found()
        
        request_param = {"ids":','.join(str(data.id) for data in data_ids),"fields":['name'],
                         "offset":offset,
                         "limit":PAGE_DATA_LIMIT
                         }
        read_record = self.perform_request(obj,id=None, kwargs=request_param, user=user)
        response_data = json.loads(read_record.data)
        if not obj in response_data:
            return self.record_not_found()
        
        page_total  = self.get_total_page(len(data_ids),PAGE_DATA_LIMIT)
        return self.get_response(200, '200', {"code":200,
                                              "data":response_data[obj],
                                              "page_total":page_total if not id else 0
                                              })
    @http.route(['/api/user/race'],type="http", auth="user",methods=['get'])
    def get_race(self, **kw):
        offset =  self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1)
        obj = 'employee.race'
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        domain = []
        if kw.get("search"):
            domain.append(('name','ilike',kw.get("search")))
            
        data_ids = request.env[obj].sudo().search(domain)
        if not data_ids:
            return self.record_not_found()
        
        request_param = {"ids":','.join(str(data.id) for data in data_ids),"fields":['name'],
                         "offset":offset,
                         "limit":PAGE_DATA_LIMIT
                         }
        read_record = self.perform_request(obj,id=None, kwargs=request_param, user=user)
        response_data = json.loads(read_record.data)
        if not obj in response_data:
            return self.record_not_found()
        
        page_total  = self.get_total_page(len(data_ids),PAGE_DATA_LIMIT)
        return self.get_response(200, '200', {"code":200,
                                              "data":response_data[obj],
                                              "page_total":page_total if not id else 0
                                              })
    
    @http.route(['/api/user/marital_status'],type="http", auth="user",methods=['get'])
    def get_marital(self, **kw):
        offset =  self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1)
        obj = 'employee.marital.status'
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        domain = []
        if kw.get("search"):
            domain.append(('name','ilike',kw.get("search")))
            
        data_ids = request.env[obj].sudo().search(domain)
        if not data_ids:
            return self.record_not_found()
        
        request_param = {"ids":','.join(str(data.id) for data in data_ids),"fields":['name'],
                         "offset":offset,
                         "limit":PAGE_DATA_LIMIT
                         }
        read_record = self.perform_request(obj,id=None, kwargs=request_param, user=user)
        response_data = json.loads(read_record.data)
        if not obj in response_data:
            return self.record_not_found()
        
        page_total  = self.get_total_page(len(data_ids),PAGE_DATA_LIMIT)
        return self.get_response(200, '200', {"code":200,
                                              "data":response_data[obj],
                                              "page_total":page_total if not id else 0
                                              })
    
        
        
    @http.route(['/api/user/relation'],type="http", auth="user",methods=['get'])
    def get_relation(self, **kw):
        offset =  self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1)
        obj = 'hr.employee.relation'
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        domain = []
        if kw.get("search"):
            domain.append(('name','ilike',kw.get("search")))
            
        data_ids = request.env[obj].sudo().search(domain)
        if not data_ids:
            return self.record_not_found()
        
        request_param = {"ids":','.join(str(data.id) for data in data_ids),"fields":['name'],
                         "offset":offset,
                         "limit":PAGE_DATA_LIMIT
                         }
        read_record = self.perform_request(obj,id=None, kwargs=request_param, user=user)
        response_data = json.loads(read_record.data)
        if not obj in response_data:
            return self.record_not_found()
        
        page_total  = self.get_total_page(len(data_ids),PAGE_DATA_LIMIT)
        return self.get_response(200, '200', {"code":200,
                                              "data":response_data[obj],
                                              "page_total":page_total if not id else 0
                                              })
        
        
    @route('/store/firebase/token',auth='user',type='json',methods=['POST'])
    def store_firebase_token(self, **kw):
        body = request.jsonrequest
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        
        user = request.env['res.users'].sudo().search([('id','=',request.env.user.id)])
        if not user:
           return self.get_response(200, '200', {"code":200, "message": "User not found"})
        token_list = ""
        if user.firebase_token:
            try:
                token_list = eval(user.firebase_token)
                if not isinstance(token_list, list):
                    user.firebase_token = "[]"
                    token_list = eval(user.firebase_token)
            except SyntaxError:
                user.firebase_token = "[]"
                token_list = eval(user.firebase_token)
            
            if body['firebase_token'] in token_list:
                pass
            else:
                token_list.append(body['firebase_token'])
                user.firebase_token = str(token_list)
                
        else:
            user.firebase_token = f"[{body['firebase_token']}]"
        return self.get_response(200, '200', {"code":200, "message": "Token Stored"})
    
    
    @route('/clear/firebase/token',auth='public',type='json',methods=['POST'])
    def clear_firebase_token(self, **kw):
        body = request.jsonrequest
        user = request.env['res.users'].sudo().search([('id','=',body['user_id'])])
        if not user:
           return self.get_response(200, '200', {"code":200, "message": "User not found"})
        token_list = ""
        if user.firebase_token:
            try:
                token_list = eval(user.firebase_token)
                if not isinstance(token_list, list):
                    user.firebase_token = "[]"
                    token_list = eval(user.firebase_token)
            except SyntaxError:
                user.firebase_token = "[]"
                token_list = eval(user.firebase_token)
            
            if body['firebase_token'] in token_list:
                token_list.remove(body['firebase_token'])
                user.firebase_token = token_list
            else:
                False
        
            
        return self.get_response(200, '200', {"code":200, "message": "Token Cleared"})
        

        