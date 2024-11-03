from numpy import average
from odoo.addons.survey.controllers.main import Survey
from odoo.http import content_disposition, Controller, request, route

class SurveyDisc(Survey):
    
    
    def _prepare_question_html(self, survey_sudo, answer_sudo, **post):
        res = super(SurveyDisc, self)._prepare_question_html(survey_sudo,answer_sudo,**post)
        if answer_sudo.state == 'done' and str(answer_sudo.survey_type).upper() == 'DISC':
            answer_sudo.generate()
            match_score = []
            technical_test = []
            mask_score = 0
            core_private_score = 0
            mirror_perceived_score = 0
            if answer_sudo.mask_public_self:
                mask_score_check = answer_sudo.mask_public_self.job_suggestion_ids.filtered(lambda line: answer_sudo.job_id.id in line.job_suggestion.ids)
                if mask_score_check:
                    mask_score = mask_score_check.mask_public_self
            if answer_sudo.core_private_self:
                core_private_check = answer_sudo.core_private_self.job_suggestion_ids.filtered(lambda line: answer_sudo.job_id.id in line.job_suggestion.ids)
                if core_private_check:
                    core_private_score = core_private_check.core_private_self
            if answer_sudo.mirror_perceived_self:
                mirror_perceived_check = answer_sudo.mirror_perceived_self.job_suggestion_ids.filtered(lambda line: answer_sudo.job_id.id in line.job_suggestion.ids)
                if mirror_perceived_check:
                    mirror_perceived_score = mirror_perceived_check.mirror_perceived_self
            technical_test.append(mask_score)
            technical_test.append(core_private_score)
            technical_test.append(mirror_perceived_score)
            match_score.append((0,0,{'name':'Mask Public Self','match_score':mask_score}))
            match_score.append((0,0,{'name':'Core Private Self','match_score':core_private_score}))
            match_score.append((0,0,{'name':'Mirror Perceived Self','match_score':mirror_perceived_score}))
            answer_sudo.disc_match_score_ids = match_score
            personality_score = request.env['quadrant.score.line'].sudo().search(
                            [('applicant_id', '=', answer_sudo.applicant_id.id), ('name', '=', 'Personality')], limit=1)
            if personality_score:
                personality_score.sudo().write({'technical_test': average(technical_test)})
            else:
                request.env['quadrant.score.line'].sudo().create(
                {'name':'Personality',
                'applicant_id':answer_sudo.applicant_id.id,
                'survey_input_id':answer_sudo.id,
                'technical_test':average(technical_test)})            

        return res