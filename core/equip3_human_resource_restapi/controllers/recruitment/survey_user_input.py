from datetime import datetime, timedelta
from itertools import count
from odoo.http import route,request
import json
from ....restapi.controllers.helper import *




class Equip3HumanResourceRestAPISurveyUserInput(RestApi):
    @route(['/api/test_result','/api/test_result/<int:id>'],auth='user', type='http', methods=['get'])
    def get_test_result(self,id=None,**kw):
        limit = int(kw.get('limit')) if 'limit' in kw else False
        offset =  self.get_limit_offset(page=int(kw.get('page')) if 'page' in kw else 1,limit=limit)
        obj = 'survey.user_input'
        auth, user, invalid = self.valid_authentication(kw)
        filter_str = f"lambda line:line"
        # if stage_id:
        #     filter_str = filter_str + f" and line.stage_id.id == {int(stage_id)}"
        # if job_id:
        #     filter_str = filter_str + f" and line.job_id.id == {int(job_id)}"
        date_from = kw.get("date_from")
        if kw.get("date_from"):
            date_from = datetime.strptime(str(kw.get('date_from')),"%Y-%m-%d") 
            filter_str = filter_str + f" and line.create_date  >= date_from.date()"

        date_to = kw.get("date_to")
        if kw.get("date_to"):
            date_to = datetime.strptime(str(kw.get('date_to')),"%Y-%m-%d") 
            filter_str = filter_str + f" and line.create_date <= date_to.date()"
            
        if kw.get("is_last_7"):
            query = """
            select data.id from survey_user_input data WHERE data.create_date  >= current_date - interval '7' day and data.create_date  < current_date
            """
            request._cr.execute(query, [request.env.user.employee_id.id])
            data_result_ids = request.env.cr.dictfetchall()
            ids = []
            if len(data_result_ids) > 0:
                ids = [id['id'] for id in data_result_ids]
            filter_str = filter_str + f" and line.id in {ids}"
            
        if kw.get("is_last_30"):
            query = """
                select data.id from survey_user_input data WHERE data.create_date  >= current_date - interval '30' day and data.create_date  < current_date           
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
            domain.append(("survey_id.name","ilike",kw.get("search")))
            domain.append(("email","ilike",kw.get("search")))
            domain.append(("partner_id.name","ilike",kw.get("search")))
        data_ids = request.env[obj].sudo().search(domain).filtered(eval(filter_str,{'kw':kw,'date_from':date_from,'date_to':date_to}))
        if not data_ids:
            return self.record_not_found()
       
        request_param = {"fields":[
                                    'survey_id',
                                    'survey_type',
                                    'create_date',
                                    'applicant_id',
                                    'access_token',
                                    'job_id',
                                    'deadline',
                                    'partner_id',
                                    'applicant_name',
                                    'email',
                                    'test_entry',
                                    'score_by_amount',
                                    'scoring_success',
                                    'state',
                                    'disc_result_ids',
                                    'chart_disc_result_score21',
                                    'chart_disc_result_score22',
                                    'chart_disc_result_score23',
                                    'mask_public_self_code',
                                    'mask_public_self',
                                    'mask_public_self_ids',
                                    'core_private_self_code',
                                    'core_private_self',
                                    'core_private_self_ids',
                                    'mirror_perceived_self_code',
                                    'mirror_perceived_self',
                                    'mirror_perceived_self_ids',
                                    'disc_match_score_ids',
                                    'personal_description',
                                    'job_match',
                                    'job_suggestion',
                                    'user_input_line_ids',
                                    'skill_score',
                                    'personality_score',
                                    'interview_result_skill_ids',
                                    'interview_result_personality_ids',
                                    'papikostick_parameter_result_ids',
                                    'chart_papikostick_result_score',
                                    'ist_scoring_result_ids',
                                    'chart_ist_result_score',
                                    'ist_scoring_final_result_ids',
                                    ]
                            }
        if not id:
            request_param = {"ids":','.join(str(data.id) for data in data_ids),"fields":[
                                                                                    'survey_id',
                                                                                    'create_date',
                                                                                     'deadline',
                                                                                     'partner_id',
                                                                                     'email',
                                                                                     'attempts_number',
                                                                                     'state',
                                                                                     'scoring_percentage'                                
                                                                                     ],
                                                                            "offset":offset,
                                                                            "limit":PAGE_DATA_LIMIT if not limit else limit
                            }
        read_record = self.perform_request(obj,id=id, kwargs=request_param, user=user)
        response_data = json.loads(read_record.data)
        if not obj in response_data:
            return self.record_not_found()
        
        if 'disc_result_ids' in response_data[obj]:
            if len(response_data[obj]['disc_result_ids']) >= 1:
                response_data[obj]['disc_result_ids'] = self.convert_one2many('survey.disc_result',{"fields":['line','d_field','i_field','s_field','c_field','star_field','total_field'],
                                                                                                 "ids":','.join(str(data) for data in response_data[obj]['disc_result_ids'])},user)
        if 'mask_public_self_ids' in response_data[obj]:
            if len(response_data[obj]['mask_public_self_ids']) >= 1:
                response_data[obj]['mask_public_self_ids'] = self.convert_one2many('survey.input.personality.line',{"fields":['personality','personality_en'],
                                                                                                 "ids":','.join(str(data) for data in response_data[obj]['mask_public_self_ids'])},user)
        if 'core_private_self_ids' in response_data[obj]:
            if len(response_data[obj]['core_private_self_ids']) >= 1:
                response_data[obj]['core_private_self_ids'] = self.convert_one2many('survey.input.personality.line',{"fields":['personality','personality_en'],
                                                                                                 "ids":','.join(str(data) for data in response_data[obj]['core_private_self_ids'])},user)
        if 'mirror_perceived_self_ids' in response_data[obj]:
            if len(response_data[obj]['mirror_perceived_self_ids']) >= 1:
                response_data[obj]['mirror_perceived_self_ids'] = self.convert_one2many('survey.input.personality.line',{"fields":['personality','personality_en'],
                                                                                                 "ids":','.join(str(data) for data in response_data[obj]['mirror_perceived_self_ids'])},user)
        if 'disc_match_score_ids' in response_data[obj]:
            if len(response_data[obj]['disc_match_score_ids']) >= 1:
                response_data[obj]['disc_match_score_ids'] = self.convert_one2many('disc.match.score',{"fields":['name'],
                                                                                                 "ids":','.join(str(data) for data in response_data[obj]['disc_match_score_ids'])},user)
        if 'user_input_line_ids' in response_data[obj]:
            if len(response_data[obj]['user_input_line_ids']) >= 1:
                response_data[obj]['user_input_line_ids'] = self.convert_one2many('survey.user_input.line',{"fields":['question_id','file','page_id','answer_type','suggested_answer_id','code','create_date','answer_score'],
                                                                                                 "ids":','.join(str(data) for data in response_data[obj]['user_input_line_ids'])},user)
        if 'interview_result_skill_ids' in response_data[obj]:
            if len(response_data[obj]['interview_result_skill_ids']) >= 1:
                response_data[obj]['interview_result_skill_ids'] = self.convert_one2many('survey.interview.skill.result',{"fields":['question','score','comment'],
                                                                                                 "ids":','.join(str(data) for data in response_data[obj]['interview_result_skill_ids'])},user)
        if 'interview_result_personality_ids' in response_data[obj]:
            if len(response_data[obj]['interview_result_personality_ids']) >= 1:
                response_data[obj]['interview_result_personality_ids'] = self.convert_one2many('survey.interview.personality.result',{"fields":['question','score','comment'],
                                                                                                 "ids":','.join(str(data) for data in response_data[obj]['interview_result_personality_ids'])},user)
        if 'papikostick_parameter_result_id' in response_data[obj]:
            if len(response_data[obj]['papikostick_parameter_result_id']) >= 1:
                response_data[obj]['papikostick_parameter_result_id'] = self.convert_one2many('survey.papikostick.parameter.result',{"fields":['parameter','description','code_pl','score_code','description_code','analysis','score'],
                                                                                                 "ids":','.join(str(data) for data in response_data[obj]['papikostick_parameter_result_id'])},user)
        if 'ist_scoring_result_ids' in response_data[obj]:
            if len(response_data[obj]['ist_scoring_result_ids']) >= 1:
                response_data[obj]['ist_scoring_result_ids'] = self.convert_one2many('ist.scoring.result',{"fields":['parameter','code','rw','sw','description','category'],
                                                                                                 "ids":','.join(str(data) for data in response_data[obj]['ist_scoring_result_ids'])},user)
        if 'ist_scoring_final_result_ids' in response_data[obj]:
            if len(response_data[obj]['ist_scoring_final_result_ids']) >= 1:
                response_data[obj]['ist_scoring_final_result_ids'] = self.convert_one2many('ist.final.scoring.result',{"fields":['total_rw','gesamt_score','iq_score','iq_category','dominance','mindset '],
                                                                                                 "ids":','.join(str(data) for data in response_data[obj]['ist_scoring_final_result_ids'])},user)
       
        
        page_total  = self.get_total_page(len(data_ids),PAGE_DATA_LIMIT if not limit else limit)
        return self.get_response(200, '200', {"code":200,
                                                "data":response_data[obj],
                                                "page_total":page_total if not id else 0
                                                })
        
    