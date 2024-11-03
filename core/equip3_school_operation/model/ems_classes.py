from odoo import api, fields, models, _, tools
from datetime import timedelta, datetime, date, time
from odoo.exceptions import ValidationError


class EmsClasses(models.Model):
    _name = 'ems.classes'
    _description = "EMS Classes"
    _order = "create_date desc"

    def _get_default_teacher(self):
        if self.env.user.has_group('school.group_school_teacher'):
            teacher = self.env['school.teacher'].sudo().search([('user_id', '=', self.env.user.id)], limit=1)
            if teacher:
                return teacher.id
        return False

    def _get_is_teacher(self):
        return self.env.user.has_group('school.group_school_teacher')

    @api.model
    def _domainSchool(self):
        allowed_branch_ids = self.env.branches.ids
        return [('school_branch_ids','in',allowed_branch_ids)]

    name = fields.Char("Name")
    school_id = fields.Many2one('school.school', string='School', domain=_domainSchool)
    year_id = fields.Many2one('academic.year', domain="[('current', '=', True)]", string="Academic Year")
    term_id = fields.Many2one('academic.month', domain="[('year_id', '=', year_id), ('checkactive', '=', True)]", string="Term")
    classroom_id = fields.Many2one('class.room', string="Classroom")
    program_id = fields.Many2one('standard.standard', string="Program", domain="[('school_id', '=', school_id)]")
    intake_id = fields.Many2one('school.standard', string="Intake", domain="[('standard_id', '=', program_id)]")
    group_class = fields.Many2many('group.class', string="Group Class")
    start_time = fields.Float(required=True, string='Start Time')
    end_time = fields.Float(required=True, string='End Time')
    subject_id = fields.Many2one("subject.subject", string="Subject")
    teacher_id = fields.Many2one('school.teacher', string="Teacher")
    related_subject_ids = fields.Many2many('subject.subject', string='Subject Related', compute='_compute_related_subject_ids')
    ems_classes_line = fields.One2many('ems.classes.line', 'ems_classes_id')
    study_day = fields.Char(string='Study Day', compute='_compute_study_day')
    start_am_pm = fields.Selection([('am', 'AM'), ('pm', 'PM')])
    end_am_pm = fields.Selection([('am', 'AM'),
                                 ('pm', 'PM')])
    class_date = fields.Datetime('Date', help="Date by which the person can open the survey and submit answers",
                                 default=datetime.now().replace(hour=0, minute=0, second=0))
    timetable_id = fields.Many2one('time.table', string="Classes")
    class_date_start = fields.Datetime(string='Date Start', compute='_compute_class_date_start')
    class_date_end = fields.Datetime(compute='_compute_class_date_end', string='End Date')
    start_time_str = fields.Char(string='Start Time', compute='_compute_start_time_str')
    end_time_str = fields.Char(string='End Time', compute='_compute_end_time_str')

    classes_type = fields.Selection([('regular', 'Regular'), ('exam', 'Exam')],
                                      'Classes Type',
                                      invisible=True,
                                      help='Select classes type')
    related_teacher_ids = fields.Many2many('school.teacher', compute='_compute_related_teacher_ids')
    state = fields.Selection([('pending', 'Pending'), ('active', 'Active'), ('done', 'Done'), ('cancelled', 'Cancelled')], string='State', default='pending')
    related_group_class_ids = fields.Many2many('group.class', compute='_compute_related_group_class_ids')
    is_teacher = fields.Boolean(default=lambda x: x._get_is_teacher())
    branch_id = fields.Many2one(comodel_name='res.branch', related='school_id.branch_id', readonly=False, string='Branch', store=True)
    exam_id = fields.Many2one('exam.exam', string="Exam")
    additional_exam_id = fields.Many2one('additional.exam', string="Exam")
    replacement_teacher_id = fields.Many2one('school.teacher', string='Replacement Teacher')

    @api.model
    def create(self,vals):
        if vals.get("start_time") >= vals.get("end_time"):
            raise ValidationError("Start time should be less than end time!")
        return super(EmsClasses, self).create(vals)

    def write(self,vals):
        if vals.get("start_time"):
            if self.end_time:
                if vals.get("start_time") >= self.end_time:
                    raise ValidationError("Start time should be less than end time!")
            else:
                if vals.get("start_time") >= vals.get("end_time"):
                    raise ValidationError("Start time should be less than end time!")
        if self.start_time:
            if vals.get("end_time"):
                if self.start_time >= vals.get("end_time"):
                    raise ValidationError("Start time should be less than end time!")
        return super(EmsClasses, self).write(vals)

    def unlink(self):
        for rec in self:
            if rec.state == 'active':
                raise ValidationError("Can't delete active class!")
        return super(EmsClasses, self).unlink()

    def _compute_hide_edit(self):
        for rec in self:
            if rec.state != 'pending':
                rec.hide_edit ='<style>.o_form_button_edit {display: none !important;}</style>'
            else:
                rec.hide_edit = False

    # cronjob
    def _action_update_class_active_cron(self):
        c = (datetime.now()+timedelta(hours=7)).strftime("%H.%M").split(".")
        current_time = float(c[0]) + float(c[1])/60

        class_ids = self.env['ems.classes'].search([('state', '=', 'pending'), ('class_date', '=', date.today()), ('start_time', '<=', current_time)])
        for class_id in class_ids:
            class_id.write({'state': 'active'})
            class_id.get_related_exam_id().write({'state': 'running'})
            # self.env['hr.attendance'].create({'employee_id': class_id.teacher_id.employee_id.id, 'check_in': class_id.class_date_start})
        # exam set to running

    def _action_update_class_done_cron(self):
        c = (datetime.now()+timedelta(hours=7)).strftime("%H.%M").split(".")
        current_time = float(c[0]) + float(c[1])/60

        class_ids = self.env['ems.classes'].search([('state', '=', 'active'), ('class_date', '=', date.today()), ('end_time', '<=', current_time)])
        for class_id in class_ids:
            class_id.write({'state': 'done'})
            class_id.get_related_exam_id().write({'state': 'finished'})
            # self.env['hr.attendance'].search([('employee_id', '=', class_id.teacher_id.employee_id.id), ('check_in', '=', class_id.class_date_start)], limit=1).write({'check_out': class_id.class_date_end})
        # exam set to finished

    # button active
    def action_active(self):
        self.write({'state': 'active'})
        self.get_related_exam_id().write({'state': 'running'})
        student_leave_requests = self.env['studentleave.request'].search(
            [
                ('start_date', '>=', self.class_date),
                ('end_date', '<=', self.class_date),
            ]
        )

        for request in student_leave_requests:
            if request.subject_id and request.subject_id == self.subject_id:
                self.set_to_absent(request)
            
            elif not request.subject_id:
                self.set_to_absent(request)
    
    def set_to_absent(self, request):
        student =  self.ems_classes_line.filtered(
            lambda line: not line.is_absent and line.student_id == request.student_id
        )
        if student:
            self.ems_classes_line.write(
                {
                    'is_absent': True,
                    'remark': request.reason,
                }
            )

    # button cancel
    def action_cancel(self):
        self.write({'state': 'cancelled'})
        self.env['daily.attendance'].search([('class_id', '=', self.id)], limit=1).write({'state': 'cancelled'})
        self.get_related_exam_id().write({'state': 'cancelled'})

    def action_done(self):
        self.write({'state': 'done'})
        self.get_related_exam_id().write({'state': 'finished'})

        for rec in self:
            attendance_lines = [(5, 0, 0)]
            for line in rec.ems_classes_line:
                vals = {
                    'student_id': False if not line.student_id else line.student_id.id,
                    'is_present': line.is_present,
                    'is_absent': line.is_absent,
                    'is_late': line.is_late,
                    'remark': line.remark
                }
                attendance_lines.append((0, 0, vals))
            
            replacement_teacher_id = False
            if rec.replacement_teacher_id:
                replacement_teacher_id = rec.replacement_teacher_id.id

            values = {
                'class_id': rec.id,
                'date': rec.class_date,
                'name': rec.name,
                'school_id': False if not rec.school_id else rec.school_id.id,
                'program_id': False if not rec.program_id else rec.program_id.id,
                'standard_id': False if not rec.intake_id else rec.intake_id.id,
                'group_class': False if not rec.group_class else rec.group_class.ids,
                'year_id': False if not rec.year_id else rec.year_id.id,
                'term_id': False if not rec.term_id else rec.term_id.id,
                'subject_id': False if not rec.subject_id else rec.subject_id.id,
                'teacher_id': False if not rec.teacher_id else rec.teacher_id.id,
                'start_time': rec.start_time,
                'end_time': rec.end_time,
                'state': 'draft',
                'daily_attendance_line': attendance_lines,
                'replacement_teacher_id': replacement_teacher_id
            }
            self.env['daily.attendance'].create(values)

    def get_related_exam_id(self):
        return self.env['exam.exam'].search([
            ('name', '=', self.name),
            ('school_id', '=', self.school_id.id),
            ('program_id', '=', self.program_id.id),
            ('intake_id', '=', self.intake_id.id),
            ('academic_year', '=', self.year_id.id),
            ('term_id', '=', self.term_id.id),
            ('subject_id', '=', self.subject_id.id),
            ('teacher_id', '=', self.teacher_id.id),
            ('classroom_id', '=', self.classroom_id.id),
        ])

    @api.depends('class_date')
    def _compute_study_day(self):
        for rec in self:
            rec.study_day = False
            if rec.class_date:
                rec.study_day = rec.class_date.strftime('%A')

    def name_get(self):
        result = []
        for ems_class in self:
            name = (ems_class.teacher_id.name or '') + ' - ' + (ems_class.subject_id.name or '') + ' - ' + '{0:02.0f}:{1:02.0f}'.format(*divmod(float(ems_class.start_time) * 60, 60)) + ' - ' + '{0:02.0f}:{1:02.0f}'.format(*divmod(float(ems_class.end_time) * 60, 60))
            result.append((ems_class.id, name))
        return result

    def _compute_class_date_start(self):
        for rec in self:
            rec.class_date_start = rec.class_date + timedelta(hours=float(rec.start_time)) - timedelta(hours=float(7))

    def _compute_class_date_end(self):
        for rec in self:
            rec.class_date_end = rec.class_date + timedelta(hours=float(rec.end_time)) - timedelta(hours=float(7))

    @api.depends('start_time')
    def _compute_start_time_str(self):
        for rec in self:
            rec.start_time_str = '{0:02.0f}:{1:02.0f}'.format(*divmod(float(rec.start_time) * 60, 60))

    @api.depends('end_time')
    def _compute_end_time_str(self):
        for rec in self:
            rec.end_time_str = '{0:02.0f}:{1:02.0f}'.format(*divmod(float(rec.end_time) * 60, 60))

    @api.depends('intake_id', 'year_id', 'term_id', 'teacher_id')
    def _compute_related_subject_ids(self):
        for rec in self:
            intake_subject_ids = rec.intake_id.intake_subject_line_ids.filtered(lambda x: x.year_id == rec.year_id and x.term_id == rec.term_id)
            related_subject_ids = intake_subject_ids.mapped('subject_id')
            rec.related_subject_ids = related_subject_ids
            if self.env.user.has_group('school.group_school_teacher'):
                if rec.teacher_id:
                    rec.related_subject_ids = related_subject_ids.filtered(lambda x: x in rec.teacher_id.subject_id)
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
                        rec.related_group_class_ids = group_classes.filtered(lambda x: x in rec.teacher_id.group_class_ids)
                    else:
                        rec.related_group_class_ids = False
            else:
                rec.related_group_class_ids = False

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

    @api.onchange('group_class')
    def _onchange_group_class(self):
        data = []
        for record in self:
            if record.group_class:
                for id in record.group_class.student_ids.ids:
                    data.append((0, 0, {
                        'student_id': id,
                    }))
            record.ems_classes_line = data

    @api.onchange('group_class')
    def _onchange_group_class(self):
        data = []
        for record in self:
            if record.group_class:
                record.ems_classes_line = [(2, r.id) for r in record.ems_classes_line]
                for id in record.group_class.student_ids.ids:
                    data.append((0, 0, {
                        'student_id': id,
                    }))
            record.ems_classes_line = data

    @api.model
    def create_daily_attendance(self):
        today_date = date.today()
        attendance = self.env['daily.attendance']
        class_ids = self.search([('class_date', '=', today_date)])
        for class_id in class_ids:
            daily_attendance_id = attendance.search([('teacher_id', '=', class_id.teacher_id.id), ('standard_id', '=', class_id.intake_id.id), ('date', '=', class_id.class_date)], limit=1)
            if daily_attendance_id:
                continue
            data = [(5, 0, 0)]
            for ems in class_id.ems_classes_line:
                vals = {
                    'student_id': ems.student_id.id,
                    'is_present': ems.is_present,
                    'is_absent': ems.is_absent
                }
                data.append((0, 0, vals))
            class_dict = {
                'class_id': class_id.id,
                'name': class_id.name,
                'teacher_id': class_id.teacher_id.id,
                'school_id': class_id.school_id.id,
                'year_id': class_id.year_id.id,
                'group_class': class_id.group_class.ids,
                'term_id': class_id.term_id.id,
                'program_id': class_id.program_id.id,
                'standard_id': class_id.intake_id.id,
                'subject_id': class_id.subject_id.id,
                'date': class_id.class_date,
                'state': 'draft',
                'daily_attendance_line': data,
                'start_time': class_id.start_time,
                'end_time': class_id.end_time
            }
            attendance.create(class_dict)

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

        result = super(EmsClasses, self).search_read(
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
        return super(EmsClasses, self).read_group(
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


class EmsClassesLine(models.Model):
    _name = 'ems.classes.line'
    _description = "EMS Classes Line"

    ems_classes_id = fields.Many2one('ems.classes', string="EMS Classes")
    student_id = fields.Many2one('student.student', string="Student")
    is_present = fields.Boolean(string="Present")
    is_absent = fields.Boolean(string="Absent")
    remark = fields.Char(string="Remark")
    is_late = fields.Boolean('Late')

    def write(self,vals):
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
        return super(EmsClassesLine, self).write(vals)
