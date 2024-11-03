from datetime import datetime, timedelta
from itertools import count
from odoo.http import route,request
import json
from ...restapi.controllers.helper import *


class Equip3HumanResourceRestAPIMultiplePaymment(RestApi):
    @route('/api/employee/create/multiple_payment',auth='user', type='json', methods=['POST'])
    def create_multiple_payment(self,**kw):
        company = request.env.company
        request_data = request.jsonrequest
        auth, user, invalid = self.valid_authentication(kw)
        payment_date  = datetime.strptime(str(request_data.get('payment_date')),"%Y-%m-%d")
            
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        
        data_create = request.env['hr.full.loan.payment'].sudo().create({
                                 'employee_id':request.env.user.employee_id.id,
                                 'loan_id':request_data.get('loan_id'),
                                 'payment_date':payment_date,
                                 })
        installment_lines = []
        if 'installment_lines' in request_data:
            for data in request_data['installment_lines']:
                installment_lines.append(data)
                
        data_create.installment_lines = [(6,0,installment_lines)]
        if data_create.installment_lines:
            principal_amount = sum([data.principal_amt for data in data_create.installment_lines])
            data_create.principal_amount = principal_amount
            interest_amount = sum([data.interest_amt for data in data_create.installment_lines])
            data_create.interest_amount = interest_amount
            emi_installment = sum([data.total for data in data_create.installment_lines])
            data_create.emi_installment = emi_installment
        data_create.onchange_approver_user()
        if request_data.get("state")  == "to_approve":
            data_create.action_confirm()
        if not data_create:
            return self.update_create_failed()   
        return self.get_response(200, '200', {"code":200, 
                                              "message":"Create Multiple payment Suscessfull"
                                              })
        
    @route('/api/employee/update/multiple_payment/<int:id>',auth='user', type='json', methods=['PUT'])
    def update_multiple_payment(self,id,**kw):
        company = request.env.company
        request_data = request.jsonrequest
        auth, user, invalid = self.valid_authentication(kw)
        payment_date  = datetime.strptime(str(request_data.get('payment_date')),"%Y-%m-%d")
            
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        
        data_update = request.env['hr.full.loan.payment'].sudo().search([('id','=',id)])
        data_update.write({'employee_id':request.env.user.employee_id.id,
                           'loan_id':request_data.get('loan_id'),
                           'payment_date':payment_date
                           })
        installment_lines = []
        if 'installment_lines' in request_data:
            for data in request_data['installment_lines']:
                installment_lines.append(data)
                
        data_update.installment_lines = [(6,0,installment_lines)]
        if data_update.installment_lines:
            principal_amount = sum([data.principal_amt for data in data_update.installment_lines])
            data_update.principal_amount = principal_amount
            interest_amount = sum([data.interest_amt for data in data_update.installment_lines])
            data_update.interest_amount = interest_amount
            emi_installment = sum([data.total for data in data_update.installment_lines])
            data_update.emi_installment = emi_installment
            
        data_update.onchange_approver_user()
        if request_data.get("state")  == "to_approve":
            data_update.action_confirm()
            
        if not data_update:
            return self.update_create_failed()
        
        return self.get_response(200, '200', {"code":200, 
                                              "message":"Update Multiple payment Suscessfull"
                                              })
    
    @route(['/api/employee/multiple_payment/','/api/employee/multiple_payment/<int:id>'],auth='user', type='http', methods=['get'])
    def get_multiple_payment(self,id=None,**kw):
        offset =  self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1)
        obj = 'hr.full.loan.payment'
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        
        filter_str = f"lambda line:line"
        if kw.get("state"):
            status = kw.get("state")
            filter_str = filter_str + f" and line.state in {status}"
            
        date_from = kw.get("date_from")
        if kw.get("date_from"):
            date_from = datetime.strptime(str(kw.get('date_from')),"%Y-%m-%d") 
            filter_str = filter_str + f" and line.payment_date.date()  >= date_from.date()"

        date_to = kw.get("date_to")
        if kw.get("date_to"):
            date_to = datetime.strptime(str(kw.get('date_to')),"%Y-%m-%d") 
            filter_str = filter_str + f" and line.payment_date.date() <= date_to.date()"
        domain = [('employee_id','=',request.env.user.employee_id.id)]
        if kw.get("search"):
            domain.append(("loan_id.name","ilike",kw.get("search")))
        data_ids = request.env[obj].sudo().search(domain).filtered(eval(filter_str,{'kw':kw,
                                                                                                                                   'date_from':date_from,
                                                                                                                                   "date_to":date_to}))
        if not data_ids:
            return self.record_not_found()
        
        request_param = {"fields":['state',
                                   'loan_id',
                                    'employee_id',
                                    'payment_date',
                                    'loan_type_id',
                                    'installment_lines',
                                    'full_loan_approver_user_ids'
                                    
     
                                   ]}
        if not id:
            request_param = {"ids":','.join(str(data.id) for data in data_ids),"fields":['loan_id',
                                                                                         'state',
                                                                                         'employee_id',
                                                                                         'installment_lines'
                                                                                         
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
                if 'installment_lines' in data:
                    if len(data['installment_lines']) >= 1:
                        data['installment_lines'] = self.convert_one2many('loan.installment.details',{"fields":['date_from',
                                                                                                                            'date_to',
                                                                                                                            'state',
                                                                                                                            'principal_amt',
                                                                                                                            'interest_amt',
                                                                                                                            'total',
                                                                                                                            'currency_id'
                                                                                                                            
                                                                                                                            ],
                                                                                                                            "ids":','.join(str(line) for line in data['installment_lines'])},user)

        if 'installment_lines' in response_data[obj]:
            if len(response_data[obj]['installment_lines']) >= 1:
                response_data[obj]['installment_lines'] = self.convert_one2many('loan.installment.details',{"fields":['date_from',
                                                                                                                    'date_to',
                                                                                                                    'install_no',
                                                                                                                    'state',
                                                                                                                    'principal_amt',
                                                                                                                    'interest_amt',
                                                                                                                    'total',
                                                                                                                    'currency_id'
                                                                                                                    
                                                                                                                    ],
                                                                                                                    "ids":','.join(str(line) for line in response_data[obj]['installment_lines'])},user)
        
        if 'full_loan_approver_user_ids' in response_data[obj]:
            if len(response_data[obj]['full_loan_approver_user_ids']) >= 1:
                response_data[obj]['full_loan_approver_user_ids'] = self.convert_one2many('full.loan.approver.user',{"fields":['user_ids',
                                                                                                                     'approver_state',
                                                                                                                     'minimum_approver',
                                                                                                                     'approved_time',
                                                                                                                     'feedback',
                                                                                                              ],
                                                                                                                    "ids":','.join(str(data) for data in response_data[obj]['full_loan_approver_user_ids'])},user)
                for data_to_convert in response_data[obj]['full_loan_approver_user_ids']:
                    if len(data_to_convert['user_ids'])>=1:
                        data_to_convert['user_ids'] = self.convert_one2many('res.users',{"fields":['name'],"ids":','.join(str(data) for data in data_to_convert['user_ids'])},user)    
    
        page_total  = self.get_total_page(len(data_ids),PAGE_DATA_LIMIT)
        return self.get_response(200, '200', {"code":200,
                                              "data":response_data[obj],
                                              "page_total":page_total if not id else 0
                                              })