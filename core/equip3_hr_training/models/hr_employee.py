from odoo import api, fields, models
from odoo.exceptions import ValidationError

class HREmployee(models.Model):
    _inherit = 'hr.employee'
    _description = 'HR Employee'

    training_history_ids = fields.One2many('training.history.line', 'employee_id', string='Training Courses')


class TrainingHistoryLine(models.Model):
    _name = 'training.history.line'
    _description = 'Training Hostory Line'

    def _compute_training_required(self):
        for rec in self:
            if rec.course_id in rec.job_id.course_ids:
                rec.training_required = 'yes'
            else:
                rec.training_required = 'no'
            if rec.state != 'expired':
                rec.update_state()
            else:
                rec.state = rec.state

    def update_state(self):
        for rec in self:
            if not rec.stage_course_id.stage_id:
                rec.state = 'to_do'
            elif rec.stage_course_id.stage_id.name == 'Approved' or rec.stage_course_id.stage_id.name == 'On Progress':
                rec.state = 'on_progress'
            elif rec.training_conduct_line_id.status == 'Success':
                rec.state = 'success'
            elif rec.training_conduct_line_id.status == 'Failed':
                rec.state = 'failed'
            if rec.training_conduct_line_id and not rec.training_conduct_line_id.attended:
                rec.state = 'not_attended'


    employee_id = fields.Many2one('hr.employee', string='Employee')
    job_id = fields.Many2one('hr.job', string='Job Position', related='employee_id.job_id')
    course_id = fields.Many2one('training.courses', string='Training Courses', required=True)
    date_completed = fields.Date(string='Date Completed', related='training_conduct_id.end_date')
    expiry_date = fields.Date(string='Expiry Date')
    state = fields.Selection(
        [('to_do', 'To Do'), ('on_progress', 'On Progress'), ('success', 'Success'), ('failed', 'Failed'),
         ('expired', 'Expired'), ('not_attended', 'Not Attended')], string='Status', default='to_do')
    training_conduct_id = fields.Many2one('training.conduct', string='Training Conduct Origin')
    start_date = fields.Date('Date Start', related='training_conduct_id.start_date')
    stage_course_id = fields.Many2one('training.courses.stages', related='training_conduct_id.stage_course_id')
    stage_course_domain_ids = fields.Many2many('training.courses.stages',
                                               related='training_conduct_id.stage_course_domain_ids')
    training_conduct_line_id = fields.Many2one('training.conduct.line', string='Training Conduct Line Origin')
    certificates = fields.Binary(string='Certificates', related='training_conduct_line_id.certificate_attachment')
    certificate_attachment_fname = fields.Char('Certificate Name', related='training_conduct_line_id.certificate_attachment_fname')
    training_required = fields.Selection([('no', 'No'), ('yes', 'Yes')], default='no', string='Training Required',
                                         compute='_compute_training_required')

    created_by_model = fields.Selection([('by_job', 'By Job'), ('by_conduct', 'By Conduct'), ('by_request', 'By Request'), ('by_update_from_conduct', 'By Update from conduct'), ('by_expiry', 'By Expiry'), ('by_failed', 'By Failed')])
