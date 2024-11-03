from datetime import datetime, timedelta
from itertools import count
import random
import string
from odoo.http import route,request
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from ...restapi.controllers.helper import *
import json
import pytz
from pytz import timezone


class Equip3HumanResourceMyAttendance(RestApi):
    
    def generate_random_string(self,length):
        letters = string.ascii_letters
        return ''.join(random.choice(letters) for _ in range(length))
    
    
    @route('/api/employee/attendance_reason',auth='user',type='http', methods=['get'])
    @authenticate
    def get_attendance_reason(self,**kw):
        obj = 'hr.attendance.reason.categ'
        domain = []
        if kw.get("search"):
            domain.append(('name', 'ilike', kw.get("search")))
        data_count = request.env[obj].with_context({'from_api': True}).search_count(domain)
        limit = int(kw.get('limit')) if 'limit' in kw else False
        offset = self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1, limit=limit)
        request_param = {"fields": ['name'],
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

    @route(['/api/employee/token/attedance'],auth='user', type='json', methods=['POST'])
    @authenticate
    def generate_token_attendance(self,**kw):
        user_tz = request.env.user.employee_id.tz or pytz.utc or 'UTC'
        now =  datetime.now(timezone(user_tz))
        string_length = 10
        random_string = self.generate_random_string(string_length)
        expire = datetime.now() + timedelta(hours=1)
        localtz = pytz.timezone(request.env.user.tz if request.env.user.tz else'Asia/Jakarta')
        token = request.env['kiosk.attendance.token.log'].create({'user_id':request.env.user.id,'token':random_string,'expired_date':expire})
        
        return self.get_response(200, '200', {"code":200, 
                                              "token":token.token,
                                              "expired_date":token.expired_date.astimezone(localtz).strftime("%Y-%m-%d %H:%M:%S"),
                                              "message":"generate token is Suscessfull"
                                              })
        
    @route(['/api/employee/check_in/attedance','/api/employee/check_in/attedance/<int:employee_id>'],auth='user', type='json', methods=['POST'])
    def check_in_attendance(self,employee_id=None,**kw):
        user_tz = request.env.user.employee_id.tz or pytz.utc or 'UTC'
        local = pytz.timezone(user_tz)
        request_data = request.jsonrequest
        now =  datetime.now(timezone(user_tz))
        now = now.replace(tzinfo=None)
        auth, user, invalid = self.valid_authentication(kw)
        check_in = False
        if request_data.get('check_in'):
            check_in  = datetime.strptime(str(request_data.get('check_in')),DEFAULT_SERVER_DATETIME_FORMAT)
        offset = local.utcoffset(now, is_dst = False).total_seconds()/3600
        check_in = check_in + timedelta(hours=-offset)
        now = now  + timedelta(hours=-offset)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        data_create = request.env['hr.attendance'].sudo().create({
                                'employee_id':request.env.user.employee_id.id if not employee_id else employee_id,
                                # 'sequence_code':request_data.get('sequence_code'),
                                'start_working_date':now.date(),
                                'check_in':now.strftime("%Y-%m-%d %H:%M:%S"),
                                'check_in_latitude':request_data.get('check_in_latitude'),
                                'check_in_longitude':request_data.get('check_in_longitude'),
                                'webcam_check_in':request_data.get('webcam_check_in'),
                                'check_in_address':request_data.get('check_in_address'),
                                'check_in_reason_categ':request_data.get('check_in_reason_categ') if 'check_in_reason_categ' in request_data else False,
                                'check_in_notes':request_data.get('check_in_notes') if 'check_in_notes' in request_data else '',
                                'active_location_id':[(6,0,request_data.get('active_location_id'))]
                                 })
     
        if not data_create:
            return self.update_create_failed()
        return self.get_response(200, '200', {"code":200, 
                                              "id":data_create.id,
                                              "message":"Check in Suscessfull"
                                              })
        
    @route(['/api/employee/check_out/attedance/<int:id>'],auth='user', type='json', methods=['PUT'])
    def check_out_attendance(self,id,**kw):
        user_tz = request.env.user.employee_id.tz or pytz.utc or 'UTC'
        local = pytz.timezone(user_tz)
        utc = pytz.timezone('UTC')
        request_data = request.jsonrequest
        now =  datetime.now(timezone(user_tz))
        now = now.replace(tzinfo=None)
        auth, user, invalid = self.valid_authentication(kw)
        check_out = False
        if request_data.get('check_out'):
            check_out  = datetime.strptime(str(request_data.get('check_out')),DEFAULT_SERVER_DATETIME_FORMAT)

        offset = local.utcoffset(now, is_dst = False).total_seconds()/3600
        check_out = check_out + timedelta(hours=-offset)
        now = now  + timedelta(hours=-offset)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        data_update = request.env['hr.attendance'].sudo().search([('id','=',id)])
        data_update.write({'check_out':now.strftime("%Y-%m-%d %H:%M:%S"),
                           'check_out_latitude':request_data.get('check_out_latitude'),
                           'check_out_longitude':request_data.get('check_out_longitude'),
                           'webcam_check_out':request_data.get('webcam_check_out'),
                           'check_out_address':request_data.get('check_out_address'),
                            'active_location_id':[(6,0,request_data.get('active_location_id'))],
                            'check_out_reason_categ':request_data.get('check_out_reason_categ') if 'check_out_reason_categ' in request_data else False,
                            'check_out_notes':request_data.get('check_out_notes') if 'check_out_notes' in request_data else '',
                            # 'sequence_code':request_data.get('sequence_code'),
                           
                           })
     
        if not data_update:
            return self.update_create_failed()
           
        return self.get_response(200, '200', {"code":200,
                                              "message":"Check out Suscessfull"
                                              })
    
    @route(['/api/user/attendance'],auth='user', type='http', methods=['get'])
    @authenticate
    def get_employee_current_attendance(self,**kw):
        check_in = '-'
        check_out = '-'
        check_in_id = '-'
        localtz = pytz.timezone(request.env.user.tz if request.env.user.tz else'Asia/Jakarta')
        query = """
        select ha.id,ha.check_in,ha.check_out from hr_attendance ha WHERE ha.employee_id = %s ORDER BY ID DESC LIMIT 1
        """
        request._cr.execute(query, [request.env.user.employee_id.id])
        my_attendance = request.env.cr.dictfetchone()
        if my_attendance:
            if  my_attendance['check_in']:
                work_calendar = request.env['employee.working.schedule.calendar'].sudo().search([('employee_id','=',request.env.user.employee_id.id)]).filtered(lambda line:line.checkin.year ==  int(my_attendance['check_in'].astimezone(localtz).year) 
                                                                                                                                                                and line.checkin.month == int(my_attendance['check_in'].astimezone(localtz).month)
                                                                                                                                                                and line.checkin.day == int(my_attendance['check_in'].astimezone(localtz).day))

                if work_calendar:
                    end_time_checkout = datetime.strptime(work_calendar[0].end_checkout.astimezone(localtz).strftime('%Y-%m-%d %H:%M:%S'), '%Y-%m-%d %H:%M:%S')
                    current_time = datetime.strptime(datetime.now().astimezone(localtz).strftime('%Y-%m-%d %H:%M:%S'), '%Y-%m-%d %H:%M:%S')
                    if current_time < end_time_checkout:
                        check_in = my_attendance['check_in'].astimezone(localtz).strftime("%H:%M:%S %p") if my_attendance['check_in'] else  '-'
                        check_out = my_attendance['check_out'].astimezone(localtz).strftime("%H:%M:%S %p") if my_attendance['check_out'] else  '-'
                        check_in_id = my_attendance['id'] if my_attendance['id'] else  '-'
                        
        attendance ={
            "check_in_id":check_in_id,
            "check_in":check_in,
            "check_out":check_out,
        }
        
        return self.get_response(200, '200', {"code":200,"data":attendance})
    
       
    @route(['/api/user/face_table'],auth='user', type='http', methods=['get'])
    @authenticate
    def get_employee_face_table(self,**kw):
        res_users_image_ids = [{"id":data.id,
                                'name':data.name,
                                'image':data.image.decode("utf-8") if data.image else "-",
                                'image_detection':data.image_detection.decode("utf-8") if data.image_detection else "-",
                                "descriptor":data.descriptor,
                                "is_cropped":data.is_cropped
                                } for data in request.env.user.res_users_image_ids.filtered(lambda line:line.is_cropped)]
        
        return self.get_response(200, '200', {"code":200,"data":res_users_image_ids})
           
        
    
    
    @route(['/api/employee/my_attendance','/api/employee/my_attendance/<int:id>'],auth='user', type='http', methods=['get'])
    def get_employee_attendance(self,id=None,**kw):
        now = datetime.now()
        user_tz = request.env.user.employee_id.tz or pytz.utc or 'UTC'
        local = pytz.timezone(user_tz)
        offset_time = local.utcoffset(now, is_dst = False).total_seconds()/3600
        offset =  self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1)
        obj = 'hr.attendance'
        auth, user, invalid = self.valid_authentication(kw)
        filter_str = f"lambda line:line"
        if kw.get("attendance_status"):
            filter_str = filter_str + f" and line.attendance_status in [kw.get('attendance_status')]"
        date_from = kw.get("date_from")
        if kw.get("date_from"):
            date_from = datetime.strptime(str(kw.get('date_from')),"%Y-%m-%d") 
            filter_str = filter_str + f" and line.start_working_date >= date_from.date()"

        date_to = kw.get("date_to")
        if kw.get("date_to"):
            date_to = datetime.strptime(str(kw.get('date_to')),"%Y-%m-%d") 
            filter_str = filter_str + f" and line.start_working_date <= date_to.date()"
            
        if kw.get("is_last_7"):
            query = """
            select ha.id from hr_attendance ha WHERE ha.start_working_date  >= current_date - interval '7' day and ha.start_working_date  <= current_date and  ha.employee_id = %s
            """
            request._cr.execute(query, [request.env.user.employee_id.id])
            attendance_result_ids = request.env.cr.dictfetchall()
            ids = []
            if len(attendance_result_ids) > 0:
                ids = [id['id'] for id in attendance_result_ids]
            filter_str = filter_str + f" and line.id in {ids}"
        if kw.get("is_last_30"):
            query = """
                select ha.id from hr_attendance ha WHERE ha.start_working_date  >= current_date - interval '30' day and ha.start_working_date  <= current_date and ha.employee_id = %s            
                """
            request._cr.execute(query, [request.env.user.employee_id.id])
            attendance_result_ids = request.env.cr.dictfetchall()
            ids = []
            if len(attendance_result_ids) > 0:
                ids = [id['id'] for id in attendance_result_ids]
            filter_str = filter_str + f" and line.id in {ids}"
            
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
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
                                   'active_location_id',
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
                                   'hr_attendance_change_id',
                                   'webcam_check_in',
                                   'webcam_check_out',
                                   'check_in_address',
                                   'check_in_latitude',
                                   'check_in_longitude',
                                   'check_out_latitude',
                                   'check_out_longitude',
                                   'check_out_address'
                                   ]}
        if not id:
            request_param = {"ids":','.join(str(data.id) for data in attendance_ids),"fields":['start_working_date','attendance_status','check_in','check_out'],
                             "order":"start_working_date desc",
                            "offset":offset,
                             "limit":PAGE_DATA_LIMIT
                             }
        read_record = self.perform_request(obj,id=id, kwargs=request_param, user=user)
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
       
        if 'active_location_id' in response_data[obj]:
            response_data[obj]['active_location_id'] = self.convert_one2many('res.partner',{"fields":['name'],
                                                                                     "ids":','.join(str(data) for data in response_data[obj]['active_location_id'])},user)
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
        
    
    @route(['/api/attendance/employee/all'],auth='user', type='http', methods=['get'])
    @authenticate
    def get_all_employee_attendance(self,id=None,**kw):
        obj = 'hr.employee'
        domain = []
        request_param = {"fields":['name','sequence_code','last_attendance_id','user_id']}
        if kw.get("search"):
            domain.append(("name",'ilike',kw.get("search")))
            employee_ids = request.env[obj].sudo().search(domain)
            request_param['ids'] = ','.join(str(data.id) for data in employee_ids)
        
        try:
            read_record = self.perform_request(obj,id=id, kwargs=request_param, user=request.env.user)
            response_data = json.loads(read_record.data)
            if not obj in response_data:
                return self.record_not_found()
        except json.decoder.JSONDecodeError:
            return self.get_response(500, '500', {"code":500,
                                              "data":read_record.data
                                              })
            
        
        user_tz = request.env.user.tz or pytz.utc
        local = timezone(user_tz)
        
        
        for data in response_data[obj]:
            if 'last_attendance_id' in data and data['last_attendance_id']:
                hr_attendance = request.env['hr.attendance'].browse([data['last_attendance_id'][0]])
                if hr_attendance:
                    data['last_attendance_id'] = {'id':hr_attendance.id,
                                                  'check_in':datetime.strftime(hr_attendance.check_in.astimezone(local), DEFAULT_SERVER_DATETIME_FORMAT) if hr_attendance.check_in  else False,
                                                  'check_out':datetime.strftime(hr_attendance.check_out.astimezone(local), DEFAULT_SERVER_DATETIME_FORMAT) if hr_attendance.check_out  else False
                                                  }
            if data['user_id']:
                res_users_image = request.env['res.users.image'].sudo().search([('res_user_id','=',data['user_id'][0])])
                if res_users_image:
                    data['decryptor'] = [{'image':img.descriptor  if img.descriptor else '-'} for img in  res_users_image]
            else:
                data['decryptor'] = []
           
        return self.get_response(200, '200', {"code":200,
                                              "data":response_data[obj]
                                              })
        