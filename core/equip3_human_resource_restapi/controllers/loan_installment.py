from datetime import datetime, timedelta
from itertools import count
from odoo.http import route,request
import json
from ...restapi.controllers.helper import *


class Equip3HumanResourceRestAPILoanInstallment(RestApi):
    @route(['/api/employee/loan_installment_dashboard/',],auth='user', type='http', methods=['get'])
    def get_employee_loan_installment_dashboard(self,id=None,**kw):
        ffset =  self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1)
        obj = 'loan.installment.details'
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        loan_installment =  request.env[obj].sudo().search([('employee_id','=',request.env.user.employee_id.id)])
        if not loan_installment:
            return self.record_not_found()
        principal_amount =  sum([data.principal_amt for data in loan_installment])
        interest_amount =  sum([data.interest_amt for data in loan_installment])
        emi_intstallment =  sum([data.total for data in loan_installment])
        response = {
            'principal_amount':principal_amount,
            'interest_amount':interest_amount,
            'emi_intstallment':emi_intstallment
            }
        return self.get_response(200, '200', {"code":200,
                                              "data":response
                                              })
        
    
    
    @route(['/api/employee/loan_installment/','/api/employee/loan_installment/<int:id>'],auth='user', type='http', methods=['get'])
    def get_employee_loan_installment(self,id=None,**kw):
        offset =  self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1)
        obj = 'loan.installment.details'
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        
        filter_str = f"lambda line:line"
        if kw.get("state"):
            status = kw.get("state")
            filter_str = filter_str + f" and line.state in {status}"
            
        if kw.get('loan_id'):
            filter_str = filter_str + f" and line.loan_id.id == {kw.get('loan_id')}"
            
        date_from = kw.get("date_from")
        if kw.get("date_from"):
            date_from = datetime.strptime(str(kw.get('date_from')),"%Y-%m-%d") 
            filter_str = filter_str + f" and line.date_from.date()  >= date_from.date()"

        date_to = kw.get("date_to")
        if kw.get("date_to"):
            date_to = datetime.strptime(str(kw.get('date_to')),"%Y-%m-%d") 
            filter_str = filter_str + f" and line.date_to.date() <= date_to.date()"
            
        if kw.get("is_last_7"):
            query = """
            select data.id from loan_installment_details data WHERE data.date_from::date  >= current_date - interval '7' day and data.date_from::date  <= current_date  and data.employee_id = %s
            """
            request._cr.execute(query, [request.env.user.employee_id.id])
            data_result_ids = request.env.cr.dictfetchall()
            ids = []
            if len(data_result_ids) > 0:
                ids = [id['id'] for id in data_result_ids]
            filter_str = filter_str + f" and line.id in {ids}"
            
        if kw.get("is_last_30"):
            query = """
                select data.id from loan_installment_details data WHERE data.date_from  >= current_date - interval '30' day and data.date_from  <= current_date and data.employee_id = %s            
                """
            request._cr.execute(query, [request.env.user.employee_id.id])
            data_result_ids = request.env.cr.dictfetchall()
            ids = []
            if len(data_result_ids) > 0:
                ids = [id['id'] for id in data_result_ids]
            filter_str = filter_str + f" and line.id in {ids}"
        
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
                                    'loan_type',
                                    'loan_repayment_method',
                                    'employee_id',
                                    'install_no',
                                    'interest_amt',
                                    'move_id',
                                    'date_from',
                                    'principal_amt',
                                    'total',
                                    'loan_installment_approver_user_ids'
                                    
     
                                   ]}
        if not id:
            request_param = {"ids":','.join(str(data.id) for data in data_ids),"fields":['state',
                                                                                         'loan_id',
                                                                                         'employee_id',
                                                                                         'date_from',
                                                                                         'date_to',
                                                                                         'principal_amt',
                                                                                         'interest_amt',
                                                                                         'total'
                                                                                         
                                                                                         ],
                             "order":"id desc",
                             "offset":offset,
                             "limit":PAGE_DATA_LIMIT
                             }
            
        read_record = self.perform_request(obj,id=id, kwargs=request_param, user=user)
        response_data = json.loads(read_record.data)
        if not obj in response_data:
            return self.record_not_found()
        
        if 'loan_installment_approver_user_ids' in response_data[obj]:
            if len(response_data[obj]['loan_installment_approver_user_ids']) >= 1:
                response_data[obj]['loan_installment_approver_user_ids'] = self.convert_one2many('loan.installment.approver.user',{"fields":['user_ids',
                                                                                                                     'approver_state',
                                                                                                                     'minimum_approver',
                                                                                                                     'approved_time',
                                                                                                                     'feedback',
                                                                                                              ],
                                                                                                                    "ids":','.join(str(data) for data in response_data[obj]['loan_installment_approver_user_ids'])},user)
                for data_to_convert in response_data[obj]['loan_installment_approver_user_ids']:
                    if len(data_to_convert['user_ids'])>=1:
                        data_to_convert['user_ids'] = self.convert_one2many('res.users',{"fields":['name'],"ids":','.join(str(data) for data in data_to_convert['user_ids'])},user)    
        
        page_total  = self.get_total_page(len(data_ids),PAGE_DATA_LIMIT)
        return self.get_response(200, '200', {"code":200,
                                              "data":response_data[obj],
                                              "page_total":page_total if not id else 0
                                              })