from odoo import http
from odoo.addons.equip3_hr_recruitment_extend.controllers.controllers import Surveyedit
import json
from odoo.exceptions import UserError
from odoo.http import content_disposition, Controller, request, route
import werkzeug
import statistics
from odoo.tools.safe_eval import safe_eval




class SurveyTraining(Surveyedit):
    
    @http.route('/survey/submit/<string:survey_token>/<string:answer_token>', type='json', auth='public', website=True)
    def survey_submit(self, survey_token, answer_token, **post):
        res = super(SurveyTraining, self).survey_submit(survey_token,answer_token,**post)
        
        access_data = self._get_access_data(survey_token, answer_token, ensure_token=True)
        if access_data['validity_code'] is not True:
            return {'error': access_data['validity_code']}
        survey_sudo, answer_sudo = access_data['survey_sudo'], access_data['answer_sudo']
        paramater = json.loads(request.httprequest.data)['params']
        if paramater['training_id'] and paramater['employee_id'] and paramater['test_type']:
            if paramater['test_type'] == 1:
                test_type = "pre_test"
            if paramater['test_type'] == 2:
                test_type = "post_test"
            answer_sudo.write({'employee_id':paramater['employee_id'],
                               'training_id':paramater['training_id'],
                               'test_type':test_type,
                               'is_hr_training':True
                               })
            if answer_sudo.survey_id.scoring_type == 'scoring_with_answers' or answer_sudo.survey_id.scoring_type == 'scoring_without_answers':
                training_conduct = request.env['training.conduct'].sudo().search([('id','=',paramater['training_id'])])
                if training_conduct:
                    
                    if training_conduct.conduct_line_ids:
                        employee_data = training_conduct.sudo().conduct_line_ids.filtered(lambda line:line.employee_id.id == paramater['employee_id'])
                        if training_conduct.stage_course_id.survey_pre_test_id.id == answer_sudo.survey_id.id:
                            list_score = []
                            score_before = request.env['survey.user_input'].sudo().search([('employee_id','=',paramater['employee_id']),('training_id','=',paramater['training_id']),('test_type','=',test_type)])
                            if score_before:
                                for data_score in score_before:
                                    list_score.append(data_score.score_by_amount)
                                final_score = sum(list_score)/len(list_score)
                                if employee_data:
                                    employee_data.sudo().pre_test = float(final_score)
                            else:
                                if employee_data:
                                    employee_data.sudo().pre_test = answer_sudo.score_by_amount
                                
                        if training_conduct.stage_course_id.survey_post_test_id.id == answer_sudo.survey_id.id:
                            list_score_post = []
                            score_before_post = request.env['survey.user_input'].sudo().search([('employee_id','=',paramater['employee_id']),('training_id','=',paramater['training_id']),('test_type','=',test_type)])
                            if score_before_post:
                                for data_score_post in score_before_post:
                                    list_score_post.append(data_score_post.score_by_amount)
                                final_score_post = sum(list_score_post)/len(list_score_post)
                                if employee_data:
                                    employee_data.sudo().post_test = float(final_score_post)
                                    if final_score_post <= training_conduct.minimal_score:
                                        employee_data.sudo().status = "Failed"
                                    else:
                                        employee_data.sudo().status = "Success"
                            else:
                                if employee_data:
                                    employee_data.sudo().post_test = answer_sudo.score_by_amount
                                    if answer_sudo.score_by_amount <= training_conduct.minimal_score:
                                        employee_data.sudo().status = "Failed"
                                    else:
                                        employee_data.sudo().status = "Success"
                        
                        if employee_data:
                            formula = training_conduct.course_id.final_score_formula
                            localdict = {"pre_test": employee_data.pre_test, "post_test": employee_data.post_test, "total": 0.0}
                            safe_eval(formula, localdict, mode='exec', nocopy=True)
                            employee_data.sudo().final_score = localdict["total"]
                                     
        return res
    
    
    
    @http.route('/survey/start/<string:survey_token>', type='http', auth='public', website=True)
    def survey_start(self, survey_token, answer_token=None, email=False, surveyId=None,applicantId=None,jobPosition=None,trainingId=None,employeeId=None,testType=None, **post):
        """ Start a survey by providing
         * a token linked to a survey;
         * a token linked to an answer or generate a new token if access is allowed;
        """
        # Get the current answer token from cookie
        res = super(SurveyTraining, self).survey_start(survey_token, answer_token, email, surveyId,applicantId,jobPosition,trainingId,employeeId, **post)
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
        if survey_sudo and trainingId and employeeId and testType:
            return request.redirect('/survey/%s/%s?surveyId=%s&trainingId=%s&employeeId=%s&testType=%s' % (survey_sudo.access_token, answer_sudo.access_token,survey_sudo.id,trainingId,employeeId,testType))

        return res