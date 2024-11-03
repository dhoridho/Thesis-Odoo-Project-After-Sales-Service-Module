from odoo.http import content_disposition, Controller, request, route
import json
from odoo.addons.survey.controllers.main import Survey


class SurveyInterview(Survey):
    
    
    def _prepare_question_html(self, survey_sudo, answer_sudo, **post):
        res = super(SurveyInterview, self)._prepare_question_html(survey_sudo,answer_sudo,**post)
        
        if answer_sudo.state == 'done' and str(answer_sudo.survey_type).upper() == 'INTERVIEW':
            answer_sudo.generate_interview_score()

            # quadrant_score = request.env['quadrant.score'].sudo().search(
            #     [('applicant', '=', answer_sudo.applicant_id.id), ('job_id', '=', answer_sudo.job_id.id)], limit=1)
            # if quadrant_score:
            if survey_sudo.survey_type == 'interview':
                skills_score = request.env['quadrant.score.line'].sudo().search(
                                [('applicant_id', '=', answer_sudo.applicant_id.id), ('name', '=', 'Skills')], limit=1)
                if skills_score:
                    skills_score.sudo().write({'interview': answer_sudo.skill_score})
                else:
                    request.env['quadrant.score.line'].sudo().create(
                    {'applicant_id':answer_sudo.applicant_id.id,
                    'name':'Skills',
                    'interview':int(answer_sudo.skill_score)})
                
                personality_score = request.env['quadrant.score.line'].sudo().search(
                                [('applicant_id', '=', answer_sudo.applicant_id.id), ('name', '=', 'Personality')], limit=1)
                if personality_score:
                    personality_score.sudo().write({'interview': answer_sudo.personality_score})
                else:
                    request.env['quadrant.score.line'].sudo().create(
                    {'applicant_id':answer_sudo.applicant_id.id,
                    'name':'Personality',
                    'interview':int(answer_sudo.personality_score)})
        elif answer_sudo.state == 'done':
            # quadrant_score = request.env['quadrant.score'].sudo().search(
            #     [('applicant', '=', answer_sudo.applicant_id.id), ('job_id', '=', answer_sudo.job_id.id)], limit=1)
            # if quadrant_score:
                if survey_sudo.survey_type == 'general':
                    skills_score = request.env['quadrant.score.line'].sudo().search(
                                    [('applicant_id', '=', answer_sudo.applicant_id.id), ('name', '=', 'Skills')], limit=1)
                    if skills_score:
                        skills_score.sudo().write({'technical_test': answer_sudo.score_by_amount})
                    else:
                        request.env['quadrant.score.line'].sudo().create(
                        {'applicant_id':answer_sudo.applicant_id.id,
                        'name':'Skills',
                        'technical_test':answer_sudo.score_by_amount})
                elif  survey_sudo.survey_type == 'epps':
                    personality_score = request.env['quadrant.score.line'].sudo().search(
                                    [('applicant_id', '=', answer_sudo.applicant_id.id), ('name', '=', 'Personality')], limit=1)
                    if personality_score:
                        personality_score.sudo().write({'technical_test': int(80)})
                    else:
                        request.env['quadrant.score.line'].sudo().create(
                        {'applicant_id':answer_sudo.applicant_id.id,
                        'name':'Personality',
                        'technical_test':int(80)})
                elif survey_sudo.survey_type == 'interview':
                    skills_score = request.env['quadrant.score.line'].sudo().search(
                                    [('applicant_id', '=', answer_sudo.applicant_id.id), ('name', '=', 'Skills')], limit=1)
                    if skills_score:
                        skills_score.sudo().write({'interview': answer_sudo.skill_score})
                    else:
                        request.env['quadrant.score.line'].sudo().create(
                        {'applicant_id':answer_sudo.applicant_id.id,
                        'name':'Skills',
                        'interview':int(answer_sudo.skill_score)})
                    
                    personality_score = request.env['quadrant.score.line'].sudo().search(
                                    [('applicant_id', '=', answer_sudo.applicant_id.id), ('name', '=', 'Personality')], limit=1)
                    if personality_score:
                        personality_score.sudo().write({'interview': answer_sudo.personality_score})
                    else:
                        request.env['quadrant.score.line'].sudo().create(
                        {'applicant_id':answer_sudo.applicant_id.id,
                        'name':'Personality',
                        'interview':int(answer_sudo.personality_score)})
                else:
                    # score = request.env['quadrant.score'].sudo().create(
                    #         {'applicant':answer_sudo.applicant_id.id,
                    #         'applicant_id':answer_sudo.applicant_id.applicant_id,
                    #         'applicant_name':answer_sudo.applicant_name,
                    #         'applicant_email':answer_sudo.email,
                    #         'job_id':answer_sudo.job_id.id})
                    if survey_sudo.survey_type == 'general':
                        request.env['quadrant.score.line'].sudo().create(
                        {'applicant_id':answer_sudo.applicant_id.id,
                        'name':'Skills',
                        'technical_test':answer_sudo.score_by_amount})
                    elif  survey_sudo.survey_type == 'epps':
                        request.env['quadrant.score.line'].sudo().create(
                        {'applicant_id':answer_sudo.applicant_id.id,
                        'name':'Personality',
                        'technical_test':int(80)})

        return res