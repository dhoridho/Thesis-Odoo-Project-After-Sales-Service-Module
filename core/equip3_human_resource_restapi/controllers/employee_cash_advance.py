from datetime import datetime, timedelta
from itertools import count
from odoo.http import route,request
import json
from ...restapi.controllers.helper import *


class Equip3HumanResourceRestAPICashAdvance(RestApi):
    @route('/api/employee/cancel/cash_advance/<int:id>',auth='user', type='json', methods=['PUT'])
    def cancel_cash_advance(self,id=None,**kw):
        request_data = request.jsonrequest
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        data_update = request.env['vendor.deposit'].sudo().search([('id','=',id)])
        if not data_update:
            return self.record_not_found()
        data_update.action_cancel_cash_advance()
        return self.get_response(200, '200', {"code":200, 
                                              "message":"Cancel My Cash Advance Suscessfull"
                                              })
        
    
    @route('/api/employee/cash_advance/cycle',auth='user',type='http', methods=['get'])
    @authenticate
    def get_cash_advance_cycle(self,**kw):
        obj = 'hr.cash.advance.cycle'
        domain = []
        if kw.get("search"):
            domain.append(('hr_year_id.name', 'ilike', kw.get("search")))
        data_count = request.env[obj].with_context({'from_api': True}).search_count(domain)
        limit = int(kw.get('limit')) if 'limit' in kw else False
        offset = self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1, limit=limit)
        request_param = {"fields": ['hr_year_id','limit_type'],
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
        
        
    @route('/api/employee/cash_advance/cycle/<int:id>',auth='user',type='http', methods=['get'])
    @authenticate
    def get_cash_advance_cycle_by_id(self,id,**kw):
        obj = 'hr.cash.advance.cycle'
        request_param = {"fields": ['hr_year_id','limit_type','cash_advance_cycle_line_ids'],
                         "context":{'from_api':True}
                         }
        try:
            read_record = self.perform_request(obj, id=id, kwargs=request_param, user=request.env.user)
            response_data = json.loads(read_record.data)
            if 'cash_advance_cycle_line_ids' in response_data[obj]:
                response_data[obj]['cash_advance_cycle_line_ids'] = self.convert_one2many('hr.cash.advance.cycle.line',{"fields":['code',
                                                                                                                                  'cycle_start',
                                                                                                                                  'cycle_end'
                                                                                                                                  ],
                                                                                                                        "ids":','.join(str(data) for data in response_data[obj]['cash_advance_cycle_line_ids'])},request.env.user)
        except json.decoder.JSONDecodeError:
            return self.get_response(500, '500', 
                                     {"code": 500,
                                      "meesage": read_record.data
                                      })

        return self.get_response(200, '200', {
            "code": 200,
            "data": response_data[obj] if obj in response_data and response_data else [],
        })

    
    @route('/api/employee/create/cash_advance/',auth='user', type='json', methods=['POST'])
    def create_cash_advance(self,**kw):
        company = request.env.company
        request_data = request.jsonrequest
        auth, user, invalid = self.valid_authentication(kw)
        advance_date  = datetime.strptime(str(request_data.get('advance_date')),"%Y-%m-%d")
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        data_create = request.env['vendor.deposit'].sudo().create({
                                 'communication':request_data.get('communication'),
                                 'cycle_code_id':request_data.get('cycle_code_id'),
                                 "employee_id":request.env.user.employee_id.id,
                                 'amount':request_data.get('amount'),
                                 'remaining_amount':request_data.get('remaining_amount'),
                                 'travel_id':request_data.get('travel_id'),
                                 'branch_id':request_data.get('branch_id'),
                                 'advance_date':advance_date,
                                 'currency_id':request_data.get('currency_id'),
                                 'employee_partner_id':request_data.get('employee_partner_id'),
                                 'deposit_reconcile_journal_id': company.deposit_reconcile_journal_id.id,
                                'deposit_account_id': company.deposit_account_id.id,
                                'journal_id': company.journal_id.id,
                                'is_cash_advance':True
                                 })
        advance_line_ids = []
        if 'advance_line_ids' in request_data:
            for data in request_data['advance_line_ids']:
                advance_line_ids.append((0,0,{'name':data['name'],'amount':data['amount']}))
        data_create.advance_line_ids = advance_line_ids
        data_create.onchange_approver_user()
        if request_data.get("state")  == "confirmed":
            data_create.action_confirm()
        # add new logic to send email notif
        # if not data_create:
        #     return self.update_create_failed()   
        # return self.get_response(200, '200', {"code":200, 
        #                                       "message":"Create My Cash Advance Suscessfull"
        #                                       })
    
        if data_create:
            data_create.approver_mail()
            return self.get_response(200, '200', {"code":200,
                                                    "message":"Create My Cash Advance Successfully"
            })
        return self.update_create_failed()
        
    @route('/api/employee/update/cash_advance/<int:id>',auth='user', type='json', methods=['PUT'])
    def update_cash_advance(self,id=None,**kw):
        request_data = request.jsonrequest
        auth, user, invalid = self.valid_authentication(kw)
        advance_date  = datetime.strptime(str(request_data.get('advance_date')),"%Y-%m-%d")
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        data_update = request.env['vendor.deposit'].sudo().search([('id','=',id)])
        if not data_update:
            return self.record_not_found()
        data_update.write({ 'communication':request_data.get('communication'),
                           "employee_id":request.env.user.employee_id.id,
                           'travel_id':request_data.get('travel_id'),
                           'branch_id':request_data.get('branch_id'),
                           'currency_id':request_data.get('currency_id'),
                           'employee_partner_id':request_data.get('employee_partner_id'),
                           'advance_date':advance_date
                           })
        result = self.update_one2many([('vendor_advance_line_id','=',data_update.id)],'cash.advance.details',request_data.get('advance_line_ids'))
        if result:
            data_update.advance_line_ids = result
        data_update.onchange_approver_user()
        if request_data.get("state")  == "confirmed":
            data_update.action_confirm()
        if not data_update:
            return self.update_create_failed()   
        return self.get_response(200, '200', {"code":200, 
                                              "message":"Update My Cash Advance Suscessfull"
                                              })
    
    @route(['/api/employee/cash_advance','/api/employee/cash_advance/<int:id>'],auth='user', type='http', methods=['get'])
    def get_employee_cash_advance(self,id=None,**kw):
        offset =  self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1)
        obj = 'vendor.deposit'
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        
        filter_str = f"lambda line:line.is_cash_advance == {True} and line.employee_id.id == {request.env.user.employee_id.id}"
        if kw.get("state"):
            state_ids = kw.get("state")
            filter_str = filter_str + f" and line.state in {state_ids}"
            
        date_from = kw.get("date_from")
        if kw.get("date_from"):
            date_from = datetime.strptime(str(kw.get('date_from')),"%Y-%m-%d") 
            filter_str = filter_str + f" and line.advance_date  >= date_from.date()"

        date_to = kw.get("date_to")
        if kw.get("date_to"):
            date_to = datetime.strptime(str(kw.get('date_to')),"%Y-%m-%d") 
            filter_str = filter_str + f" and line.advance_date <= date_to.date()"
            
        if kw.get("is_last_7"):
            query = """
            select data.id from vendor_deposit data WHERE data.advance_date  >= current_date - interval '7' day and data.advance_date  <= current_date  and data.employee_id = %s AND is_cash_advance IS TRUE
            """
            request._cr.execute(query, [request.env.user.employee_id.id])
            data_result_ids = request.env.cr.dictfetchall()
            ids = []
            if len(data_result_ids) > 0:
                ids = [id['id'] for id in data_result_ids]
            filter_str = filter_str + f" and line.id in {ids}"
        if kw.get("is_last_30"):
            query = """
                select data.id from vendor_deposit data WHERE data.advance_date  >= current_date - interval '30' day and data.advance_date  <= current_date and data.employee_id = %s  AND is_cash_advance IS TRUE      
                """
            request._cr.execute(query, [request.env.user.employee_id.id])
            data_result_ids = request.env.cr.dictfetchall()
            ids = []
            if len(data_result_ids) > 0:
                ids = [id['id'] for id in data_result_ids]
            filter_str = filter_str + f" and line.id in {ids}"
        domain = []
        if kw.get("search"):
            domain.append("|")
            domain.append(("name","ilike",kw.get("search")))
            domain.append(("communication","ilike",kw.get("search")))
        data_ids = request.env[obj].sudo().search(domain).filtered(eval(filter_str,{'kw':kw,
                                                                                                                    'date_from':date_from,
                                                                                                                    'date_to':date_to}))
        if not data_ids:
            return self.record_not_found()
        request_param = {"fields":['state',
                                    'name',
                                    'communication',
                                    'employee_id',
                                    'advance_date',
                                    'amount',
                                    'remaining_amount',
                                    'travel_id',
                                    'company_id',
                                    'branch_id',
                                    'create_date',
                                    'create_uid',
                                    'advance_line_ids',
                                    'employee_partner_id',
                                    'currency_id',
                                    'cash_approver_user_ids'
                                    ]}
        if not id:
            request_param = {"ids":','.join(str(data.id) for data in data_ids),"fields":['name',
                                                                                         'advance_date',
                                                                                         'state'
                                                                                         ],
                             "order":"id desc",
                             "offset":offset,
                             "limit":PAGE_DATA_LIMIT
                             }
            
        read_record = self.perform_request(obj,id=id, kwargs=request_param, user=user)
        response_data = json.loads(read_record.data)
        if 'advance_line_ids' in response_data[obj]:
            if len(response_data[obj]['advance_line_ids']) >= 1:
                response_data[obj]['advance_line_ids'] = self.convert_one2many('cash.advance.details',{"fields":['name',
                                                                                                                 'amount'
                                                                                                                ],
                                                                                                       "ids":','.join(str(data) for data in response_data[obj]['advance_line_ids'])},user)
        if 'cash_approver_user_ids' in response_data[obj]:
            if len(response_data[obj]['cash_approver_user_ids']) >= 1:
                response_data[obj]['cash_approver_user_ids'] = self.convert_one2many('cash.advance.approver.user',{"fields":['user_ids',
                                                                                                                             'approver_state',
                                                                                                                             'minimum_approver',
                                                                                                                             'approved_time',
                                                                                                                             'feedback'
                                                                                                                             ],
                                                                                                       "ids":','.join(str(data) for data in response_data[obj]['cash_approver_user_ids'])},user)
                for data_to_convert in response_data[obj]['cash_approver_user_ids']:
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
        
        
        
    @route(['/api/employee/cash_advance/travel'],auth='user', type='http', methods=['get'])
    def get_cash_advance_travel(self,id=None,**kw):
        offset =  self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1)
        obj = 'travel.request'
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        domain = [('employee_id','=',request.env.user.employee_id.id),'|',('cash_advance_orgin_id','=',False),('cash_advance_state','=','draft')]
        if kw.get("search"):
            domain.append(('name','ilike',kw.get("search")))
                   
        data_ids = request.env[obj].sudo().search(domain)
        if not data_ids:
            return self.record_not_found()
        
        request_param = {"ids":','.join(str(data.id) for data in data_ids),"fields":['name','travel_purpose'],
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
    
    
    @route(['/api/employee/cash_advance/branch'],auth='user', type='http', methods=['get'])
    def get_cash_advance_branch(self,id=None,**kw):
        offset =  self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1)
        obj = 'res.branch'
        user = request.env.user
        branch_ids = user.branch_ids + user.branch_id
        domain = [('id','in',branch_ids.ids)]
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        
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
        page_total  = self.get_total_page(len(data_ids),PAGE_DATA_LIMIT)
        return self.get_response(200, '200', {"code":200,
                                              "data":response_data[obj],
                                              "page_total":page_total if not id else 0
                                              })
        
    @route(['/api/employee/cash_advance/partner'],auth='user', type='http', methods=['get'])
    def get_cash_advance_partnerl(self,id=None,**kw):
        offset =  self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1)
        obj = 'res.partner'
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        domain = ['|',('company_id','=',False),('company_id','=',request.env.user.company_id.id)]
        if kw.get("search"):
            domain.append('|')
            domain.append(('name','ilike',kw.get("search")))
            domain.append(('parent_id.name','ilike',kw.get("search")))
                   
        data_ids = request.env[obj].sudo().search(domain)
        if not data_ids:
            return self.record_not_found()
        
        request_param = {"ids":','.join(str(data.id) for data in data_ids),"fields":['name','parent_id'],
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
        
