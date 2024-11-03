from datetime import datetime, timedelta
from itertools import count
from odoo.http import route,request
from ...restapi.controllers.helper import *
import pytz
import json


class Equip3HumanResourceMyAttendanceChangeRequest(RestApi):
    @route(['/api/employee/my_attendance_change_request_line'],auth='user', type='http', methods=['get'])
    def get_my_attendance_change_request_line(self,id=None,**kw):
        obj ='hr.attendance'
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        
        localtz = pytz.timezone(request.env.user.tz if request.env.user.tz else'Asia/Jakarta')
        response = []
        if not kw.get('request_date_from') or not kw.get('request_date_to'):
            return self.record_not_found()

        if kw.get('request_date_from') and kw.get('request_date_to'):
            request_date_from  = datetime.strptime(str(kw.get('request_date_from')),"%Y-%m-%d")
            request_date_to = datetime.strptime(str(kw.get('request_date_to')),"%Y-%m-%d")
            attendances = request.env[obj].sudo().search(
                            [('employee_id', '=', request.env.user.employee_id.id),
                            ('start_working_date', '>=', request_date_from.date()),
                            ('start_working_date', '<=', request_date_to.date())],order='start_working_date ASC')
            if not attendances:
                return self.record_not_found()
            for att in attendances:
                if att.check_in:
                    origin_check_in_local = datetime.strftime(pytz.utc.localize(datetime.strptime(str(att.check_in),"%Y-%m-%d %H:%M:%S")).astimezone(localtz),"%Y-%m-%d %H:%M:%S")
                    origin_check_in = datetime.strptime(str(origin_check_in_local),"%Y-%m-%d %H:%M:%S")
                    check_in_hour = origin_check_in.time().hour
                    check_in_minute = origin_check_in.time().minute
                    t, check_in_hours = divmod(float(check_in_hour), 24)
                    t, check_in_minutes = divmod(float(check_in_minute), 60)
                    check_in_minutes = check_in_minutes / 60.0
                    check_in_float = check_in_hours + check_in_minutes
                else:
                    check_in_float = 0

                if att.check_out:
                    origin_check_out_local = datetime.strftime(pytz.utc.localize(datetime.strptime(str(att.check_out),"%Y-%m-%d %H:%M:%S")).astimezone(localtz),"%Y-%m-%d %H:%M:%S")
                    origin_check_out = datetime.strptime(str(origin_check_out_local),"%Y-%m-%d %H:%M:%S")
                    check_out_hour = origin_check_out.time().hour
                    check_out_minute = origin_check_out.time().minute
                    t, check_out_hours = divmod(float(check_out_hour), 24)
                    t, check_out_minutes = divmod(float(check_out_minute), 60)
                    check_out_minutes = check_out_minutes / 60.0
                    check_out_float = check_out_hours + check_out_minutes
                else:
                    check_out_float = 0
                if att.active:
                    response.append({
                        'hr_attendance_id': att.id,
                        'date': att.start_working_date.strftime("%Y-%m-%d"),
                        'resource_calendar_id': [att.working_schedule_id.id,att.working_schedule_id.name],
                        'check_in': str(timedelta(hours=check_in_float)),
                        'check_out': str(timedelta(hours=check_out_float)),
                        'checkin_status': att.checkin_status,
                        'checkout_status': att.checkout_status,
                        'attendance_status': att.attendance_status,
                    })
        return self.get_response(200, '200', {"code":200,
                                              "data":response
                                              })
    
    @route('/api/employee/create/my_attendance_change_request',auth='user', type='json', methods=['POST'])
    def create_my_attendance_change_request(self,**kw):
        request_data = request.jsonrequest
        auth, user, invalid = self.valid_authentication(kw)
        request_date_from  = datetime.strptime(str(request_data.get('request_date_from')),"%Y-%m-%d")
        request_date_to = datetime.strptime(str(request_data.get('request_date_to')),"%Y-%m-%d")
        if not user or invalid:
            return self.get_response(401, str(401), {'code': 401, 'message': 'Authentication required'})
        attendance_change = request.env['hr.attendance.change'].sudo().create({
                                 'employee_id': request.env.user.employee_id.id,
                                 'request_date_from': request_date_from,
                                 'request_date_to': request_date_to,
                                 'attachment': request_data.get('attachment'),
                                 'attachment_name': request_data.get('attachment_name'),
                                 })

        attendance_change_line_ids = []
        for line in request_data.get('attendance_change_line_ids'):
            if line['check_in_correction']:
                check_in_correction = self.convert_time_to_float(line['check_in_correction'])    
                        
            if line['check_out_correction']:
                check_out_correction = self.convert_time_to_float(line['check_out_correction'])
                
            if line['check_in']:
                check_in = self.convert_time_to_float(line['check_in'])
                
            if line['check_out']:
                check_out = self.convert_time_to_float(line['check_out'])
                
            attendance_change_line_ids.append((0,0,{
                            'hr_attendance_id':int(line.get('hr_attendance_id')),
                            'date':datetime.strptime(str(line.get('date')),"%Y-%m-%d"),
                            'resource_calendar_id':int(line.get('resource_calendar_id')),
                            'check_in':check_in,
                            'check_out':check_out,
                            'checkin_status':line.get('checkin_status'),
                            'checkout_status':line.get('checkout_status'),
                            'attendance_status':line.get('attendance_status'),
                            'check_in_correction': check_in_correction,
                            'check_out_correction': check_out_correction,
                            'checkin_status_correction': line['checkin_status_correction'],
                            'checkout_status_correction': line['checkout_status_correction'],
                            'attendance_status_correction': line['attendance_status_correction'],
                            'reason': line['reason']
                            }))
        attendance_change.attendance_change_line_ids = attendance_change_line_ids
        attendance_change.onchange_approver_user()
        if request_data.get('state') == "to_approve":
            attendance_change.action_confirm()
            
        if not attendance_change:
            return self.update_create_failed()
        
        return self.get_response(200, '200', {"code":200, 
                                              "message":"Create My Attendance Change Request Suscessfull"
                                              })

    @route(['/api/employee/my_attendance_change_request','/api/employee/my_attendance_change_request/<int:id>'],auth='user', type='http', methods=['get'])
    def get_attendance_change_request(self,id=None,**kw):
        offset =  self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1)
        obj = 'hr.attendance.change'
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        
        filter_str = f"lambda line:line"
        if kw.get("state"):
            state_ids = kw.get("state")
            filter_str = filter_str + f" and line.state in {state_ids}"
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
            select data.id from hr_attendance_change data WHERE data.request_date_from  >= current_date - interval '7' day and data.request_date_from  <= current_date  and data.employee_id = %s
            """
            request._cr.execute(query, [request.env.user.employee_id.id])
            data_result_ids = request.env.cr.dictfetchall()
            ids = []
            if len(data_result_ids) > 0:
                ids = [id['id'] for id in data_result_ids]
            filter_str = filter_str + f" and line.id in {ids}"
        if kw.get("is_last_30"):
            query = """
                select data.id from hr_attendance_change data WHERE data.request_date_from  >= current_date - interval '30' day and data.request_date_from  <= current_date and data.employee_id = %s            
                """
            request._cr.execute(query, [request.env.user.employee_id.id])
            data_result_ids = request.env.cr.dictfetchall()
            ids = []
            if len(data_result_ids) > 0:
                ids = [id['id'] for id in data_result_ids]
            filter_str = filter_str + f" and line.id in {ids}"
        domain = [('employee_id','=',request.env.user.employee_id.id)]
        if kw.get("search"):
            domain.append(('name','ilike',kw.get("search")))
        data_ids = request.env[obj].sudo().search(domain).filtered(eval(filter_str,{'kw':kw,
                                                                                                                                   'date_from':date_from,
                                                                                                                                   'date_to':date_to}))
        if not data_ids:
            return self.record_not_found()
        request_param = {"fields":['state',
                                   'name',
                                   'employee_id',
                                   'request_date_from',
                                   'request_date_to',
                                   'attachment',
                                   'attachment_name',
                                   'attendance_change_line_ids',
                                   'attendance_change_user_ids',
                                   ]
                             }
        if not id:
            request_param = {"ids":','.join(str(data.id) for data in data_ids),"fields":['state',
                                                                                         'name',
                                                                                         'request_date_from',
                                                                                         'request_date_to'
                                                                                         ],
                             "order":"id desc",
                             "offset":offset,
                             "limit":PAGE_DATA_LIMIT
                             }
            
        read_record = self.perform_request(obj,id=id, kwargs=request_param, user=user)
        response_data = json.loads(read_record.data)
        if not obj in response_data:
            return self.record_not_found()
        
        if 'attendance_change_line_ids' in response_data[obj]:
            if len(response_data[obj]['attendance_change_line_ids']) >= 1:
                response_data[obj]['attendance_change_line_ids'] = self.convert_one2many('hr.attendance.change.line',{"fields":['date',
                                                                                                                 'resource_calendar_id',
                                                                                                                 'check_in',
                                                                                                                 'check_out',
                                                                                                                 'check_in_correction',
                                                                                                                 'check_out_correction',
                                                                                                                 'checkin_status_correction',
                                                                                                                 'checkout_status_correction',
                                                                                                                 'attendance_status_correction',
                                                                                                                 'checkin_status',
                                                                                                                 'checkout_status',
                                                                                                                 'attendance_status',
                                                                                                                 'reason',
                                                                                                                ],
                                                                                                       "ids":','.join(str(data) for data in response_data[obj]['attendance_change_line_ids'])},user)
                for data_to_correct in response_data[obj]['attendance_change_line_ids']:
                    data_to_correct['check_in'] = str(timedelta(hours=data_to_correct['check_in']))
                    data_to_correct['check_out'] = str(timedelta(hours=data_to_correct['check_out']))
                    data_to_correct['check_in_correction'] = str(timedelta(hours=data_to_correct['check_in_correction']))
                    data_to_correct['check_out_correction'] = str(timedelta(hours=data_to_correct['check_out_correction']))
                    
        if 'attendance_change_user_ids' in response_data[obj]:
            if len(response_data[obj]['attendance_change_user_ids']) >= 1:
                response_data[obj]['attendance_change_user_ids'] = self.convert_one2many('attendance.change.approver.user',{"fields":['name',
                                                                                                                 'user_ids',
                                                                                                                 'minimum_approver',
                                                                                                                 'approval_status',
                                                                                                                 'approved_time',
                                                                                                                 'feedback'
                                                                                                                ],
                                                                                                       "ids":','.join(str(data) for data in response_data[obj]['attendance_change_user_ids'])},user)
                for data_to_convert in response_data[obj]['attendance_change_user_ids']:
                    data_to_convert['user_ids'] =  self.convert_one2many('res.users',{"fields":['name'],
                                                                                      "ids":','.join(str(data) for data in data_to_convert['user_ids'])},user)
                    
                
    
        page_total  = self.get_total_page(len(data_ids),PAGE_DATA_LIMIT)
        return self.get_response(200, '200', {"code":200,
                                              "data":response_data[obj],
                                              "page_total":page_total if not id else 0
                                              })    
    
    @route('/api/employee/update/my_attendance_change_request/<int:id>',auth='user', type='json', methods=['PUT'])
    def update_my_attendance_change_request(self,id,**kw):
        request_data = request.jsonrequest
        auth, user, invalid = self.valid_authentication(kw)
        request_date_from  = datetime.strptime(str(request_data.get('request_date_from')),"%Y-%m-%d")
        request_date_to = datetime.strptime(str(request_data.get('request_date_to')),"%Y-%m-%d")
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        attendance_change = request.env['hr.attendance.change'].sudo().search([('id','=',id)])
        if not attendance_change:
            return self.record_not_found()
        
        attendance_change.write({
                                'request_date_from': request_date_from.date(),
                                'request_date_to': request_date_to.date(),
                                'attachment': request_data.get('attachment'),
                                'attachment_name': request_data.get('attachment_name'),
                                })
        for line in request_data.get('attendance_change_line_ids'):
            line['values']['check_in_correction'] = self.convert_time_to_float(line['values']['check_in_correction'])
            line['values']['check_out_correction'] = self.convert_time_to_float(line['values']['check_out_correction'])
            if 'check_in' in line['values']:
                line['values']['check_in'] = self.convert_time_to_float(line['values']['check_in'])
            if 'check_out' in line['values']:
                line['values']['check_out'] = self.convert_time_to_float(line['values']['check_out'])
                
        result = self.update_one2many([('hr_attendance_change_id','=',attendance_change.id)],'hr.attendance.change.line',request_data.get('attendance_change_line_ids'))
        if result:
            attendance_change.attendance_change_line_ids = result
        
        attendance_change.onchange_approver_user()
        if request_data.get('state') == "to_approve":
            attendance_change.action_confirm()
        
        if not attendance_change:
            return self.update_create_failed()   
        return self.get_response(200, '200', {"code":200, "message":"Update My Attendance Change Request Suscessfull"})