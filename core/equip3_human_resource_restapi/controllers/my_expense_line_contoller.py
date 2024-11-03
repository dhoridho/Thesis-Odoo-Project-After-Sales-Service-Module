from datetime import datetime, timedelta
from itertools import count
from odoo.http import route,request
from ...restapi.controllers.helper import *
import json


class Equip3HumanResourceExpenseLine(RestApi):
    @route(['/api/employee/my_expense_line_list','/api/employee/my_expense_line_list/<int:id>'],auth='user', type='http', methods=['get'])
    def get_my_expense_line_list(self,id=None,**kw):
        offset =  self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1)
        obj = 'hr.expense'
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
            filter_str = filter_str + f" and line.date  >= date_from.date()"

        date_to = kw.get("date_to")
        if kw.get("date_to"):
            date_to = datetime.strptime(str(kw.get('date_to')),"%Y-%m-%d") 
            filter_str = filter_str + f" and line.date <= date_to.date()"
            
        if kw.get("is_last_7"):
            query = """
            select data.id from hr_expense data WHERE data.date  >= current_date - interval '7' day and data.date  <= current_date  and data.employee_id = %s 
            """
            request._cr.execute(query, [request.env.user.employee_id.id])
            data_result_ids = request.env.cr.dictfetchall()
            ids = []
            if len(data_result_ids) > 0:
                ids = [id['id'] for id in data_result_ids]
            filter_str = filter_str + f" and line.id in {ids}"
        if kw.get("is_last_30"):
            query = """
                select data.id from hr_expense data WHERE data.date  >= current_date - interval '30' day and data.date  <= current_date and data.employee_id = %s      
                """
            request._cr.execute(query, [request.env.user.employee_id.id])
            data_result_ids = request.env.cr.dictfetchall()
            ids = []
            if len(data_result_ids) > 0:
                ids = [id['id'] for id in data_result_ids]
            filter_str = filter_str + f" and line.id in {ids}"
        domain = []
        if date_to or date_from or kw.get("is_last_30") or kw.get("is_last_7"): 
            domain.append(("date","!=",False))
        if kw.get("search"):
            domain.append("|")
            domain.append(("name","ilike",kw.get("search")))
            domain.append(("product_id.name","ilike",kw.get("search")))
        data_ids = request.env[obj].sudo().search(domain).filtered(eval(filter_str,{'kw':kw,'date_from':date_from,'date_to':date_to}))
        if not data_ids:
            return self.record_not_found()
        request_param = {"fields":['state',
                                    'name',
                                    'company_id',
                                    'employee_id',
                                    'product_id',
                                    'unit_amount',
                                    'quantity',
                                    'tax_ids',
                                    'total_amount',
                                    'amount_residual',
                                    'reference',
                                    'date',
                                    'account_id',
                                    'currency_id',
                                    'analytic_account_id',
                                    'analytic_tag_ids',
                                    'description',
                                    'sale_order_id',
                                    'sheet_id'
                                    ]}
        if not id:
            request_param = {"ids":','.join(str(data.id) for data in data_ids),"fields":['name',
                                                                                         'total_amount',
                                                                                         'date',
                                                                                         'state',
                                                                                         'sheet_id'
                                                                                         ],
                             "order":"id desc",
                             "offset":offset,
                             "limit":PAGE_DATA_LIMIT
                             }
            
        read_record = self.perform_request(obj,id=id, kwargs=request_param, user=user)
        response_data = json.loads(read_record.data)
        if 'id' in response_data[obj]:
             response_data[obj]['attatchment'] = self.get_attatchment('hr.expense',response_data[obj]['id'])
        if not obj in response_data:
            return self.record_not_found()   
         
        if 'tax_ids' in response_data[obj]:
            if len(response_data[obj]['tax_ids']) >= 1:
                response_data[obj]['tax_ids'] = self.convert_one2many('account.tax',{"fields":['name'],
                                                                                     "ids":','.join(str(data) for data in response_data[obj]['tax_ids'])},user)
        if 'analytic_tag_ids' in response_data[obj]:
            if len(response_data[obj]['analytic_tag_ids']) >= 1:
                response_data[obj]['analytic_tag_ids'] = self.convert_one2many('account.analytic.tag',{"fields":['name'],
                                                                                     "ids":','.join(str(data) for data in response_data[obj]['analytic_tag_ids'])},user)
        page_total  = self.get_total_page(len(data_ids),PAGE_DATA_LIMIT)
        return self.get_response(200, '200', {"code":200,
                                              "data":response_data[obj],
                                              "page_total":page_total if not id else 0
                                              })

    @route('/api/employee/update/my_expense_line/<int:id>',auth='user', type='json', methods=['PUT'])
    def update_my_expense_line(self,id=None,**kw):
        request_data = request.jsonrequest
        auth, user, invalid = self.valid_authentication(kw)
        date = request_data.get("date")
        if kw.get("date"):
            date = datetime.strptime(str(request_data.get('date')),"%Y-%m-%d") 
        if not user or invalid:
            return self.get_response(401, str(401), {'code': 401, 'message': 'Authentication required'})
        data_update= request.env['hr.expense'].sudo().search([('id','=',id)])
        if not data_update:
            return self.record_not_found()
        data_update.write({
                                'name':request_data.get('name'),
                                 'employee_id': request.env.user.employee_id.id,
                                 'product_id': request_data.get('product_id'),
                                 'product_uom_id': request_data.get('product_uom_id'),
                                 'sale_order_id': request_data.get('sale_order_id'),
                                 'unit_amount': request_data.get('unit_amount'),
                                 'quantity': request_data.get('quantity'),
                                #  'amount_residual': request_data.get('amount_residual'),
                                 'reference': request_data.get('reference'),
                                 'account_id': request_data.get('account_id'),
                                 'currency_id': request_data.get('currency_id'),
                                 'analytic_account_id': request_data.get('analytic_account_id'),
                                 'date': date,
                                 "description":request_data.get('description')
                                 
                                 })

        analytic_tag_ids = []
        if 'analytic_tag_ids' in request_data:
            for line in request_data.get('analytic_tag_ids'):
                analytic_tag_ids.append(line)
            data_update.analytic_tag_ids = [(6,0,analytic_tag_ids)]
        
        tax_ids = []
        if 'tax_ids' in request_data:
            for line in request_data.get('tax_ids'):
                tax_ids.append(line)
            data_update.tax_ids = [(6,0,tax_ids)]

        if not data_update:
            return self.update_create_failed()
        if request_data.get("state") == 'reported':
            data_update.action_submit_expenses()
            
        return self.get_response(200, '200', {"code":200,
                                              "id":data_update.id ,
                                              "message":"Create My Expense  Line Suscessfull"
                                              })
    
    @route('/api/employee/create/my_expense_line',auth='user', type='json', methods=['POST'])
    def create_my_expense_line(self,**kw):
        request_data = request.jsonrequest
        auth, user, invalid = self.valid_authentication(kw)
        date = request_data.get("date")
        if kw.get("date"):
            date = datetime.strptime(str(request_data.get('date')),"%Y-%m-%d") 
        if not user or invalid:
            return self.get_response(401, str(401), {'code': 401, 'message': 'Authentication required'})
        data_create = request.env['hr.expense'].sudo().create({
                                'name':request_data.get('name'),
                                 'employee_id': request.env.user.employee_id.id,
                                'cycle_code_id':request_data.get('cycle_code_id'),
                                 'product_id': request_data.get('product_id'),
                                 'product_uom_id': request_data.get('product_uom_id'),
                                 'sale_order_id': request_data.get('sale_order_id'),
                                 'unit_amount': request_data.get('unit_amount'),
                                 'quantity': request_data.get('quantity'),
                                #  'amount_residual': request_data.get('amount_residual'),
                                 'reference': request_data.get('reference'),
                                 'account_id': request_data.get('account_id'),
                                #  'currency_id': request_data.get('currency_id'),
                                 'analytic_account_id': request_data.get('analytic_account_id'),
                                 'date': date,
                                 "description":request_data.get('description')
                                 
                                 })

        analytic_tag_ids = []
        if 'analytic_tag_ids' in request_data:
            for line in request_data.get('analytic_tag_ids'):
                analytic_tag_ids.append(line)
            data_create.analytic_tag_ids = [(6,0,analytic_tag_ids)]
        
        tax_ids = []
        if 'tax_ids' in request_data:
            for line in request_data.get('tax_ids'):
                tax_ids.append(line)
            data_create.tax_ids = [(6,0,tax_ids)]
        

        if not data_create:
            return self.update_create_failed()
        
        if request_data.get("state") == 'reported':
            data_create.action_submit_expenses()
            
        return self.get_response(200, '200', {"code":200, 
                                              "id":data_create.id,
                                              "message":"Create My Expense  Line Suscessfull"
                                              })
        
        
    @route(['/api/employee/my_expense_line_product'],auth='user', type='http', methods=['get'])
    @authenticate
    def get_my_expense_line_product(self,id=None,**kw):
        offset =  self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1)
        obj = 'product.product'
        allowed_product = []
        if request.env.user.employee_id.employee_expense_line:
            for line in request.env.user.employee_id.employee_expense_line:
                allowed_product.append(line.product_id.id)
        domain = [('id','in',allowed_product)]
        if kw.get("search"):
            domain.append(('name','ilike',kw.get("search")))
            
        data_ids = request.env[obj].sudo().search(domain)
        if not data_ids:
            return self.record_not_found()
        
        request_param = {"ids":','.join(str(data.id) for data in data_ids),"fields":['name',
                                                                                     'lst_price',
                                                                                     'standard_price',
                                                                                     'expense_policy',
                                                                                     'uom_id',
                                                                                     'uom_po_id'
                                                                                         ],
                             "order":"name asc",
                             "offset":offset,
                             "limit":PAGE_DATA_LIMIT
                             }
            
        read_record = self.perform_request(obj,id=id, kwargs=request_param, user=request.env.user)
        response_data = json.loads(read_record.data)
        if not obj in response_data:
            return self.record_not_found()
        page_total  = self.get_total_page(len(data_ids),PAGE_DATA_LIMIT)
        return self.get_response(200, '200', {"code":200,
                                              "data":response_data[obj],
                                              "page_total":page_total if not id else 0
                                              })
        
        
    @route(['/api/employee/my_expense_account'],auth='user', type='http', methods=['get'])
    def get_my_expense_account(self,id=None,**kw):
        offset =  self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1)
        obj = 'account.account'
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        domain = [('internal_type','=','other'),('company_id','=',request.env.user.company_id.id)]
        if kw.get("search"):
            domain.append('|')
            domain.append(('code','ilike',kw.get("search")))
            domain.append(('name','ilike',kw.get("search")))
            
        data_ids = request.env[obj].sudo().search(domain)
        if not data_ids:
            return self.record_not_found()
        
        request_param = {"ids":','.join(str(data.id) for data in data_ids),"fields":['name','code'],
                         "order":"name asc",
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
        
    @route(['/api/employee/my_expense_sale_order'],auth='user', type='http', methods=['get'])
    def get_my_expense_sale_order(self,id=None,**kw):
        offset =  self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1)
        obj = 'sale.order'
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        domain = [('state','=','sale'),('company_id','=',request.env.user.company_id.id)]
        if kw.get("search"):
            domain.append('|')
            domain.append(('name','ilike',kw.get("search")))
            domain.append(('partner_id.name','ilike',kw.get("search")))
            
        data_ids = request.env[obj].sudo().search(domain)
        if not data_ids:
            return self.record_not_found()
        
        request_param = {"ids":','.join(str(data.id) for data in data_ids),"fields":['name','partner_id','analytic_account_id'],
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
        
    @route(['/api/employee/account_analytic_account'],auth='user', type='http', methods=['get'])
    def get_account_analytic_account(self,id=None,**kw):
        offset =  self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1)
        obj = 'account.analytic.account'
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        domain = ['|',('company_id','=',request.env.user.company_id.id),('company_id','=',False)]
        if kw.get("search"):
            domain.append('|')
            domain.append('|')
            domain.append(('code','ilike',kw.get("search")))
            domain.append(('partner_id.name','ilike',kw.get("search")))
            domain.append(('name','ilike',kw.get("search")))
                   
        data_ids = request.env[obj].sudo().search(domain)
        if not data_ids:
            return self.record_not_found()
        
        request_param = {"ids":','.join(str(data.id) for data in data_ids),"fields":['name','partner_id','code'],
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
        
    @route(['/api/employee/account_analytic_tag'],auth='user', type='http', methods=['get'])
    def get_account_analytic_account_tag(self,id=None,**kw):
        offset =  self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1)
        obj = 'account.analytic.tag'
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        domain = ['|',('company_id','=',request.env.user.company_id.id),('company_id','=',False)]
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
        
    @route(['/api/employee/taxes'],auth='user', type='http', methods=['get'])
    def get_taxes(self,id=None,**kw):
        offset =  self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1)
        obj = 'account.tax'
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        domain = [('company_id','=',request.env.user.company_id.id),('type_tax_use','=','purchase')]
        if kw.get("search"):
            domain.append(('name','ilike',kw.get("search")))
        
        data_ids = request.env[obj].sudo().search(domain)
        if not data_ids:
            return self.record_not_found()
        
        request_param = {"ids":','.join(str(data.id) for data in data_ids),"fields":['name','amount','amount_type'],
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
    
    
    @route(['/api/employee/get_expense_line_sum'],auth='user', type='http', methods=['get'])
    def get_expense_line_sum(self,id=None,**kw):
        obj = 'hr.expense'
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        
        to_report = request.env[obj].sudo().search([('employee_id','=',request.env.user.employee_id.id),('state','=','draft')])
        total_to_report = sum([data.total_amount for data in to_report])
        under_validation = request.env[obj].sudo().search([('employee_id','=',request.env.user.employee_id.id),('state','=','reported')])
        total_under_validation = sum([data.total_amount for data in under_validation])
        approved = request.env[obj].sudo().search([('employee_id','=',request.env.user.employee_id.id),('state','=','approved')])
        total_under_approved = sum([data.total_amount for data in approved])
        response = {
            'to_report':total_to_report,
            'under_validation':total_under_validation,
            'approved':total_under_approved
            
            
        }
        return self.get_response(200, '200', {"code":200,
                                              "data":response,
                                              
                                              })
    
        
    