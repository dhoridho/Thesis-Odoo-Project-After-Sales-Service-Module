from datetime import datetime, timedelta, time
from itertools import count
from odoo.http import route,request
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT,DEFAULT_SERVER_DATE_FORMAT
import json
from ...restapi.controllers.helper import *
from odoo import models, fields,_
import babel
import pytz


class Equip3HumanResourceMyActualOvertime(RestApi):
    @route(['/api/employee/my_actual_overtime/get_overtime_request_list'],auth='user', type='http', methods=['get'])
    def get_overtime_request_list(self,id=None,**kw):
        offset =  self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1)
        obj = 'hr.overtime.request'
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        domain = [('employee_id','=',request.env.user.employee_id.id),('state','=','approved')]
        if kw.get("search"):
            domain.append(('name','ilike',kw.get("search")))
                   
        data_ids = request.env[obj].sudo().search(domain)
        if not data_ids:
            return self.record_not_found()
        
        request_param = {"ids":','.join(str(data.id) for data in data_ids),"fields":['name','period_start','period_end'],
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
    
    @route('/api/employee/create/create_my_actual_overtime',auth='user', type='json', methods=['POST'])
    def create_my_actual_overtime(self,**kw):
        request_data = request.jsonrequest
        auth, user, invalid = self.valid_authentication(kw)
        period_start = False
        if request_data.get('period_start'):
            period_start  = datetime.strptime(str(request_data.get('period_start')),"%Y-%m-%d")
            
        period_end = False
        if request_data.get('period_end'):
            period_end  = datetime.strptime(str(request_data.get('period_end')),"%Y-%m-%d")
              
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        
        data_create = request.env['hr.overtime.actual'].sudo().create({
                                'request_type':"by_employee",
                                 'employee_id': request.env.user.employee_id.id,
                                 'period_start':period_start,
                                 'period_end':period_end,
                                 'applied_to':request_data.get('applied_to'),
                                 'actual_based_on':request_data.get('actual_based_on'),
                                 'overtime_request':request_data.get('overtime_request'),
                                 'description':request_data.get('description')
                                 
                                 })
        actual_line_ids= []
        if 'actual_line_ids' in request_data:
            for data in request_data['actual_line_ids']:
                date  = datetime.strptime(str(data['date']),"%Y-%m-%d")
                actual_start_time = self.convert_time_to_float(data['actual_start_time'])
                actual_end_time = self.convert_time_to_float(data['actual_end_time'])
                start_time = self.convert_time_to_float(data['start_time']) if 'start_time' in data else 0.0
                end_time = self.convert_time_to_float(data['end_time']) if 'end_time'in data else 0.0
                hours = self.convert_time_to_float(data['hours']) if 'hours' in data else False
                actual_line_ids.append((0,0,{'employee_id':request.env.user.employee_id.id,
                                              'overtime_reason':data['overtime_reason'],
                                              'date':date,
                                              'hours': hours,
                                              'name_of_day':date.strftime("%A"),
                                              'actual_start_time':actual_start_time,
                                              'actual_end_time':actual_end_time,
                                              "start_time":start_time,
                                              "end_time":end_time
                                              }))      
        actual_attendance_line_ids = []
        check_in = False
        check_out = False   
        if 'actual_attendance_line_ids' in request_data:
            for data in request_data['actual_attendance_line_ids']:
                if data['check_in']:
                    check_in  = datetime.strptime(str(data['check_in']),DEFAULT_SERVER_DATETIME_FORMAT) if data['check_in'] else False
                if data['check_out']:
                    check_out  = datetime.strptime(str(data['check_out']),DEFAULT_SERVER_DATETIME_FORMAT)if data['check_out'] else False
                actual_attendance_line_ids.append((0,0,{'attendance_id':data['attendance_id'],
                                                        'employee_id':request.env.user.employee_id.id,
                                                        'check_in':check_in,
                                                        'check_out':check_out,
                                                        "worked_hours":data['worked_hours'],
                                                        "attendance_status":data['attendance_status']
                                              }))        
        data_create._onchange_employee_id()
        data_create.actual_line_ids = actual_line_ids
        data_create.actual_attendance_line_ids = actual_attendance_line_ids
        if request_data.get('state') == 'to_approve':
            data_create.confirm()
            
        if not data_create:
            return self.update_create_failed()
           
        return self.get_response(200, '200', {"code":200, 
                                              "id":data_create.id,
                                              "message":"Create My Actual Overtime Request Suscessfull"
                                              })
        
    @route('/api/employee/update/my_actual_overtime/<int:id>',auth='user', type='json', methods=['PUT'])
    def update_my_actual_overtime(self,id=None,**kw):
        request_data = request.jsonrequest
        auth, user, invalid = self.valid_authentication(kw)
        period_start = False
        if request_data.get('period_start'):
            period_start  = datetime.strptime(str(request_data.get('period_start')),"%Y-%m-%d")
            
        period_end = False
        if request_data.get('period_end'):
            period_end  = datetime.strptime(str(request_data.get('period_end')),"%Y-%m-%d")
              
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        
        data_update = request.env['hr.overtime.actual'].sudo().search([('id','=',id)])
        if not data_update:
            return self.record_not_found()
        data_update.write({
                                'request_type':"by_employee",
                                 'employee_id': request.env.user.employee_id.id,
                                 'period_start':period_start,
                                 'period_end':period_end,
                                 'applied_to':request_data.get('applied_to'),
                                 'actual_based_on':request_data.get('actual_based_on'),
                                 'overtime_request':request_data.get('overtime_request'),
                                 'description':request_data.get('description')
                                 
                                 })
        
        if 'actual_line_ids' in request_data:
            for data in request_data['actual_line_ids']:
                if 'start_time' in data['values']:
                    data['values']['start_time'] = self.convert_time_to_float(data['values']['start_time'])
                    
                if 'end_time' in data['values']:
                    data['values']['end_time'] =  self.convert_time_to_float(data['values']['end_time'])
                    
                if 'hours' in data['values']:
                    data['values']['hours'] = self.convert_time_to_float(data['values']['hours'])
                    
                if 'actual_start_time' in data['values']:
                    data['values']['actual_start_time'] = self.convert_time_to_float(data['values']['actual_start_time'])
                    
                if 'actual_end_time' in data['values']:
                    data['values']['actual_end_time'] = self.convert_time_to_float(data['values']['actual_end_time'])
                    
                if 'break_time' in data['values']:
                    data['values']['break_time'] = self.convert_time_to_float(data['values']['break_time'])
                    
                if 'actual_hours' in data['values']:
                    data['values']['actual_hours'] = self.convert_time_to_float(data['values']['actual_hours'])
                    
        actual_line_ids = self.update_one2many([('actual_id','=',data_update.id)],'hr.overtime.actual.line',request_data.get('actual_line_ids'))
        if actual_line_ids:
            data_update.actual_line_ids = actual_line_ids 
        
        actual_attendance_line_ids = self.update_one2many([('actual_id','=',data_update.id)],'hr.overtime.actual.attendance.line',request_data.get('actual_attendance_line_ids'))
        if actual_attendance_line_ids:
            data_update.actual_attendance_line_ids = actual_attendance_line_ids    
    
        if request_data.get('state') == 'to_approve':
            data_update.confirm()
            
        data_update._onchange_employee_id()
        # data_update.actual_line_ids = actual_line_ids
        # data_update.actual_attendance_line_ids = actual_attendance_line_ids
        if not data_update:
            return self.update_create_failed()
        
        return self.get_response(200, '200', {"code":200, 
                                              "message":"Update My Overtime Request Suscessfull"
                                              })
        
    @route('/api/employee/calculate_overtime/my_actual_overtime/<int:id>',auth='user', type='json', methods=['PUT'])
    def calculate_my_actual_overtime(self,id=None,**kw):
        request_data = request.jsonrequest
        auth, user, invalid = self.valid_authentication(kw)      
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        
        data_update = request.env['hr.overtime.actual'].sudo().search([('id','=',id)])
        if not data_update:
            return self.record_not_found()
        
        data_update.calculate_overtime()
        if not data_update:
            return self.update_create_failed()
        
        return self.get_response(200, '200', {"code":200, 
                                              "message":"Calculate My Overtime Request Suscessfull"
                                              })
    
    @route(['/api/employee/my_actual_overtime/','/api/employee/my_actual_overtime/<int:id>'],auth='user', type='http', methods=['get'])
    def get_employee_my_actual_overtime_request(self,id=None,**kw):
        offset =  self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1)
        obj = 'hr.overtime.actual'
        auth, user, invalid = self.valid_authentication(kw)
        user_tz = request.env.user.employee_id.tz or pytz.utc or 'UTC'
        local = pytz.timezone(user_tz)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        
        filter_str = f"lambda line:line"
        if kw.get("state"):
            state = kw.get("state")
            filter_str = filter_str + f" and line.state in {state}"
            
        if kw.get("applied_to"):
            applied_to = kw.get("applied_to")
            filter_str = filter_str + f" and line.applied_to in {applied_to}"
            
        date_from = kw.get("date_from")
        if kw.get("date_from"):
            date_from = datetime.strptime(str(kw.get('date_from')),"%Y-%m-%d") 
            filter_str = filter_str + f" and line.period_start.date()  >= date_from.date()"

        date_to = kw.get("date_to")
        if kw.get("date_to"):
            date_to = datetime.strptime(str(kw.get('date_to')),"%Y-%m-%d") 
            filter_str = filter_str + f" and line.period_end.date() <= date_to.date()"
            
        if kw.get("is_last_7"):
            query = """
            select data.id from hr_overtime_actual data WHERE data.period_start::date  >= current_date - interval '7' day and data.period_start::date  <= current_date  and data.employee_id = %s
            """
            request._cr.execute(query, [request.env.user.employee_id.id])
            data_result_ids = request.env.cr.dictfetchall()
            ids = []
            if len(data_result_ids) > 0:
                ids = [id['id'] for id in data_result_ids]
            filter_str = filter_str + f" and line.id in {ids}"
            
        if kw.get("is_last_30"):
            query = """
                select data.id from hr_overtime_actual data WHERE data.period_start::date  >= current_date - interval '30' day and data.period_start::date  <= current_date and data.employee_id = %s            
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
                                    'applied_to',
                                    'request_type',
                                    'employee_id',
                                    'company_id',
                                    'actual_based_on',
                                    'overtime_request',
                                    'applied_to',
                                    'period_start',
                                    'period_end',
                                    'total_actual_hours',
                                    'total_coefficient_hours',
                                    'total_overtime_amount',
                                    'create_date',
                                    'create_uid',
                                    'description',
                                    'actual_line_ids',
                                    'actual_approval_line_ids',
                                    'actual_attendance_line_ids',
                                    
                                   ]}
        if not id:
            request_param = {"ids":','.join(str(data.id) for data in data_ids),"fields":['name',
                                                                                         'applied_to',
                                                                                         'request_type',
                                                                                         'state',
                                                                                         'period_start',
                                                                                         'period_end',
                                                                                         ],
                             "order":"id desc",
                             "offset":offset,
                             "limit":PAGE_DATA_LIMIT
                             }
            
        read_record = self.perform_request(obj,id=id, kwargs=request_param, user=user)
        response_data = json.loads(read_record.data)
        if not obj in response_data:
            return self.record_not_found()
        
        if 'actual_line_ids' in response_data[obj]:
            if len(response_data[obj]['actual_line_ids']) >= 1:
                response_data[obj]['actual_line_ids'] = self.convert_one2many('hr.overtime.actual.line',{"fields":['name_of_day',
                                                                                                                   'date',
                                                                                                                   'overtime_reason',
                                                                                                                   'start_time',
                                                                                                                   'end_time',
                                                                                                                   'hours',
                                                                                                                   'actual_start_time',
                                                                                                                   'actual_end_time',
                                                                                                                   'break_time',
                                                                                                                   'actual_hours',
                                                                                                                   'coefficient_hours',
                                                                                                                   'amount',
                                                                                                                   'meal_allowance',
                                                                                                                   ],
                                                                                                                    "ids":','.join(str(data) for data in response_data[obj]['actual_line_ids'])},user)
                for data in response_data[obj]['actual_line_ids']:
                    data['start_time'] = str(timedelta(hours=data['start_time']))
                    data['end_time'] = str(timedelta(hours=data['end_time']))
                    data['hours'] = str(timedelta(hours=data['hours']))
                    data['actual_start_time'] = str(timedelta(hours=data['actual_start_time']))
                    data['actual_end_time'] = str(timedelta(hours=data['actual_end_time']))
                    data['break_time'] = str(timedelta(hours=data['break_time']))
                    data['actual_hours'] = str(timedelta(hours=data['actual_hours']))
                
        if 'actual_approval_line_ids' in response_data[obj]:
            if len(response_data[obj]['actual_approval_line_ids']) >= 1:
                response_data[obj]['actual_approval_line_ids'] = self.convert_one2many('hr.overtime.actual.approval.line',{"fields":['approver_id','approval_status','timestamp','feedback'],
                                                                                                                    "ids":','.join(str(data) for data in response_data[obj]['actual_approval_line_ids'])},user)
                for data_to_convert in response_data[obj]['actual_approval_line_ids']:
                    if len(data_to_convert['approver_id'])>=1:
                        data_to_convert['approver_id'] = self.convert_one2many('res.users',{"fields":['name'],
                                                                                        "ids":','.join(str(data) for data in data_to_convert['approver_id'])},user)
                        
        if 'actual_attendance_line_ids' in response_data[obj]:
            if len(response_data[obj]['actual_attendance_line_ids']) >= 1:
                response_data[obj]['actual_attendance_line_ids'] = self.convert_one2many('hr.overtime.actual.attendance.line',{"fields":['attendance_status','check_in','check_out','worked_hours'],
                                                                                                                    "ids":','.join(str(data) for data in response_data[obj]['actual_attendance_line_ids'])},user)
                if response_data[obj]['actual_attendance_line_ids']:
                    for line in response_data[obj]['actual_attendance_line_ids']:
                        if line['check_in']:
                            checkin = datetime.strptime(line['check_in'], '%Y-%m-%d %H:%M:%S')
                            line['check_in'] =  datetime.strftime(checkin.astimezone(local), '%Y-%m-%d %H:%M:%S')
                        if line['check_out']:
                            check_out = datetime.strptime(line['check_out'], '%Y-%m-%d %H:%M:%S')
                            line['check_out'] = datetime.strftime(check_out.astimezone(local), '%Y-%m-%d %H:%M:%S')
        
        page_total  = self.get_total_page(len(data_ids),PAGE_DATA_LIMIT)
        return self.get_response(200, '200', {"code":200,
                                              "data":response_data[obj],
                                              "page_total":page_total if not id else 0
                                              })
        
        
    @route(['/api/employee/get_my_actual_overtime_line_attendance_line/'],auth='user', type='http', methods=['get'])
    def get_my_actual_overtime_line_onchange(self,id=None,**kw):
        period_start = datetime.strptime(str(kw.get('period_start')),"%Y-%m-%d")
        period_end = datetime.strptime(str(kw.get('period_end')),"%Y-%m-%d")
        delta = period_end - period_start
        days = [period_start + timedelta(days=i) for i in range(delta.days + 1)]
        ttyme = datetime.combine(fields.Date.from_string(period_start), time.min)
        ttyme_end = datetime.combine(fields.Date.from_string(period_end), time.min)
        locale = request.env.context.get('lang') or 'en_US'
        self.description = _('Actual Overtime for period: %s to %s') % (
            tools.ustr(babel.dates.format_date(date=ttyme, format='dd MMM YYYY', locale=locale)),
            tools.ustr(babel.dates.format_date(date=ttyme_end, format='dd MMM YYYY', locale=locale)))

        user_tz = request.env.user.employee_id.tz or pytz.utc or 'UTC'
        local = pytz.timezone(user_tz)
        date_min = datetime.combine(fields.Date.from_string(period_start), time.min)
        date_max = datetime.combine(fields.Date.from_string(period_end), time.max)
        date_start = local.localize(date_min).astimezone(pytz.UTC).replace(tzinfo=None)
        date_end = local.localize(date_max).astimezone(pytz.UTC).replace(tzinfo=None)

        overtime_line = []
        attendance_line = []
        attendances = request.env['hr.attendance'].search([('employee_id', '=', request.env.user.employee_id.id),
                                                            ('check_in', '>=', date_start),
                                                            ('check_in', '<=', date_end)], order='check_in')
        if attendances:
            for att in attendances:
                input_data = {
                    # 'actual_id': self.id,
                    'attendance_id': att.id,
                    'employee_id': att.employee_id.id,
                    'check_in': att.check_in,
                    'check_out': att.check_out,
                    'worked_hours': att.worked_hours,
                    'attendance_status': att.attendance_status
                }
                attendance_line.append(input_data)
       
        for date in days:
            dates_min = datetime.combine(fields.Date.from_string(date), time.min)
            dates_max = datetime.combine(fields.Date.from_string(date), time.max)
            dates_start = local.localize(dates_min).astimezone(pytz.UTC).replace(tzinfo=None)
            dates_end = local.localize(dates_max).astimezone(pytz.UTC).replace(tzinfo=None)
            att_obj = request.env['hr.attendance'].search([('employee_id', '=', request.env.user.employee_id.id),
                                                        ('check_in', '>=', dates_start),
                                                        ('check_in', '<=', dates_end)],
                                                    limit=1, order='check_in')
            start_times = 0.0
            end_times = 0.0
            if att_obj:
                check_ins = pytz.UTC.localize(att_obj.check_in).astimezone(local)
                if date == check_ins.date():
                    start_times = att_obj.hour_to
                if att_obj.check_out:
                    check_outs = pytz.UTC.localize(att_obj.check_out).astimezone(local)
                    checkout_times = check_outs.time()
                    if date == check_ins.date():
                        end_times = checkout_times.hour + checkout_times.minute / 60
            input_data = {
                'employee_id': request.env.user.employee_id.id,
                'date': date.strftime("%Y-%m-%d"),
                'actual_start_time': start_times,
                'actual_end_time': end_times,
                # 'actual_id': self.id,
            }
            overtime_line.append(input_data)
        for data in overtime_line:
            if data['actual_start_time']:
                data['actual_start_time'] = str(timedelta(hours=data['actual_start_time']))
            if data['actual_end_time']:
                data['actual_end_time'] = str(timedelta(hours=data['actual_end_time']))
            
        for data in attendance_line:
            if 'check_in' in data:
                if data['check_in']:
                    data['check_in'] = data['check_in'].strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                
            if 'check_out' in data:
                if data['check_out']:
                    data['check_out'] = data['check_out'].strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        response = {"actual_line_ids":overtime_line,
                    "actual_attendance_line_ids":attendance_line
                    }
        return self.get_response(200, '200', {"code":200,"data":response})
    
    @route(['/api/employee/get_my_actual_overtime_by_overtime_req'],auth='user', type='http', methods=['get'])
    def get_my_actual_overtime_line_by_overtime_request(self,id=None,**kw):
        period_start = datetime.strptime(str(kw.get('period_start')),"%Y-%m-%d")
        period_end = datetime.strptime(str(kw.get('period_end')),"%Y-%m-%d")
        user_tz = request.env.user.employee_id.tz or pytz.utc or 'UTC'
        local = pytz.timezone(user_tz)
        date_min = datetime.combine(fields.Date.from_string(period_start), time.min)
        date_max = datetime.combine(fields.Date.from_string(period_end), time.max)
        date_start = local.localize(date_min).astimezone(pytz.UTC).replace(tzinfo=None)
        date_end = local.localize(date_max).astimezone(pytz.UTC).replace(tzinfo=None)
        attendances = request.env['hr.attendance'].search([('employee_id', '=', request.env.user.employee_id.id),
                                                        ('check_in', '>=', date_start),
                                                        ('check_in', '<=', date_end)], order='check_in')
        delta = period_end - period_start
        days = [period_start + timedelta(days=i) for i in range(delta.days + 1)]
        attendance_line = []
        if attendances:
            for att in attendances:
                input_data = {
                    # 'actual_id': self.id,
                    'attendance_id': att.id,
                    'employee_id': att.employee_id.id,
                    'check_in': att.check_in,
                    'check_out': att.check_out,
                    'worked_hours': att.worked_hours,
                    'attendance_status': att.attendance_status
                }
                attendance_line.append(input_data)

        request_line = request.env['hr.overtime.request.line'].search([('employee_id', '=', request.env.user.employee_id.id),('date','in',days),('state','=','approved')], order='date')

        actual_line_ids = []
        if request_line:
            for rec in request_line:
                dates_min = datetime.combine(fields.Date.from_string(rec.date), time.min)
                dates_max = datetime.combine(fields.Date.from_string(rec.date), time.max)
                dates_start = local.localize(dates_min).astimezone(pytz.UTC).replace(tzinfo=None)
                dates_end = local.localize(dates_max).astimezone(pytz.UTC).replace(tzinfo=None)
                att_obj = request.env['hr.attendance'].search([('employee_id', '=', rec.employee_id.id),
                                                            ('check_in', '>=', dates_start),
                                                            ('check_in', '<=', dates_end)],
                                                            limit=1, order='check_in')
                start_times = 0.0
                end_times = 0.0
                if att_obj:
                    check_ins = pytz.UTC.localize(att_obj.check_in).astimezone(local)
                    check_outs = pytz.UTC.localize(att_obj.check_out).astimezone(local)
                    checkout_times = check_outs.time()
                    if rec.date == check_ins.date():
                        start_times = att_obj.hour_to
                        end_times = checkout_times.hour + checkout_times.minute / 60

                input_data = {
                    'employee_id': rec.employee_id.id,
                    'overtime_reason': rec.overtime_reason,
                    'date': rec.date,
                    'start_time': rec.start_time,
                    'end_time': rec.end_time,
                    'hours': rec.number_of_hours,
                    'actual_start_time': rec.start_time,
                    'actual_end_time': rec.end_time,
                    # 'actual_id': self.id,
                }
                actual_line_ids.append(input_data)
        for data in actual_line_ids:
            data['date'] =data['date'].strftime(DEFAULT_SERVER_DATE_FORMAT)
            data['actual_start_time'] = str(timedelta(hours=data['actual_start_time']))
            data['actual_end_time'] = str(timedelta(hours=data['actual_end_time']))
            data['start_time'] = str(timedelta(hours=data['start_time']))
            data['end_time'] = str(timedelta(hours=data['end_time']))
            data['hours'] = str(timedelta(hours=data['hours']))
            
        for data in attendance_line:
            if 'check_in' in data:
                if data['check_in']:
                    data['check_in'] = data['check_in'].strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                
            if 'check_out' in data:
                if data['check_out']:
                    data['check_out'] = data['check_out'].strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                
        response = {"actual_line_ids":actual_line_ids,
                    "actual_attendance_line_ids":attendance_line
                    }
        return self.get_response(200, '200', {"code":200,"data":response})
    
    
    @route(['/api/employee/get_my_actual_line_break_time'],auth='user', type='http', methods=['get'])
    def get_my_actual_line_break_time(self,id=None,**kw):
        actual_start_time = self.convert_time_to_float(kw.get('actual_start_time'))
        actual_end_time = self.convert_time_to_float(kw.get('actual_end_time'))
        date = datetime.strptime(str(kw.get('date')),"%Y-%m-%d")
        user_tz = request.env.user.employee_id.tz or pytz.utc
        local = pytz.timezone(user_tz)
        working_time = request.env.user.employee_id.resource_calendar_id
        wt_overtime_rule = working_time.overtime_rules_id
        week_working_day = working_time.week_working_day
        working_schedule_cal = request.env['employee.working.schedule.calendar'].search(
            [('employee_id', '=', request.env.user.employee_id.id)])
        shortday_schedule_cal = request.env['employee.working.schedule.calendar'].search([('is_holiday', '=', True),('dayofweek', '=', 4)])
        day_dict = []
        start_ovt_time = 0.0
        for cal in working_schedule_cal:
            # checkin = datetime.strftime(cal.checkin.astimezone(local), '%Y-%m-%d %H:%M:%S')
            # checkin = datetime.strptime(str(checkin), '%Y-%m-%d %H:%M:%S').date()
            # if checkin == date:
            #     start_ovt_time = cal.hour_to
                
            # day_dict += [checkin]
            
            if cal.date_start == date:
                start_ovt_time = cal.hour_to
            day_dict += [cal.date_start]

        shortday_dict = []
        for shortcal in shortday_schedule_cal:
            # checkin = datetime.strftime(shortcal.checkin.astimezone(local), '%Y-%m-%d %H:%M:%S')
            # checkin = datetime.strptime(str(checkin), '%Y-%m-%d %H:%M:%S').date()
            shortday_dict += [shortcal.date_start]

        # rule break time
        break_time_work_days = wt_overtime_rule.break_time_work_days
        break_time_offtime_five_days = wt_overtime_rule.break_time_offtime_five_days
        break_time_offtime_six_days = wt_overtime_rule.break_time_offtime_six_days
        break_time_off_public_holiday = wt_overtime_rule.break_time_off_public_holiday
        break_time = 0.0
        if date in shortday_dict:
            for breaks in break_time_off_public_holiday:
                if (actual_end_time - actual_start_time) >= breaks.minimum_hours:
                    break_time = breaks.break_time
                    
        elif date in day_dict:
            for breaks in break_time_work_days:
                if (actual_end_time - actual_start_time) >= breaks.minimum_hours:
                    break_time = breaks.break_time
                    
        elif date not in day_dict and week_working_day == 5:
            for breaks in break_time_offtime_five_days:
                if (actual_end_time - actual_start_time) >= breaks.minimum_hours:
                    break_time = breaks.break_time
                    
        elif date not in day_dict and week_working_day == 6:
            for breaks in break_time_offtime_six_days:
                if (actual_end_time - actual_start_time) >= breaks.minimum_hours:
                    break_time = breaks.break_time
                    
                    
        #actual hours
        working_time = request.env.user.employee_id.resource_calendar_id
        wt_overtime_rule = working_time.overtime_rules_id
        week_working_day = working_time.week_working_day
        working_schedule_cal = request.env['employee.working.schedule.calendar'].search(
            [('employee_id', '=', request.env.user.employee_id.id)])
        shortday_schedule_cal = request.env['employee.working.schedule.calendar'].search([('is_holiday', '=', True),
                                                                                        ('dayofweek', '=', 4)])

        day_dict = []
        start_ovt_time = 0.0
        for cal in working_schedule_cal:
            # checkin = datetime.strftime(cal.checkin.astimezone(local), '%Y-%m-%d %H:%M:%S')
            # checkin = datetime.strptime(str(checkin), '%Y-%m-%d %H:%M:%S').date()
            # if checkin == date:
            #     start_ovt_time = cal.hour_to
            # day_dict += [checkin]     
            if cal.date_start == date:
                start_ovt_time = cal.hour_to
            day_dict += [cal.date_start]

        shortday_dict = []
        for shortcal in shortday_schedule_cal:
            # checkin = datetime.strftime(shortcal.checkin.astimezone(local), '%Y-%m-%d %H:%M:%S')
            # checkin = datetime.strptime(str(checkin), '%Y-%m-%d %H:%M:%S').date()
            # shortday_dict += [checkin]
            shortday_dict += [shortcal.date_start]

        works_day = wt_overtime_rule.works_day
        last_works_day_line = works_day.search([], order='id desc', limit=1)
        off_days_working = wt_overtime_rule.off_days_working
        last_off_days_working_line = off_days_working.search([], order='id desc', limit=1)
        off_days_working_per_week = wt_overtime_rule.off_days_working_per_week
        last_off_days_working_per_week_line = off_days_working_per_week.search([], order='id desc', limit=1)
        off_days_public_holiday = wt_overtime_rule.off_days_public_holiday
        last_off_days_public_holiday_line = off_days_public_holiday.search([], order='id desc', limit=1)
        
        actual_hours_response = 0.0
        if actual_start_time > actual_end_time:
            actual_hour1 = 24.0 - actual_start_time
            actual_hour2 = actual_end_time - 0.0
            actual_hours = actual_hour1 + actual_hour2
        else:
            actual_hours = actual_end_time - actual_start_time
        actual_mins = actual_hours * 60
        actual_hour, actual_min = divmod(actual_mins, 60)
        if actual_mins >= wt_overtime_rule.minimum_time:
            if date in shortday_dict:
                if actual_hour > last_off_days_public_holiday_line.hour:
                    actual_hours_response = last_off_days_public_holiday_line.hour - break_time
                else:
                    actual_hours_response = actual_hours - break_time
                    
            elif date in day_dict:
                if actual_hour > last_works_day_line.hour:
                    actual_hours_response = last_works_day_line.hour - break_time
                else:
                    actual_hours_response = actual_hours - break_time
                    
            elif date not in day_dict and week_working_day == 5:
                if actual_hour > last_off_days_working_line.hour:
                    actual_hours_response =  last_off_days_working_line.hour - break_time
                else:
                    actual_hours_response = actual_hours - break_time
                    
            elif date not in day_dict and week_working_day == 6:
                if actual_hour > last_off_days_working_per_week_line.hour:
                    actual_hours_response =  last_off_days_working_per_week_line.hour - break_time
                else:
                    actual_hours_response = actual_hours - break_time

            if wt_overtime_rule.overtime_rounding_ids:
                actual_mins = actual_hours * 60
                actual_hour, actual_min = divmod(actual_mins, 60)
                for val in wt_overtime_rule.overtime_rounding_ids:
                    if round(actual_min) >= val.minutes:
                        hours = actual_hour * 60
                        hours_minutes = (hours + val.rounding) / 60
                        actual_hours_response = hours_minutes
        else:
            actual_hours_response = 0.0
            
        response = {
            "break_time":break_time,
            "actual_hours":actual_hours_response
            
            
        }
        
        return self.get_response(200, '200', {"code":200,"data":response})
    
    
        

            
    
    