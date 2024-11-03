from datetime import date, datetime, timedelta
from itertools import count
from odoo.http import route,request
import json
from ...restapi.controllers.helper import *
from odoo.tools.float_utils import float_round


class Equip3HumanResourceMyleaveRequest(RestApi):
    @route('/api/user/create/my_leave_Request',auth='user', type='json', methods=['POST'])
    def create_my_leave_request(self,**kw):
        request_data = request.jsonrequest
        auth, user, invalid = self.valid_authentication(kw)
        date_from  = datetime.strptime(str(request_data.get('request_date_from')),"%Y-%m-%d")
        date_to = datetime.strptime(str(request_data.get('request_date_to')),"%Y-%m-%d")  
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        leave = request.env['hr.leave'].sudo().with_context(
                leave_skip_date_check=True
            ).create({'name':request_data.get('name'),
                                 'request_date_from':date_from,
                                 'request_date_to':date_to,
                                 'attachment':request_data.get('attachment'),
                                 'attachment_name':request_data.get('attachment_name'),
                                 'request_date_from_period':request_data.get('request_date_from_period'),
                                 'holiday_type':"employee",
                                 'request_unit_half':request_data.get('request_unit_half'),
                                'employee_id': request.env.user.employee_id.id,
                                'user_id': request.env.user.id,
                                'holiday_status_id':int(request_data.get('holiday_status_id')),
                                'state':request_data.get('state'),
                                 })
        leave.request_date_from = date_from                                 
        leave.request_date_to = date_to                            
        leave._compute_date_from_to()
        if request_data.get('state') == 'confirm':
            leave.action_confirm()
            
        leave.onchange_approver_user()
        # commenting origin conditional for add an email notification
        # if not leave:
        #     return self.update_create_failed()   
        # return self.get_response(200, '200', {"code":200, 
        #                                       "message":"Create My Leave Suscessfull"
        #                                       })
        if leave:
            leave.approver_mail()
            return self.get_response(200, '200', {"code":200, 
                                              "message":"Create My Leave Suscessfull"
                                              })
        return self.update_create_failed()
        
    @route('/api/user/update/my_leave_Request/<int:id>',auth='user', type='json', methods=['PUT'])
    def update_my_leave_request(self,id,**kw):
        request_data = request.jsonrequest
        auth, user, invalid = self.valid_authentication(kw)
        date_from  = datetime.strptime(str(request_data.get('request_date_from')),"%Y-%m-%d")
        date_to = datetime.strptime(str(request_data.get('request_date_to')),"%Y-%m-%d")  
        date_from  = datetime.strptime(str(request_data.get('request_date_from')),"%Y-%m-%d")
        date_to = datetime.strptime(str(request_data.get('request_date_to')),"%Y-%m-%d")  
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        leave = request.env['hr.leave'].sudo().search([('id','=',id)])
        if not leave:
            return self.record_not_found
        else: 
            leave.write({
                                    'request_date_from':date_from.date(),
                                    'request_date_to':date_to.date(),
                                    'name':request_data.get('name'),
                                    'attachment':request_data.get('attachment'),
                                    'attachment_name':request_data.get('attachment_name'),
                                    'request_date_from_period':request_data.get('request_date_from_period'),
                                    'holiday_type':"employee",
                                    'request_unit_half':request_data.get('request_unit_half'),
                                    'employee_id': request.env.user.employee_id.id,
                                    'user_id': request.env.user.id,
                                    'holiday_status_id':int(request_data.get('holiday_status_id')),
                                    })
        if request_data.get('state') == 'confirm':
            leave.action_confirm()
        leave.onchange_approver_user()
        
        if not leave:
            return self.update_create_failed()   
        return self.get_response(200, '200', {"code":200, 
                                              "message":"Update My Leave Suscessfull"
                                              })
        
        
    @route('/api/user/update/my_leave_request_to_cancel/<int:id>',auth='user', type='json', methods=['PUT'])
    def update_my_leave_request_to_cancel(self,id,**kw):
        request_data = request.jsonrequest
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        leave = request.env['hr.leave'].sudo().search([('id','=',id)])
        if not leave:
            return self.record_not_found
        else: 
            leave.action_cancel()
        return self.get_response(200, '200', {"code":200, 
                                              "message":" My Leave Suscessfully cancelled"
                                              })
    
    
    
    @route(['/api/employee/my_leave_Request','/api/employee/my_leave_Request/<int:id>'],auth='user', type='http', methods=['get'])
    def get_employee_leave(self,id=None,**kw):
        offset =  self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1)
        obj = 'hr.leave'
        auth, user, invalid = self.valid_authentication(kw)
        filter_str = f"lambda line:line.user_id.id == {request.env.user.id}"
        now = datetime.now()
        if kw.get('leave_cancellation'):
            filter_str = filter_str + f" and line.state != 'cancel' and line.request_date_from >= now.date()"
            
        if kw.get("state"):
            state = kw.get("state")
            filter_str = filter_str + f" and line.state in {state}"
            
        date_from = kw.get("date_from")
        if kw.get("date_from"):
            date_from = datetime.strptime(str(kw.get('date_from')),"%Y-%m-%d") 
            filter_str = filter_str + f" and line.request_date_from >= date_from.date()"
            
        if kw.get("leave_type"):
            holiday_status_ids = kw.get("leave_type")
            filter_str = filter_str + f""" and line.holiday_status_id.id in {holiday_status_ids}"""
            
        date_to = kw.get("date_to")
        if kw.get("date_to"):
            date_to = datetime.strptime(str(kw.get('date_to')),"%Y-%m-%d") 
            filter_str = filter_str + f" and line.request_date_to <= date_to.date()"
            
        if kw.get("is_last_7"):
            query = """
            select leave.id from hr_leave leave WHERE leave.request_date_from  >= current_date - interval '7' day and leave.request_date_from  <= current_date and leave.user_id = %s
            """
            request._cr.execute(query, [request.env.user.id])
            leave_result_ids = request.env.cr.dictfetchall()
            ids = []
            if len(leave_result_ids) > 0:
                ids = [id['id'] for id in leave_result_ids]
            filter_str = filter_str + f" and line.id in {ids}"
            
        if kw.get("is_last_30"):
            query = """
            select leave.id from hr_leave leave WHERE leave.request_date_from  >= current_date - interval '30' day and leave.request_date_from  <= current_date   and leave.user_id = %s
            """
            request._cr.execute(query, [request.env.user.id])
            leave_result_ids = request.env.cr.dictfetchall()
            ids = []
            if len(leave_result_ids) > 0:
                ids = [id['id'] for id in leave_result_ids]
            filter_str = filter_str + f" and line.id in {ids}"
            
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        domain = []
        if kw.get("search"):
            domain.append('|')
            domain.append(('seq_name','ilike',kw.get("search")))
            domain.append(('holiday_status_id.name','ilike',kw.get("search")))
        leave_ids = request.env[obj].sudo().search(domain).filtered(eval(filter_str,{'kw':kw,
                                                                                     'date_from':date_from,
                                                                                     'date_to':date_to,
                                                                                     'now':now}))
    
        if not leave_ids:
            return self.record_not_found()
        request_param = {"fields":['seq_name',
                                   'request_date_from',
                                   'request_date_to',
                                   'state',
                                   'holiday_status_id',
                                   'request_date_from',
                                   'request_date_to',
                                   'number_of_days',
                                   'request_date_from_period',
                                   'name',
                                   'attachment',
                                   'attachment_name',
                                   'approver_user_ids'
                                   ]}
        
        if not id:
            request_param = {"ids":','.join(str(data.id) for data in leave_ids),"fields":['name','seq_name','request_date_from','request_date_to','state','holiday_status_id'],
                             "order":"id desc",
                             "offset":offset,
                             "limit":PAGE_DATA_LIMIT
                             }
            if kw.get('leave_cancellation'):
                del request_param['limit']
                del request_param['offset']
        read_record = self.perform_request(obj,id=id, kwargs=request_param, user=user)
        response_data = json.loads(read_record.data)
        if not obj in response_data:
           return self.record_not_found()
       
        if 'approver_user_ids' in response_data[obj]:
            if len(response_data[obj]['approver_user_ids']) >= 1:
                response_data[obj]['approver_user_ids'] = self.convert_one2many('leave.approver.user',{"fields":['name','employee_id','approver_state','minimum_approver','approved_time','feedback'],
                                                                                                                    "ids":','.join(str(data) for data in response_data[obj]['approver_user_ids'])},user)
                for data_to_convert in response_data[obj]['approver_user_ids']:
                    if len(data_to_convert['employee_id'])>=1:
                        data_to_convert['employee_id'] = self.convert_one2many('res.users',{"fields":['name'],
                                                                                        "ids":','.join(str(data) for data in data_to_convert['employee_id'])},user)
        page_total  = self.get_total_page(len(leave_ids),PAGE_DATA_LIMIT)
        return self.get_response(200, '200', {"code":200,
                                              "data":response_data[obj],
                                              "page_total":page_total if not id else 0
                                              })
        
    @route(['/api/employee/my_leave_type'],auth='user', type='http', methods=['get'])
    def get_employee_leave_type(self,id=None,**kw):
        obj = 'hr.leave.type'
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
                return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        if not kw.get('allocation'): 
            balance =  [data.holiday_status_id.id for data in request.env['hr.leave.balance'].search(
                        [('employee_id', '=', request.env.user.employee_id.id),
                        ('active', '=', True)]) ]
            filter_str = f"lambda line:line.id in {balance}"
            leave_type_ids = request.env[obj].sudo().search([]).filtered(eval(filter_str))
            if not leave_type_ids:
                return self.record_not_found()
            request_param = {"ids":','.join(str(data.id) for data in leave_type_ids),"fields":['name',
                                                                                               'is_required',
                                                                                               'limit_days',
                                                                                               'minimum_days_before',
                                                                                               'attachment_notes',
                                                                                               'allow_minus',
                                                                                               'allow_past_date',
                                                                                               'urgent_leave',
                                                                                               'maximum_minus',
                                                                                               'request_unit',
                                                                                               'past_days'
                                                                                               ]
                             }
            read_record = self.perform_request(obj,id=id, kwargs=request_param, user=user)
            response_data = json.loads(read_record.data)
            
            
        if kw.get('allocation'):       
            leave_type_ids = request.env[obj].sudo().search([('leave_method','=','none')])
            if not leave_type_ids:
                return self.record_not_found()
            request_param = {"ids":','.join(str(data.id) for data in leave_type_ids),"fields":['name',
                                                                                               'is_required',
                                                                                               'limit_days',
                                                                                               'minimum_days_before',
                                                                                               'attachment_notes',
                                                                                               'allow_minus',
                                                                                               'allow_past_date',
                                                                                               'urgent_leave',
                                                                                               'maximum_minus',
                                                                                               'past_days'
                                                                                               ]}
            read_record = self.perform_request(obj,id=id, kwargs=request_param, user=user)
            response_data = json.loads(read_record.data)
        if not obj in response_data:
            return self.record_not_found()
        
        for data in response_data[obj]:
            remaining = 0
            assigned = 0
            check_period = date.today().year
            leave_balance = request.env['hr.leave.balance'].sudo().search(
                [('employee_id', '=', request.env.user.employee_id.id), ('holiday_status_id', '=', data['id']),
                 ('current_period', '=', str(check_period))], limit=1)
            if leave_balance:
                remaining += float_round(leave_balance.remaining, precision_digits=2) or 0.0
                assigned += float_round(float(leave_balance.assigned) + float(leave_balance.bring_forward) + float(leave_balance.extra_leave), precision_digits=2) or 0.0
            data['remaining'] = remaining
            data['assigned'] = assigned
                
            
        
        if not kw.get('allocation'):
            for data in response_data[obj]:
                count_data = request.env['hr.leave'].search_count([('holiday_status_id','=',data['id']),('employee_id','=',request.env.user.employee_id.id),('state','=','validate')])
                data['count'] = count_data
        
        
        return self.get_response(200, '200', {"code":200,
                                              "data":response_data[obj]
                                              })   
    