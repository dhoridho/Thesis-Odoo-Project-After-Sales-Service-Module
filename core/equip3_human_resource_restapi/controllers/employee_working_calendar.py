from datetime import datetime, timedelta
from itertools import count
from odoo.http import route,request
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from ...restapi.controllers.helper import RestApi
import pytz
import json


class Equip3HumanResourceRestApiWorkingCalendar(RestApi):
    @route('/api/employee/working_calendar',auth='user', type='http', methods=['get'])
    def get_working_calendar(self, **kw):
        now = datetime.now()
        obj = 'employee.working.schedule.calendar'
        offset =  self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1)
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        
        year = now.year
        if kw.get('year'):
            year = int(kw.get('year'))
            
        filter_str = f"lambda line:line.checkin.year == {year} "
        if kw.get('month'):
            filter_str = filter_str +"and line.checkin.month == int(kw.get('month'))"
            
        if kw.get('day'):
            filter_str = filter_str +" and line.checkin.day == int(kw.get('day'))"
        
        # print(eval(filter_str,{'kw':kw}))
        work_calendar = request.env[obj].sudo().search([('employee_id','=',request.env.user.employee_id.id)],order="id asc").filtered(eval(filter_str,{'kw':kw}))
        if not work_calendar:
            return self.record_not_found()
        user_tz = request.env.user.employee_id.tz or pytz.utc
        local = pytz.timezone(user_tz)
        calendar_data_ids = [data.checkin.strftime("%Y-%m-%d") for data in work_calendar]
        final_calendar_data_ids= sorted(list(set(calendar_data_ids)),key=lambda line: datetime.strptime(line, "%Y-%m-%d"))
        to_response = []
        for date_use in final_calendar_data_ids:
             work_calendar_employee = request.env[obj].sudo().search([('employee_id','=',request.env.user.employee_id.id)]).filtered(lambda line:line.checkin.strftime("%Y-%m-%d") == date_use)
             if work_calendar_employee:
                 to_response.append({"date":date_use,
                                     "employee_data":[{"name":data.employee_id.name,
                                                       "hour_from":str(timedelta(hours=data.hour_from)),
                                                       "hour_to": str(timedelta(hours=data.hour_to)),
                                                       "checkin":datetime.strftime(data.checkin.astimezone(local), '%Y-%m-%d %H:%M:%S')  if data.checkin else "-",
                                                       "checkout":datetime.strftime(data.checkout.astimezone(local), '%Y-%m-%d %H:%M:%S')  if data.checkout else "-",
                                                       "start_checkin":datetime.strftime(data.start_checkin.astimezone(local), '%Y-%m-%d %H:%M:%S')  if data.start_checkin else "-" ,                                                     
                                                       "end_checkout":datetime.strftime(data.end_checkout.astimezone(local), '%Y-%m-%d %H:%M:%S')  if data.end_checkout else "-" ,                                                     
                                                       }for data in work_calendar_employee]
                                     })
            
        return self.get_response(200, '200', {"code":200,
                                              "data":to_response
                                              })

        