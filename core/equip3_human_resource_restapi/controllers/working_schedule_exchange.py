from datetime import datetime, timedelta
from itertools import count
from odoo.http import route,request
import json
from ...restapi.controllers.helper import *


class Equip3HumanResourceWorkingScheduleExchange(RestApi):
    @route('/api/user/create/working_schedule_exchange',auth='user', type='json', methods=['POST'])
    def create_working_schedule_exchange(self,**kw):
        request_data = request.jsonrequest
        auth, user, invalid = self.valid_authentication(kw)
        date_from  = datetime.strptime(str(request_data.get('request_date_from')),"%Y-%m-%d")
        date_to = datetime.strptime(str(request_data.get('request_date_to')),"%Y-%m-%d")
        schedule_exchange_ids = []
        schedule_calendar_ids = []
        other_employee_id = int(request_data.get('other_employee_id')) if request_data.get('other_employee_id') else False
        if 'exchange_schedule_ids' in request_data:
            schedule_exchange_ids.append((6,0,request_data.get('exchange_schedule_ids')))
            
        if 'schedule_calendar_ids' in request_data:
            schedule_calendar_ids.append((6,0,request_data.get('schedule_calendar_ids')))
               
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        
        data = request.env['schedule.exchange'].sudo().create({
                                 'date_from':date_from,
                                 'date_to':date_to,
                                 'exchange_type':request_data.get('exchange_type'),
                                 'other_employee_id':other_employee_id,
                                 'schedule_calendar_ids':schedule_calendar_ids,
                                 'exchange_schedule_ids':schedule_exchange_ids
                                 })
        if request_data.get('state') == 'confirm':
            data.action_confirm()
            
        data.onchange_approver_user()
        if not data:
            return self.update_create_failed()   
        
        return self.get_response(200, '200', {"code":200, 
                                              "message":"Create working schedule exhange successful!"
                                              })
        
        
    @route('/api/user/update/working_schedule_exchange/<int:id>',auth='user', type='json', methods=['PUT'])
    def update_working_schedule_exchange(self,id=None,**kw):
        request_data = request.jsonrequest
        auth, user, invalid = self.valid_authentication(kw)
        other_employee_id = int(request_data.get('other_employee_id')) if request_data.get('other_employee_id') else False
        date_from  = datetime.strptime(str(request_data.get('request_date_from')),"%Y-%m-%d")
        date_to = datetime.strptime(str(request_data.get('request_date_to')),"%Y-%m-%d")
        schedule_exchange_ids = []
        schedule_calendar_ids = []
        if 'exchange_schedule_ids' in request_data:
            schedule_exchange_ids.append((6,0,request_data.get('exchange_schedule_ids')))
            
        if 'schedule_calendar_ids' in request_data:
            schedule_calendar_ids.append((6,0,request_data.get('schedule_calendar_ids')))
               
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        data =request.env['schedule.exchange'].sudo().search([('id','=',id)])
        if data:
            data.write({
                                    'date_from':date_from,
                                    'date_to':date_to,
                                    'exchange_type':request_data.get('exchange_type'),
                                    'schedule_calendar_ids':schedule_calendar_ids,
                                    'exchange_schedule_ids':schedule_exchange_ids,
                                    'other_employee_id':other_employee_id,
                                    })
        else:
            return self.update_create_failed()
        if request_data.get('state') == 'confirm':
            data.action_confirm()
            
        data.onchange_approver_user()
        if not data:
            return self.update_create_failed()   
        
        return self.get_response(200, '200', {"code":200, 
                                              "message":"Update working schedule exhange successful!"
                                              })
    
    @route(['/api/employee/get_current_or_exchange_schedule'],auth='user', type='http', methods=['get'])
    def get_current_or_exchange_schedule(self,id=None,**kw):
        obj = 'employee.working.schedule.calendar'
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401), {'code': 401, 'message': 'Authentication required'})
        date_from = datetime.strptime(str(kw.get('date_from')),"%Y-%m-%d")
        date_to = datetime.strptime(str(kw.get('date_to')),"%Y-%m-%d")
        if kw.get('current_schedule'): 
            data_to_search = request.env[obj].search([('date_start', '>=',date_from),
                                                      ('date_start', '<=', date_to),
                                                      ('employee_id','=',request.env.user.employee_id.id)])
            data_ids =  [data.id for data in data_to_search]
            filter_str = f"lambda line:line.id in {data_ids}"
            result_data_ids = request.env[obj].sudo().search([]).filtered(eval(filter_str))
            if not result_data_ids:
                return self.record_not_found()
            request_param = {"ids":','.join(str(data.id) for data in result_data_ids),
                             "fields":['employee_id','checkin','checkout']
                             }
            read_record = self.perform_request(obj,id=id, kwargs=request_param, user=user)
            response_data = json.loads(read_record.data)
        if kw.get('exchange_schedule'):
            if  kw.get('exchange_type') == 'other':
                data_to_search = request.env[obj].search([('date_start', '>=',date_from),
                                                        ('date_start', '<=', date_to),
                                                        ('employee_id','=',int(kw.get('other_employee_id')))])
                data_ids =  [data.id for data in data_to_search]
                filter_str = f"lambda line:line.id in {data_ids}"
                result_data_ids = request.env[obj].sudo().search([]).filtered(eval(filter_str))
                if not result_data_ids:
                    return self.record_not_found()
                request_param = {"ids":','.join(str(data.id) for data in result_data_ids),
                                "fields":['employee_id',
                                          'checkin',
                                          'checkout']
                                }
                read_record = self.perform_request(obj,id=id, kwargs=request_param, user=user)
                response_data = json.loads(read_record.data)
            else:
                data_to_search = request.env[obj].search([('date_start', '>=',date_from),
                                                        ('date_start', '<=', date_to),
                                                        ('employee_id','=',request.env.user.employee_id.id)])
                data_ids =  [data.id for data in data_to_search]
                filter_str = f"lambda line:line.id in {data_ids}"
                result_data_ids = request.env[obj].sudo().search([]).filtered(eval(filter_str))
                if not result_data_ids:
                    return self.record_not_found()
                request_param = {"ids":','.join(str(data.id) for data in result_data_ids),
                                "fields":['employee_id','checkin','checkout']
                                }
                read_record = self.perform_request(obj,id=id, kwargs=request_param, user=user)
                response_data = json.loads(read_record.data)
        if not obj in response_data:
            return self.record_not_found()
        return self.get_response(200, '200', {"code":200,
                                              "data":response_data[obj]
                                              })   
    
    @route(['/api/employee/working_schedule_exchange','/api/employee/working_schedule_exchange/<int:id>'],auth='user', type='http', methods=['get'])
    def get_employee_working_schedule(self,id=None,**kw):
        offset =  self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1)
        obj = 'schedule.exchange'
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        
        filter_str = f"lambda line:line"
        if kw.get("state"):
            state_ids = kw.get("state")
            filter_str = filter_str + f" and line.state in {state_ids}"
            
        if kw.get("exchange_type"):
            exchange_type_ids = kw.get("exchange_type")
            filter_str = filter_str + f" and line.exchange_type in {exchange_type_ids}"
            
        date_from = kw.get("date_from")
        if kw.get("date_from"):
            date_from = datetime.strptime(str(kw.get('date_from')),"%Y-%m-%d") 
            filter_str = filter_str + f" and line.date_from  >= date_from.date()"

        date_to = kw.get("date_to")
        if kw.get("date_to"):
            date_to = datetime.strptime(str(kw.get('date_to')),"%Y-%m-%d") 
            filter_str = filter_str + f" and line.date_to <= date_to.date()"
            
        if kw.get("is_last_7"):
            query = """
            select data.id from schedule_exchange data WHERE data.date_from  >= current_date - interval '7' day and data.date_from  <= current_date  and data.employee_id = %s
            """
            request._cr.execute(query, [request.env.user.employee_id.id])
            data_result_ids = request.env.cr.dictfetchall()
            ids = []
            if len(data_result_ids) > 0:
                ids = [id['id'] for id in data_result_ids]
            filter_str = filter_str + f" and line.id in {ids}"
        if kw.get("is_last_30"):
            query = """
                select data.id from schedule_exchange data WHERE data.date_from  >= current_date - interval '30' day and data.date_from  <= current_date and data.employee_id = %s            
                """
            request._cr.execute(query, [request.env.user.employee_id.id])
            data_result_ids = request.env.cr.dictfetchall()
            ids = []
            if len(data_result_ids) > 0:
                ids = [id['id'] for id in data_result_ids]
            filter_str = filter_str + f" and line.id in {ids}"
        domain = [('employee_id','=',request.env.user.employee_id.id)]
        if kw.get("search"):
            domain.append(("name",'ilike',kw.get("search")))
            
        data_ids = request.env[obj].sudo().search(domain).filtered(eval(filter_str,{'kw':kw,'date_from':date_from,'date_to':date_to}))
        if not data_ids:
            return self.record_not_found()
        request_param = {"fields":['state',
                                    'name',
                                    'employee_id',
                                    'department_id',
                                    'exchange_type',
                                    'date_from',
                                    'date_to',
                                    'other_employee_id',
                                    'schedule_calendar_ids',
                                    'exchange_schedule_ids',
                                    'working_schedule_user_ids'
                                   ]
                             }
        if not id:
            request_param = {"ids":','.join(str(data.id) for data in data_ids),"fields":[
                                                                                         'name',
                                                                                        'state',
                                                                                         'date_from',
                                                                                         'date_to'
                                                                                         ],
                             "order":"id desc",
                             "offset":offset,
                             "limit":PAGE_DATA_LIMIT
                             }
            
        read_record = self.perform_request(obj,id=id, kwargs=request_param, user=user)
        response_data = json.loads(read_record.data)
        if not obj in response_data:
            return self.record_not_found()
        
        if 'schedule_calendar_ids' in response_data[obj]:
            if len(response_data[obj]['schedule_calendar_ids']) >= 1:
                response_data[obj]['schedule_calendar_ids'] = self.convert_one2many('employee.working.schedule.calendar',
                                                                                    {"fields":[
                                                                                        'date_start',
                                                                                        'hour_from',
                                                                                        'hour_to'
                                                                                        ],
                                                                                     "ids":','.join(str(data) for data in response_data[obj]['schedule_calendar_ids'])},user)
                for data_to_correct in response_data[obj]['schedule_calendar_ids']:
                    data_to_correct['hour_from'] = str(timedelta(hours=data_to_correct['hour_from']))
                    data_to_correct['hour_to'] = str(timedelta(hours=data_to_correct['hour_to']))
                    
        if 'exchange_schedule_ids' in response_data[obj]:
            if len(response_data[obj]['exchange_schedule_ids']) >= 1:
                response_data[obj]['exchange_schedule_ids'] = self.convert_one2many('employee.working.schedule.calendar',
                                                                                    {"fields":[
                                                                                        'date_start',
                                                                                        'hour_from',
                                                                                        'hour_to'
                                                                                        ],
                                                                                     "ids":','.join(str(data) for data in response_data[obj]['exchange_schedule_ids'])},user)
                for data_to_correct in response_data[obj]['exchange_schedule_ids']:
                    data_to_correct['hour_from'] = str(timedelta(hours=data_to_correct['hour_from']))
                    data_to_correct['hour_to'] = str(timedelta(hours=data_to_correct['hour_to']))
                    
        if 'working_schedule_user_ids' in response_data[obj]:
            if len(response_data[obj]['working_schedule_user_ids']) >= 1:
                response_data[obj]['working_schedule_user_ids'] = self.convert_one2many('working.schedule.approver.user',{"fields":['name',
                                                                                                                 'user_ids',
                                                                                                                 'minimum_approver',
                                                                                                                 'approval_status',
                                                                                                                 'approved_time',
                                                                                                                 'feedback'
                                                                                                                ],
                                                                                                       "ids":','.join(str(data) for data in response_data[obj]['working_schedule_user_ids'])},user)
                for data_to_convert in response_data[obj]['working_schedule_user_ids']:
                    if 'user_ids' in data_to_convert:
                        if  len(data_to_convert['user_ids']) >= 1:
                            data_to_convert['user_ids'] =  self.convert_one2many('res.users',{"fields":['name'],
                                                                                              "ids":','.join(str(data) for data in data_to_convert['user_ids'])},user)
             
                
    
        page_total  = self.get_total_page(len(data_ids),PAGE_DATA_LIMIT)
        return self.get_response(200, '200', {"code":200,
                                              "data":response_data[obj],
                                              "page_total":page_total if not id else 0
                                              })    
    
    
    
    @route(['/api/employee/working_schedule_exchange/employee'],auth='user', type='http', methods=['get'])
    def get_employee_working_schedule_employee(self,id=None,**kw):
        offset =  self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1)
        filter = []
        data_ids = []
        obj = 'hr.employee'
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        
        if kw.get('search'):
            filter.append(('name','ilike',kw.get('search')))
            
        employee_obj_list = request.env[obj].search(filter)
        if employee_obj_list:
            data_ids = [data.id for data in employee_obj_list if request.env['employee.working.schedule.calendar'].search([('employee_id','=',data.id)])]
        
        if not data_ids:
            return self.record_not_found()
        request_param = {"ids":','.join(str(data) for data in data_ids),"fields":['name'],
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
        