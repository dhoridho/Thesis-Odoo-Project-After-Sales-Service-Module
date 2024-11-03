from datetime import datetime, timedelta
from itertools import count
from odoo.http import route,request
import json
from ...restapi.controllers.helper import *


class Equip3HumanResourceRestAPICareerTransition(RestApi):
    @route('/api/employee/create/career_transition',auth='user', type='json', methods=['POST'])
    def create_career_transition(self,**kw):
        request_data = request.jsonrequest
        auth, user, invalid = self.valid_authentication(kw)
        transition_date  = False
        if 'transition_date' in request_data:
            transition_date   = datetime.strptime(str(request_data.get('transition_date')),"%Y-%m-%d")
            
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})

        data_create = request.env['hr.career.transition'].sudo().create({
                                 "employee_id":request.env.user.employee_id.id,
                                 'transition_category_id':request_data.get('transition_category_id'),
                                 'career_transition_type':request_data.get('career_transition_type'),
                                 'transition_date':transition_date ,
                                 'description':request_data.get('description')
                                 })
        data_create._onchange_employee_id()
        data_create.career_transition = str.lower(data_create.transition_category_id.name)
        data_create.same_as_previous = request_data.get('same_as_previous')
        data_create.new_contract_id = request_data.get('new_contract_id')
        data_create.new_contract_type_id = request_data.get('new_contract_type_id'),
        data_create.new_company_id = request_data.get('new_company_id')
        data_create.new_work_location_id = request_data.get('new_work_location_id')
        data_create.new_department_id = request_data.get('new_department_id'),
        data_create.new_job_id = request_data.get('new_job_id')
        data_create.new_employee_grade_id = request_data.get('new_employee_grade_id')
        if request_data.get("state")  == "to_approve":
            data_create.set_confirm()
            
        if not data_create:
            return self.update_create_failed()
        
        return self.get_response(200, '200', {"code":200, 
                                              "message":"Create Career Transition Suscessfull"
                                              })
        
    @route('/api/employee/update/career_transition/<int:id>',auth='user', type='json', methods=['PUT'])
    def update_career_transition(self,id=None,**kw):
        request_data = request.jsonrequest
        auth, user, invalid = self.valid_authentication(kw)
        transition_date  = False
        if 'transition_date' in request_data:
            transition_date   = datetime.strptime(str(request_data.get('transition_date')),"%Y-%m-%d")
            
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})

        data_update = request.env['hr.career.transition'].sudo().search([('id','=',id)])
        if not data_update:
            return self.record_not_found()
        
        data_update.write({
                                 "employee_id":request.env.user.employee_id.id,
                                 'transition_category_id':request_data.get('transition_category_id'),
                                 'career_transition_type':request_data.get('career_transition_type'),
                                 'transition_date':transition_date ,
                                 'description':request_data.get('description')
                                 })
        data_update._onchange_employee_id()
        data_update.career_transition = str.lower(data_update.transition_category_id.name)
        data_update.same_as_previous = request_data.get('same_as_previous')
        data_update.new_contract_id = request_data.get('new_contract_id')
        data_update.new_contract_type_id = request_data.get('new_contract_type_id'),
        data_update.new_company_id = request_data.get('new_company_id')
        data_update.new_work_location_id = request_data.get('new_work_location_id')
        data_update.new_department_id = request_data.get('new_department_id'),
        data_update.new_job_id = request_data.get('new_job_id')
        data_update.new_employee_grade_id = request_data.get('new_employee_grade_id')
        if request_data.get("state")  == "to_approve":
            data_update.action_confirm()
            
        if not data_update:
            return self.update_create_failed()
        
        return self.get_response(200, '200', {"code":200, 
                                              "message":"Update Career Transition Suscessfull"
                                              })
    
    @route(['/api/employee/career_transition_request/','/api/employee/career_transition_request/<int:id>'],auth='user', type='http', methods=['get'])
    def get_employee_career_transition_request(self,id=None,**kw):
        offset =  self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1)
        obj = 'hr.career.transition'
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        
        filter_str = f"lambda line:line"
        if kw.get("state"):
            status = kw.get("state")
            filter_str = filter_str + f" and line.status in {status}"
            
        date_from = kw.get("date_from")
        if kw.get("date_from"):
            date_from = datetime.strptime(str(kw.get('date_from')),"%Y-%m-%d") 
            filter_str = filter_str + f" and line.transition_date.date()  >= date_from.date()"

        date_to = kw.get("date_to")
        if kw.get("date_to"):
            date_to = datetime.strptime(str(kw.get('date_to')),"%Y-%m-%d") 
            filter_str = filter_str + f" and line.transition_date.date() <= date_to.date()"
            
        if kw.get("is_last_7"):
            query = """
            select data.id from hr_career_transition data WHERE data.transition_date::date  >= current_date - interval '7' day and data.transition_date::date  <= current_date  and data.employee_id = %s
            """
            request._cr.execute(query, [request.env.user.employee_id.id])
            data_result_ids = request.env.cr.dictfetchall()
            ids = []
            if len(data_result_ids) > 0:
                ids = [id['id'] for id in data_result_ids]
            filter_str = filter_str + f" and line.id in {ids}"
            
        if kw.get("is_last_30"):
            query = """
                select data.id from hr_career_transition data WHERE data.transition_date::date  >= current_date - interval '30' day and data.transition_date::date  <= current_date and data.employee_id = %s            
                """
            request._cr.execute(query, [request.env.user.employee_id.id])
            data_result_ids = request.env.cr.dictfetchall()
            ids = []
            if len(data_result_ids) > 0:
                ids = [id['id'] for id in data_result_ids]
            filter_str = filter_str + f" and line.id in {ids}"
        domain = [('employee_id','=',request.env.user.employee_id.id)]
        if kw.get("search"):
            domain.append(("number","ilike",kw.get("search")))
        data_ids = request.env[obj].sudo().search(domain).filtered(eval(filter_str,{'kw':kw,'date_from':date_from,'date_to':date_to}))
        if not data_ids:
            return self.record_not_found()
        
        request_param = {"fields":['status',
                                    'number',
                                    'employee_id',
                                    'transition_category_id',
                                    'date_of_joining',
                                    'years_of_service',
                                    'career_transition_type',
                                    'career_transition_template',
                                    'transition_date',
                                    'description',
                                    'company_id',
                                    'create_date',
                                    'create_uid',
                                    'employee_number_id',
                                    'contract_id',
                                    'contract_type_id',
                                    'work_location_id',
                                    'department_id',
                                    'job_id',
                                    'employee_grade_id',
                                    'same_as_previous',
                                    'new_contract_id',
                                    'new_contract_type_id',
                                    'new_company_id',
                                    'new_department_id',
                                    'new_job_id',
                                    'new_employee_grade_id',
                                    'approval_matrix_ids'
                                    
                                   ]}
        if not id:
            request_param = {"ids":','.join(str(data.id) for data in data_ids),"fields":['number',
                                                                                         'transition_date',
                                                                                         'status'
                                                                                         ],
                             "order":"id desc",
                             "offset":offset,
                             "limit":PAGE_DATA_LIMIT
                             }
            
        read_record = self.perform_request(obj,id=id, kwargs=request_param, user=user)
        response_data = json.loads(read_record.data)
        if not obj in response_data:
            return self.record_not_found()
                
        if 'approval_matrix_ids' in response_data[obj]:
            if len(response_data[obj]['approval_matrix_ids']) >= 1:
                response_data[obj]['approval_matrix_ids'] = self.convert_one2many('hr.career.transition.matrix',{"fields":['approver_id','approval_status','minimum_approver','timestamp','feedback'],
                                                                                                                    "ids":','.join(str(data) for data in response_data[obj]['approval_matrix_ids'])},user)
                for data_to_convert in response_data[obj]['approval_matrix_ids']:
                    if len(data_to_convert['approver_id'])>=1:
                        data_to_convert['approver_id'] = self.convert_one2many('res.users',{"fields":['name'],"ids":','.join(str(data) for data in data_to_convert['approver_id'])},user)                  
    
        page_total  = self.get_total_page(len(data_ids),PAGE_DATA_LIMIT)
        return self.get_response(200, '200', {"code":200,
                                              "data":response_data[obj],
                                              "page_total":page_total if not id else 0
                                              })
    
    @route(['/api/employee/career_transition/career_transition_category'],auth='user', type='http', methods=['get'])
    def career_transition_category(self,id=None,**kw):
        offset =  self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1)
        obj = 'career.transition.category'
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        
        ids = []
        if request.env.user.has_group('equip3_hr_career_transition.career_transition_self_service') and not request.env.user.has_group('equip3_hr_career_transition.career_transition_team_approver'):
            group_ids = request.env['career.transition.category'].search([]).filtered(lambda line: request.env.ref('equip3_hr_career_transition.career_transition_self_service').id in line.group_ids.ids)
            
        if request.env.user.has_group('equip3_hr_career_transition.career_transition_team_approver') and not request.env.user.has_group('equip3_hr_career_transition.career_transition_all_approver'):
            group_ids = request.env['career.transition.category'].search([]).filtered(lambda line: request.env.ref('equip3_hr_career_transition.career_transition_team_approver').id in line.group_ids.ids)
            
        if request.env.user.has_group('equip3_hr_career_transition.career_transition_all_approver') and not request.env.user.has_group('equip3_hr_career_transition.career_transition_administrator'):
            group_ids = self.env['career.transition.category'].search([]).filtered(lambda line: request.env.ref('equip3_hr_career_transition.career_transition_all_approver').id in line.group_ids.ids)
            
        if  request.env.user.has_group('equip3_hr_career_transition.career_transition_administrator'):
            group_ids = request.env['career.transition.category'].search([]).filtered(lambda line: request.env.ref('equip3_hr_career_transition.career_transition_administrator').id in line.group_ids.ids) 
            
        if group_ids:
            data_id = [data.id for data in group_ids]
            ids.extend(data_id)
            
        domain = [('id','in',ids)]
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
        
    @route(['/api/employee/career_transition/career_transition_type'],auth='user', type='http', methods=['get'])
    def get_career_transition_type(self,id=None,**kw):
        offset =  self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1)
        obj = 'career.transition.type'
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
            
        domain = [('career_transition_category_id','=',int(kw.get('category_id')))]
        if kw.get("search"):
            domain.append(('name','ilike',kw.get("search")))
                   
        data_ids = request.env[obj].sudo().search(domain)
        if not data_ids:
            return self.record_not_found()
        
        request_param = {"ids":','.join(str(data.id) for data in data_ids),"fields":['name','letter_id','career_transition_category_id'],
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
    