from lxml import etree

from odoo import models, fields, api, exceptions, _
from odoo.exceptions import ValidationError


class SurveyExtendInherit(models.Model):
    _inherit = 'survey.survey'
    survey_type = fields.Selection(
        [('general', 'General'), ('disc', 'DISC'), ('epps', 'EPPS'), ('interview', 'Interview'),
         ('peer_review', 'Peer Review'), ('papikostick', 'Papikostick'), ('ist', 'IST'), ('tasks', 'Tasks'),
         ('mbti', 'MBTI'), ('vak', 'VAK'), ('kraepelin', 'Kraepelin Test'), ('exit_interview', 'Exit Interview')], default='general', readonly=True)
    is_read_only_type = fields.Boolean(default=False)
    category_id = fields.Many2one('survey.category')
    kraepelin_columns = fields.Integer('Columns', default=45, required=True)
    kraepelin_rows = fields.Integer('Rows', default=45, required=True)
    kraepelin_time_per_column = fields.Integer('Time per Column (Seconds)',
                                               compute='_compute_kraepelin_actual_columns_rows_time', store=True,
                                               readonly=False)
    kraepelin_actual_columns = fields.Integer('Actual Columns', compute='_compute_kraepelin_actual_columns_rows_time',
                                              store=True)
    kraepelin_actual_rows = fields.Integer('Actual Rows', compute='_compute_kraepelin_actual_columns_rows_time',
                                           store=True)

    @api.depends('kraepelin_columns', 'kraepelin_rows')
    def _compute_kraepelin_actual_columns_rows_time(self):
        for survey in self:
            if survey.survey_type == 'kraepelin':
                survey.kraepelin_time_per_column = survey.kraepelin_rows * 2 / 3
                survey.kraepelin_actual_rows = 2 * survey.kraepelin_rows - 1
                survey.kraepelin_actual_columns = 2 * survey.kraepelin_columns

                for page in survey.question_and_page_ids:
                    if page.question_type == 'kraepelin':
                        page.kraepelin_columns = survey.kraepelin_columns
                        page.kraepelin_rows = survey.kraepelin_rows
                        page.kraepelin_time_per_column = survey.kraepelin_time_per_column
                        page.kraepelin_actual_columns = survey.kraepelin_actual_columns
                        page.kraepelin_actual_rows = survey.kraepelin_actual_rows

    @api.constrains('kraepelin_columns', 'kraepelin_rows')
    def _check_kraepelin_columns_rows(self):
        for survey in self:
            if survey.survey_type == 'kraepelin':
                if not survey.kraepelin_columns or not survey.kraepelin_rows:
                    raise ValidationError("Columns and Rows must be filled.")

    # def unlink(self):
    #     for rec in self:
    #         if rec.survey_type in ('disc','epps'):
    #             raise ValidationError(f"Cannot delete survey type {str(rec.survey_type).upper()}")
    #     res = super(SurveyExtendInherit, self).unlink()
    #     return res

    def action_send_survey(self):
        """ Open a window to compose an email, pre-filled with the survey message """
        # Ensure that this survey has at least one page with at least one question.
        if (not self.page_ids and self.questions_layout == 'page_per_section') or not self.question_ids:
            raise exceptions.UserError(_('You cannot send an invitation for a survey that has no questions.'))

        if self.state == 'closed':
            raise exceptions.UserError(_("You cannot send invitations for closed surveys."))

        template = self.env.ref('survey.mail_template_user_input_invite', raise_if_not_found=False)

        local_context = dict(
            self.env.context,
            default_survey_id=self.id,
            default_use_template=bool(template),
            default_template_id=template and template.id or False,
            notif_layout='mail.mail_notification_light',
        )
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'name': 'Hashmicro',
            'res_model': 'survey.invite',
            'target': 'new',
            'context': local_context,
        }

    @api.onchange('survey_type')
    def _onchange_survey_type(self):
        for record in self:
            if record.survey_type == 'disc':
                master_list = []
                if not record.question_and_page_ids:
                    master_data = self.env['survey.question'].search([('is_primary_master_data', '=', True)])
                    data = [line.id for line in master_data]
                    master_list.extend(data)
                    record.question_and_page_ids = [(6, 0, master_list)]

    @api.model
    def write(self, vals):
        for survey in self:
            if survey.survey_type == 'kraepelin':
                for page in survey.question_and_page_ids:
                    if page.question_type == 'kraepelin':
                        if 'kraepelin_columns' in vals:
                            page.kraepelin_columns = vals['kraepelin_columns']
                        if 'kraepelin_rows' in vals:
                            page.kraepelin_rows = vals['kraepelin_rows']
                        if 'kraepelin_time_per_column' in vals:
                            page.kraepelin_time_per_column = vals['kraepelin_time_per_column']
                        page.kraepelin_actual_columns = 2 * page.kraepelin_columns
                        page.kraepelin_actual_rows = 2 * page.kraepelin_rows - 1
        res = super(SurveyExtendInherit, self).write(vals)
        return res
