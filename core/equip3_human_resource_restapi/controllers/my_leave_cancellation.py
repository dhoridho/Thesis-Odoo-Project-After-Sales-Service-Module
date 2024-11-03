
from datetime import datetime, timedelta
from itertools import count
from odoo.http import route,request
import json
from ...restapi.controllers.helper import *


class Equip3HumanResourceMyleaveCancellation(RestApi):
    
    @route('/api/user/create/my_leave_cancellation',auth='user', type='json', methods=['POST'])
    def create_my_leave_cancellation_request(self,**kw):
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        request_data = request.jsonrequest
        leave_request = request.env['hr.leave'].sudo().search([('id','=',request_data.get('leave_id'))])
        data_create = request.env['hr.leave.cancelation'].sudo().create({
                                 'leave_id':request_data.get('leave_id'),
                                 'reason':request_data.get('reason') ,
                                 'number_of_days':leave_request.number_of_days,
                                 'request_date_from':leave_request.request_date_from,
                                 'request_date_to':leave_request.request_date_to,
                                 'holiday_status_id':leave_request.holiday_status_id.id,
                                 })

        if request_data.get('state') == 'confirm':
            data_create.action_confirm()
        if data_create.holiday_status_id.leave_validation_type != 'no_validation':
            data_create.onchange_approver_user()
        if not data_create:
            return self.update_create_failed()   
        return self.get_response(200, '200', {"code":200, 
                                              "message":"Create My Leave Cancellation Request Suscessfull"
                                              })
        
    @route('/api/user/update/my_leave_cancellation/<int:id>',auth='user', type='json', methods=['PUT'])
    def update_my_leave_cancellation_request(self,id=None,**kw):
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        request_data = request.jsonrequest
        leave_request = request.env['hr.leave'].sudo().search([('id','=',request_data.get('leave_id'))])
        data_update = request.env['hr.leave.cancelation'].sudo().search([('id','=',id)])
        if not data_update:
            return self.record_not_found()
        data_update.write({
                                 'leave_id':request_data.get('leave_id'),
                                 'reason':request_data.get('reason') ,
                                 'number_of_days':leave_request.number_of_days,
                                 'request_date_from':leave_request.request_date_from,
                                 'request_date_to':leave_request.request_date_to,
                                 'holiday_status_id':leave_request.holiday_status_id.id,
                                 })

        if request_data.get('state') == 'confirm':
            data_update.action_confirm()
        if data_update.holiday_status_id.leave_validation_type != 'no_validation':
            data_update.onchange_approver_user()
        if not data_update:
            return self.update_create_failed()   
        return self.get_response(200, '200', {"code":200, 
                                              "message":"Update My Leave Cancellation Request Suscessfull"
                                              })
    
    @route(['/api/employee/my_leave_cancellation','/api/employee/my_leave_cancellation/<int:id>'],auth='user', type='http', methods=['get'])
    def get_employee_leave_cancellation(self,id=None,**kw):
        offset =  self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1)
        obj = 'hr.leave.cancelation'
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        filter_str = f"lambda line:line"
        if kw.get("state"):
            filter_str = filter_str + f" and line.state in kw.get('state')"
        if kw.get("holiday_status_id"):
            holiday_status_ids = kw.get("holiday_status_id")
            filter_str = filter_str + f" and line.leave_id.holiday_status_id.id in {holiday_status_ids}"
            
        date_from = kw.get("date_from")
        if kw.get("date_from"):
            date_from = datetime.strptime(str(kw.get('date_from')),"%Y-%m-%d") 
            filter_str = filter_str + f" and line.request_date_from  >= date_from.date()"

        date_to = kw.get("date_to")
        if kw.get("date_to"):
            date_to = datetime.strptime(str(kw.get('date_to')),"%Y-%m-%d") 
            filter_str = filter_str + f" and line.request_date_to <= date_to.date()"
            
        if kw.get("is_last_7"):
            query = """
            select data.id from hr_leave_cancelation data WHERE data.request_date_from  >= current_date - interval '7' day and data.request_date_from  <= current_date  and data.employee_id = %s
            """
            request._cr.execute(query, [request.env.user.employee_id.id])
            data_result_ids = request.env.cr.dictfetchall()
            ids = []
            if len(data_result_ids) > 0:
                ids = [id['id'] for id in data_result_ids]
            filter_str = filter_str + f" and line.id in {ids}"
        if kw.get("is_last_30"):
            query = """
                select data.id from hr_leave_cancelation data WHERE data.request_date_from  >= current_date - interval '30' day and data.request_date_from  <= current_date and data.employee_id = %s            
                """
            request._cr.execute(query, [request.env.user.employee_id.id])
            data_result_ids = request.env.cr.dictfetchall()
            ids = []
            if len(data_result_ids) > 0:
                ids = [id['id'] for id in data_result_ids]
            filter_str = filter_str + f" and line.id in {ids}"
        domain = [('employee_id','=',request.env.user.employee_id.id)]
        if kw.get("search"):
            domain.append(("name","ilike",kw.get("search")))
            
        data_ids = request.env[obj].sudo().search(domain).filtered(eval(filter_str,{'kw':kw,'date_from':date_from,'date_to':date_to}))
        if not data_ids:
            return self.record_not_found()
        request_param = {"fields":['state',
                                    'name',
                                    'employee_id',
                                    'holiday_status_id',
                                    'leave_id',
                                    'request_date_from',
                                    'request_date_to',
                                    'number_of_days',
                                    'reason',
                                    'approver_user_ids',
                                    
                                    
                                    ]}
        if not id:
            request_param = {"ids":','.join(str(data.id) for data in data_ids),"fields":['name',
                                                                                         'holiday_status_id',
                                                                                         'request_date_from',
                                                                                         'request_date_to',
                                                                                         'state'
                                                                                         ],
                             "order":"id desc",
                             "offset":offset,
                             "limit":PAGE_DATA_LIMIT
                             }
            
        read_record = self.perform_request(obj,id=id, kwargs=request_param, user=user)
        response_data = json.loads(read_record.data)
        
        if not obj in response_data:
            return self.record_not_found()
        
        if 'approver_user_ids' in response_data[obj]:
            if len(response_data[obj]['approver_user_ids']) >= 1:
                response_data[obj]['approver_user_ids'] = self.convert_one2many('leave.cancel.approver.user',{"fields":['employee_id',
                                                                                                                      'approver_state',
                                                                                                                      'minimum_approver',
                                                                                                                      'approved_time',
                                                                                                                      'feedback'],
                                                                                                            "ids":','.join(str(data) for data in response_data[obj]['approver_user_ids'])},user)
                for data_to_convert in response_data[obj]['approver_user_ids']:
                    if len(data_to_convert['employee_id'])>=1:
                        data_to_convert['employee_id'] = self.convert_one2many('res.users',{"fields":['name'],
                                                                                         "ids":','.join(str(data) for data in data_to_convert['employee_id'])},user)
        page_total  = self.get_total_page(len(data_ids),PAGE_DATA_LIMIT)
        return self.get_response(200, '200', {"code":200,
                                              "data":response_data[obj],
                                              "page_total":page_total if not id else 0
                                              })