from datetime import datetime, timedelta
from itertools import count
from odoo.http import route,request
from ...restapi.controllers.helper import *
import json
import base64

class Equip3HumanResourceMySpt(RestApi):
    @route(['/api/employee/my_spt','/api/employee/my_spt/<int:id>'],auth='user', type='http', methods=['get'])
    def get_my_spt_list(self,id=None,**kw):
        offset =  self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1)
        obj = 'hr.my.spt'
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        filter_str = f"lambda line:line"
        if kw.get("default_year_id"):
            default_year_ids = json.loads(kw.get("default_year_id"))
            period = request.env['hr.payslip.period'].sudo().search([('id','in',default_year_ids)])
            period_name = []
            for rec in period:
                period_name.append(rec.name)
            filter_str = filter_str + f" and line.year in {period_name}"
        data_ids = request.env[obj].sudo().search([('employee_id','=',request.env.user.employee_id.id)]).filtered(eval(filter_str,{'kw':kw}))
        if not data_ids:
            return self.record_not_found()
        
        request_param = {"fields":['employee_id',
                                    'year',
                                    'month',
                                    'kpp',
                                    'spt_type',
                                    'attachment_fname',
                                    'attachment'
                                   ]}
        
        if not id:
            request_param = {"ids":','.join(str(data.id) for data in data_ids),"fields":['spt_type','year','month'],
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