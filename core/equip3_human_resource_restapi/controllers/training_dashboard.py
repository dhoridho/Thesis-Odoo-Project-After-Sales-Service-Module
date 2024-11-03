from datetime import datetime, timedelta
from itertools import count
from odoo.http import route,request
from ...restapi.controllers.helper import RestApi
import pytz
import json


class Equip3HumanResourceRestApiTrainingDashboard(RestApi):
    @route('/api/employee/training_dashboard',auth='user', type='http', methods=['get'])
    def get_training_dashboard(self, **kw):
        now = datetime.now()
        obj = 'training.conduct.line'
        offset =  self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1)
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        
        year = now.year
        if kw.get('year'):
            year = int(kw.get('year'))
        domain = [('employee_id','=',request.env.user.employee_id.id),('start_date','!=',False)]
        filter_str = f"lambda line:line.start_date.year == {year} "
        if kw.get('month'):
            filter_str = filter_str +"and line.start_date.month == int(kw.get('month'))"
            
        if kw.get('date'):
            filter_str = filter_str +" and line.start_date.date == int(kw.get('date'))"
            
        training_conduct_line = request.env[obj].sudo().search(domain,order="id asc").filtered(eval(filter_str,{'kw':kw}))
        if not training_conduct_line:
            return self.record_not_found()
        
        calendar_data_ids = [data.start_date.strftime("%Y-%m-%d") for data in training_conduct_line]
        final_calendar_data_ids= sorted(list(set(calendar_data_ids)),key=lambda line: datetime.strptime(line, "%Y-%m-%d"))
        to_response = []
        for date_use in final_calendar_data_ids:
             training_to_use = request.env[obj].sudo().search([('employee_id','=',request.env.user.employee_id.id),('start_date','!=',False)]).filtered(lambda line:line.start_date.strftime("%Y-%m-%d") == date_use)
             if training_to_use:
                 for data in training_to_use:
                    to_response.append({"name":data.name,
                                        "start_date":date_use,
                                        "end_date":data.end_date.strftime("%Y-%m-%d"),
                                        "course_id":[data.course_id.id,data.course_id.name]
                                        
                                        })
            
        return self.get_response(200, '200', {"code":200,
                                              "data":to_response
                                              })