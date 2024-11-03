from datetime import datetime, timedelta
from itertools import count
from odoo.http import route,request
import json
from ...restapi.controllers.helper import *


class Equip3HumanResourceRestAPIEmployeeProbation(RestApi):
    @route(['/api/employee/probation','/api/employee/probation/<int:id>'],auth='user', type='http', methods=['get'])
    def get_employee_probation(self,id=None,**kw):
        offset =  self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1)
        obj = 'employee.probation'
        filter_str = f"lambda line:line"
        if kw.get("state"):
            state_ids = kw.get("state")
            filter_str = filter_str + f" and line.state in {state_ids}"
            
        date_from = kw.get("date_from")
        if kw.get("date_from"):
            date_from = datetime.strptime(str(kw.get('date_from')),"%Y-%m-%d") 
            filter_str = filter_str + f" and line.start_date  >= date_from.date()"

        date_to = kw.get("date_to")
        if kw.get("date_to"):
            date_to = datetime.strptime(str(kw.get('date_to')),"%Y-%m-%d") 
            filter_str = filter_str + f" and line.end_date <= date_to.date()"
            
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        
        domain = [('employee_id','=',request.env.user.employee_id.id)]
        if kw.get("search"):
            domain.append(('name','ilike',kw.get("search")))
            
        data_ids = request.env[obj].sudo().search(domain).filtered(eval(filter_str,{'kw':kw,'date_from':date_from,'date_to':date_to}))
        if not data_ids:
            return self.record_not_found()
        
        request_param = {"fields":['state',
                                    'name',
                                    'employee_id',
                                    'employee_email',
                                    'department_id',
                                    'manager_id',
                                    'company_id',
                                    'start_date',
                                    'end_date',
                                    'description',
                                    'review_ids'
                                    ]}
        if not id:
            request_param = {"ids":','.join(str(data.id) for data in data_ids),"fields":['name',
                                                                                         'state',
                                                                                         'employee_id',
                                                                                         'start_date',
                                                                                         'end_date',
                                                                                         'review_ids'
                                                                                         ],
                             "order":"id desc",
                             "offset":offset,
                             "limit":PAGE_DATA_LIMIT
                             }
            
        read_record = self.perform_request(obj,id=id, kwargs=request_param, user=user)
        response_data = json.loads(read_record.data)
        if not id:
            for data in response_data[obj]:
                if data['review_ids']:
                    data['review_ids'] = self.convert_one2many('probation.review',{"fields":['user_id',
                                                                                             'review_date',
                                                                                             'short_review',
                                                                                             'performance',
                                                                                             'rating'
                                                                                             ],
                                                                                                       "ids":','.join(str(record) for record in data['review_ids'])},user)
        
        
        
        if 'review_ids' in response_data[obj]:
            if len(response_data[obj]['review_ids']) >= 1:
                response_data[obj]['review_ids'] = self.convert_one2many('probation.review',{"fields":['user_id',
                                                                                                       'review_date',
                                                                                                        'short_review',
                                                                                                        'performance',
                                                                                                        'rating',
                                                                                                                ],
                                                                                                       "ids":','.join(str(data) for data in response_data[obj]['review_ids'])},user)
        
        if not obj in response_data:
            return self.record_not_found()
        
        page_total  = self.get_total_page(len(data_ids),PAGE_DATA_LIMIT)
        return self.get_response(200, '200', {"code":200,
                                              "data":response_data[obj],
                                              "page_total":page_total if not id else 0
                                              })
    