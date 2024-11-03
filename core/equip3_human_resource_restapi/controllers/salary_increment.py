from datetime import datetime, timedelta
from itertools import count
from odoo.http import route,request
import json
from ...restapi.controllers.helper import *


class Equip3HumanResourceRestAPIEmployeeSalaryIncrement(RestApi):
    @route('/api/employee/create/salary_incement',auth='user', type='json', methods=['POST'])
    def create_salary_increment(self,**kw):
        request_data = request.jsonrequest
        auth, user, invalid = self.valid_authentication(kw)
        effective_date = False
        if request_data.get('effective_date'):
            effective_date  = datetime.strptime(str(request_data.get('effective_date')),"%Y-%m-%d")
                          
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        
        data_create = request.env['hr.salary.increment'].sudo().create({
                                 'employee_ids': [(6,0,[request.env.user.employee_id.id])],
                                 'apply_to':'by_employee',
                                 'based_on':request_data.get('based_on'),
                                 'amount':request_data.get('amount'),
                                 'percentage':request_data.get('percentage')/100,
                                 'effective_date':effective_date
                                 
                                 })  
        if request_data.get('state') == 'to_approve':
            data_create.submit()
        data_create.onchange_salary_increment()
        data_create.onchange_employee()
        if not data_create:
            return self.update_create_failed()   
        return self.get_response(200, '200', {"code":200, 
                                              "message":"Create Salary Incement Suscessfull"
                                              })
        
    @route('/api/employee/create/salary_incement/<int:id>',auth='user', type='json', methods=['PUT'])
    def update_salary_increment(self,id,**kw):
        request_data = request.jsonrequest
        auth, user, invalid = self.valid_authentication(kw)
        effective_date = False
        if request_data.get('effective_date'):
            effective_date  = datetime.strptime(str(request_data.get('effective_date')),"%Y-%m-%d")
                          
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        
        
        data_update = request.env['hr.salary.increment'].sudo().search([('id','=',id)])
        data_update.write({
                                 'employee_ids': [(6,0,[request.env.user.employee_id.id])],
                                 'apply_to':'by_employee',
                                 'based_on':request_data.get('based_on'),
                                 'amount':request_data.get('amount'),
                                 'percentage':float(request_data.get('percentage'))/100,
                                 'effective_date':effective_date
                                 
                                 })  
        if request_data.get('state') == 'to_approve':
            data_update.submit()
        data_update.onchange_salary_increment()
        data_update.onchange_employee()
        if not data_update:
            return self.update_create_failed()   
        return self.get_response(200, '200', {"code":200, 
                                              "message":"Update Salary Incement Suscessfull"
                                              })
    
    @route(['/api/employee/salary_increment/','/api/employee/salary_increment/<int:id>'],auth='user', type='http', methods=['get'])
    def get_salary_increment(self,id=None,**kw):
        offset =  self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1)
        obj = 'hr.salary.increment'
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        
        filter_str = f"lambda line:{request.env.user.employee_id.id} in line.employee_ids.ids"
        if kw.get("state"):
            state = kw.get("state")
            filter_str = filter_str + f" and line.state in {state}"
            
        if kw.get("based_on"):
            based_on = kw.get("based_on")
            filter_str = filter_str + f" and line.based_on in {based_on}"
            
        date_from = kw.get("date_from")
        if kw.get("date_from"):
            date_from = datetime.strptime(str(kw.get('date_from')),"%Y-%m-%d") 
            filter_str = filter_str + f" and line.effective_date.date()  >= date_from.date()"

        date_to = kw.get("date_to")
        if kw.get("date_to"):
            date_to = datetime.strptime(str(kw.get('date_to')),"%Y-%m-%d") 
            filter_str = filter_str + f" and line.effective_date.date() <= date_to.date()"
            
        if kw.get("is_last_7"):
            query = """
            select data.id from hr_salary_increment data WHERE data.effective_date::date  >= current_date - interval '7' day and data.effective_date  <= current_date
            """
            request._cr.execute(query, [request.env.user.employee_id.id])
            data_result_ids = request.env.cr.dictfetchall()
            ids = []
            if len(data_result_ids) > 0:
                ids = [id['id'] for id in data_result_ids]
            filter_str = filter_str + f" and line.id in {ids}"
            
        if kw.get("is_last_30"):
            query = """
                select data.id from hr_salary_increment data WHERE data.effective_date::date  >= current_date - interval '30' day and data.effective_date  <= current_date        
                """
            request._cr.execute(query, [request.env.user.employee_id.id])
            data_result_ids = request.env.cr.dictfetchall()
            ids = []
            if len(data_result_ids) > 0:
                ids = [id['id'] for id in data_result_ids]
            filter_str = filter_str + f" and line.id in {ids}"
            
        domain = [('employee_id','=',request.env.user.employee_id.id)]
        if kw.get("search"):
            domain.append(('name','ilike',kw.get('search')))
            
        data_ids = request.env[obj].sudo().search(domain).filtered(eval(filter_str,{'kw':kw,'date_from':date_from,'date_to':date_to}))
        if not data_ids:
            return self.record_not_found()
        
        request_param = {"fields":['state',
                                    'name',
                                    'apply_to',
                                    'employee_ids',
                                    'company_ids',
                                    'department_ids',
                                    'job_ids',
                                    'based_on',
                                    'amount',
                                    'percentage',
                                    'effective_date',
                                    'create_date',
                                    'create_uid',
                                    'line_ids',
                                    'approver_user_ids'
                                   ]}
        if not id:
            request_param = {"ids":','.join(str(data.id) for data in data_ids),"fields":['state',
                                                                                         'name',
                                                                                         'apply_to',
                                                                                         'based_on',
                                                                                         'effective_date',
                                                                                         ],
                             "order":"id desc",
                             "offset":offset,
                             "limit":PAGE_DATA_LIMIT
                             }
            
        read_record = self.perform_request(obj,id=id, kwargs=request_param, user=user)
        response_data = json.loads(read_record.data)
        if not obj in response_data:
            return self.record_not_found()
        
        if 'employee_ids' in response_data[obj]:
            if len(response_data[obj]['employee_ids']) >= 1:
                response_data[obj]['employee_ids'] = self.convert_one2many('hr.employee',{"fields":['name'],
                                                                                                      "ids":','.join(str(data) for data in response_data[obj]['employee_ids'])},user)
        if 'company_ids' in response_data[obj]:
            if len(response_data[obj]['company_ids']) >= 1:
                response_data[obj]['company_ids'] = self.convert_one2many('res.company',{"fields":['name'],
                                                                                                      "ids":','.join(str(data) for data in response_data[obj]['company_ids'])},user)
        if 'department_ids' in response_data[obj]:
            if len(response_data[obj]['department_ids']) >= 1:
                response_data[obj]['department_ids'] = self.convert_one2many('hr.department',{"fields":['name'],
                                                                                                      "ids":','.join(str(data) for data in response_data[obj]['department_ids'])},user)
        if 'line_ids' in response_data[obj]:
            if len(response_data[obj]['line_ids']) >= 1:
                response_data[obj]['line_ids'] = self.convert_one2many('hr.salary.increment.line',{"fields":['sequence',
                                                                                                                'employee_id',
                                                                                                                'job_id',
                                                                                                                'last_salary',
                                                                                                                'new_salary'
                                                                                                                ],
                                                                                                      "ids":','.join(str(data) for data in response_data[obj]['line_ids'])},user)
        if 'approver_user_ids' in response_data[obj]:
            if len(response_data[obj]['approver_user_ids']) >= 1:
                response_data[obj]['approver_user_ids'] = self.convert_one2many('salary.increment.approver.user',{"fields":['sequence',
                                                                                                                'approver_id',
                                                                                                                'minimum_approver',
                                                                                                                'approval_status',
                                                                                                                'timestamp',
                                                                                                                'feedback'
                                                                                                                ],
                                                                                                      "ids":','.join(str(data) for data in response_data[obj]['approver_user_ids'])},user)
                for data_to_convert in response_data[obj]['approver_user_ids']:
                    if len(data_to_convert['approver_id'])>=1:
                        data_to_convert['approver_id'] = self.convert_one2many('res.users',{"fields":['name'],
                                                                                        "ids":','.join(str(data) for data in data_to_convert['approver_id'])},user)
     
        
        page_total  = self.get_total_page(len(data_ids),PAGE_DATA_LIMIT)
        return self.get_response(200, '200', {"code":200,
                                              "data":response_data[obj],
                                              "page_total":page_total if not id else 0
                                              })