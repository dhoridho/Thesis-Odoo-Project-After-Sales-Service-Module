from datetime import datetime, timedelta
from itertools import count
from odoo.http import route,request
import json
from ...restapi.controllers.helper import *


class Equip3HumanResourceRestAPIEmployeeDocument(RestApi):
    @route(['/api/employee/employee_document/','/api/employee/employee_document/<int:id>'],auth='user', type='http', methods=['get'])
    def get_employee_document(self,id=None,**kw):
        offset =  self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1)
        obj = 'hr.employee.document'
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        
        filter_str = f"lambda line:line"
        date_from = kw.get("date_from")
        if kw.get("date_from"):
            date_from = datetime.strptime(str(kw.get('date_from')),"%Y-%m-%d") 
            filter_str = filter_str + f" and line.issue_date.date()  >= date_from.date()"

        date_to = kw.get("date_to")
        if kw.get("date_to"):
            date_to = datetime.strptime(str(kw.get('date_to')),"%Y-%m-%d") 
            filter_str = filter_str + f" and line.expiry_date.date() <= date_to.date()"
            
        if kw.get("is_last_7"):
            query = """
            select data.id from hr_employee_document data WHERE data.issue_date::date  >= current_date - interval '7' day and data.issue_date::date  <= current_date  and data.employee_ref = %s
            """
            request._cr.execute(query, [request.env.user.employee_id.id])
            data_result_ids = request.env.cr.dictfetchall()
            ids = []
            if len(data_result_ids) > 0:
                ids = [id['id'] for id in data_result_ids]
            filter_str = filter_str + f" and line.id in {ids}"
            
        if kw.get("is_last_30"):
            query = """
                select data.id from hr_employee_document data WHERE data.issue_date  >= current_date - interval '30' day and data.issue_date  <= current_date and data.employee_ref = %s            
                """
            request._cr.execute(query, [request.env.user.employee_id.id])
            data_result_ids = request.env.cr.dictfetchall()
            ids = []
            if len(data_result_ids) > 0:
                ids = [id['id'] for id in data_result_ids]
            filter_str = filter_str + f" and line.id in {ids}"
        
        domain = [('employee_ref','=',request.env.user.employee_id.id)]
        if kw.get("date_from") or kw.get("is_last_30") or kw.get("is_last_7"):
            domain.append(('issue_date','!=',False))
        if kw.get("date_to"):
            domain.append(('expiry_date','!=',False))
        if kw.get("search"):
            domain.append(("name","ilike",kw.get("search")))
        
        data_ids = request.env[obj].sudo().search(domain).filtered(eval(filter_str,{'kw':kw,'date_from':date_from,"date_to":date_to}))
        if not data_ids:
            return self.record_not_found()
        
        request_param = {"fields":['name',
                                   'employee_ref',
                                    'document_type',
                                    'document_name',
                                    'issue_date',
                                    'expiry_date',
                                    'notification_type',
                                    'doc_attachment_id',
                                    'description',
                                    
     
                                   ]}
        if not id:
            request_param = {"ids":','.join(str(data.id) for data in data_ids),"fields":['name',
                                                                                         'employee_ref',
                                                                                         'document_type',
                                                                                         'expiry_date'
                                                                                         ],
                             "order":"id desc",
                             "offset":offset,
                             "limit":PAGE_DATA_LIMIT
                             }
            
        read_record = self.perform_request(obj,id=id, kwargs=request_param, user=user)
        response_data = json.loads(read_record.data)
        if not obj in response_data:
            return self.record_not_found()
        
        if 'doc_attachment_id' in response_data[obj]:
            if len(response_data[obj]['doc_attachment_id']) >= 1:
                attachment =  request.env['ir.attachment'].sudo().browse(response_data[obj]['doc_attachment_id'])
                response_data[obj]['doc_attachment_id'] = [{'name':data.name,
                                                            'datas':data.datas.decode("utf-8")} for data in attachment]
        
        page_total  = self.get_total_page(len(data_ids),PAGE_DATA_LIMIT)
        return self.get_response(200, '200', {"code":200,
                                              "data":response_data[obj],
                                              "page_total":page_total if not id else 0
                                              })