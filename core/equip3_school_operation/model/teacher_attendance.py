import math
from odoo import api, fields, models, _, tools


class TeacherAttendance(models.Model):
    _name = 'teacher.attendance'
    _rec_name = 'teacher_id'
    _order = "create_date desc"

    @api.model
    def _domainSchool(self):
        allowed_branch_ids = self.env.branches.ids
        return [('school_branch_ids', 'in', allowed_branch_ids)]

    teacher_id = fields.Many2one('school.teacher', required=True, string='Teacher')
    school_id = fields.Many2one('school.school', string='School', required=True, domain=_domainSchool)
    program_id = fields.Many2one('standard.standard', string='Program', required=True)
    intake_id = fields.Many2one('school.standard', string='Intake', required=True)
    year_id = fields.Many2one('academic.year', string='Academic Year', required=True)
    term_id = fields.Many2one('academic.month', string='Term', required=True)
    subject_id = fields.Many2one('subject.subject', string='Subject', required=True)
    total_presence = fields.Integer(string='Total Presence', compute='_compute_total_presence')
    daily_attendance_ids = fields.One2many('daily.attendance', 'teacher_attendance_id', string="Daily Attendance")
    total_hours = fields.Float(string='Total Hours', compute='_compute_total_hours')
    branch_id = fields.Many2one('res.branch', related='school_id.branch_id', readonly=False, string='Branch')
    group_class = fields.Many2one('group.class', string='Group Class', required=True)
    related_group_class_ids = fields.Many2many('group.class', compute='_compute_related_group_class_ids')
    related_subject_ids = fields.Many2many('subject.subject', string='Subject Related',
                                           compute='_compute_related_subject_ids')
    related_teacher_ids = fields.Many2many('school.teacher', compute='_compute_related_teacher_ids')

    @api.depends('group_class', 'subject_id')
    def _compute_related_teacher_ids(self):
        for rec in self:
            related_teacher_ids = rec.group_class.subject_ids.filtered(lambda x: x.subject_id == rec.subject_id)
            teacher_ids = related_teacher_ids.mapped('teacher_id')
            rec.related_teacher_ids = teacher_ids
            if self.env.user.has_group('school.group_school_teacher'):
                if rec.teacher_id:
                    rec.related_teacher_ids = teacher_ids.filtered(lambda x: x == rec.teacher_id)
                else:
                    rec.related_teacher_ids = False

    @api.depends('intake_id', 'year_id', 'term_id', 'teacher_id')
    def _compute_related_subject_ids(self):
        for rec in self:
            intake_subject_line_ids = rec.intake_id.intake_subject_line_ids.filtered(
                lambda x: x.year_id == rec.year_id and x.term_id == rec.term_id)
            subject_ids = intake_subject_line_ids.mapped('subject_id')
            rec.related_subject_ids = subject_ids
            if self.env.user.has_group('school.group_school_teacher'):
                if rec.teacher_id:
                    rec.related_subject_ids = subject_ids.filtered(lambda x: x in rec.teacher_id.subject_id)
                else:
                    rec.related_subject_ids = False

    @api.depends('intake_id', 'teacher_id')
    def _compute_related_group_class_ids(self):
        for rec in self:
            if rec.intake_id:
                group_classes = self.env['group.class'].search([('intake', '=', rec.intake_id.id)])
                rec.related_group_class_ids = group_classes
                if self.env.user.has_group('school.group_school_teacher'):
                    if rec.teacher_id:
                        rec.related_group_class_ids = group_classes.filtered(
                            lambda x: x in rec.teacher_id.group_class_ids)
                    else:
                        rec.related_group_class_ids = False
            else:
                rec.related_group_class_ids = False

    @api.depends('daily_attendance_ids')
    def _compute_total_presence(self):
        for rec in self:
            rec.total_presence = len(rec.daily_attendance_ids)

    @api.depends('daily_attendance_ids')
    def _compute_total_hours(self):
        for rec in self:
            rec.total_hours = sum(line.hours for line in rec.daily_attendance_ids)
    
    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context

        if context.get("allowed_company_ids"):
            domain += [("school_id.company_id", "in", context.get("allowed_company_ids"))]

        if context.get("allowed_branch_ids"):
            domain += [
                "|",
                ("branch_id", "in", context.get("allowed_branch_ids")),
                ("branch_id", "=", False),
            ]

        result = super(TeacherAttendance, self).search_read(
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
            domain.extend([("school_id.company_id", "in", self.env.companies.ids)])

        if context.get("allowed_branch_ids"):
            domain.extend(
                [
                    "|",
                    ("branch_id", "in", context.get("allowed_branch_ids")),
                    ("branch_id", "=", False),
                ]
            )
        return super(TeacherAttendance, self).read_group(
            domain,
            fields,
            groupby,
            offset=offset,
            limit=limit,
            orderby=orderby,
            lazy=lazy,
        )
