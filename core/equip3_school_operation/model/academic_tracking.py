from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError

class AcademicTracking(models.Model):
    _name = "academic.tracking"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = "student_id"
    _description = "Academic Tracking"
    _order = "create_date desc"

    student_id = fields.Many2one('student.student', string='Student', required=True)
    school_id = fields.Many2one('school.school', string='School', required=True)
    total_credit = fields.Float(string='Total Credit' ,track_visibility='onchange', compute='_compute_total_credit')
    pass_credit = fields.Float(string='Pass Credit' ,track_visibility='onchange', compute='_compute_pass_credit')
    pending_credit = fields.Float(string='Pending Credit' ,track_visibility='onchange')
    related_program_ids = fields.One2many('standard.standard', related='student_id.program_ids', string='Related Programs')
    program_id = fields.Many2one('standard.standard', string='Program', domain="[('id', 'in', related_program_ids)]", required=True)
    intake_ids = fields.One2many('academic.tracking.intake', 'academic_tracking_id', string='Intake')
    all_score_subject_ids = fields.One2many('subject.score', 'all_academic_tracking_id', string='All Subject')
    current_score_subject_ids = fields.One2many('subject.score', 'current_academic_tracking_id', string='Current Subject')
    pass_score_subject_ids = fields.One2many('subject.score', 'pass_academic_tracking_id', string='Pass Subject')
    failed_score_subject_ids = fields.One2many('subject.score', 'failed_academic_tracking_id', string='Failed Subject')
    message_ids = fields.One2many(
        "mail.message",
        "res_id",
        "Messages",
        domain=lambda self: [("model", "=", self._name)],
        auto_join=True,
        help="Messages can entered",
    )
    message_follower_ids = fields.One2many(
        "mail.followers",
        "res_id",
        "Followers",
        domain=lambda self: [("res_model", "=", self._name)],
        help="Select message followers",
    )
    activity_ids = fields.One2many(
        'mail.activity', 'res_id', 'Activities',
        auto_join=True,
        groups="base.group_user", )
    branch_id = fields.Many2one('res.branch', readonly=True, compute='_compute_branch_id')
    student_admission_id = fields.Many2one(comodel_name='student.admission.register', string='Student Admission')

    @api.depends('school_id')
    def _compute_branch_id(self):
        for rec in self:
            rec.branch_id = rec.school_id.branch_id.id

    @api.depends('all_score_subject_ids', 'all_score_subject_ids.credits')
    def _compute_total_credit(self):
        for rec in self:
            rec.total_credit = sum(line.credits for line in rec.all_score_subject_ids)

    @api.depends('pass_score_subject_ids', 'pass_score_subject_ids.credits')
    def _compute_pass_credit(self):
        for rec in self:
            rec.pass_credit = sum(line.credits for line in rec.pass_score_subject_ids)

    # @api.model
    # def create(self, vals):
    #     res = super(AcademicTracking, self).create(vals)
    #     for subject in res.all_subject_ids:
    #         core_subject = subject.core_subject_id and subject.core_subject_id.id
    #         elective_subject = subject.elective_subject_ids and subject.elective_subject_ids.id
    #         vals = {
    #             'student_id': res.student_id and res.student_id.id,
    #             'subject_id': core_subject or elective_subject,
    #             'intake_id': subject.intake_id and subject.intake_id.id,
    #             'program_id': res.program_id and res.program_id.id,
    #             'year_id': subject.year_id and subject.year_id.id,
    #             'term_id': subject.term_id and subject.term_id.id,
    #         }
    #         score = self.env['subject.score'].create(vals)
    
    def subject_score_action_form_btn(self):
        domain = [('student_id', '=', self.student_id.id), ('program_id', '=', self.program_id.id)]
        action = {
            'type': 'ir.actions.act_window',
            'name': 'Subject Score',
            'res_model': 'subject.score',
            'domain': domain,
            'view_mode': 'tree,form',
            'context': {'search_default_groupby_program': 1, 'search_default_groupby_student': 1, 'search_default_groupby_year':1, 'search_default_groupby_term': 1},
        }
        return action

    def attendance_action_btn(self):
        domain = [('student_id', '=', self.student_id.id)]
        action = {
            'type': 'ir.actions.act_window',
            'name': 'Attendance Line',
            'res_model': 'daily.attendance.line',
            'domain': domain,
            'view_mode': 'tree',
            'context': {'search_default_groupby_year': 1, 'search_default_groupby_term':1, 'search_default_groupby_subject': 1},
        }
        return action

    def transcript_btn(self):
        pass

class AcademicTrackingIntake(models.Model):
    _name = "academic.tracking.intake"

    academic_tracking_id = fields.Many2one('academic.tracking', string='Tracking')
    intake_id = fields.Many2one('school.standard', string='Intake')
    status = fields.Selection([('active', 'Active'), ('unactive', 'Unactive'), ('fail', 'Fail'),  ('pass', 'Pass')],'Status')
    group_class_id = fields.Many2one('group.class', string='Group Class')

    @api.onchange('intake_id')
    def _onchange_intake_id(self):
        group = self.env['group.class'].search([('name', '=', self.intake_id.name)])
        self.group_class_id = group.id
