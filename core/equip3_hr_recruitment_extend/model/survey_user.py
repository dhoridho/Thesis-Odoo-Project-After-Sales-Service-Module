from odoo import api, fields, models, _
from datetime import datetime

class SurveyUserInput(models.Model):
    """ Metadata for a set of one user's answers to a particular survey """
    _inherit = "survey.user_input"
    score_by_amount = fields.Float("Score",compute="_get_score_value", store=True)
    min_qualification = fields.Float("Minimal Score")
    is_all_test_result = fields.Boolean()

    
    @api.depends('user_input_line_ids','user_input_line_ids.answer_score')
    def _get_score_value(self):
        for record in self:
            total = 0
            if record.user_input_line_ids:
                for line in record.user_input_line_ids:
                    total +=  line.answer_score
                record.score_by_amount = total
            else:
                record.score_by_amount = 0
                
    @api.model
    def update_applicant_test_result_score(self):
        now = datetime.now()
        applicant_result = self.sudo().search([('survey_type', '=', 'GENERAL'),('create_date', '<', now)])
        for res in applicant_result:
            total = 0
            if res.user_input_line_ids:
                for line in res.user_input_line_ids:
                    total +=  line.answer_score
                res.score_by_amount = total
            else:
                res.score_by_amount = 0

        applicants = self.env['hr.applicant'].sudo().search([('active','=',True)])
        for applicant in applicants:
            survey_user_input = self.sudo().search([('applicant_id','=',applicant.id),('survey_type','=','GENERAL')], order='create_date desc',limit=1)
            if survey_user_input:
                applicant.previous_score = survey_user_input.score_by_amount