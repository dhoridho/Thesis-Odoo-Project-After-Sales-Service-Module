from odoo import _, api, fields, models, tools
from odoo.exceptions import UserError, ValidationError, Warning
from datetime import datetime, date
from ...school.models.school import EM

import re

# Override email validation method to fix blank spaces
def emailvalidation(email):
    """Check valid email."""
    if email:
        email_regex = re.compile(EM)
        if not email_regex.match(email):
            raise ValidationError(_("This seems not to be valid email. Please enter email in correct format!"))

class StandardStandard(models.Model):
    _name = 'standard.standard'
    _inherit = ["standard.standard", "mail.thread", "mail.activity.mixin"]
    _description = "Program"
    _rec_name = 'title'
    _order = "create_date desc"

    @api.model
    def _domainSchool(self):
        allowed_branch_ids = self.env.branches.ids
        return [('school_branch_ids', 'in', allowed_branch_ids)]
    
    @api.model
    def _default_branch(self):
        default_branch_id = self.env.context.get('default_branch_id',False)
        if default_branch_id:
            return default_branch_id
        return self.env.company_branches[0].id if len(self.env.company_branches) == 1 else False

    @api.model
    def _domain_branch(self):
        return [
            ('id', 'in', self.env.branches.ids),
            ('company_id','=', self.env.company.id)
        ]

    color = fields.Integer('Color Index', help='Index of color')
    name = fields.Char(track_visibility='onchange')
    fees_ids = fields.Many2one(
        'student.fees.structure',
        string='Fees Structure',
        required=True,
        track_visibility='onchange',
    )
    school_id = fields.Many2one('school.school', string="School", required=True, domain=_domainSchool)
    intake_ids = fields.One2many('school.standard', 'standard_id', string="Intake")
    academic_month_ids = fields.Many2many("academic.month", string="Term")
    course_ids = fields.Many2many("subject.subject", string="Course")
    program_subject_ids = fields.One2many("program.subject.line", 'program_id', string="EMS Subject")
    sequence = fields.Integer(required=False)
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
    branch_id = fields.Many2one(
        comodel_name='res.branch',
        check_company=True,
        domain=_domain_branch,
        readonly=False,
        required=False,
        default=_default_branch
    )
    title = fields.Char(string='Title', track_visibility='onchange', compute='_compute_title')
    branch_ids = fields.One2many(
        comodel_name='res.branch',
        related='school_id.school_branch_ids',
        string="Branch"
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        default=lambda self: self.env.company,
        string="Company",
    )
    school_approval_matrix_id = fields.Many2one('school.approval.matrix', string="School Approval Matrix")
    active = fields.Boolean(default=True, help="Activate/Deactivate Program")

    @api.depends('name', 'branch_id')
    def _compute_title(self):
        for rec in self:
            if rec.branch_id and rec.name:
                rec.title = rec.name + ' - ' + rec.branch_id.name
            else:
                rec.title = rec.name

    @api.depends('school_id')
    def _compute_branch_id(self):
        for rec in self:
            rec.branch_id = rec.school_id.branch_id.id

    @api.model
    def create(self, vals):
        res = super(StandardStandard, self).create(vals)
        for program_subject in res.program_subject_ids:
            subject = program_subject.subject_id
            if subject and (res.id not in subject.standard_ids.ids):
                subject.write({'standard_ids': [(4, res.id)]})
        return res

    def write(self, vals):
        res = super(StandardStandard, self).write(vals)
        for program_subject in self.program_subject_ids:
            subject = program_subject.subject_id
            if subject and (self.id not in subject.standard_ids.ids):
                subject.write({'standard_ids': [(4, self.id)]})
        return res

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context

        if context.get("allowed_company_ids"):
            domain += [("company_id", "in", context.get("allowed_company_ids"))]

        if context.get("allowed_branch_ids"):
            domain += [
                "|",
                ("branch_id", "in", context.get("allowed_branch_ids")),
                ("branch_id", "=", False),
            ]

        result = super(StandardStandard, self).search_read(
            domain=domain, fields=fields, offset=offset, limit=limit, order=order
        )

        return result

    @api.model
    def read_group(
        self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True
    ):
        domain = domain or []
        context = self.env.context

        if context.get("allowed_company_ids"):
            domain.extend([("company_id", "in", self.env.companies.ids)])

        if context.get("allowed_branch_ids"):
            domain.extend(
                [
                    "|",
                    ("branch_id", "in", context.get("allowed_branch_ids")),
                    ("branch_id", "=", False),
                ]
            )
        return super(StandardStandard, self).read_group(
            domain,
            fields,
            groupby,
            offset=offset,
            limit=limit,
            orderby=orderby,
            lazy=lazy,
        )
    
    def action_archive(self):
        for record in self:
            record.write({'active': False})
    
    def action_unarchive(self):
        for record in self:
            record.write({'active': True})


class ProgramSubjectLine(models.Model):
    _name = 'program.subject.line'
    _description = "Program Subject Line"

    program_id = fields.Many2one('standard.standard', string='Program')
    subject_id = fields.Many2one('subject.subject', string='Subject')
    subject_type = fields.Selection([('core', 'Core'), ('elective', 'Elective')], string='Subject Type')


class StandardDivision(models.Model):
    _inherit = 'standard.division'

    color = fields.Integer('Color Index', help='Index of color')


class StandardMedium(models.Model):
    _inherit = 'standard.medium'

    color = fields.Integer('Color Index', help='Index of color')


class ClassRoom(models.Model):
    _inherit = 'class.room'

    color = fields.Integer('Color Index', help='Index of color')


class StudentHistory(models.Model):
    _inherit = 'student.history'

    medium_id = fields.Many2one('standard.medium', 'Medium', required=False,
                                help='Medium of the standard')
    maritual_status = fields.Selection([('unmarried', 'Unmarried'),
                                        ('married', 'Married')],
                                       'Status')
    status = fields.Selection([('active', 'Active'), ('transition', 'Transition'), ('unactive', 'Unactive')],
                              'Status')
    division_id = fields.Many2one('standard.division', 'Division',
                                  required=False, help='Standard division')
    standard_id = fields.Many2one('school.standard', 'Intake',
                                  help='Standard of the following student')
    school_id = fields.Many2one('school.school', string='School')
    program_id = fields.Many2one('standard.standard', string='Program')
    term_id = fields.Many2one('academic.month', string="Term")
    fees_ids = fields.Many2one('student.fees.structure', related="program_id.fees_ids", string='Fees Structure',
                               store=True)
    group_class_id = fields.Many2one('group.class', string='Group Class')
    branch_id = fields.Many2one(comodel_name='res.branch', readonly=True, compute='_compute_branch_id')

    @api.depends('school_id')
    def _compute_branch_id(self):
        for rec in self:
            rec.branch_id = rec.school_id.branch_id.id


class AcademicMonth(models.Model):
    _inherit = 'academic.month'

    enrollment_date_start = fields.Date('Enrollment Start Date', required=True,
                                        help='Enrollment starting date of academic year')
    enrollment_date_stop = fields.Date('Enrollment End Date', required=True,
                                       help='Enrollment ending of academic year')
    term_id = fields.Many2one("standard.standard", string="Term")
    # active = fields.Boolean(string='Active', compute='_compute_active')
    checkactive = fields.Boolean(compute='_compute_active', string='Active', store="1")

    @api.depends('date_start', 'date_stop', 'year_id')
    def _compute_active(self):
        for rec in self:
            # rec.active = True
            rec.checkactive = True
            if not rec.date_stop or date.today() > rec.date_stop or not rec.year_id.current or not (
                    rec.date_start.month <= date.today().month <= rec.date_stop.month):
                # rec.active = False
                rec.checkactive = False

    @api.constrains('date_start', 'date_stop')
    def check_months(self):
        '''Method to check duration of date'''
        for rec in self:
            if rec.date_stop < rec.date_start:
                raise ValidationError(_('End of Period date should be greater than Start of Periods Date!'))
            # """Check start date should be less than stop date."""
            exist_month_rec = rec.search([('id', '!=', rec.ids)])
            for old_month in exist_month_rec:
                if old_month.date_start <= rec.date_start <= old_month.date_stop \
                        or old_month.date_start <= rec.date_stop <= old_month.date_stop:
                    raise ValidationError(_(
                        "Error! You cannot define overlapping months!"))
    
    @api.constrains('enrollment_date_start', 'enrollment_date_stop', 'date_start')
    def check_enrollment_start_end_date(self):
        for term in self:
            message = ""
            if term.enrollment_date_start and term.enrollment_date_stop and term.date_start:
                if term.enrollment_date_start >= term.date_start and term.enrollment_date_stop >= term.date_start:
                    message = "Enrollment Start Date and Enrollment End Date must be less than to Date Start!"
                elif term.enrollment_date_start >= term.date_start:
                    message = "Enrollment Start Date must be less than to Date Start!"
                elif term.enrollment_date_stop >= term.date_start:
                    message = "Enrollment End Date must be less than to Date Start!"

            if len(message) > 0:
                raise ValidationError(_(message))

class SubjectSubject(models.Model):
    _name = "subject.subject"
    _inherit = ["subject.subject", "mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"

    name = fields.Char(string='Name', track_visibility='onchange')
    syllabus = fields.Binary(string='Syllabus', attachment=True)
    file_name = fields.Char(string="File Name")
    program_id = fields.Many2one('standard.standard', string='Program', required=False)
    related_term_ids = fields.Many2many(related='program_id.academic_month_ids')
    classroom_id = fields.Many2one('class.room', string="Class Room", required=False)
    term_id = fields.Many2one('academic.month', string="Term", required=False)
    subject_type = fields.Selection(
        string='Subject Type',
        selection=[('core', 'Core'), ('elective', 'Elective')], default="core")
    timetable_ids = fields.One2many('time.table', 'subject_ids', 'TimeTable',
                                    help='Enter the timetable pattern')
    credits = fields.Integer(string='Credits', track_visibility='onchange', help='Credits of subject')
    intake_id = fields.Many2many('school.standard', string="Intake")
    year_id = fields.Many2one('school.school', string='School', required=False)
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
    active = fields.Boolean(default=True, help="Activate/Deactivate Subject")

    _sql_constraints = [
        ('name_code_subject_uniq', 'unique(name, code)', "Two subjects can't have the same name and code!")
    ]

    @api.model
    def create(self, vals):
        res = super(SubjectSubject, self).create(vals)
        for rec in res.standard_ids:
            rec.write({'program_subject_ids': [(0, 0, {'subject_id': res.id, 'subject_type': res.subject_type})]})
        return res

    @api.constrains("maximum_marks", "minimum_marks")
    def check_marks(self):
        """Method to check marks."""
        if self.minimum_marks >= self.maximum_marks:
            pass

    def write(self, vals):
        res = super(SubjectSubject, self).write(vals)
        for rec in self.standard_ids.program_subject_ids:
            if rec.subject_id.id == self.id:
                rec.write({'subject_type': self.subject_type,
                           'subject_id': self.id})

        # for x in self.standard_ids:
        #     vals2 = {
        #         'ems_program_id': x.id,
        #     }
        #     if self.subject_type == 'core':
        #         vals2.update({'core_subject_id': self.id})
        #     elif self.subject_type == 'elective':
        #         vals2.update({'elective_subject_ids': self.id})
        #     self.env['ems.subject'].write(vals2)

        if 'teacher_ids' in vals:
            initial_teacher = set(self.teacher_ids.ids)
            current_teacher = set(vals['teacher_ids'][0][2])
            deleted_ids = initial_teacher - current_teacher

            if deleted_ids:
                for deleted_id in deleted_ids:
                    deleted = self.env['school.teacher'].browse(deleted_id)
                    message_body = 'Teacher (%s) is Removed' % (deleted.name)
                    self.message_post(body=message_body)

        return res

    def action_view_intake(self):
        intake_ids = []
        for intake in self.env['school.standard'].search([]):
            subject_ids = []
            if self.subject_type == 'core':
                subject_ids = intake.intake_subject_line_ids.mapped('subject_id').ids
            if self.id in subject_ids:
                intake_ids.append(intake.id)

        return {
            'type': 'ir.actions.act_window',
            'name': _('Intake'),
            'res_model': 'school.standard',
            'view_mode': 'tree,form,pivot',
            'domain': [('id', 'in', intake_ids)],
            'context': {},
            "target": 'current',
        }
    
    def action_archive(self):
        for record in self:
            record.write({'active': False})
    
    def action_unarchive(self):
        for record in self:
            record.write({'active': True})

class SubjectSyllabus(models.Model):
    _inherit = "subject.syllabus"

    file_name = fields.Char(string="File Name")


class SchoolApprovalMatrix(models.Model):
    _name = 'school.approval.matrix'
    _description = 'Admission Approval'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"

    @api.model
    def _domainSchool(self):
        allowed_branch_ids = self.env.branches.ids
        return [("school_branch_ids", "in", allowed_branch_ids)]

    @api.model
    def _default_branches(self):
        allowed_branch_ids = self.env.branches.ids
        return allowed_branch_ids

    name = fields.Char(string='Name', track_visibility='onchange')
    school_id = fields.Many2one('school.school', string='School', tracking=True, domain=_domainSchool)
    program_id = fields.Many2one(
        'standard.standard',
        string="Program",
        tracking=True
    )
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('applied', 'Applied'),
            ('confirmed', 'Confirmed'),
            ('done', 'Done'),
            ('reject', 'Reject')
        ],
        string='Status',
        readonly=True,
        default="draft",
        help='State of the student registration form'
    )
    level = fields.Integer(compute="_get_level")
    approval_matrix_ids = fields.One2many('school.approval.matrix.line', 'approval_matrix_id')
    program_ids = fields.One2many(
        comodel_name='standard.standard',
        inverse_name='school_approval_matrix_id',
        related="school_id.school_program_ids",
        string="Program",
        store=False
    )
    branch_id = fields.Many2one('res.branch', readonly=True, compute='_compute_branch_id')
    branch_ids = fields.One2many(
        comodel_name='res.branch',
        readonly=True,
        related='school_id.school_branch_ids',
        string="Branch"
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        related='school_id.company_id',
        string="Company"
    )
    approval_for = fields.Selection([
        ('admission', 'Admission'),
        ('student_leave', 'Student Leave')
    ], string='Approval For')

    @api.onchange('school_id')
    def _onchange_school_id(self):
        if self.school_id:
            return {'domain': {'program_id': [('id', 'in', self.school_id.school_program_ids.ids)]}}
        else:
            return {'domain': {'program_id': []}}

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context

        if context.get("allowed_company_ids"):
            domain += [("company_id", "in", context.get("allowed_company_ids"))]

        if context.get("allowed_branch_ids"):
            domain += [
                "|",
                ("branch_ids", "in", context.get("allowed_branch_ids")),
                ("branch_ids", "=", False),
            ]

        result = super(SchoolApprovalMatrix, self).search_read(
            domain=domain, fields=fields, offset=offset, limit=limit, order=order
        )

        return result

    @api.model
    def read_group(
        self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True
    ):
        domain = domain or []
        context = self.env.context

        if context.get("allowed_company_ids"):
            domain.extend([("company_id", "in", self.env.companies.ids)])

        if context.get("allowed_branch_ids"):
            domain.extend(
                [
                    "|",
                    ("branch_ids", "in", context.get("allowed_branch_ids")),
                    ("branch_ids", "=", False),
                ]
            )
        return super(SchoolApprovalMatrix, self).read_group(
            domain,
            fields,
            groupby,
            offset=offset,
            limit=limit,
            orderby=orderby,
            lazy=lazy,
        )

    @api.depends('school_id')
    def _compute_branch_id(self):
        for rec in self:
            rec.branch_id = rec.school_id.branch_id.id

    @api.onchange('approval_matrix_ids')
    def _onchange_approval_matrix(self):
        is_admission = self.approval_for == "admission" or not self.approval_for
        if self.approval_matrix_ids and is_admission:
            draft_ids = len(self.approval_matrix_ids.filtered(lambda x: x.state == "draft"))
            confirmed_ids = len(self.approval_matrix_ids.filtered(lambda x: x.state == "confirmed"))
            done_ids = len(self.approval_matrix_ids.filtered(lambda x: x.state == "done"))
            if draft_ids > 1 or confirmed_ids > 1 or done_ids > 1:
                raise ValidationError(_("Duplicate Status Not Allowed."))

    @api.constrains('school_id', 'program_id')
    def _check_existing_record(self):
        for record in self:
            domain = [
                ('school_id', '=', record.school_id.id),
                ('id', '!=', record.id),
                ('program_id', '=', record.program_id.id),
            ]
            if record.school_id and record.program_id:
                if record.approval_for == 'admission' or not record.approval_for:
                    domain.extend(
                        [
                            '|',
                            ('approval_for', '=', 'admission'),
                            ('approval_for', '=', False)
                        ]
                    )
                    school_id = self.search(domain, limit=1)
                    if school_id:
                        raise ValidationError("Please select other School and Program.")

                elif record.approval_for == 'student_leave':
                    domain.extend([('approval_for', '=', 'student_leave')])
                    school_id = self.search(domain, limit=1)
                    if school_id:
                        raise ValidationError("Please select other School and Program.")

    @api.depends('approval_matrix_ids')
    def _get_level(self):
        for record in self:
            if record.approval_matrix_ids:
                record.level = len(record.approval_matrix_ids)
            else:
                record.level = 0
    
    def _reset_sequence(self):
        for rec in self:
            current_sequence = 1
            for line in rec.approval_matrix_ids:
                line.sequence = current_sequence
                current_sequence += 1

    def copy(self, default=None):
        res = super(
            SchoolApprovalMatrix, self.with_context(keep_line_sequence=True)
        ).copy(default)
        return res

class SchoolApprovalMatrixLine(models.Model):
    _name = 'school.approval.matrix.line'
    _description = 'New Description'

    user_id = fields.Many2many('res.users', ondelete="cascade",
                               help='Enter related user of the student',
                               domain=lambda self: [
                                   ("groups_id", "!=", self.env.ref("school.group_school_student").id),
                                   ("groups_id", "!=", self.env.ref("school.group_school_parent").id),
                                   ("groups_id", "=", self.env.ref("base.group_user").id),
                               ])
    approval_matrix_id = fields.Many2one('school.approval.matrix')
    minimum_approver = fields.Integer(default=1)
    approved_users = fields.Many2many('res.users', 'approved_users_school_rel', 'class_id', 'user_id', string='Users')
    last_approved = fields.Many2one('res.users', string='Users')
    approved = fields.Boolean('Approved', compute="_compute_approved", store=True)
    stu_id = fields.Many2one('student.student', string="Student")
    state = fields.Selection([('draft', 'Draft'),
                              ('confirmed', 'Pending Payment'),
                              ('done', 'Done')],
                             'Status', readonly=False, default="draft",
                             help='State of the student registration form')
    approval_time = fields.Char(string='Approval Time')
    approved_status = fields.Char(string='Approved Status')
    sequence = fields.Integer('Sequence')

    @api.depends('user_id', 'approved_users')
    def _compute_approved(self):
        for record in self:
            record.approved = False
            if len(record.approved_users) == record.minimum_approver:
                record.approved = True

    def write(self, vals):
        if 'user_id' in vals:
            initial_users = set(self.user_id.mapped('id'))
            current_users = set(vals['user_id'][0][2])
            to_delete = initial_users - current_users
            to_add = current_users - initial_users

            if to_add:
                for user_id in to_add:
                    user = self.env['res.users'].browse(user_id)
                    message_body = "%s Added %s to '%s' Approvers" % (self.env.user.name, user.name, self.state)
                    self.approval_matrix_id.message_post(body=message_body)

            if to_delete:
                for user_id in to_delete:
                    user = self.env['res.users'].browse(user_id)
                    message_body = "%s Deleted %s from '%s' Approvers" % (self.env.user.name, user.name, self.state)
                    self.approval_matrix_id.message_post(body=message_body)

        return super(SchoolApprovalMatrixLine, self).write(vals)

    @api.model
    def default_get(self, fields):
        res = super(SchoolApprovalMatrixLine, self).default_get(fields)
        if self._context:
            context_keys = self._context.keys()
            next_sequence = 1
            if "approval_matrix_ids" in context_keys:
                if len(self._context.get("approval_matrix_ids")) > 0:
                    next_sequence = len(self._context.get("approval_matrix_ids")) + 1
            res.update({"sequence": next_sequence})
        return res
    
    def unlink(self):
        approval = self.approval_matrix_id
        res = super(SchoolApprovalMatrixLine, self).unlink()
        approval._reset_sequence()
        return res

    @api.model
    def create(self, vals):
        res = super(SchoolApprovalMatrixLine, self).create(vals)
        if not self.env.context.get("keep_line_sequence", False):
            res.approval_matrix_id._reset_sequence()
        return res

    @api.constrains('approval_matrix_id', 'user_id', 'minimum_approver')
    def check_minimum_approver(self):
        for line in self:
            if line.approval_matrix_id.approval_for != 'student_leave':
                continue
            
            minimum_approver = line.minimum_approver
            total_allowed_approvers = len(line.user_id)
            
            if not minimum_approver or minimum_approver <= 0:
                raise UserError(_("Minimum approver must be greater than 0."))

            if minimum_approver > total_allowed_approvers:
                raise UserError(_("Minimum approver must be less than or equal to %d" % total_allowed_approvers))


class SchoolSchool(models.Model):
    _inherit = "school.school"
    _rec_name = 'name'

    name = fields.Char(string='School Name', required=True, tracking=True)
    school_program_ids = fields.One2many('standard.standard', 'school_id', string='Program')
    school_branch_ids = fields.One2many('res.branch', 'school_id', string='Branches')
    branch_id = fields.Many2one('res.branch', string='Branch', tracking=True, default=lambda self: self.env.branch.id)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    street2 = fields.Char()
    zip = fields.Char(change_default=True)
    city = fields.Char()
    state_id = fields.Many2one("res.country.state", string='State', ondelete='restrict',
                               domain="[('country_id', '=?', country_id)]")
    country_id = fields.Many2one('res.country', string='Country', ondelete='restrict')
    currency_id = fields.Many2one('res.currency', string='Currency', required=True)

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context

        if "is_res_users" not in context:
            if context.get("allowed_company_ids"):
                domain += [("company_id", "in", context.get("allowed_company_ids"))]

            if context.get("allowed_branch_ids"):
                domain += [
                    "|",
                    ("school_branch_ids", "in", context.get("allowed_branch_ids")),
                    ("school_branch_ids", "=", False),
                ]

        result = super(SchoolSchool, self).search_read(
            domain=domain, fields=fields, offset=offset, limit=limit, order=order
        )

        return result

    @api.model
    def read_group(
        self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True
    ):
        domain = domain or []
        context = self.env.context

        if context.get("allowed_company_ids"):
            domain.extend([("company_id", "in", self.env.companies.ids)])

        if context.get("allowed_branch_ids"):
            domain.extend(
                [
                    "|",
                    ("school_branch_ids", "in", context.get("allowed_branch_ids")),
                    ("school_branch_ids", "=", False),
                ]
            )
        return super(SchoolSchool, self).read_group(
            domain,
            fields,
            groupby,
            offset=offset,
            limit=limit,
            orderby=orderby,
            lazy=lazy,
        )

class ResBranch(models.Model):
    _inherit = 'res.branch'
    _description = 'Branch'

    @api.model
    def _domainSchool(self):
        active_company = self.env.company.id
        return [('company_id', '=', active_company)]

    school_id = fields.Many2one(
        'school.school',
        string='School',
        required=True,
        domain=_domainSchool
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        compute="_compute_company_id",
        readonly=True,
        required=False,
        store=True
    )

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context

        if "is_res_users" not in context:
            if context.get("allowed_company_ids"):
                domain += [("company_id", "in", context.get("allowed_company_ids"))]

            if context.get("allowed_branch_ids"):
                domain += [
                    "|",
                    ("id", "in", context.get("allowed_branch_ids")),
                    ("id", "=", False),
                ]

        result = super(ResBranch, self).search_read(
            domain=domain, fields=fields, offset=offset, limit=limit, order=order
        )

        return result

    @api.model
    def read_group(
        self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True
    ):
        domain = domain or []
        context = self.env.context

        if context.get("allowed_company_ids"):
            domain.extend([("company_id", "in", self.env.companies.ids)])

        if context.get("allowed_branch_ids"):
            domain.extend(
                [
                    "|",
                    ("id", "in", context.get("allowed_branch_ids")),
                    ("id", "=", False),
                ]
            )
        return super(ResBranch, self).read_group(
            domain,
            fields,
            groupby,
            offset=offset,
            limit=limit,
            orderby=orderby,
            lazy=lazy,
        )

    @api.depends('school_id')
    def _compute_company_id(self):
        for rec in self:
            rec.company_id = rec.school_id.company_id.id


class ResCompany(models.Model):
    _inherit = 'res.company'
    _description = 'Company'

    school_ids = fields.One2many('school.school', 'company_id', string='Schools')


class EmsSubject(models.Model):
    _name = "ems.subject"
    _description = "EMS Subject"
    _rec_name = "program_id"

    program_id = fields.Many2one("school.standard", string="Program")


#     ems_program_id = fields.Many2one("standard.standard", string="Program")
#     year = fields.Char(string="Year")
#     core_subject_id = fields.Many2one("subject.subject", domain="[('subject_type', '=', 'core')]",
#                                       string="Core Subject")
#     elective_subject_ids = fields.Many2one("subject.subject", domain="[('subject_type', '=', 'elective')]",
#                                            string="Elective Subject")
#     year_id = fields.Many2one("academic.year", string="Academic Year")
#     term_id = fields.Many2one("academic.month", string="Term", domain="[('year_id', '=', year_id)]")
#     academic_year = fields.Many2one('academic.year', string='Academic Year')
#     status = fields.Selection([('active', 'Active'), ('unactive', 'Unactive')], string='Status',
#                               compute='_compute_status', store=True)
#     teacher_ids = fields.Many2many('school.teacher', string="teacher", help='Teachers of the following subject')
#     all_academic_tracking_id = fields.Many2one('academic.tracking', string='All Academic Tracking')
#     current_academic_tracking_id = fields.Many2one('academic.tracking', string='Current Academic Tracking')
#     pass_academic_tracking_id = fields.Many2one('academic.tracking', string='Pass Academic Tracking')
#     failed_academic_tracking_id = fields.Many2one('academic.tracking', string='Failed Academic Tracking')
#     credits = fields.Integer(string='Credits', related='core_subject_id.credits')
#     intake_id = fields.Many2one('school.standard', string='Intake')
#     total_percentage_exam = fields.Float(string='Total Exam Percentage', compute='_compute_total_percentage_exam')
#     total_percentage_assigment = fields.Float(string='Total Assignment Percentage')
#     total_percentage_additional = fields.Float(string='Total Additional Percentage',
#                                                compute='_compute_total_percentage_additional')
#     final_percentage = fields.Float(string='Final Percentage', compute='_compute_final_percentage')
#     assignment_line_ids = fields.One2many('school.teacher.assignment', 'subject_weightage', string='Assignment Line')
#     additional_line_ids = fields.One2many('additional.exam', 'subject_weightage', string='Additional Exam')
#     exam_line_ids = fields.One2many('exam.exam', 'subject_weightage', string='Exam Line')
#     subject_id = fields.Many2one('subject.subject', compute='_compute_subject_id')
#     core_subject_domain = fields.Many2many('subject.subject', compute='_get_core_subject_domain')
#     elective_subject_domain = fields.Many2many('subject.subject', compute='_get_elective_subject_domain')
#     # subject_status = fields.Selection([('active', 'Active'), ('unactive', 'Unactive')], string="Status")
#     subject_status = fields.Selection(
#         [('active', 'Active'), ('unactive', 'Unactive'), ('pending', 'Pending'), ('pass', 'Pass'), ('fail', 'Fail')],
#         string="Status", compute="_compute_subject_status")
#     grade_type = fields.Many2one("grade.master", "Grade Type", help="Select Grade System")
#     presence_persentage = fields.Float(string='Presence Percentage', compute='_compute_presence_persentage')
#     grade = fields.Many2one('grade.line', string="Grade", compute="_compute_grade")
#     teacher_id = fields.Many2one('school.teacher', string="Teacher")
#     group_class = fields.Many2one('group.class', string='Group Class')
#
#     @api.depends('academic_year', 'term_id', 'term_id.checkactive')
#     def _compute_subject_status(self):
#         for rec in self:
#             rec.subject_status = False
#             if rec.term_id.checkactive:
#                 rec.subject_status = 'active'
#             else:
#                 term_id = rec.term_id
#                 current_term_id = self.env['academic.month'].search(
#                     [('year_id', '=', term_id.year_id.id), ('checkactive', '=', True)])
#                 if current_term_id and current_term_id.date_stop < term_id.date_stop:
#                     rec.subject_status = 'pending'
#                 elif not current_term_id or current_term_id.date_stop >= term_id.date_stop:
#                     score_id = self.env['subject.score'].search(
#                         [('student_id', '=', rec.all_academic_tracking_id.student_id.id),
#                          ('program_id', '=', rec.all_academic_tracking_id.program_id.id),
#                          ('subject_id', '=', rec.subject_id.id)])
#                     if date.today() == term_id.date_stop:
#                         rec.subject_status = 'active'
#                     else:
#                         if score_id.result == 'Pass':
#                             rec.subject_status = 'pass'
#                             rec.failed_academic_tracking_id = False
#                             rec.pass_academic_tracking_id = rec.all_academic_tracking_id
#                         elif score_id.result == 'Fail':
#                             rec.subject_status = 'fail'
#                             rec.pass_academic_tracking_id = False
#                             rec.failed_academic_tracking_id = rec.all_academic_tracking_id
#                         else:
#                             rec.pass_academic_tracking_id = False
#                             rec.failed_academic_tracking_id = False
#
#     @api.depends('total_percentage_exam', 'total_percentage_additional', 'total_percentage_assigment')
#     def _compute_final_percentage(self):
#         for record in self:
#             record.final_percentage = (
#                                               record.total_percentage_exam + record.total_percentage_additional + record.total_percentage_assigment) * 100
#
#     def _compute_subject_id(self):
#         for record in self:
#             record.subject_id = record.core_subject_id.id or record.elective_subject_ids.id
#
#     @api.onchange('final_percentage')
#     def _onchange_final_percentage(self):
#         for rec in self:
#             if rec.final_percentage > 100:
#                 raise ValidationError(_('Final Percentage cannot be greater than 100'))
#
#     @api.depends('program_id.standard_id')
#     def _get_core_subject_domain(self):
#         for rec in self:
#             rec.core_subject_domain = []
#             if rec.program_id and rec.program_id.standard_id:
#                 program = rec.program_id.standard_id
#                 core_subject_ids = program.ems_subject_ids.mapped('core_subject_id').ids
#                 rec.core_subject_domain = [(6, 0, core_subject_ids)]
#
#     @api.depends('program_id.standard_id')
#     def _get_elective_subject_domain(self):
#         for rec in self:
#             rec.elective_subject_domain = []
#             if rec.program_id and rec.program_id.standard_id:
#                 program = rec.program_id.standard_id
#                 elective_subject_ids = program.ems_subject_ids.mapped('elective_subject_ids').ids
#                 rec.elective_subject_domain = [(6, 0, elective_subject_ids)]
#
#     @api.depends('year_id', 'year_id.current', 'term_id', 'term_id.checkactive')
#     def _compute_status(self):
#         for record in self:
#             if record.year_id and record.term_id and record.year_id.current and record.term_id.checkactive:
#                 record.status = 'active'
#             else:
#                 record.status = 'unactive'
#
#     def _compute_total_percentage_exam(self):
#         for record in self:
#             record.total_percentage_exam = sum(line.exam_percentage for line in record.exam_line_ids)
#
#     def _compute_total_percentage_additional(self):
#         for record in self:
#             record.total_percentage_additional = sum(line.percentage for line in record.additional_line_ids)
#
#     @api.depends('core_subject_id', 'elective_subject_ids', 'all_academic_tracking_id',
#                  'all_academic_tracking_id.student_id')
#     def _compute_presence_persentage(self):
#         for record in self:
#             attendance_line = self.env["daily.attendance.line"]
#             subject_id = record.core_subject_id.id or record.elective_subject_ids.id
#             domain = [('subject_id', '=', subject_id),
#                       ('student_id', '=', record.all_academic_tracking_id.student_id.id)]
#             total_attendance = attendance_line.search_count(domain)
#             if total_attendance:
#                 total_present = attendance_line.search_count(domain + [('is_present', '=', True)])
#                 record.presence_persentage = total_present / total_attendance
#             else:
#                 record.presence_persentage = 0
#
#     @api.depends('intake_id', 'core_subject_id', 'elective_subject_ids', 'all_academic_tracking_id',
#                  'all_academic_tracking_id.student_id')
#     def _compute_grade(self):
#         for record in self:
#             subject_id = record.core_subject_id.id or record.elective_subject_ids.id
#             subject_score = self.env["subject.score"].search(
#                 [('subject_id', '=', subject_id), ('student_id', '=', record.all_academic_tracking_id.student_id.id),
#                  ('intake_id', '=', record.intake_id.id)])
#             record.grade = subject_score.grade.id
#
#     @api.model
#     def create(self, vals):
#         res = super(EmsSubject, self).create(vals)
#         domain = []
#         duplicate = False
#         if res.ems_program_id:
#             domain = [('ems_program_id', '=', res.ems_program_id.id)]
#             subject = res.core_subject_id or res.elective_subject_ids
#             if subject:
#                 if res.ems_program_id not in subject.standard_ids:
#                     subject.write({'standard_ids': [(4, res.ems_program_id.id)]})
#         elif res.program_id:
#             domain = [('program_id', '=', res.program_id.id)]
#
#         if domain:
#             if res.core_subject_id:
#                 domain.append(('core_subject_id', '=', res.core_subject_id.id))
#             elif res.elective_subject_ids:
#                 domain.append(('elective_subject_ids', '=', res.elective_subject_ids.id))
#             if len(self.search(domain)) > 1:
#                 raise ValidationError("Can't have duplicate subjects")
#         return res
#
#     def write(self, vals):
#         if 'core_subject_id' in vals:
#             for fee in self.env['subject.subject'].browse(vals.get('core_subject_id')):
#                 message_body = "Program Changed Core Subject %s to %s" % (self.core_subject_id.name, fee.name)
#                 if self.ems_program_id:
#                     self.ems_program_id.message_post(body=message_body)
#                 elif self.program_id:
#                     self.program_id.message_post(body=message_body)
#
#         if 'year' in vals:
#             for fee in self.env['standard.standard'].browse(vals['year']):
#                 message_body = "Program Changed Year from %s to %s" % (self.year, vals.get('year') or self.year)
#                 if self.ems_program_id:
#                     self.ems_program_id.message_post(body=message_body)
#                 elif self.program_id:
#                     self.program_id.message_post(body=message_body)
#
#         subject_is_change = vals.get('core_subject_id', False) or vals.get('elective_subject_ids', False)
#         if self.ems_program_id and subject_is_change:
#             old_subject = self.core_subject_id or self.elective_subject_ids
#             if old_subject and self.ems_program_id in old_subject.standard_ids:
#                 old_subject.write({'standard_ids': [(3, self.ems_program_id.id)]})
#
#         res = super(EmsSubject, self).write(vals)
#
#         domain = []
#         duplicate = False
#         if self.ems_program_id:
#             domain = [('ems_program_id', '=', self.ems_program_id.id)]
#             subject = self.core_subject_id or self.elective_subject_ids
#             if subject:
#                 if self.ems_program_id not in subject.standard_ids:
#                     subject.write({'standard_ids': [(4, self.ems_program_id.id)]})
#         elif self.program_id:
#             domain = [('program_id', '=', self.program_id.id)]
#
#         if domain:
#             if self.core_subject_id:
#                 domain.append(('core_subject_id', '=', self.core_subject_id.id))
#             elif self.elective_subject_ids:
#                 domain.append(('elective_subject_ids', '=', self.elective_subject_ids.id))
#             if len(self.search(domain)) > 1:
#                 raise ValidationError("Can't have duplicate subjects")
#         return res
#
#     def unlink(self):
#         if self.ems_program_id:
#             subject = self.core_subject_id or self.elective_subject_ids
#             if subject:
#                 if self.ems_program_id in subject.standard_ids:
#                     subject.write({'standard_ids': [(3, self.ems_program_id.id)]})
#         return super(EmsSubject, self).unlink()
#
#     def name_get(self):
#         result = []
#         for record in self:
#             if self.env.context.get('display_subject_name', False):
#                 result.append((record.id, record.subject_id.name))
#             else:
#                 result.append((record.id, record.program_id.name))
#         return result
#
#     def subject_score_action_form_btn(self):
#         domain = [('subject_id', '=', self.subject_id.id), ('intake_id', '=', self.program_id.id),
#                   ('year_id', '=', self.year_id.id), ('term_id', '=', self.term_id.id)]
#         action = {
#             'type': 'ir.actions.act_window',
#             'name': 'Subject Score',
#             'res_model': 'subject.score',
#             'domain': domain,
#             'view_mode': 'tree,form',
#             'context': {'search_default_groupby_program': 1, 'search_default_groupby_student': 1,
#                         'search_default_groupby_year': 1, 'search_default_groupby_term': 1},
#         }
#         return action
#
#     def print_result(self, partner_id=False):
#         if not partner_id:
#             partner_id = self.env.company.partner_id
#
#         all_percentage = [self.total_percentage_assigment * 100, self.total_percentage_exam * 100,
#                           self.total_percentage_additional * 100, self.final_percentage]
#         scoring_data = self.env['subject.score'].search(
#             [('subject_id', '=', self.subject_id.id), ('intake_id', '=', self.program_id.id),
#              ('year_id', '=', self.year_id.id), ('term_id', '=', self.term_id.id)])
#         temp_student = []
#         temp_assignment = []
#         temp_exam = []
#         temp_additional = []
#         temp_final_score = []
#         temp_grade = []
#         counter = 0
#         total_score_assignment = 0
#
#         for record in scoring_data:
#             try:
#                 total_score_assignment = sum(record.assignment_line_ids.mapped('assignment_score')) / len(
#                     record.assignment_line_ids)
#             except ZeroDivisionError:
#                 total_score_assignment = 0
#
#             temp_student.append(record.student_id.name)
#             temp_assignment.append(total_score_assignment * record.total_percentage_assigment)
#             temp_exam.append(sum(line.result_score_exam for line in record.exam_line_ids))
#             temp_additional.append(sum(line.result_additional_exam for line in record.additional_line_ids))
#             temp_final_score.append((temp_exam[counter] + temp_assignment[counter] + temp_additional[counter]))
#             temp_grade.append(record.grade.grade)
#             counter = counter + 1
#
#         data = {
#             'weightage_id': self.read()[0],
#             'program_data': self.program_id.standard_id.name,
#             'all_percentage_data': all_percentage,
#             'student_data': temp_student,
#             'assignment_data': temp_assignment,
#             'exam_data': temp_exam,
#             'additional_exam_data': temp_additional,
#             'final_score_data': temp_final_score,
#             'grade_data': temp_grade,
#             'company': self.env.company.read()[0],
#             'address': self._get_address_details(partner_id),
#             'street': self._get_street(partner_id),
#             'font_family': self.env.company.font_id.family,
#             'font_size': self.env.company.font_size,
#             'mobile': partner_id.mobile,
#             'email': partner_id.email,
#             'partner': partner_id.name,
#         }
#         return self.env.ref('equip3_school_report.action_print_final_grade_subject_weightage').report_action(self,
#                                                                                                              data=data)
#
#     def get_address_details(self, partner):
#         return self._get_address_details(partner)
#
#     def get_street(self, partner):
#         return self._get_street(partner)
#
#     def _get_address_details(self, partner):
#         self.ensure_one()
#         res = {}
#         address = ''
#         if partner.city:
#             address = "%s" % (partner.city)
#         if partner.state_id.name:
#             address += ", %s" % (partner.state_id.name)
#         if partner.zip:
#             address += ", %s" % (partner.zip)
#         if partner.country_id.name:
#             address += ", %s" % (partner.country_id.name)
#         # reload(sys)
#         html_text = str(tools.plaintext2html(address, container_tag=True))
#         data = html_text.split('p>')
#         if data:
#             return data[1][:-2]
#         return False
#
#     def _get_street(self, partner):
#         self.ensure_one()
#         res = {}
#         address = ''
#         if partner.street:
#             address = "%s" % (partner.street)
#         if partner.street2:
#             address += ", %s" % (partner.street2)
#         # reload(sys)
#         html_text = str(tools.plaintext2html(address, container_tag=True))
#         data = html_text.split('p>')
#         if data:
#             return data[1][:-2]
#         return False


class StudentFeesStructure(models.Model):
    """Fees structure"""

    _name = "student.fees.structure"
    _inherit = ["student.fees.structure", "mail.thread", "mail.activity.mixin"]
    _description = "Fees Structure"

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

    def write(self, vals):
        if 'line_ids' in vals:
            initial_users = set(self.line_ids.ids)
            current_users = set(vals['line_ids'][0][2])
            deleted_ids = initial_users - current_users
            if deleted_ids:
                for deleted_id in deleted_ids:
                    deleted = self.env['student.fees.structure.line'].browse(deleted_id)
                    message_body = 'Fees Head (%s) is Removed' % (deleted.name)
                    self.message_post(body=message_body)

        return super(StudentFeesStructure, self).write(vals)

class AcademicYear(models.Model):
    _inherit = "academic.year"
    _order = "create_date desc"


class SchoolSettingsInherit(models.Model):
    _inherit = "school.config.settings"

    @api.onchange("leave_approval_matrix")
    def _onchange_leave_approval_matrix(self):
        group = self.env.ref("equip3_school_operation.group_student_leave_request_menu")
        user = self.env.user

        for record in self:
            if record.leave_approval_matrix:
                user.write({"groups_id": [(4, group.id)]})
                record.leave_approval_matrix = True
            else:
                user.write({"groups_id": [(3, group.id)]})
                record.leave_approval_matrix = False