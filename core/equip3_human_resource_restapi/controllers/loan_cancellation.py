
from datetime import datetime, timedelta
from itertools import count
from odoo.http import route,request
import json
from ...restapi.controllers.helper import *


class Equip3HumanResourceRestAPILoanCancellation(RestApi):
    @route('/api/employee/create/loan_cancellation',auth='user', type='json', methods=['POST'])
    def create_loan_cancellation(self,**kw):
        company = request.env.company
        request_data = request.jsonrequest
        auth, user, invalid = self.valid_authentication(kw)
        date_applied = False
        if 'date_applied' in request_data:
            date_applied  = datetime.strptime(str(request_data.get('date_applied')),"%Y-%m-%d")
        date_disb = False
        if 'date_disb' in request_data:
            date_disb  = datetime.strptime(str(request_data.get('date_disb')),"%Y-%m-%d")
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        loan = request.env['employee.loan.details'].sudo().search([('id','=',int(request_data.get('loan_id')))])
        data_create = request.env['employee.loan.cancelation'].sudo().create({
                                 'employee_id':loan.user_id.employee_id.id,
                                 'date_applied':date_applied,
                                 'loan_id':loan.id,
                                 'notes':request_data.get('notes'),
                                 'principal_amount':loan.principal_amount,
                                 'date_disb':date_disb,
                                 'company_id':loan.company_id.id,
                                 'currency_id':loan.currency_id.id,
                                 'user_id':loan.user_id.id,
                                 })
        data_create.onchange_approver_user()
        if request_data.get("state")  == "to_approve":
            data_create.action_confirm()
        if not data_create:
            return self.update_create_failed()   
        return self.get_response(200, '200', {"code":200, 
                                              "message":"Create Loan Cancellation Suscessfull"
                                              })
        
    @route('/api/employee/update/loan_cancellation/<int:id>',auth='user', type='json', methods=['PUT'])
    def update_loan_cancellation(self,id=None,**kw):
        request_data = request.jsonrequest
        auth, user, invalid = self.valid_authentication(kw)
        date_applied  = datetime.strptime(str(request_data.get('date_applied')),"%Y-%m-%d")
        date_disb = False
        if 'date_disb' in request_data:
            date_disb  = datetime.strptime(str(request_data.get('date_disb')),"%Y-%m-%d")
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        loan = request.env['employee.loan.details'].sudo().search([('id','=',int(request_data.get('loan_id')))])
        data_update = request.env['employee.loan.cancelation'].sudo().search([('id','=',id)])
        if not data_update:
            return self.record_not_found()
        data_update.write({
                                 'employee_id':loan.user_id.employee_id.id,
                                 'date_applied':date_applied,
                                 'loan_id':loan.id,
                                 'notes':request_data.get('notes'),
                                 'principal_amount':loan.principal_amount,
                                 'date_disb':date_disb,
                                 'company_id':loan.company_id.id,
                                 'currency_id':loan.currency_id.id,
                                 'user_id':loan.user_id.id,
                                 })
        data_update.onchange_approver_user()
        if request_data.get("state")  == "to_approve":
            data_update.action_confirm()
        if not data_update:
            return self.update_create_failed()   
        return self.get_response(200, '200', {"code":200, 
                                              "message":"Update Loan Cancellation Suscessfull"
                                              })
    
    @route(['/api/employee/loan_cancellation/','/api/employee/loan_cancellation/<int:id>'],auth='user', type='http', methods=['get'])
    def get_employee_loan_cancellation(self,id=None,**kw):
        offset =  self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1)
        obj = 'employee.loan.cancelation'
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        
        filter_str = f"lambda line:line.employee_id.id == {request.env.user.employee_id.id}"
        if kw.get("state"):
            status = kw.get("state")
            filter_str = filter_str + f" and line.state in {status}"

        if kw.get("loan_type"):
            loan_type = kw.get("loan_type")
            filter_str = filter_str + f" and line.loan_type.id in {loan_type}"
        domain = []
        if kw.get("search"):
            domain.append("|")
            domain.append(("name","ilike",kw.get("search")))
            domain.append(("oan_id.name","ilike",kw.get("search")))
        data_ids = request.env[obj].sudo().search(domain).filtered(eval(filter_str,{'kw':kw}))
        if not data_ids:
            return self.record_not_found()
        
        request_param = {"fields":['state',
                                    'name',
                                    'loan_id',
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
                                                                                         'loan_type',
                                                                                         'state',
                                                                                         'loan_id',
                                                                                         'date_applied'
                                                                                         
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