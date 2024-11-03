from datetime import datetime, timedelta
from itertools import count
from odoo.http import route,request
import json
from ...restapi.controllers.helper import *


class Equip3HumanResourceRestAPILoanRequest(RestApi):
    @route('/api/employee/create/loan_request',auth='user', type='json', methods=['POST'])
    def create_loan_request(self,**kw):
        company = request.env.company
        request_data = request.jsonrequest
        auth, user, invalid = self.valid_authentication(kw)
        date_applied  = datetime.strptime(str(request_data.get('date_applied')),"%Y-%m-%d")
        date_disb = False
        if 'date_disb' in request_data:
            date_disb  = datetime.strptime(str(request_data.get('date_disb')),"%Y-%m-%d")
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        
        data_create = request.env['employee.loan.details'].sudo().create({
                                 'date_applied':date_applied,
                                 'loan_type':request_data.get('loan_type'),
                                 'date_disb':date_disb,
                                 'principal_amount':request_data.get('principal_amount'),
                                 'int_payable':request_data.get('int_payable'),
                                 'interest_mode':request_data.get('interest_mode'),
                                 'duration':request_data.get('duration'),
                                 'notes':request_data.get('notes'),
                                 'int_rate':request_data.get('int_rate'),
                                 })
        loan_proof_ids = []
        if 'loan_proof_ids' in request_data:
            for data in request_data['loan_proof_ids']:
                loan_proof_ids.append((0,0,{'name':data['name'],'attachment':data['attachment'],'attachment':data['attachment'],'mandatory':data['mandatory'],"attachment_name":data['attachment_name']}))
        
        loan_policy_ids = []
        if 'loan_policy_ids' in request_data:
            for data in request_data['loan_policy_ids']:
                loan_policy_ids.append(data)
                
        data_create.loan_proof_ids = loan_proof_ids
        data_create.loan_policy_ids = [(6,0,loan_policy_ids)]
        data_create.onchange_approver_user()
        if request_data.get("state")  == "applied":
            data_create.action_applied()
        if not data_create:
            return self.update_create_failed()   
        return self.get_response(200, '200', {"code":200, 
                                              "message":"Create Loan Request Suscessfull"
                                              })
        
    @route('/api/employee/update/loan_request/<int:id>',auth='user', type='json', methods=['PUT'])
    def update_loan_request(self,id=None,**kw):
        request_data = request.jsonrequest
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        data_update = request.env['employee.loan.details'].sudo().search([('id','=',id)])
        date_applied  = datetime.strptime(str(request_data.get('date_applied')),"%Y-%m-%d")
        date_disb = False
        if 'date_disb' in request_data:
            date_disb  = datetime.strptime(str(request_data.get('date_disb')),"%Y-%m-%d")
        if not data_update:
            return self.record_not_found()
        data_update.write({
                            'date_applied':date_applied,
                            'loan_type':request_data.get('loan_type'),
                            'date_disb':date_disb,
                            'principal_amount':request_data.get('principal_amount'),
                            'int_payable':request_data.get('int_payable'),
                            'interest_mode':request_data.get('interest_mode'),
                            'duration':request_data.get('duration'),
                            'notes':request_data.get('notes'),
                            'int_rate':request_data.get('int_rate'),
                                 })
        result = self.update_one2many([('emp_loan_id','=',data_update.id)],'employee.loan.proof',request_data.get('loan_proof_ids'))
        if result:
            data_update.loan_proof_ids = result
        loan_policy_ids = []
        if 'loan_policy_ids' in request_data:
            for data in request_data['loan_policy_ids']:
                loan_policy_ids.append(data)
        data_update.loan_policy_ids = [(6,0,loan_policy_ids)]
        data_update.onchange_approver_user()
        if request_data.get("state")  == "applied":
            data_update.action_applied()
            
        if not data_update:
            return self.update_create_failed()   
        return self.get_response(200, '200', {"code":200, 
                                              "message":"Update Loan Request Suscessfull"
                                              })
    
    
    @route(['/api/employee/loan_request/','/api/employee/loan_request/<int:id>'],auth='user', type='http', methods=['get'])
    def get_employee_loan_request(self,id=None,**kw):
        offset =  self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1)
        obj = 'employee.loan.details'
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        
        filter_str = f"lambda line:line"
        if kw.get("state"):
            status = kw.get("state")
            filter_str = filter_str + f" and line.state in {status}"

        if kw.get("loan_type"):
            loan_type = kw.get("loan_type")
            filter_str = filter_str + f" and line.loan_type.id in {loan_type}"
            
        date_from = kw.get("date_from")
        if kw.get("date_from"):
            date_from = datetime.strptime(str(kw.get('date_from')),"%Y-%m-%d") 
            filter_str = filter_str + f" and line.date_applied.date()  >= date_from.date()"

        date_to = kw.get("date_to")
        if kw.get("date_to"):
            date_to = datetime.strptime(str(kw.get('date_to')),"%Y-%m-%d") 
            filter_str = filter_str + f" and line.date_applied.date() <= date_to.date()"
            
        domain = [('employee_id','=',request.env.user.employee_id.id)]
        if kw.get('search'):
            domain.append(('name','ilike',kw.get('search')))
            
        data_ids = request.env[obj].sudo().search(domain).filtered(eval(filter_str,{'kw':kw,'date_from':date_from,"date_to":date_to}))
        if not data_ids:
            return self.record_not_found()
        
        request_param = {"fields":['state',
                                    'name',
                                    'employee_id',
                                    'date_applied',
                                    'loan_type',
                                    'date_approved',
                                    'date_disb',
                                    'department_id',
                                    'company_id',
                                    'user_id',
                                    'principal_amount',
                                    'int_payable',
                                    'interest_mode',
                                    'duration',
                                    'int_rate',
                                    'installment_lines',
                                    'final_total',
                                    'total_interest_amount',
                                    'total_amount_paid',
                                    'total_amount_due',
                                    'loan_proof_ids',
                                    'journal_id',
                                    'move_id',
                                    'journal_id1',
                                    'journal_id2',
                                    'employee_loan_account',
                                    'loan_policy_ids',
                                    'notes',
                                    'loan_approver_user_ids'
                                    
     
                                   ]}
        if not id:
            request_param = {"ids":','.join(str(data.id) for data in data_ids),"fields":['name',
                                                                                         'state',
                                                                                         'loan_type',
                                                                                         'date_applied',
                                                                                         'date_approved',
                                                                                         'final_total'
                                                                                         
                                                                                         ],
                             "order":"id desc",
                             "offset":offset,
                             "limit":PAGE_DATA_LIMIT
                             }
            
        read_record = self.perform_request(obj,id=id, kwargs=request_param, user=user)
        response_data = json.loads(read_record.data)
        if not obj in response_data:
            return self.record_not_found()
        
        if 'installment_lines' in response_data[obj]:
            if len(response_data[obj]['installment_lines']) >= 1:
                response_data[obj]['installment_lines'] = self.convert_one2many('loan.installment.details',{"fields":['date_from',
                                                                                                                      'date_to',
                                                                                                                      'state',
                                                                                                                      'principal_amt',
                                                                                                                      'interest_amt',
                                                                                                                      'total',
                                                                                                                      'currency_id'
                                                                                                                      
                                                                                                                      ],
                                                                                                                    "ids":','.join(str(data) for data in response_data[obj]['installment_lines'])},user)
        if 'loan_proof_ids' in response_data[obj]:
            if len(response_data[obj]['loan_proof_ids']) >= 1:
                response_data[obj]['loan_proof_ids'] = self.convert_one2many('employee.loan.proof',{"fields":['name',
                                                                                                              'attachment_name',
                                                                                                              'attachment',
                                                                                                              'mandatory'
                                                                                                              ],
                                                                                                                    "ids":','.join(str(data) for data in response_data[obj]['loan_proof_ids'])},user)
        if 'loan_policy_ids' in response_data[obj]:
            if len(response_data[obj]['loan_policy_ids']) >= 1:
                response_data[obj]['loan_policy_ids'] = self.convert_one2many('loan.policy',{"fields":['name',
                                                                                                        'policy_value',
                                                                                                        'code',
                                                                                                        'company_id',
                                                                                                        'policy_type',
                                                                                                              ],
                                                                                                                    "ids":','.join(str(data) for data in response_data[obj]['loan_policy_ids'])},user)
        if 'loan_approver_user_ids' in response_data[obj]:
            if len(response_data[obj]['loan_approver_user_ids']) >= 1:
                response_data[obj]['loan_approver_user_ids'] = self.convert_one2many('loan.approver.user',{"fields":['user_ids',
                                                                                                                     'approver_state',
                                                                                                                     'minimum_approver',
                                                                                                                     'approved_time',
                                                                                                                     'feedback',
                                                                                                              ],
                                                                                                                    "ids":','.join(str(data) for data in response_data[obj]['loan_approver_user_ids'])},user)
                for data_to_convert in response_data[obj]['loan_approver_user_ids']:
                    if len(data_to_convert['user_ids'])>=1:
                        data_to_convert['user_ids'] = self.convert_one2many('res.users',{"fields":['name'],"ids":','.join(str(data) for data in data_to_convert['user_ids'])},user)    
         
    
        page_total  = self.get_total_page(len(data_ids),PAGE_DATA_LIMIT)
        return self.get_response(200, '200', {"code":200,
                                              "data":response_data[obj],
                                              "page_total":page_total if not id else 0
                                              })
        
        
    @route(['/api/employee/loan_request/loan_type'],auth='user', type='http', methods=['get'])
    def get_loan_type(self,id=None,**kw):
        offset =  self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1)
        obj = 'loan.type'
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        domain = []
        if kw.get("search"):
            domain.append(('name','ilike',kw.get("search")))
                   
        data_ids = request.env[obj].sudo().search(domain).filtered(lambda line: request.env.user.employee_id.id in line.employee_ids.ids)
        if not data_ids:
            return self.record_not_found()
        
        request_param = {"ids":','.join(str(data.id) for data in data_ids),"fields":['name',
                                                                                     'int_payable',
                                                                                     'interest_mode',
                                                                                     'int_rate',
                                                                                     'loan_proof_ids',
                                                                                     ],
                         "offset":offset,
                         "limit":PAGE_DATA_LIMIT
                             }  
        
        read_record = self.perform_request(obj,id=id, kwargs=request_param, user=user)
        response_data = json.loads(read_record.data)
        if not obj in response_data:
            return self.record_not_found()
    
        for data in response_data[obj]:
            if 'loan_proof_ids' in data:
                if len(data['loan_proof_ids']) >= 1:
                    data['loan_proof_ids'] = self.convert_one2many('loan.proof',{"fields":['name',
                                                                                           'mandatory'
                                                                                           ],
                                                                                            "ids":','.join(str(data) for data in data['loan_proof_ids'])},user)
        page_total  = self.get_total_page(len(data_ids),PAGE_DATA_LIMIT)
        return self.get_response(200, '200', {"code":200,
                                              "data":response_data[obj],
                                              "page_total":page_total if not id else 0
                                              })
        
        
    @route(['/api/employee/loan_request/loan_policy'],auth='user', type='http', methods=['get'])
    def get_loan_policies(self,id=None,**kw):
        offset =  self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1)
        obj = 'loan.policy'
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        employee = request.env['hr.employee'].sudo().browse(request.env.user.employee_id.id)
        policies_on_categ = []
        policies_on_empl = []
        for categ in employee.sudo().category_ids:
            if categ.loan_policy:
                policies_on_categ += map(lambda x:x.id, categ.loan_policy)
        if employee.loan_policy:
            policies_on_empl += map(lambda x:x.id, employee.loan_policy)
        loan_policy_ids = list(set(policies_on_categ + policies_on_empl))
        domain = []
        if kw.get("search"):
            domain.append('|'),
            domain.append('|'),
            domain.append(('name','ilike',kw.get("search")))
            domain.append(('code','ilike',kw.get("search")))
            domain.append(('company_id.name','ilike',kw.get("search")))
        ids_filter = []
        data_ids = request.env[obj].sudo().search(domain).filtered(lambda line: line.id in loan_policy_ids)         
        if not data_ids:
            return self.record_not_found()
        
        request_param = {"ids":','.join(str(data) for data in ids_filter),"fields":['name',
                                                                                     'code',
                                                                                     'policy_type',
                                                                                     'policy_value',
                                                                                     'company_id',
                                                                                     ],
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