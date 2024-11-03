from datetime import datetime, timedelta, time
from itertools import count
from odoo.http import route,request
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT,DEFAULT_SERVER_DATE_FORMAT
import json
from ...restapi.controllers.helper import *
from odoo import models, fields,_
import babel
import pytz

class Equip3HumanResourceEmployeeChangeRequest(RestApi):
    @route('/api/employee/create/employee_change_request',auth='user', type='json', methods=['POST'])
    def create_employee_change_request(self,**kw):
        company = request.env.company
        request_data = request.jsonrequest
        auth, user, invalid = self.valid_authentication(kw)
        birthday  = False
        if request_data.get('birthday'):
            birthday  = datetime.strptime(str(request_data.get('birthday')),"%Y-%m-%d")
            
        visa_expire  = False
        if request_data.get('visa_expire'):
            visa_expire  = datetime.strptime(str(request_data.get('visa_expire')),"%Y-%m-%d")
            
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        
        data_create = request.env['hr.employee.change.request'].sudo().create({
                                 "employee_id":request.env.user.employee_id.id})
        data_create.onchange_employee()
        data_create.private_email = request_data.get('private_email')
        data_create.phone = request_data.get('phone')
        data_create.km_home_work = request_data.get('km_home_work')
        data_create.religion_id = request_data.get('religion_id')
        data_create.race_id = request_data.get('race_id')
        data_create.gender = request_data.get('gender')
        data_create.marital = request_data.get('marital')
        data_create.country_id = request_data.get('country_id')
        data_create.state_id = request_data.get('state_id')
        data_create.identification_id = request_data.get('identification_id')
        data_create.passport_id = request_data.get('passport_id')
        data_create.birthday = birthday
        data_create.place_of_birth = request_data.get('place_of_birth')
        data_create.country_of_birth = request_data.get('country_of_birth')
        data_create.blood_type = request_data.get('blood_type')
        data_create.height = request_data.get('height')
        data_create.weight = request_data.get('weight')
        data_create.visa_no = request_data.get('visa_no')
        data_create.permit_no = request_data.get('permit_no')
        data_create.visa_expire = visa_expire
        get_address_ids = []
        if 'get_address_ids' in request_data:
            for data in request_data['get_address_ids']:
                get_address_ids.append((0,0,{'address_type':data['address_type'],
                                             'street':data['street'],
                                             'location':data['location'],
                                             'country_id':data['country_id'],
                                             'state_id':data['state_id'],
                                             'postal_code':data['postal_code'],
                                             'tel_number':data['tel_number']
                                             }))
        get_emergency_ids = []
        if 'get_emergency_ids' in request_data:
            for data in request_data['get_emergency_ids']:
                get_emergency_ids.append((0,0,{'name':data['name'],
                                             'phone':data['phone'],
                                             'relation_id':data['relation_id'],
                                             'address':data['address']
                                             }))
                
        get_bank_ids = []
        if 'get_bank_ids' in request_data:
            for data in request_data['get_bank_ids']:
                get_bank_ids.append((0,0,{'is_used':data['is_used'],
                                          'name':data['name'],
                                          'bank_unit':data['bank_unit'],
                                          'acc_number':data['acc_number'],
                                          'acc_holder':data['acc_holder']
                                             }))
                
        get_fam_ids = []
        if 'get_fam_ids' in request_data:
            for data in request_data['get_fam_ids']:
                get_fam_ids.append((0,0,{'member_name':data['member_name'],
                                          'relation_id':data['relation_id'],
                                          'gender':data['gender'],
                                          'age':data['age'],
                                          'education':data['education'],
                                          'occupation':data['occupation'],
                                          'city':data['city']
                                             }))
        get_education_ids = []
        if 'get_education_ids' in request_data:
            for data in request_data['get_education_ids']:
                get_education_ids.append((0,0,{'certificate':data['certificate'],
                                          'study_field':data['study_field'],
                                          'study_school':data['study_school'],
                                          'city':data['city'],
                                          'graduation_year':data['graduation_year'],
                                          'gpa_score':data['gpa_score']
                                             }))
                

        get_health_ids = []
        if 'get_health_ids' in request_data:
            for data in request_data['get_health_ids']:
                date_from  = False
                if data['date_from']:
                    date_from  = datetime.strptime(str(data.get('date_from')),"%Y-%m-%d")
                date_to  = False
                if data['date_to']:
                    date_to  = datetime.strptime(str(data.get('date_to')),"%Y-%m-%d")
                get_health_ids.append((0,0,{'name':data['name'],
                                          'illness_type':data['illness_type'],
                                          'date_from':date_from,
                                          'date_to':date_to,
                                          'notes':data['notes']
                                             }))
        face_ids = []
        if 'face_ids' in request_data:
            for data in request_data['face_ids']:
                face_ids.append((0,0,{'name':data['name'],
                                          'image':data['image'],
                                          'descriptor':data['descriptor'],
                                          'image_detection':data['image_detection'],
                                          'is_cropped':data['is_cropped']
                                             }))
                
        data_create.get_address_ids = get_address_ids
        data_create.get_emergency_ids = get_emergency_ids
        data_create.get_bank_ids = get_bank_ids
        data_create.get_fam_ids = get_fam_ids
        data_create.get_education_ids = get_education_ids
        data_create.face_ids = [(6,0,[])]
        data_create.face_ids = face_ids
        data_create.get_health_ids = get_health_ids
        if request_data.get("state")  == "to_approve":
            data_create.confirm()
        if not data_create:
            return self.update_create_failed()   
        return self.get_response(200, '200', {"code":200, 
                                              "message":"Update Employee Change request Successfull"
                                              })
        
    @route('/api/employee/update/employee_change_request/<int:id>',auth='user', type='json', methods=['PUT'])
    def update_employee_change_request(self,id=None,**kw):
        request_data = request.jsonrequest
        auth, user, invalid = self.valid_authentication(kw)
        birthday  = False
        if request_data.get('birthday'):
            birthday  = datetime.strptime(str(request_data.get('birthday')),"%Y-%m-%d")
            
        visa_expire  = False
        if request_data.get('visa_expire'):
            visa_expire  = datetime.strptime(str(request_data.get('visa_expire')),"%Y-%m-%d")
            
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        
        data_update = request.env['hr.employee.change.request'].sudo().search([('id','=',id)])
        if not data_update:
            return self.record_not_found()
        
        data_update.private_email = request_data.get('private_email')
        data_update.phone = request_data.get('phone')
        data_update.km_home_work = request_data.get('km_home_work')
        data_update.religion_id = request_data.get('religion_id')
        data_update.race_id = request_data.get('race_id')
        data_update.gender = request_data.get('gender')
        data_update.marital = request_data.get('marital')
        data_update.country_id = request_data.get('country_id')
        data_update.state_id = request_data.get('state_id')
        data_update.identification_id = request_data.get('identification_id')
        data_update.passport_id = request_data.get('passport_id')
        data_update.birthday = birthday
        data_update.place_of_birth = request_data.get('place_of_birth')
        data_update.country_of_birth = request_data.get('country_of_birth')
        data_update.blood_type = request_data.get('blood_type')
        data_update.height = request_data.get('height')
        data_update.weight = request_data.get('weight')
        data_update.visa_no = request_data.get('visa_no')
        data_update.permit_no = request_data.get('permit_no')
        data_update.visa_expire = visa_expire


        if 'get_address_ids' in request_data:
            result = self.update_one2many([('change_request_id','=',data_update.id)],'hr.employee.address.change.line',request_data.get('get_address_ids'))
            if result:
                data_update.get_address_ids = result   
                
        if 'get_emergency_ids' in request_data:
            result = self.update_one2many([('change_request_id','=',data_update.id)],'employee.emergency.contact.change.line',request_data.get('get_emergency_ids'))
            if result:
                data_update.get_emergency_ids = result   
                
        if 'get_bank_ids' in request_data:
            result = self.update_one2many([('change_request_id','=',data_update.id)],'bank.account.change.line',request_data.get('get_bank_ids'))
            if result:
                data_update.get_bank_ids = result   
                    
        if 'get_fam_ids' in request_data:
            result = self.update_one2many([('change_request_id','=',data_update.id)],'hr.employee.family.change.line',request_data.get('get_fam_ids'))
            if result:
                data_update.get_fam_ids = result   
                
        if 'get_education_ids' in request_data:
            result = self.update_one2many([('change_request_id','=',data_update.id)],'hr.employee.education.change.line',request_data.get('get_education_ids'))
            if result:
                data_update.get_education_ids = result      
        
        if 'get_health_ids' in request_data:
            result = self.update_one2many([('change_request_id','=',data_update.id)],'employee.health.records.change.line',request_data.get('get_health_ids'))
            if result:
                data_update.get_health_ids = result 
                  
        if 'face_ids' in request_data:
            result = self.update_one2many([('change_id','=',data_update.id)],'employee.change.request.image',request_data.get('face_ids'))
            if result:
                data_update.face_ids = result              

        if request_data.get("state")  == "to_approve":
            data_update.confirm()
            
        if not data_update:
            return self.update_create_failed()   
        return self.get_response(200, '200', {"code":200, 
                                              "message":"Update Employee Change request Successfull"
                                              })
    
    
    
    @route(['/api/employee/employee_change_request/<int:id>/approve'],auth='user', type='json', methods=['put'])
    @authenticate
    def approve_change_request(self,id=None,**kw):
        request_data = request.jsonrequest
        obj = 'employee.change.approval.wizard'
        change_request = request.env[obj].sudo().create({'changes_request_id':id,'state':'approved','feedback':request_data['feedback']})
        change_request.submit()
        return self.get_response(200, '200', {"code":200,
                                        "message":"Change Request Approved"
                                        })
        
    @route(['/api/employee/employee_change_request/<int:id>/reject'],auth='user', type='json', methods=['put'])
    @authenticate
    def reject_change_request(self,id=None,**kw):
        request_data = request.jsonrequest
        obj = 'employee.change.approval.wizard'
        change_request = request.env[obj].sudo().create({'changes_request_id':id,'state':'rejected','feedback':request_data['feedback']})
        change_request.submit()
        return self.get_response(200, '200', {"code":200,
                                        "message":"Change Request Rejected"
                                        })
    
    
    @route(['/api/employee/employee_change_request','/api/employee/employee_change_request/<int:id>'],auth='user', type='http', methods=['get'])
    @authenticate
    def get_employee_change_request(self,id=None,**kw):
        offset =  self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1)
        obj = 'hr.employee.change.request'        
        filter_str = f"lambda line:line"
        if kw.get("state"):
            state = kw.get("state")
            filter_str = filter_str + f" and line.state in {state}"
            
        start_date = kw.get("start_date")
        if kw.get("start_date"):
            start_date = datetime.strptime(str(kw.get('start_date')),"%Y-%m-%d") 
            filter_str = filter_str + f" and line.create_date.date()  >= start_date.date()"

        end_date = kw.get("end_date")
        if kw.get("end_date"):
            end_date = datetime.strptime(str(kw.get('end_date')),"%Y-%m-%d") 
            filter_str = filter_str + f" and line.create_date.date() <= end_date.date()"
            
        if kw.get("is_last_7"):
            query = """
            select data.id from hr_employee_change_request data WHERE data.create_date::date  >= current_date - interval '7' day and data.create_date::date  <= current_date  and data.employee_id = %s
            """
            request._cr.execute(query, [request.env.user.employee_id.id])
            data_result_ids = request.env.cr.dictfetchall()
            ids = []
            if len(data_result_ids) > 0:
                ids = [id['id'] for id in data_result_ids]
            filter_str = filter_str + f" and line.id in {ids}"
            
        if kw.get("is_last_30"):
            query = """
                select data.id from hr_employee_change_request data WHERE data.create_date::date  >= current_date - interval '30' day and data.create_date::date  <= current_date and data.employee_id = %s            
                """
            request._cr.execute(query, [request.env.user.employee_id.id])
            data_result_ids = request.env.cr.dictfetchall()
            ids = []
            if len(data_result_ids) > 0:
                ids = [id['id'] for id in data_result_ids]
            filter_str = filter_str + f" and line.id in {ids}"
            
        data_ids = request.env[obj].sudo().search([('employee_id','=',request.env.user.employee_id.id)]).filtered(eval(filter_str,{'kw':kw,
                                                                                                                    'start_date':start_date,
                                                                                                                    'end_date':end_date}))
        if not data_ids:
            return self.record_not_found()
        
        if kw.get('my_active_user'):
            for my_active in data_ids:
                my_active._compute_can_approve()      
            data_ids =  data_ids.filtered(lambda line:line.is_approver)  
        
        request_param = {"fields":['state',
                                    'employee_id',
                                    'sequence_code',
                                    'job_id',
                                    'department_id',
                                    'location_id',
                                    'date_of_joining',
                                    'create_date',
                                    'create_uid',
                                    'private_email',
                                    'phone',
                                    'km_home_work',
                                    'religion_id',
                                    'race_id',
                                    'gender',
                                    'marital',
                                    'country_id',
                                    'country_domicile_code',
                                    'state_id',
                                    'identification_id',
                                    'passport_id',
                                    'birthday',
                                    'place_of_birth',
                                    'country_of_birth',
                                    'blood_type',
                                    'height',
                                    'weight',
                                    'visa_no',
                                    'permit_no',
                                    'visa_expire',
                                    'get_address_ids',
                                    'get_emergency_ids',
                                    'get_bank_ids',
                                    'get_fam_ids',
                                    'get_education_ids',
                                    'get_health_ids',
                                    'face_ids',
                                    'change_request_line_ids',
                                    'address_before_ids',
                                    'address_after_ids',
                                    'emergency_before_ids',
                                    'emergency_after_ids',
                                    'bank_before_ids',
                                    'bank_after_ids',
                                    'fam_before_ids',
                                    'fam_after_ids',
                                    'education_before_ids',
                                    'education_after_ids',
                                    'health_before_ids',
                                    'health_after_ids',
                                    'before_face_ids',
                                    'after_face_ids',
                                    'approval_line_ids'
                                   ]}
        if not id:
            request_param = {"ids":','.join(str(data.id) for data in data_ids),"fields":['employee_id',
                                                                                         'state',
                                                                                         'create_date',
                                                                                         ],
                             "order":"id desc",
                             "offset":offset,
                             "limit":PAGE_DATA_LIMIT
                             }
            
        read_record = self.perform_request(obj,id=id, kwargs=request_param, user=request.env.user)
        try:
            response_data = json.loads(read_record.data)
            if not obj in response_data:
                return self.record_not_found()
        except json.decoder.JSONDecodeError:
            return read_record.data
                
        if 'get_address_ids' in response_data[obj]:
            if len(response_data[obj]['get_address_ids']) >= 1:
                response_data[obj]['get_address_ids'] = self.convert_one2many('hr.employee.address.change.line',{"fields":['address_type','street','location','country_id','state_id','postal_code','tel_number'],
                                                                                                                    "ids":','.join(str(data) for data in response_data[obj]['get_address_ids'])},user)
        
        if 'get_emergency_ids' in response_data[obj]:
            if len(response_data[obj]['get_emergency_ids']) >= 1:
                response_data[obj]['get_emergency_ids'] = self.convert_one2many('employee.emergency.contact.change.line',{"fields":['name','phone','relation_id','address'],
                                                                                                                    "ids":','.join(str(data) for data in response_data[obj]['get_emergency_ids'])},user)
        
        if 'get_bank_ids' in response_data[obj]:
            if len(response_data[obj]['get_bank_ids']) >= 1:
                response_data[obj]['get_bank_ids'] = self.convert_one2many('bank.account.change.line',{"fields":['is_used','acc_holder','name','bic','bank_unit','acc_number'],
                                                                                                                    "ids":','.join(str(data) for data in response_data[obj]['get_bank_ids'])},user)
        
        if 'get_fam_ids' in response_data[obj]:
            if len(response_data[obj]['get_fam_ids']) >= 1:
                response_data[obj]['get_fam_ids'] = self.convert_one2many('hr.employee.family.change.line',{"fields":['member_name','relation_id','gender','age','education','occupation','city'],
                                                                                                                    "ids":','.join(str(data) for data in response_data[obj]['get_fam_ids'])},user)
        
        if 'get_education_ids' in response_data[obj]:
            if len(response_data[obj]['get_education_ids']) >= 1:
                response_data[obj]['get_education_ids'] = self.convert_one2many('hr.employee.education.change.line',{"fields":['certificate','study_field','study_school','city','graduation_year','gpa_score'],
                                                                                                                    "ids":','.join(str(data) for data in response_data[obj]['get_education_ids'])},user)
        
        if 'get_health_ids' in response_data[obj]:
            if len(response_data[obj]['get_health_ids']) >= 1:
                response_data[obj]['get_health_ids'] = self.convert_one2many('employee.health.records.change.line',{"fields":['name','illness_type','medical_checkup','date_from','date_to','notes'],
                                                                                                                    "ids":','.join(str(data) for data in response_data[obj]['get_health_ids'])},user)
        
        if 'face_ids' in response_data[obj]:
            if len(response_data[obj]['face_ids']) >= 1:
                response_data[obj]['face_ids'] = self.convert_one2many('employee.change.request.image',{"fields":['sequence','name','image'],
                                                                                                                    "ids":','.join(str(data) for data in response_data[obj]['face_ids'])},user)
        
        if 'change_request_line_ids' in response_data[obj]:
            if len(response_data[obj]['change_request_line_ids']) >= 1:
                response_data[obj]['change_request_line_ids'] = self.convert_one2many('hr.employee.change.request.line',{"fields":['name_of_field','before','after'],
                                                                                                                    "ids":','.join(str(data) for data in response_data[obj]['change_request_line_ids'])},user)

        if 'address_before_ids' in response_data[obj]:
            if len(response_data[obj]['address_before_ids']) >= 1:
                response_data[obj]['address_before_ids'] = self.convert_one2many('hr.employee.address.change.line',{"fields":['address_type','street','location','country_id','state_id','postal_code','tel_number'],
                                                                                                                    "ids":','.join(str(data) for data in response_data[obj]['address_before_ids'])},user)
        
        if 'address_after_ids' in response_data[obj]:
            if len(response_data[obj]['address_after_ids']) >= 1:
                response_data[obj]['address_after_ids'] = self.convert_one2many('hr.employee.address.change.line',{"fields":['address_type','street','location','country_id','state_id','postal_code','tel_number'],
                                                                                                                    "ids":','.join(str(data) for data in response_data[obj]['address_after_ids'])},user)
        
        if 'emergency_before_ids' in response_data[obj]:
            if len(response_data[obj]['emergency_before_ids']) >= 1:
                response_data[obj]['emergency_before_ids'] = self.convert_one2many('employee.emergency.contact.change.line',{"fields":['name','phone','relation_id','address'],
                                                                                                                    "ids":','.join(str(data) for data in response_data[obj]['emergency_before_ids'])},user)
        
        if 'emergency_after_ids' in response_data[obj]:
            if len(response_data[obj]['emergency_after_ids']) >= 1:
                response_data[obj]['emergency_after_ids'] = self.convert_one2many('employee.emergency.contact.change.line',{"fields":['name','phone','relation_id','address'],
                                                                                                                    "ids":','.join(str(data) for data in response_data[obj]['emergency_after_ids'])},user)

        if 'bank_before_ids' in response_data[obj]:
            if len(response_data[obj]['bank_before_ids']) >= 1:
                response_data[obj]['bank_before_ids'] = self.convert_one2many('bank.account.change.line',{"fields":['is_used','acc_holder','name','bic','bank_unit','acc_number'],
                                                                                                                    "ids":','.join(str(data) for data in response_data[obj]['bank_before_ids'])},user)

        if 'bank_after_ids' in response_data[obj]:
            if len(response_data[obj]['bank_after_ids']) >= 1:
                response_data[obj]['bank_after_ids'] = self.convert_one2many('bank.account.change.line',{"fields":['is_used','acc_holder','name','bic','bank_unit','acc_number'],
                                                                                                                    "ids":','.join(str(data) for data in response_data[obj]['bank_after_ids'])},user)

        if 'fam_before_ids' in response_data[obj]:
            if len(response_data[obj]['fam_before_ids']) >= 1:
                response_data[obj]['fam_before_ids'] = self.convert_one2many('hr.employee.family.change.line',{"fields":['member_name','relation_id','gender','age','education','occupation','city'],
                                                                                                                    "ids":','.join(str(data) for data in response_data[obj]['fam_before_ids'])},user)

        if 'fam_after_ids' in response_data[obj]:
            if len(response_data[obj]['fam_after_ids']) >= 1:
                response_data[obj]['fam_after_ids'] = self.convert_one2many('hr.employee.family.change.line',{"fields":['member_name','relation_id','gender','age','education','occupation','city'],
                                                                                                                    "ids":','.join(str(data) for data in response_data[obj]['fam_after_ids'])},user)

        if 'education_before_ids' in response_data[obj]:
            if len(response_data[obj]['education_before_ids']) >= 1:
                response_data[obj]['education_before_ids'] = self.convert_one2many('hr.employee.education.change.line',{"fields":['certificate','study_field','study_school','city','graduation_year','gpa_score'],
                                                                                                                    "ids":','.join(str(data) for data in response_data[obj]['education_before_ids'])},user)

        if 'education_after_ids' in response_data[obj]:
            if len(response_data[obj]['education_after_ids']) >= 1:
                response_data[obj]['education_after_ids'] = self.convert_one2many('hr.employee.education.change.line',{"fields":['certificate','study_field','study_school','city','graduation_year','gpa_score'],
                                                                                                                    "ids":','.join(str(data) for data in response_data[obj]['education_after_ids'])},user)

        if 'health_before_ids' in response_data[obj]:
            if len(response_data[obj]['health_before_ids']) >= 1:
                response_data[obj]['health_before_ids'] = self.convert_one2many('employee.health.records.change.line',{"fields":['name','illness_type','medical_checkup','date_from','date_to','notes'],
                                                                                                                    "ids":','.join(str(data) for data in response_data[obj]['health_before_ids'])},user)

        if 'health_after_ids' in response_data[obj]:
            if len(response_data[obj]['health_after_ids']) >= 1:
                response_data[obj]['health_after_ids'] = self.convert_one2many('employee.health.records.change.line',{"fields":['name','illness_type','medical_checkup','date_from','date_to','notes'],
                                                                                                                    "ids":','.join(str(data) for data in response_data[obj]['health_after_ids'])},user)

        if 'before_face_ids' in response_data[obj]:
            if len(response_data[obj]['before_face_ids']) >= 1:
                response_data[obj]['before_face_ids'] = self.convert_one2many('employee.change.request.image',{"fields":['sequence','name','image'],
                                                                                                                    "ids":','.join(str(data) for data in response_data[obj]['before_face_ids'])},user)

        if 'after_face_ids' in response_data[obj]:
            if len(response_data[obj]['after_face_ids']) >= 1:
                response_data[obj]['after_face_ids'] = self.convert_one2many('employee.change.request.image',{"fields":['sequence','name','image'],
                                                                                                                    "ids":','.join(str(data) for data in response_data[obj]['after_face_ids'])},user)

        if 'approval_line_ids' in response_data[obj]:
            if len(response_data[obj]['approval_line_ids']) >= 1:
                response_data[obj]['approval_line_ids'] = self.convert_one2many('employee.change.request.approval.line',{"fields":['user_ids','minimum_approver','approver_state','approval_status','timestamp','feedback'],
                                                                                                                    "ids":','.join(str(data) for data in response_data[obj]['approval_line_ids'])},user)
                for data_to_convert in response_data[obj]['approval_line_ids']:
                    if len(data_to_convert['user_ids'])>=1:
                        data_to_convert['user_ids'] = self.convert_one2many('res.users',{"fields":['name'],
                                                                                        "ids":','.join(str(data) for data in data_to_convert['user_ids'])},user)
        
        page_total  = self.get_total_page(len(data_ids),PAGE_DATA_LIMIT)
        return self.get_response(200, '200', {"code":200,
                                              "data":response_data[obj],
                                              "page_total":page_total if not id else 0
                                              })
        
    @route(['/api/employee/employee_change_request/get_current_data'],auth='user', type='http', methods=['get'])
    def get_current_employee_data(self,**kw):
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        user_env = request.env.user
        response = {
        'private_email' :user_env.employee_id.private_email,
        'phone':user_env.employee_id.phone,
        'km_home_work':user_env.employee_id.km_home_work,
        'religion_id':[user_env.employee_id.religion_id.id,user_env.employee_id.religion_id.name] if user_env.employee_id.religion_id else False,
        'race_id' :[user_env.employee_id.race_id.id,user_env.employee_id.race_id.name] if user_env.employee_id.race_id else False,
        'gender' :user_env.employee_id.gender,
        'marital':[user_env.employee_id.marital.id,user_env.employee_id.marital.name] if user_env.employee_id.marital else False,
        'country_id' :[user_env.employee_id.country_id.id,user_env.employee_id.country_id.name] if user_env.employee_id.country_id else False,
        'state_id' :[user_env.employee_id.state_id.id,user_env.employee_id.state_id.name] if user_env.employee_id.state_id else False,
        'identification_id' : user_env.employee_id.identification_id,
        'passport_id' : user_env.employee_id.passport_id,
        'birthday' : user_env.employee_id.birthday.strftime("%Y-%m-%d") if user_env.employee_id.birthday else False,
        'place_of_birth' : user_env.employee_id.place_of_birth,
        'country_of_birth': [user_env.employee_id.country_of_birth.id,user_env.employee_id.country_of_birth.name] if user_env.employee_id.country_of_birth else False,
        'blood_type':user_env.employee_id.blood_type,
        'height':user_env.employee_id.height,
        'weight': user_env.employee_id.weight,
        'visa_no':user_env.employee_id.visa_no,
        'permit_no':user_env.employee_id.permit_no,
        'visa_expire' : user_env.employee_id.visa_expire.strftime("%Y-%m-%d") if user_env.employee_id.visa_expire else  False,
        'get_address_ids' :[{'address_type':data.address_type,
                         'street':data.street,
                         'location':data.location,
                         'country_id':[data.country_id.id,data.country_id.name] if data.country_id.id else False,
                         'state_id':[data.state_id.id,data.state_id.name] if data.state_id else False,
                         'postal_code':data.postal_code,
                         'tel_number':data.tel_number} for data in user_env.employee_id.address_ids],
        'get_emergency_ids':[{'name':data.name,
                              'phone':data.phone,
                              'relation_id':[data.relation_id.id,data.relation_id.name] if data.relation_id else False,
                              'address':data.address}for data in user_env.employee_id.emergency_ids],
        'get_bank_ids' : [{'is_used':data.is_used,
                           'acc_holder':data.acc_holder,
                           'name':data.name.name,
                           'bic':data.bic,
                           'bank_unit':data.bank_unit,
                           'acc_number':data.acc_number
                           }for data in user_env.employee_id.bank_ids],
        'get_fam_ids' :[{'member_name':data.member_name,
                         'relation_id':[data.relation_id.id,data.relation_id.name] if data.relation_id else False,
                         'gender':data.gender,
                         'age':data.age,
                         'education':data.education,
                         'occupation':data.occupation,
                         'city':data.city}for data in user_env.employee_id.fam_ids],
        'get_education_ids': [{'certificate':data.certificate,
                               'study_field':data.study_field,
                               'study_school':data.study_school,
                               'city':data.city,
                               'graduation_year':data.graduation_year,
                               'gpa_score':data.gpa_score
                               }for data in user_env.employee_id.education_ids],
        'get_health_ids': [{'name':data.name,
                            'illness_type':data.illness_type,
                            'medical_checkup':data.medical_checkup,
                            'date_from':data.date_from.strftime("%Y-%m-%d") if  data.date_from else False,
                            'date_to':data.date_to.strftime("%Y-%m-%d") if  data.date_to else False,
                            'notes':data.notes,
                        
                        } for data in user_env.employee_id.health_ids],
        'face_ids':[]
        }
        # if user_env.employee_id.user_id.res_users_image_ids:
        #     face_ids = []
        #     if user_env.employee_id.user_id.res_users_image_ids:
        #         for data in user_env.employee_id.user_id.res_users_image_ids:
        #             if data.image and data.name and data.image_detection:
        #                 face_ids.append({
        #                     'name':data.name,
        #                     'sequence':data.sequence,
        #                     'image':data.image.decode("utf-8") or False,
        #                     'image_detection':data.image_detection.decode("utf-8") or False,
        #                     'descriptor':data.descriptor,

        #                 })
        #     response['face_ids'] = face_ids
        return self.get_response(200, '200', {"code":200,
                                              "data":response
                                              })