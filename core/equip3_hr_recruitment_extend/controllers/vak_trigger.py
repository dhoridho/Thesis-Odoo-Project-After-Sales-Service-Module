from odoo.addons.survey.controllers.main import Survey


class SurveyIst(Survey):
    
    
    def _prepare_question_html(self, survey_sudo, answer_sudo, **post):
        res = super(SurveyIst, self)._prepare_question_html(survey_sudo,answer_sudo,**post)
        if answer_sudo.state == 'done' and str(answer_sudo.survey_type).upper() == 'VAK':
            answer_sudo.generate_vak()

        return res