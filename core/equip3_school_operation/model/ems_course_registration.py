from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError, Warning

class EmsCourseRegistration(models.Model):
    _name = 'ems.course.registration'
    _description = "EMS Course Registration"
    _rec_name = 'school_id'

    student_id = fields.Many2one('student.student', required=True, string='Student Name')
    pid = fields.Char(related="student_id.pid", string="Student ID", readonly=True, help="Student Personal ID No.")
    school_id = fields.Many2one('school.school', required=True, string='School')
    related_program_ids = fields.One2many('standard.standard', string='Related Program', compute='_compute_related_program_ids')
    program_id = fields.Many2one('standard.standard', required=True, string='Program', domain="[('school_id', '=', school_id.id)]")
    line_ids = fields.One2many('ems.course.registration.line', 'course_registration_id', string='Course Registration Line')
    state = fields.Selection([('draft', 'Draft'), ('applied', 'Applied'), ('confirmed', 'Confirmed'), ('done', 'Done'), ('rejected', 'Rejected')], string='Status', default='draft')
    approved_matrix_id = fields.Many2one('course.approval.matrix', compute="_compute_approved_matrix", string="Approving Matrix", store=True)
    approved_matrix_ids = fields.One2many('course.approval.matrix.line', 'ems_course_id', compute="_approving_matrix_lines", store=True, string="Approved Matrix")
    is_approve_button = fields.Boolean(string='Is Approve Button', compute='_get_approve_button', store=False)
    approval_matrix_line_id = fields.Many2one('course.approval.matrix.line', string='Approval Matrix Line', compute='_get_approve_button', store=False)

    @api.depends('school_id')
    def _compute_related_program_ids(self):
        for rec in self:
            rec.related_program_ids = rec.school_id.school_program_ids

    @api.depends('school_id', 'program_id')
    def _compute_approved_matrix(self):
        for record in self:
            record.approved_matrix_id = False
            if record.school_id and record.program_id:
                approval_matrix_id = self.env['course.approval.matrix'].search([
                    ('school_id', '=', record.school_id.id),
                    ('program_id', '=', record.program_id.id)
                ], limit=1)
                record.approved_matrix_id = approval_matrix_id and approval_matrix_id.id or False

    @api.depends('approved_matrix_id')
    def _approving_matrix_lines(self):
        data = [(5, 0, 0)]
        for record in self:
            record.approved_matrix_ids = []
            for line in record.approved_matrix_id.approval_matrix_ids:
                data.append((0, 0, {
                    'state' : line.state,
                    'user_id' : [(6, 0, line.user_id.ids)],
                    'minimum_approver' : line.minimum_approver,
                }))
            record.approved_matrix_ids = data
    
    def _get_approve_button(self):
        for record in self:
            record.is_approve_button = False
            record.approval_matrix_line_id = False
            if record.state == "applied":
                matrix_lines = sorted(record.approved_matrix_ids.filtered(lambda r: not r.approved and r.state == "applied"))
                if matrix_lines:
                    matrix_line_id = matrix_lines[0]
                    if self.env.user.id in matrix_line_id.user_id.ids and self.env.user.id != matrix_line_id.last_approved.id:
                        record.is_approve_button = True
                        record.approval_matrix_line_id = matrix_line_id.id
            elif record.state == "confirmed":
                matrix_lines = sorted(record.approved_matrix_ids.filtered(lambda r: not r.approved and r.state == "confirmed"))
                if matrix_lines:
                    matrix_line_id = matrix_lines[0]
                    if self.env.user.id in matrix_line_id.user_id.ids and self.env.user.id != matrix_line_id.last_approved.id:
                        record.is_approve_button = True
                        record.approval_matrix_line_id = matrix_line_id.id
    
    def action_apply(self):
        for record in self:
            record.state = 'applied'

    def ems_course_done(self):
        for record in self:
            record.state = 'done'

    def action_confirm(self):
        for record in self:
            record.approval_matrix_line_id.write({
                'last_approved': self.env.user.id,
                'approved_users': [(4, self.env.user.id)]
            })
            if record.approval_matrix_line_id.approved:
                record.state = 'confirmed'

    def action_reject(self):
        for record in self:
            record.approval_matrix_line_id.write({
                'last_approved': self.env.user.id,
                'approved_users': [(4, self.env.user.id)]
            })
            if record.approval_matrix_line_id.approved:
                record.state = 'rejected'

    def action_set_to_draft(self):
        for record in self:
            record.approval_matrix_line_id.write({
                'last_approved': self.env.user.id,
                'approved_users': [(4, self.env.user.id)]
            })
            if record.approval_matrix_line_id.approved:
                record.state = 'draft'
    
    def ems_course_done(self):
        for record in self:
            record.approval_matrix_line_id.write({
                'last_approved': self.env.user.id,
                'approved_users': [(4, self.env.user.id)]
            })
            record.state = 'done'

class EmsCourseRegistrationLine(models.Model):
    _name = 'ems.course.registration.line'
    _description = "EMS Course Registration Line"

    course_registration_id = fields.Many2one('ems.course.registration', string='EMS Course Registration')
    course_id = fields.Many2one('subject.subject', string='Subject Name')
    course_code = fields.Char(related='course_id.code', readonly=True, string='Subject Code')

class CourseApprovalMatrix(models.Model):
    _name = 'course.approval.matrix'

    name = fields.Char(string='Name', required=True)
    school_id = fields.Many2one('school.school', string='School', required=True)
    program_id = fields.Many2one('standard.standard', string="Program", required=True)
    approval_matrix_ids = fields.One2many('course.approval.matrix.line', 'approval_matrix_id', string='Approval Matrix')
    program_ids = fields.One2many('standard.standard',related="school_id.school_program_ids", string="Program", store=False)

    @api.constrains('school_id', 'program_id')
    def _check_existing_record(self):
        for record in self:
            if record.school_id and record.program_id:
                school_id = self.search([('school_id', '=', record.school_id.id), 
                              ('id', '!=', record.id),
                              ('program_id', '=', record.program_id.id)], limit=1)
                if school_id:
                    raise ValidationError("Please select other School and Program.")

class CourseApprovalMatrixLine(models.Model):
    _name = 'course.approval.matrix.line'

    user_id = fields.Many2many('res.users', ondelete="cascade",
                              help='Enter related user of the student')
    approval_matrix_id = fields.Many2one('course.approval.matrix')
    minimum_approver = fields.Integer(default=1)    
    approved_users = fields.Many2many('res.users', 'approved_users_course_rel', 'class_id', 'user_ids', string='Users') 
    last_approved = fields.Many2one('res.users', string='Users')
    approved = fields.Boolean('Approved', compute="_compute_approved", store=True)    
    ems_course_id = fields.Many2one('ems.course.registration', string="EMS Course")
    state = fields.Selection([('applied', 'Applied'),
                              ('confirmed', 'Confirmed')],
                             'Status', readonly=False, default="draft",
                             help='State of the student registration form')
    

    @api.depends('user_id', 'approved_users')
    def _compute_approved(self):
        for record in self:
            record.approved = False
            if len(record.approved_users) == record.minimum_approver:
                record.approved = True