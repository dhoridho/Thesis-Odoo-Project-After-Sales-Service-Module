
from datetime import datetime, timedelta
from itertools import count
from odoo.http import route,request
import json
from ...restapi.controllers.helper import *


class Equip3HumanResourceMyleaveBalance(RestApi):
    @route(['/api/employee/my_leave_balance','/api/employee/my_leave_balance/<int:id>'],auth='user', type='http', methods=['get'])
    def get_employee_leave_balance(self,id=None,**kw):
        offset =  self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1)
        obj = 'hr.leave.balance'
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        filter_str = f"lambda line:line"
        if kw.get("holiday_status_id"):
            holiday_status_ids = kw.get("holiday_status_id")
            filter_str = filter_str + f" and line.holiday_status_id.id in {holiday_status_ids}"
        date_from = kw.get("date_from")
        if kw.get("date_from"):
            date_from = datetime.strptime(str(kw.get('date_from')),"%Y-%m-%d") 
            filter_str = filter_str + f" and line.start_date  >= date_from.date()"

        date_to = kw.get("date_to")
        if kw.get("date_to"):
            date_to = datetime.strptime(str(kw.get('date_to')),"%Y-%m-%d") 
            filter_str = filter_str + f" and line.start_date <= date_to.date()"
            
        if kw.get("is_last_7"):
            query = """
            select data.id from hr_leave_balance data WHERE data.start_date  >= current_date - interval '7' day and data.start_date  <= current_date  and data.employee_id = %s
            """
            request._cr.execute(query, [request.env.user.employee_id.id])
            data_result_ids = request.env.cr.dictfetchall()
            ids = []
            if len(data_result_ids) > 0:
                ids = [id['id'] for id in data_result_ids]
            filter_str = filter_str + f" and line.id in {ids}"
        if kw.get("is_last_30"):
            query = """
                select data.id from hr_leave_balance data WHERE data.start_date  >= current_date - interval '30' day and data.start_date  <= current_date and data.employee_id = %s            
                """
            request._cr.execute(query, [request.env.user.employee_id.id])
            data_result_ids = request.env.cr.dictfetchall()
            ids = []
            if len(data_result_ids) > 0:
                ids = [id['id'] for id in data_result_ids]
            filter_str = filter_str + f" and line.id in {ids}"
        domain  = [('employee_id','=',request.env.user.employee_id.id)]
        if kw.get("search"):
            domain.append(("code","ilike",kw.get("search")))
            
        data_ids = request.env[obj].sudo().search(domain).filtered(eval(filter_str,{'kw':kw,'date_from':date_from,'date_to':date_to}))
        if not data_ids:
            return self.record_not_found()
        request_param = {"fields":['holiday_status_id',
                                    'remaining',
                                    'code',
                                    'current_period',
                                    'assigned',
                                    'bring_forward',
                                    'extra_leave',
                                    'start_date',
                                    'leave_entitlement',
                                    'used',
                                    'carry_forward'
                                    
                                    
                                    ]}
        if not id:
            request_param = {"ids":','.join(str(data.id) for data in data_ids),"fields":['holiday_status_id',
                                                                                         'remaining'
                                                                                         ],
                             "order":"id desc",
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