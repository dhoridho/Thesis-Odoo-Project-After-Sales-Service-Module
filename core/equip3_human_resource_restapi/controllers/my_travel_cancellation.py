from datetime import datetime, timedelta
from itertools import count

import pytz
from odoo.http import route,request
import json
from ...restapi.controllers.helper import *


class Equip3HumanResourceMyTravelRequestCancellation(RestApi):
    @route('/api/employee/create/my_travel_cancellation',auth='user', type='json', methods=['POST'])
    def create_my_travel_cancellation(self,**kw):
        request_data = request.jsonrequest
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        
        data_create = request.env['employee.travel.cancellation'].sudo().create({
                                 'employee_id': request.env.user.employee_id.id,
                                 'travel_id':request_data.get('travel_id')
                                 
                                 })    
            
        if request_data.get('state') == 'confirmed':
            data_create.action_confirm()
            
        data_create.onchange_approver_user()
        if not data_create:
            return self.update_create_failed()
           
        return self.get_response(200, '200', {"code":200, 
                                              "message":"Create My Travel Cancellation Suscessfull"
                                              })
        
    @route('/api/employee/update/my_travel_cancellation/<int:id>',auth='user', type='json', methods=['PUT'])
    def update_my_travel_cancellation(self,id=None,**kw):
        request_data = request.jsonrequest
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        
        data_update = request.env['employee.travel.cancellation'].sudo().search([('id','=',id)]
                                                                                   )
        if not data_update:
            return self.record_not_found()
        
        data_update.write({
                                 'employee_id': request.env.user.employee_id.id,
                                 'travel_id':request_data.get('travel_id')
                                 
                                 })    
            
        if request_data.get('state') == 'confirmed':
            data_update.action_confirm()
            
        data_update.onchange_approver_user()
        if not data_update:
            return self.update_create_failed()
           
        return self.get_response(200, '200', {"code":200, 
                                              "message":"Update My Travel Cancellation Suscessfull"
                                              })
    
    @route(['/api/employee/my_travel_cancellation/','/api/employee/my_travel_cancellation/<int:id>'],auth='user', type='http', methods=['get'])
    def get_employee_travel_cancellation(self,id=None,**kw):
        now = datetime.now()
        user_tz = request.env.user.employee_id.tz or pytz.utc or 'UTC'
        local = pytz.timezone(user_tz)
        offset_time = local.utcoffset(now, is_dst = False).total_seconds()/3600
        offset =  self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1)
        offset =  self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1)
        obj = 'employee.travel.cancellation'
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

        date_to = kw.get("date_to")
        if kw.get("date_to"):
            date_to = datetime.strptime(str(kw.get('date_to')),"%Y-%m-%d") 
            filter_str = filter_str + f" and line.req_return_date.date() <= date_to.date()"
            
        if kw.get("is_last_7"):
            query = """
            select data.id from employee_travel_cancellation data WHERE data.req_departure_date::date  >= current_date - interval '7' day and data.req_departure_date  <= current_date  and data.employee_id = %s
            """
            request._cr.execute(query, [request.env.user.employee_id.id])
            data_result_ids = request.env.cr.dictfetchall()
            ids = []
            if len(data_result_ids) > 0:
                ids = [id['id'] for id in data_result_ids]
                
            filter_str = filter_str + f" and line.id in {ids}"
        if kw.get("is_last_30"):
            query = """
                select data.id from employee_travel_cancellation data WHERE data.req_departure_date::date  >= current_date - interval '30' day and data.req_departure_date  <= current_date and data.employee_id = %s            
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
            domain.append("|")
            domain.append(("name","ilike",kw.get("search")))
            domain.append(("travel_id.name","ilike",kw.get("search")))
            domain.append(("travel_purpose","ilike",kw.get("search")))
        data_ids = request.env[obj].sudo().search(domain).filtered(eval(filter_str,{'kw':kw,
                                                                                                                    'date_from':date_from,
                                                                                                                    'date_to':date_to}))
        if not data_ids:
            return self.record_not_found()
        
        request_param = {"fields":['state',
                                    'name',
                                    'travel_id',
                                    'employee_id',
                                    'department_manager_id',
                                    'department_id',
                                    'job_id',
                                    'currency_id',
                                    'start_today_date',
                                    'expence_sheet_id',
                                    'cash_advance_orgin_id',
                                    'travel_purpose',
                                    'project_id',
                                    'account_analytic_id',
                                    'from_city',
                                    'from_state_id',
                                    'from_country_id',
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
                                    'travel_cancel_approver_user_ids'
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
        if 'travel_cancel_approver_user_ids' in response_data[obj]:
            if len(response_data[obj]['travel_cancel_approver_user_ids']) >= 1:
                response_data[obj]['travel_cancel_approver_user_ids'] = self.convert_one2many('travel.cancel.approver.user',{"fields":['name','user_ids','approver_state','minimum_approver','approved_time','feedback'],
                                                                                                                    "ids":','.join(str(data) for data in response_data[obj]['travel_cancel_approver_user_ids'])},user)
                for data_to_convert in response_data[obj]['travel_cancel_approver_user_ids']:
                    if len(data_to_convert['user_ids'])>=1:
                        data_to_convert['user_ids'] = self.convert_one2many('res.users',{"fields":['name'],
                                                                                        "ids":','.join(str(data) for data in data_to_convert['user_ids'])},user)
        
        page_total  = self.get_total_page(len(data_ids),PAGE_DATA_LIMIT)
        return self.get_response(200, '200', {"code":200,
                                              "data":response_data[obj],
                                              "page_total":page_total if not id else 0
                                              })    