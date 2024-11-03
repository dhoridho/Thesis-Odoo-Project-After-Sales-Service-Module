from datetime import datetime, timedelta
from itertools import count
from odoo.http import route,request
from ...restapi.controllers.helper import *
import json


class Equip3HumanResourceExpense(RestApi):
    @route('/api/employee/expense/cycle',auth='user',type='http', methods=['get'])
    @authenticate
    def get_expense_cycle(self,**kw):
        obj = 'hr.expense.cycle'
        domain = []
        if kw.get("search"):
            domain.append(('name', 'ilike', kw.get("search")))
        data_count = request.env[obj].with_context({'from_api': True}).search_count(domain)
        limit = int(kw.get('limit')) if 'limit' in kw else False
        offset = self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1, limit=limit)
        request_param = {"fields": ['name','start_date','end_date','start_period_based_on'],
                         "offset": offset,
                         "domain": domain,
                         "limit": PAGE_DATA_LIMIT if not limit else limit,
                         "order": "id asc",
                         "context":{'from_api':True}
                         }
        try:
            read_record = self.perform_request(obj, id=None, kwargs=request_param, user=request.env.user)
            response_data = json.loads(read_record.data)
        except json.decoder.JSONDecodeError:
            return self.get_response(500, '500', 
                                     {"code": 500,
                                      "meesage": read_record.data
                                      })
        page_total = self.get_total_page(data_count, PAGE_DATA_LIMIT if not limit else limit)
        return self.get_response(200, '200', {
            "code": 200,
            "data": response_data[obj] if obj in response_data and response_data else [],
            "page_total": page_total if page_total else 0
        })
    
    
    @route('/api/employee/expense/cycle/<int:id>',auth='user',type='http', methods=['get'])
    @authenticate
    def get_expense_cycle_by_id(self,id,**kw):
        obj = 'hr.expense.cycle'
        request_param = {"fields": ['name','start_date','end_date','start_period_based_on','year_ids'],
                         "context":{'from_api':True}
                         }
        try:
            read_record = self.perform_request(obj, id=id, kwargs=request_param, user=request.env.user)
            response_data = json.loads(read_record.data)
            if 'year_ids' in response_data[obj]:
                response_data[obj]['year_ids'] = self.convert_one2many('hr.expense.cycle.line',{"fields":['year',
                                                                                                          'month',
                                                                                                          'code',
                                                                                                          'cycle_start',
                                                                                                          'cycle_end',
                                                                                                          'reimbursement_date',
                                                                                                          ],
                                                                                                                        "ids":','.join(str(data) for data in response_data[obj]['year_ids'])},request.env.user)
        except json.decoder.JSONDecodeError:
            return self.get_response(500, '500', 
                                     {"code": 500,
                                      "meesage": read_record.data
                                      })

        return self.get_response(200, '200', {
            "code": 200,
            "data": response_data[obj] if obj in response_data and response_data else [],
        })
    
    
    @route(['/api/employee/get_travel_expense'],auth='user', type='http', methods=['get'])
    def get_employee_travel_expense(self,id=None,**kw):
        offset =  self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1)
        obj = 'travel.request'
        auth, user, invalid = self.valid_authentication(kw)
        domain = [('state','=','returned'),('employee_id','=',request.env.user.employee_id.id)]
        if kw.get("search"):
            domain.append(('name','ilike',kw.get("search")))
        data_ids = request.env[obj].sudo().search(domain)
        if not data_ids:
            return self.record_not_found()
        
        if not user or invalid:
            return self.get_response(401, str(401), {'code': 401, 'message': 'Authentication required'})
        
        request_param = {"ids":','.join(str(data.id) for data in data_ids),
                         "fields":['name'],
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
        
    @route(['/api/employee/get_cash_advance_expense'],auth='user', type='http', methods=['get'])
    def get_employee_cash_advance_expense(self,id=None,**kw):
        offset =  self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1)
        obj = 'vendor.deposit'
        auth, user, invalid = self.valid_authentication(kw)
        domain = [('state','=','post'),('employee_id','=',request.env.user.employee_id.id),('is_cash_advance','=',True)]
        if kw.get("search"):
            domain.append(('name','ilike',kw.get("search")))
        data_ids = request.env[obj].sudo().search(domain)
        if not data_ids:
            return self.record_not_found()
        
        if not user or invalid:
            return self.get_response(401, str(401), {'code': 401, 'message': 'Authentication required'})
        
        request_param = {"ids":','.join(str(data.id) for data in data_ids),
                         "fields":['name','amount'],
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
    
    
    @route(['/api/employee/my_expense_line'],auth='user', type='http', methods=['get'])
    def get_employee_expense_line(self,id=None,**kw):
        offset =  self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1)
        obj = 'hr.expense'
        auth, user, invalid = self.valid_authentication(kw)
        data_ids = request.env[obj].sudo().search([('state','=','draft'),('employee_id','=',request.env.user.employee_id.id),('company_id','=',request.env.user.company_id.id)])
        if not data_ids:
            return self.record_not_found()
        if not user or invalid:
            return self.get_response(401, str(401), {'code': 401, 'message': 'Authentication required'})
        
        request_param = {"ids":','.join(str(data.id) for data in data_ids),"fields":['date',
                                    'name',
                                    'analytic_account_id',
                                    'tax_ids',
                                    'total_amount',
                                    'total_amount_company',
                                    ],
                         "offset":offset,
                         "limit":PAGE_DATA_LIMIT 
                         }
        read_record = self.perform_request(obj,id=id, kwargs=request_param, user=user)
        response_data = json.loads(read_record.data)
        if not obj in response_data:
            return self.record_not_found()
        
        if 'tax_ids' in response_data[obj]:
            if len(response_data[obj]['tax_ids']) >= 1:
                response_data[obj]['tax_ids'] = self.convert_one2many('account.tax',{"fields":['name'],
                                                                                     "ids":','.join(str(data) for data in response_data[obj]['tax_ids'])},user)
        
        page_total  = self.get_total_page(len(data_ids),PAGE_DATA_LIMIT)
        return self.get_response(200, '200', {"code":200,
                                              "data":response_data[obj],
                                              "page_total":page_total if not id else 0
                                              })
    
    @route('/api/employee/create/my_expense',auth='user', type='json', methods=['POST'])
    def create_my_expense(self,**kw):
        request_data = request.jsonrequest
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401), {'code': 401, 'message': 'Authentication required'})
        data_create = request.env['hr.expense.sheet'].sudo().create({
                                'name':request_data.get('name'),
                                 'employee_id': request.env.user.employee_id.id,
                                 'user_id': request_data.get('user_id'),
                                 'travel_id': request_data.get('travel_id'),
                                 'expense_advance': request_data.get('is_expense_advance'),
                                 })

        data_line_ids = []
        if 'expense_line_ids' in request_data:
            for line in request_data.get('expense_line_ids'):
                data_line_ids.append(line['expense_id'])
            data_create.expense_line_ids = [(6,0,data_line_ids)]
        cash_advance_number_ids = []
        if 'cash_advance_number_ids' in request_data:
            for line in request_data.get('cash_advance_number_ids'):
                data_line_ids.append(line)
            data_create.cash_advance_number_ids = [(6,0,cash_advance_number_ids)]
        data_create.onchange_approver_user()
        if request_data.get("state") == "submit":
            data_create.action_submit_sheet()
        if not data_create:
            return self.update_create_failed()
        return self.get_response(200, '200', {"code":200, 
                                              "message":"Create My Expense Suscessfull"
                                              })
        
    @route('/api/employee/update/my_expense/<int:id>',auth='user', type='json', methods=['PUT'])
    def update_my_expense(self,id=None,**kw):
        request_data = request.jsonrequest
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401), {'code': 401, 'message': 'Authentication required'})
        data_update = request.env['hr.expense.sheet'].sudo().search([('id','=',id)])
        data_update.write({
                                'name':request_data.get('name'),
                                 'employee_id': request.env.user.employee_id.id,
                                 'user_id': request_data.get('user_id'),
                                 'travel_id': request_data.get('travel_id'),
                                 'expense_advance': request_data.get('is_expense_advance'),
                                 })

        data_line_ids = []
        if 'expense_line_ids' in request_data:
            for line in request_data.get('expense_line_ids'):
                data_line_ids.append(line['expense_id'])
            data_update.expense_line_ids = [(6,0,data_line_ids)]
            
        cash_advance_number_ids = []
        if 'cash_advance_number_ids' in request_data:
            for line in request_data.get('cash_advance_number_ids'):
                data_line_ids.append(line)
            data_update.cash_advance_number_ids = [(6,0,cash_advance_number_ids)]
            
        data_update.onchange_approver_user()
        if kw.get("state") == "submitted":
            data_update.action_submit_sheet()
            
        if not data_update:
            return self.update_create_failed()
        
        return self.get_response(200, '200', {"code":200, 
                                              "message":"Upate My Expense Suscessfull"
                                              })

    @route(['/api/employee/my_expense','/api/employee/my_expense/<int:id>'],auth='user', type='http', methods=['get'])
    def get_my_expense_advance(self,id=None,**kw):
        offset =  self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1)
        obj = 'hr.expense.sheet'
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        filter_str = f"lambda line:line.employee_id.id == {request.env.user.employee_id.id}"
        if kw.get("state"):
            state_ids = kw.get("state")
            filter_str = filter_str + f" and line.state in {state_ids}"
        date_from = kw.get("date_from")
        if kw.get("date_from"):
            date_from = datetime.strptime(str(kw.get('date_from')),"%Y-%m-%d") 
            filter_str = filter_str + f" and line.reimbursement_date  >= date_from.date()"

        date_to = kw.get("date_to")
        if kw.get("date_to"):
            date_to = datetime.strptime(str(kw.get('date_to')),"%Y-%m-%d") 
            filter_str = filter_str + f" and line.reimbursement_date <= date_to.date()"
            
        if kw.get("is_last_7"):
            query = """
            select data.id from hr_expense_sheet data WHERE data.reimbursement_date  >= current_date - interval '7' day and data.reimbursement_date  <= current_date  and data.employee_id = %s 
            """
            request._cr.execute(query, [request.env.user.employee_id.id])
            data_result_ids = request.env.cr.dictfetchall()
            ids = []
            if len(data_result_ids) > 0:
                ids = [id['id'] for id in data_result_ids]
            filter_str = filter_str + f" and line.id in {ids}"
        if kw.get("is_last_30"):
            query = """
                select data.id from hr_expense_sheet data WHERE data.reimbursement_date  >= current_date - interval '30' day and data.reimbursement_date  <= current_date and data.employee_id = %s      
                """
            request._cr.execute(query, [request.env.user.employee_id.id])
            data_result_ids = request.env.cr.dictfetchall()
            ids = []
            if len(data_result_ids) > 0:
                ids = [id['id'] for id in data_result_ids]
            filter_str = filter_str + f" and line.id in {ids}"
        domain = []
        if date_to or date_from or kw.get("is_last_30") or kw.get("is_last_7"):
            domain.append(("reimbursement_date","!=",False))
        if kw.get("search"):
            domain.append(("seq_name","ilike",kw.get("search")))
        data_ids = request.env[obj].sudo().search(domain).filtered(eval(filter_str,{'kw':kw,'date_from':date_from,'date_to':date_to}))
        if not data_ids:
            return self.record_not_found()
        request_param = {"fields":['state',
                                    'seq_name',
                                    'name',
                                    'company_id',
                                    'employee_id',
                                    'user_id',
                                    'expense_advance',
                                    'travel_id',
                                    'expense_cycle',
                                    'reimbursement_date',
                                    'journal_id',
                                    'total_amount',
                                    'accounting_date',
                                    'account_move_id',
                                    'create_date',
                                    'create_uid',
                                    'expense_line_ids',
                                    'cash_advance_number_ids',
                                    'cash_advance_amount',
                                    'expense_approver_user_ids'
                                    ]}
        if not id:
            request_param = {"ids":','.join(str(data.id) for data in data_ids),"fields":['seq_name',
                                                                                         'state',
                                                                                         'employee_id',
                                                                                         'accounting_date',
                                                                                         'name',
                                                                                         'total_amount',
                                                                                         ],
                             "order":"id desc",
                             "offset":offset,
                             "limit":PAGE_DATA_LIMIT
                             }
            
        read_record = self.perform_request(obj,id=id, kwargs=request_param, user=user)
        response_data = json.loads(read_record.data)
        if 'expense_line_ids' in response_data[obj]:
            if len(response_data[obj]['expense_line_ids']) >= 1:
                response_data[obj]['expense_line_ids'] = self.convert_one2many('hr.expense',{"fields":['date',
                                                                                                       'name',
                                                                                                       'cycle_code_id',
                                                                                                       'product_id',
                                                                                                       'analytic_account_id',
                                                                                                       'tax_ids',
                                                                                                       'total_amount',
                                                                                                       'total_amount_company',
                                                                                                                ],
                                                                                                       "ids":','.join(str(data) for data in response_data[obj]['expense_line_ids'])},user)
                for data in response_data[obj]['expense_line_ids']:
                    data['attatchment'] = self.get_attatchment('hr.expense',data['id'])
                    if 'tax_ids' in data:
                        if len(data['tax_ids']) >= 1:
                            data['tax_ids'] = self.convert_one2many('account.tax',{"fields":['name'],
                                                                                                "ids":','.join(str(data) for data in data['tax_ids'])},user)
        if 'cash_advance_number_ids' in response_data[obj]:
            if len(response_data[obj]['cash_advance_number_ids']) >= 1:
                response_data[obj]['cash_advance_number_ids'] = self.convert_one2many('vendor.deposit',{"fields":['name'],
                                                                                             "ids":','.join(str(data) for data in response_data[obj]['cash_advance_number_ids'])},user)
            
        if 'expense_approver_user_ids' in response_data[obj]:
            if len(response_data[obj]['expense_approver_user_ids']) >= 1:
                response_data[obj]['expense_approver_user_ids'] = self.convert_one2many('expense.approver.user',{"fields":['user_ids',
                                                                                                                             'approver_state',
                                                                                                                             'minimum_approver',
                                                                                                                             'approved_time',
                                                                                                                             'feedback'
                                                                                                                             ],
                                                                                                       "ids":','.join(str(data) for data in response_data[obj]['expense_approver_user_ids'])},user)
                
                for data_to_convert in response_data[obj]['expense_approver_user_ids']:
                    if len(data_to_convert['user_ids'])>=1:
                        data_to_convert['user_ids'] = self.convert_one2many('res.users',{"fields":['name'],
                                                                                        "ids":','.join(str(data) for data in data_to_convert['user_ids'])},user)
        
        if not obj in response_data:
            return self.record_not_found()
        
        page_total  = self.get_total_page(len(data_ids),PAGE_DATA_LIMIT)
        return self.get_response(200, '200', {"code":200,
                                              "data":response_data[obj],
                                              "page_total":page_total if not id else 0
                                              })