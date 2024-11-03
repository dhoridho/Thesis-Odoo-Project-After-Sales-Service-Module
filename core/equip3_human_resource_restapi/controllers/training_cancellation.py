from datetime import datetime, timedelta
from itertools import count
from odoo.http import route,request
import json
from ...restapi.controllers.helper import *


class Equip3HumanResourceRestAPITrainingRequest(RestApi):
    @route('/api/employee/create/training_cancellation',auth='user', type='json', methods=['POST'])
    def create_training_cancellation(self,**kw):
        request_data = request.jsonrequest
        auth, user, invalid = self.valid_authentication(kw)       
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        
        data_create = request.env['hr.training.cancellation'].sudo().create({
                                 'employee_id': request.env.user.employee_id.id,
                                 "job_id":request.env.user.employee_id.job_id.id,
                                 "training_request_id":request_data.get("training_request_id"),
                                 "description":request_data.get("description")
                                 
                                 })
        if request_data.get('state') == 'to_approve':
            data_create.action_confirm()
        
        data_create.onchange_approver_user()
        if not data_create:
            return self.update_create_failed()
           
        return self.get_response(200, '200', {"code":200, 
                                              "message":"Create My Training Cancellation Suscessfull"
                                              })
        
    @route('/api/employee/update/training_cancellation/<int:id>',auth='user', type='json', methods=['PUT'])
    def update_training_cancellation(self,id=None,**kw):
        request_data = request.jsonrequest
        auth, user, invalid = self.valid_authentication(kw)       
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        
        data_update = request.env['hr.training.cancellation'].sudo().search([('id','=',id)])
        if not data_update:
            return self.record_not_found()
        
        data_update.write({
            'employee_id': request.env.user.employee_id.id,
            "job_id":request.env.user.employee_id.job_id.id,
             "training_request_id":request_data.get("training_request_id"),
              "description":request_data.get("description")
              })
        if request_data.get('state') == 'to_approve':
            data_update.action_confirm()
        
        data_update.onchange_approver_user()
        if not data_update:
            return self.update_create_failed()
           
        return self.get_response(200, '200', {"code":200, 
                                              "message":"Update My Training Cancellation Suscessfull"
                                              })
        
    @route(['/api/employee/training_cancellation/','/api/employee/training_cancellation/<int:id>'],auth='user', type='http', methods=['get'])
    def get_employee_training_cancellation(self,id=None,**kw):
        offset =  self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1)
        obj = 'hr.training.cancellation'
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        
        filter_str = f"lambda line:line.employee_id.id == {request.env.user.employee_id.id}"
        if kw.get("state"):
            status = kw.get("state")
            filter_str = filter_str + f" and line.state in {status}"
        domain = []
        if kw.get("search"):
            domain.append("|")    
            domain.append(("name","ilike",kw.get("search")))    
            domain.append(("training_request_id.name","ilike",kw.get("search")))    
        data_ids = request.env[obj].sudo().search(domain).filtered(eval(filter_str,{'kw':kw}))
        if not data_ids:
            return self.record_not_found()
        
        request_param = {"fields":['state',
                                    'name',
                                    'employee_id',
                                    'job_id',
                                    'training_job_id',
                                    'training_request_id',
                                    'description',
                                    'training_cancel_approver_user_ids'
                                    
                                   ]}
        if not id:
            request_param = {"ids":','.join(str(data.id) for data in data_ids),"fields":['name',
                                                                                         'state',
                                                                                         'training_request_id'
                                                                                         ],
                             "order":"id desc",
                             "offset":offset,
                             "limit":PAGE_DATA_LIMIT
                             }
        read_record = self.perform_request(obj,id=id, kwargs=request_param, user=user)
        response_data = json.loads(read_record.data)
        if not obj in response_data:
            return self.record_not_found()
        if not id:
            for data in response_data[obj]:
                if 'training_request_id' in data:
                    if len(data['training_request_id']) >= 1:
                        training_request = request.env['training.request'].sudo().search([('id','=',data['training_request_id'][0])])
                        if training_request:
                            data['course_id'] = [training_request.course_id.id,training_request.course_id.name] if training_request.course_id else []
                
        
        if 'training_request_id' in response_data[obj]:
            if len(response_data[obj]['training_request_id']) >= 1:
                training_request = request.env['training.request'].sudo().search([('id','=',response_data[obj]['training_request_id'][0])])
                if training_request:
                    response_data[obj]['course_id'] = [training_request.course_id.id,training_request.course_id.name] if training_request.course_id else []
                    
        if 'training_job_id' in response_data[obj]:
            if len(response_data[obj]['training_job_id']) >= 1:
                response_data[obj]['training_job_id'] = self.convert_one2many('training.courses',{"fields":['name'],
                                                                                                                    "ids":','.join(str(data) for data in response_data[obj]['training_job_id'])},user)
        
        if 'training_cancel_approver_user_ids' in response_data[obj]:
            if len(response_data[obj]['training_cancel_approver_user_ids']) >= 1:
                response_data[obj]['training_cancel_approver_user_ids'] = self.convert_one2many('training.cancel.approver.user',{"fields":['user_ids','approval_status','minimum_approver','approved_time','feedback'],
                                                                                                                    "ids":','.join(str(data) for data in response_data[obj]['training_cancel_approver_user_ids'])},user)
                
                for data_to_convert in response_data[obj]['training_cancel_approver_user_ids']:
                    if len(data_to_convert['user_ids'])>=1:
                        data_to_convert['user_ids'] = self.convert_one2many('res.users',{"fields":['name'],"ids":','.join(str(data) for data in data_to_convert['user_ids'])},user)                  
    
        page_total  = self.get_total_page(len(data_ids),PAGE_DATA_LIMIT)
        return self.get_response(200, '200', {"code":200,
                                              "data":response_data[obj],
                                              "page_total":page_total if not id else 0
                                              })