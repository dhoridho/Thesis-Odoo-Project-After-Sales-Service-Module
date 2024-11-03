from datetime import datetime, timedelta
from itertools import count
from odoo.http import route,request
import json
from ...restapi.controllers.helper import *


class Equip3HumanResourceRestAPITrainingList(RestApi):
    @route(['/api/employee/my_training_list/','/api/employee/my_training_list/<int:id>'],auth='user', type='http', methods=['get'])
    def get_employee_training_histories(self,id=None,**kw):
        now = datetime.now()
        last_7 = now.date() + timedelta(days=-7)
        last_30 = now.date() + timedelta(days=-30)
        offset =  self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1)
        obj = 'training.histories'
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        
        filter_str = f"lambda line:line"
        if kw.get("state"):
            status = kw.get("state")
            filter_str = filter_str + f" and line.state in {status}"

        if kw.get("course_ids"):
            course_ids = kw.get("course_ids")
            filter_str = filter_str + f" and any(course in line.course_ids.ids for course in {course_ids})"
            
        date_from = kw.get("date_from")
        if kw.get("date_from"):
            date_from = datetime.strptime(str(kw.get('date_from')),"%Y-%m-%d") 
            filter_str = filter_str + f" and line.start_date.date()  >= date_from.date()"
        
        date_to = kw.get("date_to")
        if kw.get("date_to"):
            date_to = datetime.strptime(str(kw.get('date_to')),"%Y-%m-%d") 
            filter_str = filter_str + f" and line.end_date.date() <= date_to.date()"
            
        if kw.get("is_last_7"):
            filter_str = filter_str + f" and last_7 >= line.start_date.date() and line.start_date.date() <= now.date()"
        if kw.get("is_last_30"):
            filter_str = filter_str + f" and last_30 >= line.start_date.date() and line.start_date.date() <= now.date()"
        
        domain = [('employee_id','=',request.env.user.employee_id.id)]
        if kw.get("is_last_7") or kw.get("is_last_30") or kw.get("date_from") or kw.get("date_to"):
            domain.append(('start_date','!=',False))
        if kw.get("search"):
            domain.append(("name","ilike",kw.get("search")))
    
        data_ids = request.env[obj].sudo().search(domain).filtered(eval(filter_str,{'kw':kw,
                                                                                    'date_from':date_from,
                                                                                    'date_to':date_to,
                                                                                    'now':now,
                                                                                    'last_7':last_7,
                                                                                    'last_30':last_30
                                                                                    }))
        if not data_ids:
            return self.record_not_found()
        
        request_param = {"fields":['state',
                                    'name',
                                    'employee_id',
                                    'start_date',
                                    'end_date',
                                    'job_id',
                                    'course_ids',
                                    'training_required',
                                    'training_context'
                                    
                                   ]}
        if not id:
            request_param = {"ids":','.join(str(data.id) for data in data_ids),"fields":['name',
                                                                                         'start_date',
                                                                                         'course_ids',
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
        
        if not id:
            for data in response_data[obj]:
                if data['course_ids']:
                    data['course_ids'] = self.convert_one2many('training.courses',{"fields":['name'],"ids":','.join(str(id) for id in data['course_ids'])},user)
                
        if 'course_ids' in response_data[obj]:
            if len(response_data[obj]['course_ids']) >= 1:
                response_data[obj]['course_ids'] = self.convert_one2many('training.courses',{"fields":['name'],
                                                                                                                    "ids":','.join(str(data) for data in response_data[obj]['course_ids'])},user)
        page_total  = self.get_total_page(len(data_ids),PAGE_DATA_LIMIT)
        return self.get_response(200, '200', {"code":200,
                                              "data":response_data[obj],
                                              "page_total":page_total if not id else 0
                                              })
    