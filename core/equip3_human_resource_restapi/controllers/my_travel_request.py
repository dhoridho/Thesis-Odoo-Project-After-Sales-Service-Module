from datetime import datetime, timedelta
from itertools import count
from odoo.http import route,request
import json
from ...restapi.controllers.helper import *
import pytz


class Equip3HumanResourceMyTravelRequest(RestApi):
    @route('/api/employee/create/my_travel_request',auth='user', type='json', methods=['POST'])
    def create_my_travel_request(self,**kw):
        request_data = request.jsonrequest
        auth, user, invalid = self.valid_authentication(kw)
        
        req_departure_date = False
        if request_data.get('req_departure_date'):
            req_departure_date  = datetime.strptime(str(request_data.get('req_departure_date')),"%Y-%m-%d")
            
        req_return_date = False
        if request_data.get('req_return_date'):
            req_return_date = datetime.strptime(str(request_data.get('req_return_date')),"%Y-%m-%d")
            
        days = False
        if request_data.get('days'):
              days = datetime.strptime(str(request_data.get('days')),"%Y-%m-%d")
              
        available_return_date = False
        if request_data.get('available_return_date'):
              available_return_date = datetime.strptime(str(request_data.get('available_return_date')),"%Y-%m-%d")
              
        available_departure_date = False
        if request_data.get('available_departure_date'):
              available_departure_date = datetime.strptime(str(request_data.get('available_departure_date')),"%Y-%m-%d")
              
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        
        travel_request = request.env['travel.request'].sudo().create({
                                 'employee_id': request.env.user.employee_id.id,
                                 "job_id":request.env.user.employee_id.job_id.id,
                                 "department_id":request.env.user.employee_id.department_id.id,
                                 'currency_id':request_data.get('currency_id'),
                                 'travel_purpose':request_data.get('travel_purpose'),
                                 'project_id':request_data.get('project_id'),
                                 'account_analytic_id':request_data.get('account_analytic_id'),
                                 'from_city':request_data.get('from_city'),
                                 'from_state_id':request_data.get('from_state_id'),
                                 'from_country_id':request_data.get('from_country_id'),
                                 'to_street':request_data.get('to_street'),
                                 'to_street_2':request_data.get('to_street_2'),
                                 'to_city':request_data.get('to_city'),
                                 'to_state_id':request_data.get('to_state_id'),
                                 'to_zip_code':request_data.get('to_zip_code'),
                                 'to_country_id':request_data.get('country_id'),
                                 'req_travel_mode_id':request_data.get('req_travel_mode_id'),
                                 'req_departure_date':req_departure_date,
                                 'req_return_date':req_return_date,
                                 'days':days,
                                 'phone_no':request_data.get('phone_no'),
                                 'email':request_data.get('email'),
                                 'available_departure_date':available_departure_date,
                                 'departure_mode_travel_id':request_data.get('departure_mode_travel_id'),
                                 'visa_agent_id':request_data.get('visa_agent_id'),
                                 'return_mode_travel_id':request_data.get('return_mode_travel_id'),
                                 'ticket_booking_agent_id':request_data.get('ticket_booking_agent_id'),
                                 'bank_id':request_data.get('bank_id'),
                                 'cheque_number':request_data.get('cheque_number'),
                                 'available_return_date':available_return_date,
                                 
                                 })
        cash_advance_ids= []
        if 'cash_advance_ids' in request_data:
            for data in request_data['cash_advance_ids']:
                cash_advance_ids.append((0,0,{'employee_id':request.env.user.employee_id.id,'amount':data['amount'],'name':data['name']}))      
            
        if request_data.get('state') == 'confirmed':
            travel_request.action_confirm()
        travel_request.onchange_employee()
        travel_request.onchange_approver_user()
        travel_request.cash_advance_ids = cash_advance_ids
        if not travel_request:
            return self.update_create_failed()
        travel_request.approver_mail()   
        return self.get_response(200, '200', {"code":200, 
                                              "message":"Create My Travel Suscessfull"
                                              })

    
    @route('/api/employee/update/my_travel_request/<int:id>',auth='user', type='json', methods=['PUT'])
    def update_my_travel_request(self,id=None,**kw):
        request_data = request.jsonrequest
        auth, user, invalid = self.valid_authentication(kw)
        
        req_departure_date = False
        if request_data.get('req_departure_date'):
            req_departure_date  = datetime.strptime(str(request_data.get('req_departure_date')),"%Y-%m-%d")
            
        req_return_date = False
        if request_data.get('req_return_date'):
            req_return_date = datetime.strptime(str(request_data.get('req_return_date')),"%Y-%m-%d")
            
        days = False
        if request_data.get('days'):
              days = datetime.strptime(str(request_data.get('days')),"%Y-%m-%d")
              
        available_return_date = False
        if request_data.get('available_return_date'):
              available_return_date = datetime.strptime(str(request_data.get('available_return_date')),"%Y-%m-%d")
              
        available_departure_date = False
        if request_data.get('available_departure_date'):
              available_departure_date = datetime.strptime(str(request_data.get('available_departure_date')),"%Y-%m-%d")
              
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        
        travel_request = request.env['travel.request'].sudo().search([('id','=',id)])
        
        if not travel_request:
            return self.record_not_found()
        
        travel_request.write({
                                 'employee_id': request.env.user.employee_id.id,
                                 "job_id":request.env.user.employee_id.job_id.id,
                                 "department_id":request.env.user.employee_id.department_id.id,
                                 'currency_id':request_data.get('currency_id'),
                                 'travel_purpose':request_data.get('travel_purpose'),
                                 'project_id':request_data.get('project_id'),
                                 'account_analytic_id':request_data.get('account_analytic_id'),
                                 'from_city':request_data.get('from_city'),
                                 'from_state_id':request_data.get('from_state_id'),
                                 'from_country_id':request_data.get('from_country_id'),
                                 'to_street':request_data.get('to_street'),
                                 'to_street_2':request_data.get('to_street_2'),
                                 'to_city':request_data.get('to_city'),
                                 'to_state_id':request_data.get('to_state_id'),
                                 'to_zip_code':request_data.get('to_zip_code'),
                                 'to_country_id':request_data.get('country_id'),
                                 'req_travel_mode_id':request_data.get('req_travel_mode_id'),
                                 'req_departure_date':req_departure_date,
                                 'req_return_date':req_return_date,
                                 'days':days,
                                 'phone_no':request_data.get('phone_no'),
                                 'email':request_data.get('email'),
                                 'available_departure_date':available_departure_date,
                                 'departure_mode_travel_id':request_data.get('departure_mode_travel_id'),
                                 'visa_agent_id':request_data.get('visa_agent_id'),
                                 'return_mode_travel_id':request_data.get('return_mode_travel_id'),
                                 'ticket_booking_agent_id':request_data.get('ticket_booking_agent_id'),
                                 'bank_id':request_data.get('bank_id'),
                                 'cheque_number':request_data.get('cheque_number'),
                                 'available_return_date':available_return_date,
                                 
                                 })
        
        if 'cash_advance_ids' in request_data:
            result = self.update_one2many([('travel_cash_id','=',travel_request.id)],'travel.vendor.deposit',request_data.get('cash_advance_ids'))
            if result:
                travel_request.cash_advance_ids = result      
            
        if request_data.get('state') == 'confirmed':
            travel_request.action_confirm()
        travel_request.onchange_employee()
        travel_request.onchange_approver_user()
        
        if not travel_request:
            return self.update_create_failed()   
        return self.get_response(200, '200', {"code":200, 
                                              "message":"Update My Travel Suscessfull"
                                              })
    
    
    @route(['/api/employee/my_travel_request/','/api/employee/my_travel_request/<int:id>'],auth='user', type='http', methods=['get'])
    def get_employee_travel_request(self,id=None,**kw):
        now = datetime.now()
        user_tz = request.env.user.employee_id.tz or pytz.utc or 'UTC'
        local = pytz.timezone(user_tz)
        offset_time = local.utcoffset(now, is_dst = False).total_seconds()/3600
        offset =  self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1)
        obj = 'travel.request'
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        filter_str = f"lambda line:line.employee_id.id == {request.env.user.employee_id.id}"
        if kw.get("state"):
            state = kw.get("state")
            filter_str = filter_str + f" and line.state in {state}"
            
        date_from = kw.get("date_from")
        if kw.get("date_from"):
            date_from = datetime.strptime(str(kw.get('date_from')),"%Y-%m-%d") 
            filter_str = filter_str + f" and line.req_departure_date.date()  >= date_from.date()"
            
        date_now = datetime.now() 
        if kw.get("my_travel_cancel"):
            filter_str = filter_str + f" and line.req_departure_date.date()  > date_now.date()"

        date_to = kw.get("date_to")
        if kw.get("date_to"):
            date_to = datetime.strptime(str(kw.get('date_to')),"%Y-%m-%d") 
            filter_str = filter_str + f" and line.req_return_date.date() <= date_to.date()"
            
        if kw.get("is_last_7"):
            query = """
            select data.id from travel_request data WHERE data.req_departure_date::date  >= current_date - interval '7' day and data.req_departure_date  <= current_date  and data.employee_id = %s
            """
            request._cr.execute(query, [request.env.user.employee_id.id])
            data_result_ids = request.env.cr.dictfetchall()
            ids = []
            if len(data_result_ids) > 0:
                ids = [id['id'] for id in data_result_ids]
            filter_str = filter_str + f" and line.id in {ids}"
        if kw.get("is_last_30"):
            query = """
                select data.id from travel_request data WHERE data.req_departure_date::date  >= current_date - interval '30' day and data.req_departure_date  <= current_date and data.employee_id = %s            
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
            domain.append(('name','ilike',kw.get('search')))
            domain.append(('travel_purpose','ilike',kw.get('search')))
        data_ids = request.env[obj].sudo().search(domain).filtered(eval(filter_str,{'kw':kw,
                                                                                                                    'date_from':date_from,
                                                                                                                    'date_to':date_to,
                                                                                                                    'date_now':date_now
                                                                                                                    }))
        if not data_ids:
            return self.record_not_found()
        
        request_param = {"fields":['state',
                                    'name',
                                    'employee_id',
                                    'department_manager_id',
                                    'department_id',
                                    'job_id',
                                    'currency_id',
                                    'expence_sheet_id',
                                    'cash_advance_orgin_id',
                                    'travel_purpose',
                                    'project_id',
                                    'account_analytic_id',
                                    'from_city',
                                    'from_state_id',
                                    'from_country_id',
                                    'to_street',
                                    'to_street_2',
                                    'to_city',
                                    'to_state_id',
                                    'to_zip_code',
                                    'to_country_id',
                                    'req_departure_date',
                                    'req_return_date',
                                    'req_travel_mode_id',
                                    'days',
                                    'phone_no',
                                    'email',
                                    'available_departure_date',
                                    'departure_mode_travel_id',
                                    'visa_agent_id',
                                    'available_return_date',
                                    'return_mode_travel_id',
                                    'ticket_booking_agent_id',
                                    'bank_id',
                                    'cheque_number',
                                    'cash_advance_ids',
                                    'travel_approver_user_ids'
                                   ]}
        if not id:
            request_param = {"ids":','.join(str(data.id) for data in data_ids),"fields":['state',
                                                                                         'name',
                                                                                         'req_departure_date',
                                                                                         'req_return_date'
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
                if 'req_departure_date' in data:
                    if data['req_departure_date']:
                        true_time = datetime.strptime(data['req_departure_date'],DEFAULT_SERVER_DATETIME_FORMAT)  + timedelta(hours=offset_time)
                        data['req_departure_date'] =  true_time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                        
                if 'req_return_date' in data:
                    if data['req_return_date']:
                        true_time = datetime.strptime(data['req_return_date'],DEFAULT_SERVER_DATETIME_FORMAT)  + timedelta(hours=offset_time)
                        data['req_return_date'] =  true_time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        if 'req_departure_date' in response_data[obj]:
            if response_data[obj]['req_departure_date']:
                true_time = datetime.strptime(response_data[obj]['req_departure_date'],DEFAULT_SERVER_DATETIME_FORMAT)  + timedelta(hours=offset_time)
                response_data[obj]['req_departure_date'] =  true_time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                
        if 'req_return_date' in response_data[obj]:
            if response_data[obj]['req_return_date']:
                true_time = datetime.strptime(response_data[obj]['req_return_date'],DEFAULT_SERVER_DATETIME_FORMAT)  + timedelta(hours=offset_time)
                response_data[obj]['req_return_date'] =  true_time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                
        if 'available_return_date' in response_data[obj]:
            if response_data[obj]['available_return_date']:
                true_time = datetime.strptime(response_data[obj]['available_return_date'],DEFAULT_SERVER_DATETIME_FORMAT)  + timedelta(hours=offset_time)
                response_data[obj]['available_return_date'] =  true_time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        if 'available_departure_date' in response_data[obj]:
            if response_data[obj]['available_departure_date']:
                true_time = datetime.strptime(response_data[obj]['available_departure_date'],DEFAULT_SERVER_DATETIME_FORMAT)  + timedelta(hours=offset_time)
                response_data[obj]['available_departure_date'] =  true_time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        
        
        if 'cash_advance_ids' in response_data[obj]:
            if len(response_data[obj]['cash_advance_ids']) >= 1:
                response_data[obj]['cash_advance_ids'] = self.convert_one2many('travel.vendor.deposit',{"fields":['name',
                                                                                                                'employee_id',
                                                                                                                'state',
                                                                                                                'amount'],
                                                                                                      "ids":','.join(str(data) for data in response_data[obj]['cash_advance_ids'])},user)
        if 'travel_approver_user_ids' in response_data[obj]:
            if len(response_data[obj]['travel_approver_user_ids']) >= 1:
                response_data[obj]['travel_approver_user_ids'] = self.convert_one2many('travel.approver.user',{"fields":['name','user_ids','approver_state','minimum_approver','approved_time','feedback'],
                                                                                                                    "ids":','.join(str(data) for data in response_data[obj]['travel_approver_user_ids'])},user)
                for data_to_convert in response_data[obj]['travel_approver_user_ids']:
                    if len(data_to_convert['user_ids'])>=1:
                        data_to_convert['user_ids'] = self.convert_one2many('res.users',{"fields":['name'],
                                                                                        "ids":','.join(str(data) for data in data_to_convert['user_ids'])},user)
        
        page_total  = self.get_total_page(len(data_ids),PAGE_DATA_LIMIT)
        return self.get_response(200, '200', {"code":200,
                                              "data":response_data[obj],
                                              "page_total":page_total if not id else 0
                                              })    
        
    @route(['/api/employee/travel_request/travel_mode'],auth='user', type='http', methods=['get'])
    def get_travel_mode(self,id=None,**kw):
        offset =  self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1)
        obj = 'travel.mode'
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        domain = []
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
    
    
    @route(['/api/employee/travel_request/account_analytic_account'],auth='user', type='http', methods=['get'])
    def get_account_analytic_account_travel(self,id=None,**kw):
        offset =  self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1)
        obj = 'account.analytic.account'
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        domain = []
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
                                                                         
    @route(['/api/employee/travel_request/project_id'],auth='user', type='http', methods=['get'])
    def get_travel_project(self,id=None,**kw):
        offset =  self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1)
        obj = 'project.task'
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        domain = []
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
        
        
        
        