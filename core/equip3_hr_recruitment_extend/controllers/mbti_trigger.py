from odoo.addons.survey.controllers.main import Survey


class SurveyMbti(Survey):
    
    
    def _prepare_question_html(self, survey_sudo, answer_sudo, **post):
        res = super(SurveyMbti, self)._prepare_question_html(survey_sudo,answer_sudo,**post)
        if answer_sudo.state == 'done' and str(answer_sudo.survey_type).upper() == 'MBTI':
            answer_sudo.generate_mbti()
            answer_sudo.next_stage_on_psy_test()
        return res