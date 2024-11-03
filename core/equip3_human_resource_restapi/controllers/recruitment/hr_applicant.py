from datetime import datetime, timedelta
from itertools import count
from odoo.http import route,request
import json
from ....restapi.controllers.helper import *




class Equip3HumanResourceRestAPIHRApplicant(RestApi):
    @route(['/api/hr_applicant','/api/hr_applicant/<int:id>','/api/hr_applicant/stage/<int:stage_id>','/api/hr_applicant/stage/<int:stage_id>/job/<int:job_id>'],auth='user', type='http', methods=['get'])
    def get_hr_applicant(self,id=None,stage_id=None,job_id=None,**kw):
        limit = int(kw.get('limit')) if 'limit' in kw else False
        offset =  self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1,limit=limit)
        obj = 'hr.applicant'
        auth, user, invalid = self.valid_authentication(kw)
        filter_str = f"lambda line:line"
        if stage_id:
            filter_str = filter_str + f" and line.stage_id.id == {int(stage_id)}"
        if job_id:
            filter_str = filter_str + f" and line.job_id.id == {int(job_id)}"
        date_from = kw.get("date_from")
        if kw.get("date_from"):
            date_from = datetime.strptime(str(kw.get('date_from')),"%Y-%m-%d") 
            filter_str = filter_str + f" and line.aplicant_create_date  >= date_from.date()"

        date_to = kw.get("date_to")
        if kw.get("date_to"):
            date_to = datetime.strptime(str(kw.get('date_to')),"%Y-%m-%d") 
            filter_str = filter_str + f" and line.aplicant_create_date <= date_to.date()"
            
        if kw.get("is_last_7"):
            query = """
            select data.id from hr_applicant data WHERE data.aplicant_create_date  >= current_date - interval '7' day and data.aplicant_create_date  < current_date
            """
            request._cr.execute(query, [request.env.user.employee_id.id])
            data_result_ids = request.env.cr.dictfetchall()
            ids = []
            if len(data_result_ids) > 0:
                ids = [id['id'] for id in data_result_ids]
            filter_str = filter_str + f" and line.id in {ids}"
            
        if kw.get("is_last_30"):
            query = """
                select data.id from hr_applicant data WHERE data.aplicant_create_date  >= current_date - interval '30' day and data.aplicant_create_date  < current_date           
                """
            request._cr.execute(query, [request.env.user.employee_id.id])
            data_result_ids = request.env.cr.dictfetchall()
            ids = []
            if len(data_result_ids) > 0:
                ids = [id['id'] for id in data_result_ids]
            filter_str = filter_str + f" and line.id in {ids}"
            
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        
        domain = []
        if kw.get("search"):
            domain.append("|")
            domain.append("|")
            domain.append(("name","ilike",kw.get("search")))
            domain.append(("partner_name","ilike",kw.get("search")))
            domain.append(("email_from","ilike",kw.get("search")))
        data_ids = request.env[obj].sudo().search(domain).filtered(eval(filter_str,{'kw':kw,'date_from':date_from,'date_to':date_to}))
        if not data_ids:
            return self.record_not_found()
       
        request_param = {"fields":[
                                    'stage_id',
                                    'name',
                                    'partner_name',
                                    'applicant_id',
                                    'email_from',
                                    'email_cc',
                                    'partner_phone',
                                    'partner_mobile',
                                    'type_id',
                                    'file_cv',
                                    'identification_no',
                                    'gender',
                                    'date_of_birth',
                                    'birth_years',
                                    'marital_status',
                                    'religion',
                                    'address',
                                    'categ_ids',
                                    'user_id',
                                    'priority',
                                    'medium_id',
                                    'source_id',
                                    'job_id',
                                    'aplicant_create_date',
                                    'previous_score',
                                    'department_id',
                                    'company_id',
                                    'last_drawn_salary',
                                    'salary_expected',
                                    'salary_proposed',
                                    'availability',
                                    'past_experience_ids',
                                    'description',
                                    'category_id',
                                    'applicant_question_answer_spesific',
                                    'employee_skill_ids',
                                    'quadran_line_ids',
                                    'participations_count',
                                    'meeting_count',
                                    ]
                            }
        if not id:
            request_param = {"ids":','.join(str(data.id) for data in data_ids),"fields":[
                                                                                    'stage_id',
                                                                                    'name',
                                                                                     'partner_name',
                                                                                     'applicant_id',
                                                                                     'email_from',
                                                                                     'email_cc',
                                                                                     'partner_phone',
                                                                                     'partner_mobile',
                                                                                     'job_id',
                                                                                     'aplicant_create_date',
                                                                                     'department_id',
                                                                                     'company_id'                                   
                                                                                     ],
                                                                            "offset":offset,
                                                                            "limit":PAGE_DATA_LIMIT if not limit else limit
                            }
        read_record = self.perform_request(obj,id=id, kwargs=request_param, user=user)
        response_data = json.loads(read_record.data)
        if not obj in response_data:
            return self.record_not_found()
        if 'categ_ids' in response_data[obj]:
            if len(response_data[obj]['categ_ids']) >= 1:
                response_data[obj]['categ_ids'] = self.convert_one2many('hr.applicant.category',{"fields":['name'],
                                                                                                 "ids":','.join(str(data) for data in response_data[obj]['categ_ids'])},user)
        if 'applicant_question_answer_spesific' in response_data[obj]:
            if len(response_data[obj]['applicant_question_answer_spesific']) >= 1:
                response_data[obj]['applicant_question_answer_spesific'] = self.convert_one2many('applicant.answer',{"fields":['question','answer','file'],
                                                                                                 "ids":','.join(str(data) for data in response_data[obj]['applicant_question_answer_spesific'])},user)
        if 'past_experience_ids' in response_data[obj]:
            if len(response_data[obj]['past_experience_ids']) >= 1:
                response_data[obj]['past_experience_ids'] = self.convert_one2many('hr.applicant.past.experience',{"fields":['start_date','end_date','is_currently_work_here','company_name','position','job_descriptions','reason_for_leaving','salary','company_telephone_number'],
                                                                                                 "ids":','.join(str(data) for data in response_data[obj]['past_experience_ids'])},user)
        if 'quadran_line_ids' in response_data[obj]:
            if len(response_data[obj]['quadran_line_ids']) >= 1:
                response_data[obj]['quadran_line_ids'] = self.convert_one2many('quadrant.score.line',{"fields":['name','technical_test','interview','index'],
                                                                                                 "ids":','.join(str(data) for data in response_data[obj]['quadran_line_ids'])},user)
        if 'employee_skill_ids' in response_data[obj]:
            if len(response_data[obj]['employee_skill_ids']) >= 1:
                response_data[obj]['employee_skill_ids'] = self.convert_one2many('hr.applicant.skill',{"fields":['skill_type_id','skill_id','skill_level_id'],
                                                                                                 "ids":','.join(str(data) for data in response_data[obj]['employee_skill_ids'])},user)
        
        page_total  = self.get_total_page(len(data_ids),PAGE_DATA_LIMIT if not limit else limit)
        return self.get_response(200, '200', {"code":200,
                                                "data":response_data[obj],
                                                "page_total":page_total if not id else 0
                                                })
        
    @http.route(['/api/stage_recruitment'],type="http", auth="user",methods=['get'])
    def get_stage_recruitment(self, **kw):
        limit = int(kw.get('limit')) if 'limit' in kw else False
        offset =  self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1,limit=limit)
        obj = 'hr.recruitment.stage'
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        domain = []
        if kw.get("search"):
            domain.append(('name','ilike',kw.get("search")))
            
        data_ids = request.env[obj].sudo().search(domain)
        if not data_ids:
            return self.record_not_found()
        
        request_param = {"ids":','.join(str(data.id) for data in data_ids),"fields":['name'],
                         "offset":offset,
                         "limit":PAGE_DATA_LIMIT if not limit else limit
                         }
        read_record = self.perform_request(obj,id=None, kwargs=request_param, user=user)
        response_data = json.loads(read_record.data)
        if not obj in response_data:
            return self.record_not_found()
        
        page_total  = self.get_total_page(len(data_ids),PAGE_DATA_LIMIT if not limit else limit)
        return self.get_response(200, '200', {"code":200,
                                              "data":response_data[obj],
                                              "page_total":page_total
                                              })