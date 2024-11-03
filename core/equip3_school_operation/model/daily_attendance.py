import math
from odoo import api, fields, models, _, tools
from odoo.exceptions import ValidationError


class DailyAttendance(models.Model):
    _inherit = 'daily.attendance'
    _order = "create_date desc"

    def _get_is_teacher(self):
        return self.env.user.has_group('school.group_school_teacher')

    @api.model
    def _domainSchool(self):
        allowed_branch_ids = self.env.branches.ids
        return [('school_branch_ids', 'in', allowed_branch_ids)]

    attendance_line_ids = fields.Many2many("attendance.sheet.line.matrix", string="Attendance Line")
    class_id = fields.Many2one("ems.classes", string='Class')
    name = fields.Char(string='Name')
    standard_id = fields.Many2one('school.standard', string="Intake")
    year_id = fields.Many2one("academic.year", string="Academic Year")
    group_class = fields.Many2many("group.class", string="Group Class")
    term_id = fields.Many2one("academic.month", string="Term")
    program_id = fields.Many2one("standard.standard", string="Program")
    subject_id = fields.Many2one("subject.subject", string="Subject")
    daily_attendance_line = fields.One2many('daily.attendance.line', 'daily_attendance_id')
    school_id = fields.Many2one('school.school', string='School', domain=_domainSchool)
    intake_id = fields.Many2many('subject.subject', string='Intake')
    state = fields.Selection(selection_add=[('cancelled', 'Cancelled')])
    related_subject_ids = fields.Many2many('subject.subject', string='Subject Related',
                                           compute='_compute_related_subject_ids')
    total_present = fields.Integer(string='Total Student Presence', compute='_compute_total_present')
    total_absent = fields.Integer(string='Total Student Absent', compute='_compute_total_absent')
    teacher_attendance_id = fields.Many2one('teacher.attendance', string='Teacher Attendance')
    start_time = fields.Float(string='Start Time', required=True)
    end_time = fields.Float(string='End Time', required=True)
    related_group_class_ids = fields.Many2many('group.class', compute='_compute_related_group_class_ids')
    is_teacher = fields.Boolean(default=lambda x: x._get_is_teacher())
    hours = fields.Float(string='Number of Hours', compute='_compute_hours')
    branch_id = fields.Many2one(comodel_name='res.branch', related='school_id.branch_id', readonly=False, store=True,
                                string='Branch', )
    related_teacher_ids = fields.Many2many('school.teacher', compute='_compute_related_teacher_ids')
    teacher_id = fields.Many2one('school.teacher', string="Teacher", domain="[('id', 'in', related_teacher_ids)]")
    replacement_teacher_id = fields.Many2one('school.teacher', string='Replacement Teacher')

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

    @api.depends('standard_id', 'year_id', 'term_id', 'teacher_id')
    def _compute_related_subject_ids(self):
        for rec in self:
            intake_subject_line_ids = rec.standard_id.intake_subject_line_ids.filtered(
                lambda x: x.year_id == rec.year_id and x.term_id == rec.term_id)
            subject_ids = intake_subject_line_ids.mapped('subject_id')
            rec.related_subject_ids = subject_ids
            if self.env.user.has_group('school.group_school_teacher'):
                if rec.teacher_id:
                    rec.related_subject_ids = subject_ids.filtered(lambda x: x in rec.teacher_id.subject_id)
                else:
                    rec.related_subject_ids = False

    @api.constrains('start_time', 'end_time')
    def _checking_hours(self):
        if self.start_time and self.end_time:
            for rec in self:
                if rec.start_time > rec.end_time:
                    raise ValidationError("End Time must be greater than Start time")

    @api.onchange('year_id')
    def _onchange_year_id(self):
        for rec in self:
            dom = {'domain': {'term_id': [('checkactive', '=', True), ('year_id', '=', rec.year_id.id)]}}
            return dom

    @api.onchange('year_id')
    def _onchange_year_id(self):
        for rec in self:
            dom = {'domain': {'term_id': [('checkactive', '=', True), ('year_id', '=', rec.year_id.id)]}}
            return dom

    @api.onchange('standard_id')
    def _onchange_standard_id(self):
        year_ids = []
        term_ids = []
        # subject
        for rec in self.standard_id.intake_subject_line_ids:
            year_ids.append(rec.year_id.id)
            term_ids.append(rec.term_id.id)
        
        # Assign intake_id with a many2many command (6, 0, [ids])
        # self.intake_id = [(6, 0, year_ids)]

        return {
            'domain': {
                'year_id': [('id', 'in', year_ids)],
                'term_id': [('id', 'in', term_ids)],
            }
        }

    @api.onchange('group_class')
    def _set_attendance_line_based_on_group_class(self):
        self.daily_attendance_line = [(5, 0, 0)] + [
            (0, 0, {'daily_attendance_id': self.id, 'is_present': True, 'student_id': id}) for id in
            self.group_class.student_ids.ids]

    @api.onchange('group_class', 'year_id', 'term_id')
    def _onchange_group(self):
        if self.group_class and self.year_id and self.term_id:
            group_class_subject_data = self.env['group.class.subject'].search(
                [('group_class_id', 'in', self.group_class.ids), ('year_id', '=', self.year_id.id),
                 ('term_id', '=', self.term_id.id)])
            dom = {'domain': {'subject_id': [('id', 'in', group_class_subject_data.subject_id.ids)]}}
            return dom

    @api.onchange('group_class', 'year_id', 'term_id')
    def _onchange_group_class(self):
        if self.group_class and self.year_id and self.term_id:
            group_class_subject_data = self.env['group.class.subject'].search(
                [('group_class_id', 'in', self.group_class.ids), ('year_id', '=', self.year_id.id),
                 ('term_id', '=', self.term_id.id)])
            dom = {'domain': {'subject_id': [('id', 'in', group_class_subject_data.subject_id.ids)]}}
            return dom

    @api.depends('daily_attendance_line')
    def _compute_total_present(self):
        for record in self:
            record.total_present = self.env["daily.attendance.line"].search_count(
                [('daily_attendance_id', '=', record.id), ('is_present', '=', True)])

    @api.depends('daily_attendance_line')
    def _compute_total_absent(self):
        for record in self:
            record.total_absent = self.env["daily.attendance.line"].search_count(
                [('daily_attendance_id', '=', record.id), ('is_absent', '=', True)])

    @api.depends('standard_id', 'teacher_id')
    def _compute_related_group_class_ids(self):
        for rec in self:
            if rec.standard_id:
                group_classes = self.env['group.class'].search([('intake', '=', rec.standard_id.id)])
                rec.related_group_class_ids = group_classes
                if self.env.user.has_group('school.group_school_teacher'):
                    if rec.teacher_id:
                        rec.related_group_class_ids = group_classes.filtered(
                            lambda x: x in rec.teacher_id.group_class_ids)
                    else:
                        rec.related_group_class_ids = False
            else:
                rec.related_group_class_ids = False

    def float_time_convert(self, float_val):
        factor = float_val < 0 and -1 or 1
        val = abs(float_val)
        hour = factor * int(math.floor(val))
        minutes = int(round((val % 1) * 60))
        return hour + (minutes / 100)

    @api.depends('start_time', 'end_time')
    def _compute_hours(self):
        for rec in self:
            duration = rec.end_time - rec.start_time
            rec.hours = self.float_time_convert(duration)

    def attendance_validate(self):
        res = super(DailyAttendance, self).attendance_validate()
        teacher_attendance = self.env['teacher.attendance']
        attendance_line = self.env['daily.attendance.line']
        for rec in self:
            teacher_id = False
            if rec.replacement_teacher_id:
                teacher_id = rec.replacement_teacher_id.id
            elif not rec.replacement_teacher_id and rec.teacher_id:
                teacher_id = rec.teacher_id.id

            for line in rec.daily_attendance_line:
                attendance_line_id = attendance_line.search([('student_id', '=', line.student_id.id)])
                for data in attendance_line_id:
                    data.write(
                        {
                            'student_attendance': [
                                (
                                    0,0,
                                    {
                                        'attendance_line_id': line.id, 'daily_attendance_id': rec.id,
                                        'is_present': line.is_present, 'is_absent': line.is_absent
                                    }
                                )
                            ]
                        }
                    )

            teacher_attendance_id = teacher_attendance.search(
                [
                    ('teacher_id', '=', teacher_id),
                    ('school_id', '=', rec.school_id.id),
                    ('subject_id', '=', rec.subject_id.id)
                ], limit=1
            )

            if teacher_attendance_id:
                teacher_attendance_id.write(
                    {
                        'daily_attendance_ids': [(4, self.id)]
                    }
                )
                continue

            attendance_dict = {
                'teacher_id': teacher_id,
                'school_id': rec.school_id.id,
                'program_id': rec.program_id.id,
                'intake_id': rec.standard_id.id,
                'year_id': rec.year_id.id,
                'term_id': rec.term_id.id,
                'subject_id': rec.subject_id.id,
                'group_class': rec.group_class.id,
                'daily_attendance_ids': [(4, self.id)]
            }
            teacher_attendance.create(attendance_dict)
        return res

    def attendance_draft(self):
        res = super(DailyAttendance, self).attendance_draft()
        teacher_attendance = self.env['teacher.attendance']
        attendance_line = self.env['daily.attendance.line']
        for rec in self:
            for line in rec.daily_attendance_line:
                attendance_line_id = attendance_line.search([('student_id', '=', line.student_id.id)])
                for data in attendance_line_id:
                    data.student_attendance.search([('daily_attendance_id', '=', rec.id)]).unlink()

            teacher_attendance_id = teacher_attendance.search(
                [('teacher_id', '=', rec.teacher_id.id), ('school_id', '=', rec.school_id.id),
                 ('subject_id', '=', rec.subject_id.id)], limit=1)
            if teacher_attendance_id:
                teacher_attendance_id.write({'daily_attendance_ids': [(3, self.id)]})
                if teacher_attendance_id.total_presence == 0:
                    teacher_attendance_id.unlink()
        return res
    
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

        result = super(DailyAttendance, self).search_read(
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
        return super(DailyAttendance, self).read_group(
            domain,
            fields,
            groupby,
            offset=offset,
            limit=limit,
            orderby=orderby,
            lazy=lazy,
        )
    
    @api.onchange("subject_id")
    def get_domain_replacement_teacher(self):
        if not self.subject_id:
            return {}
        
        teacher_ids = self.subject_id.teacher_ids.ids

        return {
            "domain": {
                "replacement_teacher_id": [("id", "in", teacher_ids)]
            }
        }


class DailyAttendanceLine(models.Model):
    _name = 'daily.attendance.line'
    _description = "Daily Attendance Line"
    _rec_name = 'student_id'
    _order = "create_date desc"

    daily_attendance_id = fields.Many2one('daily.attendance', string="Daily Attendance", ondelete="cascade")
    student_attendance = fields.One2many('student.attendance', 'attendance_line_id')
    school_id = fields.Many2one('school.school', string='School', related='daily_attendance_id.school_id', store=True)
    program_id = fields.Many2one('standard.standard', string='Program', related='daily_attendance_id.program_id',
                                 store=True)
    intake_id = fields.Many2one('school.standard', string='Intake', related='daily_attendance_id.standard_id',
                                store=True)
    year_id = fields.Many2one('academic.year', string='Academic Year', related='daily_attendance_id.year_id',
                              store=True)
    term_id = fields.Many2one('academic.month', string='Term', related='daily_attendance_id.term_id', store=True)
    subject_id = fields.Many2one('subject.subject', string='Subject', related='daily_attendance_id.subject_id',
                                 store=True)
    teacher_id = fields.Many2one('school.teacher', string='Teacher', related='daily_attendance_id.teacher_id',
                                 store=True)
    student_id = fields.Many2one('student.student', string="Student")
    student_pid = fields.Char(string="Student ID", related="student_id.pid")
    is_present = fields.Boolean(string="Present")
    is_absent = fields.Boolean(string="Absent")
    remark = fields.Text(string="Remark")
    group_class_id = fields.Many2many('group.class', string="Group Class", related='daily_attendance_id.group_class')
    date = fields.Date(string="Date", related='daily_attendance_id.date')
    is_late = fields.Boolean('Late')

    def write(self, vals):
        if vals.get("is_present"):
            if vals.get("is_present") == True:
                self.is_absent = False
                self.is_late = False
        if vals.get("is_absent"):
            if vals.get("is_absent") == True:
                self.is_present = False
                self.is_late = False
        if vals.get("is_late"):
            if vals.get("is_late") == True:
                self.is_present = False
                self.is_absent = False
        return super().write(vals)


class AttendanceSheet(models.Model):
    _inherit = 'attendance.sheet'

    month_id = fields.Many2one("academic.month", string="Term", required=False)
    year_id = fields.Many2one("academic.year", string="Academic Year", required=False)


class StudentAttendance(models.Model):
    _name = 'student.attendance'

    attendance_line_id = fields.Many2one('daily.attendance.line', string="Attendance Line", ondelete="cascade")
    student_id = fields.Many2one('student.student', string="Student", related='attendance_line_id.student_id')
    daily_attendance_id = fields.Many2one('daily.attendance', string="Daily Attendance")
    class_id = fields.Char(string="Class", related='daily_attendance_id.name')
    is_present = fields.Boolean(string="Present")
    is_absent = fields.Boolean(string="Absent")
