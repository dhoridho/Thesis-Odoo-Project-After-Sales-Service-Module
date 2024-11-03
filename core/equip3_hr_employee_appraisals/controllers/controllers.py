from odoo import http
# from odoo.addons.survey.controllers.main import Survey
from odoo.addons.equip3_hr_recruitment_extend.controllers.controllers import Surveyedit
import json
from odoo.exceptions import UserError
from odoo.http import content_disposition, Controller, request, route
import werkzeug
from datetime import date

class SurveyPeerReview(Surveyedit):

    @http.route('/survey/start/<string:survey_token>', type='http', auth='public', website=True)
    def survey_start(self, survey_token, answer_token=None, email=False, surveyId=None, performanceId=None, reviewerRole=None, companyName=None, reviewerName=None, reviewerEmail=None, **post):
        """ Start a survey by providing
         * a token linked to a survey;
         * a token linked to an answer or generate a new token if access is allowed;
        """
        # Get the current answer token from cookie
        res = super(SurveyPeerReview, self).survey_start(survey_token, answer_token, email, **post)
        access_data = self._get_access_data(survey_token, answer_token, ensure_token=False)
        if access_data['validity_code'] is not True:
            return self._redirect_with_error(access_data, access_data['validity_code'])

        survey_sudo, answer_sudo = access_data['survey_sudo'], access_data['answer_sudo']
        if not answer_sudo:
            try:
                answer_sudo = survey_sudo._create_answer(user=request.env.user, email=email)
            except UserError:
                answer_sudo = False

        if not answer_sudo:
            try:
                survey_sudo.with_user(request.env.user).check_access_rights('read')
                survey_sudo.with_user(request.env.user).check_access_rule('read')
            except:
                return werkzeug.utils.redirect("/")
            else:
                return request.render("survey.survey_403_page", {'survey': survey_sudo})
        if surveyId and performanceId and reviewerRole:
            answer_before = request.env['survey.user_input'].sudo().search([('survey_id','=',survey_sudo.id),('email','=',answer_sudo.email),('employee_performance_id','=',int(performanceId)),('reviewer_role','=',reviewerRole)])
            if answer_before:
                return werkzeug.utils.redirect("/")
            else:
                return request.redirect('/survey/%s/%s?surveyId=%s&performanceId=%s&reviewerRole=%s&companyName=%s&reviewerName=%s&reviewerEmail=%s' % (survey_sudo.access_token, answer_sudo.access_token,surveyId,performanceId,reviewerRole,companyName,reviewerName,reviewerEmail))
        
        if surveyId and performanceId and survey_sudo.survey_type == 'tasks':
            answer_before = request.env['survey.user_input'].sudo().search([('survey_id','=',survey_sudo.id),('email','=',answer_sudo.email),('employee_performance_id','=',int(performanceId))])
            if answer_before:
                return werkzeug.utils.redirect("/")
            else:
                return request.redirect('/survey/%s/%s?surveyId=%s&performanceId=%s&email=%s' % (survey_sudo.access_token, answer_sudo.access_token,surveyId,performanceId,email))

        return res
    
    @http.route('/survey/submit/<string:survey_token>/<string:answer_token>', type='json', auth='public', website=True)
    def survey_submit(self, survey_token, answer_token, **post):
        res = super(SurveyPeerReview, self).survey_submit(survey_token,answer_token,**post)
        
        access_data = self._get_access_data(survey_token, answer_token, ensure_token=True)
        if access_data['validity_code'] is not True:
            return {'error': access_data['validity_code']}
        survey_sudo, answer_sudo = access_data['survey_sudo'], access_data['answer_sudo']
        
        if survey_sudo.survey_type == 'peer_review':
            url_peer_review = request.httprequest.referrer
            url_peer_review_split = url_peer_review.split("&")[-5:]
            if len(url_peer_review_split[0].split("="))>1:
                performance_param = url_peer_review_split[0].split("=")[0]
                performance_id = url_peer_review_split[0].split("=")[1]
                reviewer_role = url_peer_review_split[1].split("=")[1]
                reviewer_name = url_peer_review_split[3].split("=")[1]
                reviewer_email = url_peer_review_split[4].split("=")[1]
                if reviewer_role == "external":
                    company_name = url_peer_review_split[2].split("=")[1]
                if performance_param == 'performanceId':
                    employee_performance = request.env['employee.performance'].sudo().search([('id','=',int(performance_id))])
                    if employee_performance:
                        subordinate_max_reviewer = 1
                        peer_max_reviewer = 1
                        external_max_reviewer = 1
                        if employee_performance.employee_id.job_id.performance_all_review_id:
                            peer_review = employee_performance.employee_id.job_id.performance_all_review_id
                            if peer_review.is_included_subordinate:
                                subordinate_max_reviewer = peer_review.subordinate_max_reviewer
                            if peer_review.is_included_peer:
                                peer_max_reviewer = peer_review.peer_max_reviewer
                            if peer_review.is_included_external:
                                external_max_reviewer = peer_review.external_max_reviewer
                        
                        if reviewer_role == "external":
                            answer_sudo.write({'employee_performance_id':employee_performance.id,
                                                'reviewer_role':reviewer_role,
                                                'company_name':company_name.replace('%20', ' '),
                                                'reviewer_name':reviewer_name.replace('%20', ' '),
                                                'email': reviewer_email
                                                })
                        else:
                            if not answer_sudo.email:
                                answer_sudo.email = reviewer_email
                            answer_sudo.write({'employee_performance_id':employee_performance.id,
                                                'reviewer_role':reviewer_role,
                                                'reviewer_name':reviewer_name.replace('%20', ' ')
                                                })
                        if employee_performance.peer_reviews_line_ids:
                            role_data = employee_performance.sudo().peer_reviews_line_ids.filtered(lambda line:line.role == reviewer_role)
                            list_score = []
                            if reviewer_role == "subordinate":
                                score_before = request.env['survey.user_input'].sudo().search([('employee_performance_id','=',int(performance_id)),('reviewer_role','=',reviewer_role)],limit=subordinate_max_reviewer,order='create_date asc')
                            elif reviewer_role == "peer":
                                score_before = request.env['survey.user_input'].sudo().search([('employee_performance_id','=',int(performance_id)),('reviewer_role','=',reviewer_role)],limit=peer_max_reviewer,order='create_date asc')
                                survey = score_before.mapped("survey_id")
                                if score_before:
                                    final_score = 0
                                    for line in survey:
                                        survey_result = score_before.filtered(lambda r: r.survey_id.id == line.id)
                                        survey_score = []
                                        for data_score in survey_result:
                                            survey_score.append(data_score.score_by_amount)
                                        final_score += sum(survey_score)/len(survey_score)
                                    if role_data:
                                        role_data.sudo().score = float(final_score)
                                else:
                                    if role_data:
                                        role_data.sudo().score = answer_sudo.score_by_amount
                            elif reviewer_role == "external":
                                score_before = request.env['survey.user_input'].sudo().search([('employee_performance_id','=',int(performance_id)),('reviewer_role','=',reviewer_role)],limit=external_max_reviewer,order='create_date asc')
                            else:
                                score_before = request.env['survey.user_input'].sudo().search([('employee_performance_id','=',int(performance_id)),('reviewer_role','=',reviewer_role)])
                            if reviewer_role != "peer":
                                if score_before:
                                    for data_score in score_before:
                                        list_score.append(data_score.score_by_amount)
                                    final_score = sum(list_score)/len(list_score)
                                    if role_data:
                                        role_data.sudo().score = float(final_score)
                                else:
                                    if role_data:
                                        role_data.sudo().score = answer_sudo.score_by_amount
        
        elif survey_sudo.survey_type == 'tasks':
            url_tasks = request.httprequest.referrer
            url_tasks_split = url_tasks.split("?")
            url_tasks_var = url_tasks_split[1].split("&")
            if len(url_tasks_var[1].split("="))>1:
                performance_param = url_tasks_var[1].split("=")[0]
                performance_id = url_tasks_var[1].split("=")[1]
                email = url_tasks_var[2].split("=")[1]
                if performance_param == 'performanceId':
                    employee_performance = request.env['employee.performance'].sudo().search([('id','=',int(performance_id))])
                    if employee_performance:
                        if not answer_sudo.email:
                            answer_sudo.email = email
                        answer_sudo.write({'employee_performance_id':employee_performance.id})
                        if employee_performance.task_challenge_line_ids:
                            tasks_data = employee_performance.sudo().task_challenge_line_ids.filtered(lambda line:line.task_challenge_id.id == survey_sudo.id)
                            today = date.today()
                            if tasks_data and today <= employee_performance.deadline:
                                tasks_data.sudo().score_survey = answer_sudo.score_by_amount

        return res