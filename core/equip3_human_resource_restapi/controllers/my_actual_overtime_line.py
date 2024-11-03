    
from datetime import datetime, timedelta
from itertools import count
from odoo.http import route,request
import json
from ...restapi.controllers.helper import *


class Equip3HumanResourceMyActualOvertimeLine(RestApi):
    @route(['/api/employee/my_actual_overtime_line/','/api/employee/my_actual_overtime_line/<int:id>'],auth='user', type='http', methods=['get'])
    def get_my_actual_overtime_line(self,id=None,**kw):
        offset =  self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1)
        obj = 'hr.overtime.actual.line'
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        
        filter_str = f"lambda line:line.employee_id.id == {request.env.user.employee_id.id}"
        if kw.get("state"):
            state = kw.get("state")
            filter_str = filter_str + f" and line.state in {state}"
            
        date_from = kw.get("date_from")
        if kw.get("date_from"):
            date_from = datetime.strptime(str(kw.get('date_from')),"%Y-%m-%d") 
            filter_str = filter_str + f" and line.date.date()  >= date_from.date()"

        date_to = kw.get("date_to")
        if kw.get("date_to"):
            date_to = datetime.strptime(str(kw.get('date_to')),"%Y-%m-%d") 
            filter_str = filter_str + f" and line.date.date() <= date_to.date()"
            
        if kw.get("is_last_7"):
            query = """
            select data.id from hr_overtime_actual_line data WHERE data.date::date  >= current_date - interval '7' day and data.date::date  <= current_date  and data.employee_id = %s
            """
            request._cr.execute(query, [request.env.user.employee_id.id])
            data_result_ids = request.env.cr.dictfetchall()
            ids = []
            if len(data_result_ids) > 0:
                ids = [id['id'] for id in data_result_ids]
            filter_str = filter_str + f" and line.id in {ids}"
            
        if kw.get("is_last_30"):
            query = """
                select data.id from hr_overtime_actual_line data WHERE data.date::date  >= current_date - interval '30' day and data.date::date  <= current_date and data.employee_id = %s            
                """
            request._cr.execute(query, [request.env.user.employee_id.id])
            data_result_ids = request.env.cr.dictfetchall()
            ids = []
            if len(data_result_ids) > 0:
                ids = [id['id'] for id in data_result_ids]
            filter_str = filter_str + f" and line.id in {ids}"
        domain = []
        if kw.get("search"):
            domain.append("|")
            domain.append("|")
            domain.append(("actual_id.name","ilike",kw.get("search")))
            domain.append(("name_of_day","ilike",kw.get("search")))
            domain.append(("overtime_reason","ilike",kw.get("search")))
        data_ids = request.env[obj].sudo().search(domain).filtered(eval(filter_str,{'kw':kw,'date_from':date_from,'date_to':date_to}))
        if not data_ids:
            return self.record_not_found()
        
        request_param = {"fields":['actual_id',
                                    'employee_id',
                                    'overtime_reason',
                                    'date',
                                    'name_of_day',
                                    'actual_start_time',
                                    'actual_end_time',
                                    'actual_hours',
                                    'coefficient_hours',
                                    'amount',
                                    'state'
                                    
                                   ]}
        if not id:
            request_param = {"ids":','.join(str(data.id) for data in data_ids),"fields":['actual_id',
                                                                                         'date',
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
        
        if 'actual_start_time' in response_data[obj]:
            response_data[obj]['actual_start_time'] = str(timedelta(hours=response_data[obj]['actual_start_time']))
            
        if 'actual_end_time' in response_data[obj]:
            response_data[obj]['actual_end_time'] = str(timedelta(hours=response_data[obj]['actual_end_time']))
            
        if 'actual_hours' in response_data[obj]:
            response_data[obj]['actual_hours'] = str(timedelta(hours=response_data[obj]['actual_hours']))
            
        page_total  = self.get_total_page(len(data_ids),PAGE_DATA_LIMIT)
        return self.get_response(200, '200', {"code":200,"data":response_data[obj],"page_total":page_total if not id else 0})