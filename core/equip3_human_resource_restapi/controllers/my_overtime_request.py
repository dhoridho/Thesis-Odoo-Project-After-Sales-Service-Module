from datetime import datetime, timedelta
from itertools import count
from odoo.http import route,request
import json
from ...restapi.controllers.helper import *


class Equip3HumanResourceMyOvertimeRequest(RestApi):
    @route('/api/employee/create/create_my_overtime_request',auth='user', type='json', methods=['POST'])
    def create_my_overtime_request(self,**kw):
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
        
        data_create = request.env['hr.overtime.request'].sudo().create({
                                'request_type':"by_employee",
                                 'employee_id': request.env.user.employee_id.id,
                                 'period_start':period_start,
                                 'period_end':period_end,
                                 'description':request_data.get('description')
                                 
                                 })
        request_line_ids= []
        if 'request_line_ids' in request_data:
            for data in request_data['request_line_ids']:
                date  = datetime.strptime(str(data['date']),"%Y-%m-%d")
                start_time = self.convert_time_to_float(data['start_time'])
                end_time = self.convert_time_to_float(data['end_time'])
                number_of_hours = self.convert_time_to_float(data['number_of_hours'])
                request_line_ids.append((0,0,{'employee_id':request.env.user.employee_id.id,
                                              'overtime_reason':data['overtime_reason'],
                                              'date':date,
                                              'name_of_day':date.strftime("%A"),
                                              'start_time':start_time,
                                              'end_time':end_time,
                                              'number_of_hours':number_of_hours
                                              }))      
        data_create._onchange_employee_id()
        data_create.request_line_ids = request_line_ids
        if request_data.get('state') == 'to_approve':
            data_create.confirm()
        if not data_create:
            return self.update_create_failed()
           
        return self.get_response(200, '200', {"code":200, 
                                              "message":"Create My Overtime Request Suscessfull"
                                              })
        
    @route('/api/employee/update/create_my_overtime_request/<int:id>',auth='user', type='json', methods=['PUT'])
    def update_my_overtime_request(self,id=None,**kw):
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
        
        data_update = request.env['hr.overtime.request'].sudo().search([('id','=',id)])
        if not data_update:
            self.record_not_found()
        data_update.write({
                                'request_type':"by_employee",
                                 'employee_id': request.env.user.employee_id.id,
                                 'period_start':period_start,
                                 'period_end':period_end,
                                 'description':request_data.get('description')
                                 
                                 })
        if 'request_line_ids' in request_data:
            for data in request_data['request_line_ids']:
                print(data)
                data['values']['date']  = datetime.strptime(str(data['values']['date']),"%Y-%m-%d")
                data['values']['start_time'] = self.convert_time_to_float(data['values']['start_time'])
                data['values']['end_time'] = self.convert_time_to_float(data['values']['end_time'])
                data['values']['number_of_hours'] = self.convert_time_to_float(data['values']['number_of_hours'])
            result = self.update_one2many([('request_id','=',data_update.id)],'hr.overtime.request.line',request_data.get('request_line_ids'))
            if result:
                data_update.request_line_ids = result
            
        if request_data.get('state') == 'to_approve':
            data_update.confirm()
            
        data_update._onchange_employee_id()

        if not data_update:
            return self.update_create_failed()
           
        return self.get_response(200, '200', {"code":200, 
                                              "message":"Update My Overtime Request Suscessfull"
                                              })
    
    @route(['/api/employee/my_overtime_request/','/api/employee/my_overtime_request/<int:id>'],auth='user', type='http', methods=['get'])
    def get_employee_overtime_request(self,id=None,**kw):
        offset =  self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1)
        obj = 'hr.overtime.request'
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        filter_str = f"lambda line:line"
        if kw.get("state"):
            state = kw.get("state")
            filter_str = filter_str + f" and line.state in {state}"
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
            select data.id from hr_overtime_request data WHERE data.period_start::date  >= current_date - interval '7' day and data.period_start  <= current_date  and data.employee_id = %s
            """
            request._cr.execute(query, [request.env.user.employee_id.id])
            data_result_ids = request.env.cr.dictfetchall()
            ids = []
            if len(data_result_ids) > 0:
                ids = [id['id'] for id in data_result_ids]
            filter_str = filter_str + f" and line.id in {ids}"
        if kw.get("is_last_30"):
            query = """
                select data.id from hr_overtime_request data WHERE data.period_start::date  >= current_date - interval '30' day and data.period_start  <= current_date and data.employee_id = %s            
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
                                    'employee_id',
                                    'request_type',
                                    'period_start',
                                    'period_end',
                                    'total_hours',
                                    'company_id',
                                    'create_date',
                                    'create_uid',
                                    'description',
                                    'request_line_ids',
                                    'request_approval_line_ids',
                                   ]}
        if not id:
            request_param = {"ids":','.join(str(data.id) for data in data_ids),"fields":['state',
                                                                                         'name',
                                                                                         'request_type',
                                                                                         'period_start',
                                                                                         'period_end'
                                                                                         ],
                             "order":"id desc",
                             "offset":offset,
                             "limit":PAGE_DATA_LIMIT
                             }
        read_record = self.perform_request(obj,id=id, kwargs=request_param, user=user)
        response_data = json.loads(read_record.data)
        if not obj in response_data:
            return self.record_not_found()
        
        if 'request_line_ids' in response_data[obj]:
            if len(response_data[obj]['request_line_ids']) >= 1:
                response_data[obj]['request_line_ids'] = self.convert_one2many('hr.overtime.request.line',{"fields":[
                                                                                                                'employee_id',
                                                                                                                'name_of_day',
                                                                                                                'start_time',
                                                                                                                'date',
                                                                                                                'end_time',
                                                                                                                'number_of_hours',
                                                                                                                'overtime_reason'
                                                                                                                ],
                                                                                                      "ids":','.join(str(data) for data in response_data[obj]['request_line_ids'])},user)
                for data_to_correct in response_data[obj]['request_line_ids']:
                    data_to_correct['start_time'] = str(timedelta(hours=data_to_correct['start_time']))
                    data_to_correct['end_time'] = str(timedelta(hours=data_to_correct['end_time']))
                    data_to_correct['number_of_hours'] = str(timedelta(hours=data_to_correct['number_of_hours']))
                    
        if 'request_approval_line_ids' in response_data[obj]:
            if len(response_data[obj]['request_approval_line_ids']) >= 1:
                response_data[obj]['request_approval_line_ids'] = self.convert_one2many('hr.overtime.request.approval.line',{"fields":['approver_id','approval_status','minimum_approver','timestamp','feedback'],
                                                                                                                    "ids":','.join(str(data) for data in response_data[obj]['request_approval_line_ids'])},user)
                for data_to_convert in response_data[obj]['request_approval_line_ids']:
                    if len(data_to_convert['approver_id'])>=1:
                        data_to_convert['approver_id'] = self.convert_one2many('res.users',{"fields":['name'],
                                                                                        "ids":','.join(str(data) for data in data_to_convert['approver_id'])},user)
        
        page_total  = self.get_total_page(len(data_ids),PAGE_DATA_LIMIT)
        return self.get_response(200, '200', {"code":200,
                                              "data":response_data[obj],
                                              "page_total":page_total if not id else 0
                                              })  