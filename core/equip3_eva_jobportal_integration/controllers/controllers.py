# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from itertools import count
from odoo.http import route,request
from ...restapi.controllers.helper import *
import pytz
import json


class Equip3EvaJobPortalIntegration(RestApi):
    @route(['/api/hr_applicant/job_portal','/api/hr_applicant/job_portal/<int:id>','/api/hr_applicant/job_portal/stage/<int:stage_id>','/api/hr_applicant/job_portal/stage/<int:stage_id>/job/<int:job_id>'],auth='user', type='http', methods=['get'])
    @authenticate
    def get_hr_applicant_job_portal(self,id=None,stage_id=None,job_id=None,**kw):
        limit = int(kw.get('limit')) if 'limit' in kw else False
        offset =  self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1,limit=limit)
        obj = 'hr.applicant'    
        domain = []
        if kw.get("search"):
            domain.append("|")
            domain.append("|")
            domain.append(("name","ilike",kw.get("search")))
            domain.append(("partner_name","ilike",kw.get("search")))
            domain.append(("email_from","ilike",kw.get("search")))
        data_ids = request.env[obj].sudo().search_count(domain)
        if not data_ids:
            return self.record_not_found()   
        
        request_param = {"fields":['stage_id',
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
                                    'working_experience',
                                    'working_experience_months',
                                    'working_experience_days'
                                    ],
                            "offset":offset,
                            "domain":domain,
                            "limit":PAGE_DATA_LIMIT if not limit else limit
                            }
 
        read_record = self.perform_request(obj,id=id, kwargs=request_param, user=request.env.user)
        response_data = json.loads(read_record.data)
        if not obj in response_data:
            return self.record_not_found()
        
        for line in response_data[obj]:
            if 'categ_ids' in line:
                if len(line['categ_ids']) >= 1:
                    line['categ_ids'] = self.convert_one2many('hr.applicant.category',{"fields":['name'],
                                                                                                    "ids":','.join(str(data) for data in line['categ_ids'])},request.env.user)
            if 'applicant_question_answer_spesific' in line:
                if len(line['applicant_question_answer_spesific']) >= 1:
                    line['applicant_question_answer_spesific'] = self.convert_one2many('applicant.answer',{"fields":['question','answer','file'],
                                                                                                    "ids":','.join(str(data) for data in line['applicant_question_answer_spesific'])},request.env.user)
            if 'past_experience_ids' in line:
                if len(line['past_experience_ids']) >= 1:
                    line['past_experience_ids'] = self.convert_one2many('hr.applicant.past.experience',{"fields":['start_date','end_date','is_currently_work_here','company_name','position','job_descriptions','reason_for_leaving','salary','company_telephone_number'],
                                                                                                    "ids":','.join(str(data) for data in line['past_experience_ids'])},request.env.user)
            if 'quadran_line_ids' in line:
                if len(line['quadran_line_ids']) >= 1:
                    line['quadran_line_ids'] = self.convert_one2many('quadrant.score.line',{"fields":['name','technical_test','interview','index'],
                                                                                                    "ids":','.join(str(data) for data in line['quadran_line_ids'])},request.env.user)
            if 'employee_skill_ids' in line:
                if len(line['employee_skill_ids']) >= 1:
                    line['employee_skill_ids'] = self.convert_one2many('hr.applicant.skill',{"fields":['skill_type_id','skill_id','skill_level_id'],
                                                                                                    "ids":','.join(str(data) for data in line['employee_skill_ids'])},request.env.user)
        
        page_total  = self.get_total_page(data_ids,PAGE_DATA_LIMIT if not limit else limit)
        return self.get_response(200, '200', {"code":200,
                                                "data":response_data[obj],
                                                "page_total":page_total if not id else 0
                                                })
        
        
    @http.route(['/api/job-portal/company',],type="http", auth="user",methods=['get'])
    @authenticate
    def get_all_job_portal_company(self, **kw):
        limit = int(kw.get('limit')) if 'limit' in kw else False
        offset =  self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1,limit=limit)
        obj = 'res.company'
        domain  = []
        if kw.get("search"):
            domain.append(('name','ilike',kw.get("search")))       
        data_ids = request.env[obj].sudo().search_count(domain)
        request_param = {"fields":['name','corporate_id','logo','phone','email','street','street2'],
                         "offset":offset,
                         "domain":domain,
                         "limit":PAGE_DATA_LIMIT if not limit else limit
                         }
        
        read_record = self.perform_request(obj,id=None, kwargs=request_param, user=request.env.user)
        response_data = json.loads(read_record.data)
        if not obj in response_data:
            return self.record_not_found()
          
        page_total  = self.get_total_page(data_ids,PAGE_DATA_LIMIT if not limit else limit)
        return self.get_response(200, '200', {"code":200,
                                              "data":response_data[obj],
                                              "page_total":page_total
                                              })
        
        
    @http.route(['/api/job-portal/job',],type="http", auth="user",methods=['get'])
    @authenticate
    def get_all_job_portal_job(self, **kw):
        limit = int(kw.get('limit')) if 'limit' in kw else False
        base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url', default='')
        offset =  self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1,limit=limit)
        obj = 'hr.job'
        domain  = []
        if kw.get("search"):
            domain.append(('name','ilike',kw.get("search")))       
        data_ids = request.env[obj].sudo().search_count(domain)
        request_param = {"fields":['name',
                                   'experience_length',
                                   'is_published',
                                   'company_id',
                                   'website_description',
                                   'description',
                                   'is_salary_confidential',
                                   'job_type',
                                   'workplace_type',
                                   'experience_level',
                                   'vacancy_deadline',
                                   'minimum_salary',
                                   'maximum_salary',
                                   'currency_job_id',
                                   'scheduled_pay',
                                   'custom_work_location_id',
                                   ],
                         "offset":offset,
                         "domain":domain,
                         "limit":PAGE_DATA_LIMIT if not limit else limit
                         }
        
        read_record = self.perform_request(obj,id=None, kwargs=request_param, user=request.env.user)
        response_data = json.loads(read_record.data)
        if not obj in response_data:
            return self.record_not_found()
        
        for data in response_data[obj]:
            data['job_apply_url'] =  base_url + '/jobs/apply/' + str(data['id'])
          
        page_total  = self.get_total_page(data_ids,PAGE_DATA_LIMIT if not limit else limit)
        return self.get_response(200, '200', {"code":200,
                                              "data":response_data[obj],
                                              "page_total":page_total
                                              })
        
    
    
    
        


        
        
        
        
        
        
        
        
        
        

