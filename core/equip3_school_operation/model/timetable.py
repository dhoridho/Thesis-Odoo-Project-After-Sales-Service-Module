from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

class ExtendedTimeTableLine(models.Model):
    _inherit = "time.table.line"

    time_table_id = fields.Many2one('time.table', string='Time Table')
    start_am_pm = fields.Selection([('am', 'AM'),
                                 ('pm', 'PM')])

    end_am_pm = fields.Selection([('am', 'AM'),
                                 ('pm', 'PM')])
    start_time = fields.Float(required=False)
    end_time = fields.Float(required=False)
    table_student_id = fields.Many2one('time.table', string='Move Term')
    student_id = fields.Many2one('student.student', string='Student')

class TimeTable(models.Model):
    _inherit = "time.table"
    _order = "create_date desc"

    @api.model
    def _domainSchool(self):
        allowed_branch_ids = self.env.branches.ids
        return [('school_branch_ids','in',allowed_branch_ids)]

    term_id = fields.Many2one('academic.month', string="Term")
    course_id = fields.Many2one('subject.subject', string="Course")
    program_id = fields.Many2one('standard.standard', string="Program")
    teacher_id = fields.Many2one('school.teacher',  string="Teacher")
    group_class = fields.Many2one('group.class', string="Group Class", domain="[('intake', '=', standard_id), ('state', '=', 'validated')]")
    study_day = fields.Selection(string='Study Day', selection=[('sunday', 'Sunday'), ('monday', 'Monday'), ('tuesday', 'Tuesday'), ('wednesday', 'Wednesday'), ('thrusday', 'Thrusday'), ('friday', 'Friday'), ('saturday', 'Saturday')])
    classroom_id = fields.Many2one('class.room', string="Class Room")
    start_time = fields.Float(required=False)
    end_time = fields.Float(required=False)
    timetable_line_ids = fields.One2many(
        "time.table.line", "time_table_id", "TimeTable Lines",
        help="Timetable"
    )
    standard_id = fields.Many2one('school.standard', string='Program', required=False)
    ems_classes_ids = fields.One2many('ems.classes', 'timetable_id', string="TimeTable")
    subject_ids = fields.Many2one('subject.subject', string="Subject")
    start_am_pm = fields.Selection([('am', 'AM'), ('pm', 'PM')])
    end_am_pm = fields.Selection([('am', 'AM'), ('pm', 'PM')])
    student_line_ids = fields.One2many('time.table.line', 'table_student_id', string='Student')
    school_id = fields.Many2one('school.school', string='School', required=True, domain=_domainSchool)
    description = fields.Text(string='Description')
    class_already_generated = fields.Boolean(string='Check', default=False)
    branch_id = fields.Many2one(comodel_name='res.branch', related='school_id.branch_id', readonly=False, string='Branch', store=True)
    ems_classes_count = fields.Integer('Ems Classes Count', compute='_compute_ems_classes_count')

    @api.onchange('standard_id', 'term_id', 'timetable_type')
    def _onchange_first_middle_last_name(self):
        if self.timetable_type == 'regular':
            name_presented = self.standard_id.name
            if self.term_id:
                name_presented += ' - ' + self.term_id.name + ' (Regular)'
            self.name = name_presented
        elif self.timetable_type == 'exam':
            name_presented = self.standard_id.name
            if self.term_id:
                name_presented += ' - ' + self.term_id.name + ' (Exam)'
            self.name = name_presented

    @api.onchange('group_class')
    def _onchange_group_class(self):
        self.student_line_ids = [(5, 0, 0)] + [(0, 0, {'table_student_id': self.id, 'student_id': id}) for id in self.group_class.student_ids.ids]

    @api.onchange('school_id', 'program_id', 'standard_id', 'year_id', 'term_id', 'group_class')
    def _onchange_timetable(self):
        if self.timetable_type == 'regular':
            data = [(5,0,0)]
            for record in self:
                if record.group_class and record.year_id and record.term_id:
                    group_class_subject_data = self.env['group.class.subject'].search([('group_class_id', '=', record.group_class.id), ('year_id', '=', record.year_id.id), ('term_id', '=', record.term_id.id)])
                    for subject in group_class_subject_data:
                        data.append((0, 0, {
                                'subject_id' : False if not subject.subject_id else subject.subject_id.id,
                                'teacher_id': False if not subject.teacher_id else subject.teacher_id.id,
                            }))
                record.timetable_line_ids = data
        elif self.timetable_type == 'exam':
            data = [(5,0,0)]
            exam_obj = self.env['exam.exam']
            domain = [
                ('school_id', '=', self.school_id.id),
                ('program_id', '=', self.program_id.id),
                ('intake_id', '=', self.standard_id.id),
                ('academic_year', '=', self.year_id.id),
                ('term_id', '=', self.term_id.id),
                ('state', '=', 'draft')
            ]
            data += [(0,0,{
                'exm_date': e.exam_date,
                'week_day': e.exam_day.lower(),
                'subject_id': e.subject_id.id, 
                'teacher_id': e.teacher_id.id, 
                'class_room_id': e.classroom_id.id, 
                'start_time': e.start_time, 
                'end_time': e.end_time }) for e in exam_obj.search(domain)]
            self.timetable_line_ids = data

    @api.onchange('year_id')
    def _onchange_year_id(self):
        for rec in self:
            dom = {'domain': {'term_id': [('checkactive', '=', True), ('year_id', '=', rec.year_id.id)]}}
            return dom

    @api.constrains("timetable_line_ids")
    def _check_exam(self):
        """Method to check same exam is not assigned on same day."""
        if self.timetable_type == "exam":
            if not self.timetable_line_ids:
                raise ValidationError(_(""" Please Enter Exam Timetable!"""))
            domain = [("table_id", "in", self.ids)]
            line_ids = self.env["time.table.line"].search(domain)
            for rec in line_ids:
                records = [
                    rec_check.id
                    for rec_check in line_ids
                    if (
                        rec.day_of_week == rec_check.day_of_week
                        and rec.start_time == rec_check.start_time
                        and rec.end_time == rec_check.end_time
                        and rec.teacher_id.id == rec.teacher_id.id
                        and rec.exm_date == rec.exm_date
                    )
                ]
                if len(records) > 1:
                    raise ValidationError(
                        _(
                            """
    You cannot set exam at same time %s  at same day %s for teacher %s!"""
                        )
                        % (
                            rec.start_time,
                            rec.day_of_week,
                            rec.teacher_id.name,
                        )
                    )

    def action_generate_classes(self):
        if self.group_class:
            total_student = len(self.group_class.student_ids)
            for line in self.timetable_line_ids:
                if line.class_room_id and line.class_room_id.capacity < total_student:
                    raise ValidationError('Please select other class. The capacity of classes is not enough.')

        if self.class_already_generated == False:
            for time in self:
                start_date = time.term_id.date_start
                end_date = time.term_id.date_stop
                for record in time.timetable_line_ids:
                    self.env["generate.classes"].create_classes(start_date, end_date, record, time)
            self.class_already_generated = True
        else:
            raise ValidationError("This timetable has already been generated")
    
    @api.depends('ems_classes_ids')
    def _compute_ems_classes_count(self):
        for rec in self:
            if rec.ems_classes_ids:
                rec.ems_classes_count = len(rec.ems_classes_ids)
            else:
                rec.ems_classes_count = 0
    
    def action_view_classes(self):
        action = {
            'type': 'ir.actions.act_window',
            'res_model': 'ems.classes',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'domain': [('timetable_id', '=', self.id)],
            'name':"Classes",
            'views': [
                (self.env.ref('equip3_school_operation.ems_class_view_tree').id, 'tree'),
                (self.env.ref('equip3_school_operation.ems_class_form').id, 'form')
            ],
        }

        return action
    
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

        result = super(TimeTable, self).search_read(
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
        return super(TimeTable, self).read_group(
            domain,
            fields,
            groupby,
            offset=offset,
            limit=limit,
            orderby=orderby,
            lazy=lazy,
        )
