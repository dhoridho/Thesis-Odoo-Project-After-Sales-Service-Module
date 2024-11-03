from datetime import datetime, timedelta,date
from itertools import count
from odoo.http import route,request
from ...restapi.controllers.helper import *
import json
from dateutil.relativedelta import relativedelta


class Equip3HumanResourceMyAllocationRequest(RestApi):
    @route('/api/user/create/my_allocation_request',auth='user', type='json', methods=['POST'])
    def create_my_allocation_request(self,**kw):
        request_data = request.jsonrequest
        auth, user, invalid = self.valid_authentication(kw)
        date_from  = datetime.strptime(str(request_data.get('allocation_date_from')),"%Y-%m-%d")
        date_to = datetime.strptime(str(request_data.get('allocation_date_to')),"%Y-%m-%d")  
        effective_date = datetime.strptime(str(request_data.get('effective_date')),"%Y-%m-%d")  
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        allocation = request.env['hr.leave.allocation'].sudo().create({
                                 'name':request_data.get('name'),
                                 "overtime_id":request_data.get("overtime_id"),
                                'holiday_status_id':int(request_data.get('holiday_status_id')),
                                 'allocation_date_from':date_from,
                                 'allocation_date_to':date_to,
                                 'effective_date':effective_date,
                                 'allocation_type_by':request_data.get('allocation_type_by'),
                                 'allocation_half_day':request_data.get('allocation_half_day'),
                                 'allocation_date_from_period':request_data.get('allocation_date_from_period'),
                                'employee_id': request.env.user.employee_id.id,
                                'notes': request_data.get('notes'),
                                 })
        allocation._onchange_holiday_status_id()
        if request_data.get("state")  == "confirm":
            allocation.action_confirm()
        if not allocation:
            return self.update_create_failed()   
        return self.get_response(200, '200', {"code":200, 
                                              "message":"Create My Allocation Request Suscessfull"
                                              })
        
    @route('/api/user/update/my_allocation_request/<int:id>',auth='user', type='json', methods=['put'])
    def update_my_allocation_request(self,id=None,**kw):
        request_data = request.jsonrequest
        auth, user, invalid = self.valid_authentication(kw)
        date_from  = datetime.strptime(str(request_data.get('allocation_date_from')),"%Y-%m-%d")
        date_to = datetime.strptime(str(request_data.get('allocation_date_to')),"%Y-%m-%d")  
        effective_date = datetime.strptime(str(request_data.get('effective_date')),"%Y-%m-%d")  
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        
        allocation = request.env['hr.leave.allocation'].sudo().search([('id','=',id)])
        if not allocation:
            return self.record_not_found()  
        
        allocation.write({'name':request_data.get('name'),
                          "overtime_id":request_data.get("overtime_id"),
                          'holiday_status_id':int(request_data.get('holiday_status_id')),
                          'allocation_date_to':date_to,
                          'effective_date':effective_date,
                          'allocation_type_by':request_data.get('allocation_type_by'),
                          'allocation_half_day':request_data.get('allocation_half_day'),
                          'allocation_date_from_period':request_data.get('allocation_date_from_period'),
                          'notes': request_data.get('notes'),
                                 })
        allocation._onchange_holiday_status_id()
        if request_data.get("state")  == "confirm":
            allocation.action_confirm()
        if not allocation:
            return self.update_create_failed()   
        return self.get_response(200, '200', {"code":200, 
                                              "message":"Update My Allocation Request Suscessfull"
                                              })
    
    @route(['/api/employee/my_allocation','/api/employee/my_allocation/<int:id>'],auth='user', type='http', methods=['get'])
    def get_employee_allocation(self,id=None,**kw):
        offset =  self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1)
        obj = 'hr.leave.allocation'
        auth, user, invalid = self.valid_authentication(kw)
        filter_str = f"lambda line:line"
        if kw.get("state"):
            filter_str = filter_str + f" and line.state in kw.get('state')"
        if kw.get("holiday_status_id"):
            holiday_status_ids = kw.get("holiday_status_id")
            filter_str = filter_str + f" and line.holiday_status_id.id in {holiday_status_ids}"
        date_from = kw.get("date_from")
        if kw.get("date_from"):
            date_from = datetime.strptime(str(kw.get('date_from')),"%Y-%m-%d") 
            filter_str = filter_str + f" and line.allocation_date_from  >= date_from.date()"

        date_to = kw.get("date_to")
        if kw.get("date_to"):
            date_to = datetime.strptime(str(kw.get('date_to')),"%Y-%m-%d") 
            filter_str = filter_str + f" and line.allocation_date_to <= date_to.date()"
            
        if kw.get("is_last_7"):
            query = """
            select data.id from hr_leave_allocation data WHERE data.allocation_date_from  >= current_date - interval '7' day and data.allocation_date_from  <= current_date  and data.employee_id = %s
            """
            request._cr.execute(query, [request.env.user.employee_id.id])
            data_result_ids = request.env.cr.dictfetchall()
            ids = []
            if len(data_result_ids) > 0:
                ids = [id['id'] for id in data_result_ids]
            filter_str = filter_str + f" and line.id in {ids}"
        if kw.get("is_last_30"):
            query = """
                select data.id from hr_leave_allocation data WHERE data.allocation_date_from  >= current_date - interval '30' day and data.allocation_date_from  <= current_date and data.employee_id = %s            
                """
            request._cr.execute(query, [request.env.user.employee_id.id])
            data_result_ids = request.env.cr.dictfetchall()
            ids = []
            if len(data_result_ids) > 0:
                ids = [id['id'] for id in data_result_ids]
            filter_str = filter_str + f" and line.id in {ids}"
            
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        
        domain = [('employee_id','=',request.env.user.employee_id.id)]
        if kw.get("search"):
            domain.append(("seq_name","ilike",kw.get("search")))
        data_ids = request.env[obj].sudo().search(domain).filtered(eval(filter_str,{'kw':kw,
                                                                                                                    'date_from':date_from,
                                                                                                                    'date_to':date_to}))
        if not data_ids:
            return self.record_not_found()
        request_param = {"fields":['state',
                                    'sequence',
                                    'name',
                                    'holiday_status_id',
                                    'allocation_type_by',
                                    'allocation_date_from',
                                    'allocation_date_to',
                                    'number_of_days_display',
                                    'effective_date',
                                    'notes',
                                    'holiday_status_id',
                                    'approver_user_ids',
                                    'overtime_id',
                                    'number_of_hours_display',
                                    'allocation_half_day',
                                    'allocation_date_from_period',
                                    
                                    ]}
        if not id:
            request_param = {"ids":','.join(str(data.id) for data in data_ids),"fields":['sequence','allocation_date_from','allocation_date_to','holiday_status_id','state','number_of_hours_display','overtime_id','allocation_half_day','allocation_date_from_period','number_of_days_display'],
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
                response_data[obj]['approver_user_ids'] = self.convert_one2many('allocation.approver.user',{"fields":['user_ids','approver_state','minimum_approver','approved_time','feedback'],
                                                                                                                    "ids":','.join(str(data) for data in response_data[obj]['approver_user_ids'])},user)
                for data_to_convert in response_data[obj]['approver_user_ids']:
                    if len(data_to_convert['user_ids'])>=1:
                        data_to_convert['user_ids'] = self.convert_one2many('res.users',{"fields":['name'],
                                                                                        "ids":','.join(str(data) for data in data_to_convert['user_ids'])},user)
        page_total  = self.get_total_page(len(data_ids),PAGE_DATA_LIMIT)
        return self.get_response(200, '200', {"code":200,
                                                "data":response_data[obj],
                                                "page_total":page_total if not id else 0
                                                })
        
        
    @route(['/api/employee/overtime'],auth='user', type='http', methods=['get'])
    def get_employee_overtome(self,id=None,**kw):
        offset =  self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1)
        obj = 'hr.overtime.actual'
        auth, user, invalid = self.valid_authentication(kw)
        holiday_status_id = request.env['hr.leave.type'].sudo().search([('id','=',kw.get("holiday_status_id"))])
        period = date.today() + relativedelta(days=holiday_status_id.min_days_before_alloc)
        if not holiday_status_id:
            period = date.today()
        domain = [('period_start', '>=', period),('employee_id', '=', request.env.user.employee_id.id),('applied_to','=','extra_leave')]
        if kw.get("search"):
          domain.append(('name','ilike',kw.get("search")))

        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        data_ids = request.env[obj].sudo().search(domain)
        if not data_ids:
            return self.record_not_found()
    
        if not id:
            request_param = {"ids":','.join(str(data.id) for data in data_ids),"fields":['name','period_start','period_end','total_actual_hours','actual_line_ids'],
                                "order":"name asc",
                            "offset":offset,
                                "limit":PAGE_DATA_LIMIT
                                }
        read_record = self.perform_request(obj,id=id, kwargs=request_param, user=user)
        response_data = json.loads(read_record.data)
        
        
        if not obj in response_data:
            return self.record_not_found()
        for data in response_data[obj]:
            if 'actual_line_ids' in data:
                if len(data['actual_line_ids']) >= 1:
                    data['actual_line_ids'] = self.convert_one2many('hr.overtime.actual.line',{"fields":['actual_hours',],
                                                                                                                        "ids":','.join(str(data) for data in data['actual_line_ids'])},user)
        
        number_of_days_display = 0.0
        for data in response_data[obj]:  
            formula = holiday_status_id.formula
            if holiday_status_id.total_actual_hours:
                localdict = {"actual_hours": data['total_actual_hours'],
                             "duration": 0.0}
                safe_eval(formula, localdict, mode='exec', nocopy=True)
                number_of_days_display = localdict['duration']
            else:
                total_duration = 0.0
                for line in data['actual_line_ids']:
                    localdict = {"actual_hours": line['actual_hours'],"duration": 0.0}
                    safe_eval(formula, localdict, mode='exec', nocopy=True)
                    total_duration += localdict['duration']
                    number_of_days_display = total_duration
            data['number_of_days_display'] = number_of_days_display
        page_total  = self.get_total_page(len(data_ids),PAGE_DATA_LIMIT)
        return self.get_response(200, '200', {"code":200,
                                                "data":response_data[obj],
                                                "page_total":page_total if not id else 0
                                                })