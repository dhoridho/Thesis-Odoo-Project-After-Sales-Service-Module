from datetime import datetime, timedelta
from itertools import count
from odoo.http import route,request
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from ...restapi.controllers.helper import *
import json
import pytz
from pytz import timezone


class Equip3HumanResourceMyAttendance(RestApi):
    @route('/api/employee/create/attedance_offline',auth='user', type='json', methods=['POST'])
    @authenticate
    def create_attendance(self,**kw):
        user_tz = request.env.user.employee_id.tz or pytz.utc or 'UTC'
        local = pytz.timezone(user_tz)
        request_data = request.jsonrequest
        now =  datetime.now(timezone(user_tz))
        now = now.replace(tzinfo=None)
        offset = local.utcoffset(now, is_dst = False).total_seconds()/3600
        check_in = False
        if request_data.get('check_in'):
            check_in  = datetime.strptime(str(request_data.get('check_in')),DEFAULT_SERVER_DATETIME_FORMAT)

        check_in = check_in + timedelta(hours=-offset)
        check_out = False
        if request_data.get('check_out'):
            check_out  = datetime.strptime(str(request_data.get('check_out')),DEFAULT_SERVER_DATETIME_FORMAT)
            check_out = check_out + timedelta(hours=-offset)
            
        data_create = request.env['hr.attendance.offline'].sudo().create({
                                'start_working_date':now.date(),
                                "employee_id":request.env.user.employee_id.id,
                                'check_in':check_in,
                                'check_in_latitude':request_data.get('check_in_latitude'),
                                'check_in_longitude':request_data.get('check_in_longitude'),
                                'webcam_check_in':request_data.get('webcam_check_in'),
                                'check_in_address':request_data.get('check_in_address'),
                                'check_out':check_out,
                                'check_out_latitude':request_data.get('check_out_latitude'),
                                'check_out_longitude':request_data.get('check_out_longitude'),
                                'webcam_check_out':request_data.get('webcam_check_out'),
                                'check_in_face_distance':request_data.get('check_in_face_distance',),
                                'check_out_face_distance':request_data.get('check_out_face_distance',)
                                
                                 
                                 })
        data_create.onchange_employee()
     
        if not data_create:
            return self.update_create_failed()
           
        return self.get_response(200, '200', {"code":200, 
                                              "id":data_create.id,
                                              "message":"create attendance offline Suscessfull"
                                              })
    
    
    @route(['/api/employee/my_attendance_offline','/api/employee/my_attendance_offline/<int:id>'],auth='user', type='http', methods=['get'])
    @authenticate
    def get_employee_attendance_offline(self,id=None,**kw):
        now = datetime.now()
        user_tz = request.env.user.employee_id.tz or pytz.utc or 'UTC'
        local = pytz.timezone(user_tz)
        offset_time = local.utcoffset(now, is_dst = False).total_seconds()/3600
        offset =  self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1)
        obj = 'hr.attendance.offline'
        filter_str = f"lambda line:line"
        if kw.get("attendance_status"):
            filter_str = filter_str + f" and line.attendance_status in [kw.get('attendance_status')]"
            
        date_from = kw.get("date_from")
        if date_from:
            date_from = datetime.strptime(str(kw.get('date_from')),"%Y-%m-%d") 
            filter_str = filter_str + f" and line.start_working_date >= date_from.date()"

        date_to = kw.get("date_to")
        if date_to:
            date_to = datetime.strptime(str(kw.get('date_to')),"%Y-%m-%d") 
            filter_str = filter_str + f" and line.start_working_date <= date_to.date()"
            
        if kw.get("is_last_7"):
            query = """
            select ha.id from hr_attendance_offline ha WHERE ha.start_working_date  >= current_date - interval '7' day and ha.start_working_date  <= current_date and  ha.employee_id = %s
            """
            request._cr.execute(query, [request.env.user.employee_id.id])
            attendance_result_ids = request.env.cr.dictfetchall()
            ids = []
            if len(attendance_result_ids) > 0:
                ids = [id['id'] for id in attendance_result_ids]
            filter_str = filter_str + f" and line.id in {ids}"
        if kw.get("is_last_30"):
            query = """
                select ha.id from hr_attendance_offline ha WHERE ha.start_working_date  >= current_date - interval '30' day and ha.start_working_date  <= current_date and ha.employee_id = %s            
                """
            request._cr.execute(query, [request.env.user.employee_id.id])
            attendance_result_ids = request.env.cr.dictfetchall()
            ids = []
            if len(attendance_result_ids) > 0:
                ids = [id['id'] for id in attendance_result_ids]
            filter_str = filter_str + f" and line.id in {ids}"
            
        domain = [('employee_id','=',request.env.user.employee_id.id)]
        if kw.get("search"):
            domain.append("|")
            domain.append(("attendance_status",'ilike',kw.get("search")))
            domain.append(("count_status",'ilike',kw.get("search")))
        attendance_ids = request.env[obj].sudo().search(domain).filtered(eval(filter_str,{'kw':kw,'date_from':date_from,'date_to':date_to}))
        if not attendance_ids:
            return self.record_not_found()
        request_param = {"fields":['start_working_date',
                                   'attendance_status',
                                   'sequence_code',
                                   'department_id',
                                   'job_id',
                                   'working_schedule_id',
                                   'active_location_ids',
                                   'hour_from',
                                   'hour_to',
                                   'check_in',
                                   'check_in_diff',
                                   'checkin_status',
                                   'check_out',
                                   'check_out_diff',
                                   'checkout_status',
                                   'tolerance_late',
                                   'minimum_hours',
                                   'worked_hours',
                                   'webcam_check_in',
                                   'webcam_check_out',
                                   'check_in_address',
                                   'check_in_latitude',
                                   'check_in_longitude',
                                   'check_out_latitude',
                                   'check_out_longitude',
                                   'check_out_address',
                                   'check_in_face_distance',
                                   'check_out_face_distance',
                                   ]}
        if not id:
            request_param = {"ids":','.join(str(data.id) for data in attendance_ids),"fields":['start_working_date','attendance_status','check_in','check_out'],
                             "order":"start_working_date desc",
                            "offset":offset,
                             "limit":PAGE_DATA_LIMIT
                             }
            
        read_record = self.perform_request(obj,id=id, kwargs=request_param, user=request.env.user)
        print("read_record")
        print(read_record.data)
        response_data = json.loads(read_record.data)
        
        if not obj in response_data:
           return self.record_not_found()
       
        if not id:
            for data in response_data[obj]:
                if 'check_in' in data:
                    if data['check_in']:
                        true_time = datetime.strptime(data['check_in'],DEFAULT_SERVER_DATETIME_FORMAT)  + timedelta(hours=offset_time)
                        data['check_in'] =  true_time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                if 'check_out' in data:
                    if data['check_out']:
                        true_time = datetime.strptime(data['check_out'],DEFAULT_SERVER_DATETIME_FORMAT)  + timedelta(hours=offset_time)
                        data['check_out'] =  true_time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        if 'check_in' in response_data[obj]:
            if response_data[obj]['check_in']:
                true_time = datetime.strptime(response_data[obj]['check_in'],DEFAULT_SERVER_DATETIME_FORMAT)  + timedelta(hours=offset_time)
                response_data[obj]['check_in'] =  true_time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            
        if 'check_out' in response_data[obj]:
            if response_data[obj]['check_out']:
                true_time_checkout = datetime.strptime(response_data[obj]['check_out'],DEFAULT_SERVER_DATETIME_FORMAT)  + timedelta(hours=offset_time)
                response_data[obj]['check_out'] =  true_time_checkout.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
       
        if 'active_location_ids' in response_data[obj]:
            response_data[obj]['active_location_ids'] = self.convert_one2many('res.partner',{"fields":['name'],
                                                                                     "ids":','.join(str(data) for data in response_data[obj]['active_location_ids'])},request.env.user)
        if 'check_in_diff' in response_data[obj]:
            response_data[obj]['check_in_diff'] = str(timedelta(hours=response_data[obj]['check_in_diff']))
            
        if 'check_out_diff' in response_data[obj]:
            response_data[obj]['check_out_diff'] = str(timedelta(hours=response_data[obj]['check_out_diff']))
            
        if 'hour_from' in response_data[obj]:
            response_data[obj]['hour_from'] = str(timedelta(hours=response_data[obj]['hour_from']))
            
        if 'hour_to' in response_data[obj]:
            response_data[obj]['hour_to'] = str(timedelta(hours=response_data[obj]['hour_to']))
            
        if 'tolerance_late' in response_data[obj]:
            response_data[obj]['tolerance_late'] = str(timedelta(hours=response_data[obj]['tolerance_late']))
            
        if 'minimum_hours' in response_data[obj]:
            response_data[obj]['minimum_hours'] = str(timedelta(hours=response_data[obj]['minimum_hours']))
            
        page_total  = self.get_total_page(len(attendance_ids),PAGE_DATA_LIMIT)
        return self.get_response(200, '200', {"code":200,
                                              "data":response_data[obj],
                                              "page_total":page_total if not id else 0
                                              })