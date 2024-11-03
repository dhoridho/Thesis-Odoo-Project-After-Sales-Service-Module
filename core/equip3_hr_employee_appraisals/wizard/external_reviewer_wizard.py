from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from ...equip3_general_features.models.email_wa_parameter import EmailParam,waParam

class HrAppraisalExternalReviewerWizard(models.TransientModel):
    _name = 'hr.appraisal.external.reviewer.wizard'

    description = fields.Char('Description', default="Fill out the details about the Subject of your external feedback")
    appraisal_id = fields.Many2one('employee.performance', string="Appraisal")
    performance_review_id = fields.Many2one('performance.all.reviews', string="Performance Review")
    survey_id = fields.Many2one('survey.survey', string="Feedback Template")
    line_ids = fields.One2many('hr.appraisal.external.reviewer.wizard.line','parent_id')

    
    def send_external_feedback_wa_notification(self, reviewer, survey_url):
        send_by_wa = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_employee_appraisals.send_by_wa')
        wa_sender = waParam()
        wa_template_id = self.env.ref('equip3_hr_employee_appraisals.wa_template_peer_reviews', raise_if_not_found=False)
        if send_by_wa:
            wa_string = str(wa_template_id.message)
            phone_num = str(reviewer.work_phone)

            if "${reviewer_name}" in wa_string:
                wa_string = wa_string.replace("${reviewer_name}", reviewer.reviewer_name)
            if "${employee_name}" in wa_string:
                wa_string = wa_string.replace("${employee_name}", self.appraisal_id.employee_id.name)
            if "${job_position}" in wa_string:
                wa_string = wa_string.replace("${job_position}", self.appraisal_id.employee_id.job_id.name)
            if "${url_review}" in wa_string:
                wa_string = wa_string.replace("${url_review}", survey_url)
            if "${br}" in wa_string:
                wa_string = wa_string.replace("${br}", "\n")
            if "+" in phone_num:
                phone_num = int(phone_num.replace("+", ""))
            
            wa_sender.set_wa_string(wa_string,wa_template_id._name,template_id=wa_template_id)
            wa_sender.send_wa(phone_num)

    def action_send(self):
        count_lines = len(self.line_ids)
        if count_lines < 1:
            raise ValidationError("Reviewers line can't be empty!")
        peer_reviews_line = []
        external_target_score = 0
        for question in self.performance_review_id.external_feedback_template_id.question_and_page_ids:
            higher_score = max(question.suggested_answer_ids.mapped("answer_score"))
            external_target_score += higher_score
        peer_reviews_line.append((0, 0, {'role': 'external','weightage':self.performance_review_id.external_weightage,'target_score':external_target_score}))
        template_id = self.env.ref('equip3_hr_employee_appraisals.mail_template_peer_reviews', raise_if_not_found=False)
        external_reviewer_line = []
        for line in self.line_ids:
            external_reviewer_line.append((0, 0, {'company_name': line.company_name,'reviewer_name':line.reviewer_name,'email':line.email,'work_phone':line.work_phone,'relation':line.relation}))
            survey_review = self.env['survey.invite'].create(
                                            {'survey_id': self.performance_review_id.external_feedback_template_id.id,
                                            'emails': str(line.email), 'template_id': template_id.id})
            context = self.env.context = dict(self.env.context)
            survey_url = survey_review.survey_start_url + f"?surveyId={self.survey_id.id}&performanceId={self.appraisal_id.id}&reviewerRole=external&companyName={line.company_name}&reviewerName={line.reviewer_name}&reviewerEmail={line.email}"
            context.update({
                'email_to': line.email,
                'reviewer_name': line.reviewer_name,
                'employee_name': self.appraisal_id.employee_id.name,
                'url_review': survey_url,
                'title': self.performance_review_id.external_feedback_template_id.title,
                'job_position': self.appraisal_id.employee_id.job_id.name

            })
            template_id.send_mail(self.appraisal_id.id, force_send=False)
            template_id.with_context(context)
            self.send_external_feedback_wa_notification(line, survey_url)
        
        self.appraisal_id.peer_reviews_line_ids = peer_reviews_line
        self.appraisal_id.external_reviewer_line_ids = external_reviewer_line
        self.appraisal_id.is_sent_feedback = True
        self.appraisal_id.is_included_external_reviewers = False
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'hr.appraisal.external.reviewer.wizard.message',
            'target': 'new',
            'name': _('Message'),
        }

class HrAppraisalExternalReviewerWizardLine(models.TransientModel):
    _name = 'hr.appraisal.external.reviewer.wizard.line'

    parent_id = fields.Many2one('hr.appraisal.external.reviewer.wizard')
    company_name = fields.Char('Company Name')
    reviewer_name = fields.Char('Reviewer Name')
    email = fields.Char('Email')
    work_phone = fields.Char('Work Phone')
    relation = fields.Char('Relation')

class HrAppraisalExternalReviewerWizardMessage(models.TransientModel):
    _name = 'hr.appraisal.external.reviewer.wizard.message'
    _description = "Message Send feedback external"