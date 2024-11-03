from odoo import _, api, fields, models, tools
from odoo.exceptions import ValidationError
from datetime import date


class AdditionalExamLine(models.Model):
    _name = 'additional.exam.line'
    _description = "Additional Exam Results"
    _order = "create_date desc"

    user_ids = fields.Many2many('res.users', string='Users')
    name = fields.Char("Additional Exam Name", help="Assignment Name")
    subject_id = fields.Many2one("subject.subject", "Subject", required=True, help="Select Subject")
    standard_id = fields.Many2one("school.standard", "Class", required=True, help="Select Standard")
    group_class = fields.Many2many('group.class', string="Group Class", domain="[('intake', '=', standard_id)]",
                                   related="additional_exam_id.group_class")
    rejection_reason = fields.Text("Reject Reason", help="Reject Reason")
    teacher_id = fields.Many2one("school.teacher", "Teacher", required=True,
                                 help="""Teacher responsible to assign assignment""")
    exam_date = fields.Date("Assign Date", required=True, help="Starting date of assignment")
    student_id = fields.Many2one("student.student", "Student", required=True, help="Name of Student")
    stud_roll_no = fields.Integer(string="Roll no", help="Roll No of student")
    attached_homework = fields.Binary("Attached Home work", help="Homework Attached by student")
    student_standard = fields.Many2one("standard.standard", "Student Standard", help="Select student standard")
    submission_type = fields.Selection(
        [("hardcopy", "Hardcopy(Paperwork)"), ("softcopy", "Softcopy"), ('online', 'Online')],
        default="hardcopy",
        string="Submission Type",
        help="Select assignment type",
    )
    attachfile_format = fields.Char("Submission Fileformat", help="Enter assignment fileformat")
    submit_assign = fields.Binary("Submit Assignment", help="Attach assignment here")
    file_name = fields.Char("File Name", help="Enter file name")
    active = fields.Boolean("Active", default=True, help="Activate/Deactivate assignment")
    additional_exam_id = fields.Many2one('additional.exam', string='Exam')
    state = fields.Selection(
        selection=[
            ('active', 'Active'),
            ('done', 'Done'),
            ('reject', 'Reject'),
            ('cancelled', 'Cancelled')
        ], string='Status', readonly=True
    )
    survey_id = fields.Many2one('survey.survey', string="Survey")
    attached_homework_file_name = fields.Char(string="File Name")
    answers_count = fields.Integer(string="Answer", compute="_compute_answers_count")
    school_id = fields.Many2one('school.school', string="School", related="additional_exam_id.school_id", store=True)
    program_id = fields.Many2one('standard.standard', string="Program", related="additional_exam_id.program_id",
                                 store=True)
    academic_year = fields.Many2one('academic.year', string="Academic Year", related="additional_exam_id.academic_year",
                                    store=True)
    term_id = fields.Many2one('academic.month', string="Term", related="additional_exam_id.term_id", store=True)
    score_assignment = fields.Many2one('subject.score', string="Score Assignment")
    start_time = fields.Float(string='Start Time')
    end_time = fields.Float(string='End Time')
    additional_score_ids = fields.One2many('additional.exam.score', 'student_additional_id',
                                           string='Additional Exam Score')
    score_id = fields.Many2one('subject.score', string="Score")
    scoring_percentage = fields.One2many('survey.user_input', 'additional_id', string="Scoring Percentage")
    additional_percentage = fields.Float(string="Additional Percentage", related="additional_exam_id.percentage",
                                         readonly=True)
    score_additional_exam = fields.Float(string="Score", compute="_compute_score_additional_exam",
                                         inverse='_inverse_score_additional_exam')
    grade_system = fields.Many2one("grade.master", "Grade System", help="Select Grade System",
                                   related="additional_exam_id.grade_system")
    result_additional_exam = fields.Float(string="Result Additional Exam", compute="_compute_result_additional_exam")
    score = fields.Float(string="Score")
    branch_id = fields.Many2one(comodel_name='res.branch', related='school_id.branch_id', readonly=True, string='Branch', store=True)

    @api.depends("additional_percentage", "score_additional_exam")
    def _compute_result_additional_exam(self):
        for record in self:
            record.result_additional_exam = record.score_additional_exam * record.additional_percentage

    @api.depends('additional_score_ids')
    def _compute_score_additional_exam(self):
        for record in self:
            record.score_additional_exam = sum(record.additional_score_ids.mapped('score'))

    def _inverse_score_additional_exam(self):
        for record in self:
            if record.submission_type != 'online':
                record.score = record.score_additional_exam
            else:
                pass

    def _compute_answers_count(self):
        for record in self:
            survey_answer_count = self.env['survey.user_input'].search_count([('additional_id', '=', record.id)])
            record.answers_count = survey_answer_count

    def action_show_survey(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Student Assignment'),
            'res_model': 'survey.user_input',
            'view_mode': 'tree,form',
            'domain': [('additional_id', '=', self.id)],
            'context': {},
            "target": "current",
        }

    def set_running(self):
        """This method change state as active"""
        if not self.attached_homework:
            raise ValidationError(_("""Kindly attach homework!"""))
        self.state = "active"

    def done_reject(self):
        self.state = "reject"
        self._add_assignment_to_score()

    def done_done(self):
        self.state = "done"
        self._add_assignment_to_score()

    def reassign_assignment(self):
        """This method change state as active"""
        self.ensure_one()
        self.state = "active"

    @api.constrains("submit_assign", "file_name")
    def check_file_format(self):
        if self.file_name:
            file_format = self.file_name.split('.')[-1]
            if len(file_format) == 2:
                if file_format[1] not in ['pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx']:
                    raise ValidationError(_("Please Select Valid File Format"))
            else:
                pass

    def done_assignment(self):
        res = super(AdditionalExamLine, self).done_assignment()
        self._add_assignment_to_score()
        return res

    def _add_assignment_to_score(self):
        if self.student_id and self.standard_id and self.academic_year and self.term_id and self.subject_id:
            domain = [
                ('student_id', '=', self.student_id.id),
                ('intake_id', '=', self.standard_id.id),
                ('year_id', '=', self.academic_year.id),
                ('term_id', '=', self.term_id.id),
                ('subject_id', '=', self.subject_id.id)
            ]

            subject_score = self.env['subject.score'].search(domain)
            if subject_score:
                subject_score.write({'additional_line_ids': [(4, self.id)]})

    @api.model
    def create(self, vals):
        res = super(AdditionalExamLine, self).create(vals)
        self.env['additional.exam.score'].create({
            'student_additional_id': res.id,
            'subject_id': res.subject_id.id,
        })
        return res

    def write(self, vals):
        res = super(AdditionalExamLine, self).write(vals)
        if vals.get('subject_id'):
            self.teacher_assignment_ids.write({'subject_id': vals.get('subject_id')})
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

        result = super(AdditionalExamLine, self).search_read(
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
        return super(AdditionalExamLine, self).read_group(
            domain,
            fields,
            groupby,
            offset=offset,
            limit=limit,
            orderby=orderby,
            lazy=lazy,
        )


class AdditionalExamScore(models.Model):
    _name = "additional.exam.score"

    student_additional_id = fields.Many2one('additional.exam.line', string="Student Assignment")
    score = fields.Float(string="Score", compute="_compute_score")
    subject_id = fields.Many2one('subject.subject', string="Subject")
    grade = fields.Many2one('grade.line', string="Grade System", compute="_compute_grade")
    result = fields.Char(
        compute="_compute_result",
        string="Result",
        help="Result Obtained",
        sore=True,
    )

    @api.depends('student_additional_id.scoring_percentage',
                 'student_additional_id.scoring_percentage.scoring_percentage')
    def _compute_score(self):
        for record in self:
            record.score = record.student_additional_id.scoring_percentage.scoring_percentage + record.student_additional_id.score

    @api.depends('score')
    def _compute_grade(self):
        for record in self:
            grade = self.env['grade.line'].search(
                [('from_mark', '<=', record.score), ('to_mark', '>=', record.score)], limit=1)
            record.grade = grade.id

    @api.depends("score")
    def _compute_result(self):
        """Method to compute result"""
        for rec in self:
            flag = False
            if rec.grade:
                if rec.grade.fail == True:
                    rec.result = "Fail"
                else:
                    rec.result = "Pass"
            else:
                rec.result = "Fail"


class AdditionalExam(models.Model):
    """Defining model for additional exam."""

    _inherit = "additional.exam"
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

    user_ids = fields.Many2many('res.users', string='Users')
    student_name = fields.Char('Student Name', store=True, readonly=True, help='Student Name')
    exam_url = fields.Char(string='Exam URL', store=True, compute='_compute_exam_url')
    school_id = fields.Many2one('school.school', string='School', domain=_domainSchool)
    program_id = fields.Many2one('standard.standard', string='Program', domain="[('school_id', '=', school_id)]")
    standard_id = fields.Many2one('school.standard', string='Intake', domain="[('standard_id', '=', program_id)]")
    group_class = fields.Many2many('group.class', string="Group Class")
    academic_year = fields.Many2one('academic.year', string='Academic Year')
    term_id = fields.Many2one('academic.month', string='Term',
                              domain="[('year_id', '=', academic_year), ('checkactive', '=', True)]")
    grade_system = fields.Many2one("grade.master", "Grade System", help="Select Grade System")
    type_submission = fields.Selection([('online', 'Online'), ('softcopy', 'Softcopy'), ('hardcopy', 'Hardcopy')],
                                       string='Type')
    related_subject_ids = fields.Many2many('subject.subject', string='Subject Related',
                                           compute='_compute_related_subject_ids')
    subject_id = fields.Many2one('subject.subject', string='Subject')
    attached_homework_file_name = fields.Char(string="File Name")
    attached_homework = fields.Binary(attachment=True)
    attach_files = fields.Char("File Name", help="Enter file name")
    file_format = fields.Many2one("file.format", "File Format", help="File format")
    exam_date = fields.Date(string='Date')
    exam_day = fields.Char(string='Exam Day', compute='_compute_exam_day')
    survey_id = fields.Many2one('survey.survey', string="Question", domain="[('state','=','open')]")
    start_time = fields.Float(string='Start Time')
    end_time = fields.Float(string='End Time')
    timetable_type = fields.Char(string='Time Table Type', readonly=True, default='Additional Exam')
    question_id = fields.Many2one('survey.survey', string="Question", domain="[('state','=','open')]")
    additional_exam_ids = fields.One2many(
        "additional.exam.line",
        "additional_exam_id",
        string="Student Assignments",
        help="Enter student assignments", )
    subject_weightage = fields.Many2one('subject.weightage', string='Subject',
                                        domain="[('standard_id', '=', standard_id)]")
    percentage = fields.Float(string="Percentage")
    state = fields.Selection(
        [
            ('hide', 'Create New'),
            ("draft", "Draft"),
            ("running", "Running"),
            ("finished", "Finished"),
            ("cancelled", "Cancelled")
        ],
        "Status",
        default="draft",
        help="State of Additional Exam",
    )
    additional_code = fields.Char(
        "Exam Code",
        required=True,
        readonly=True,
        help="Code of exam",
        default=lambda obj: obj.env["ir.sequence"].next_by_code("additional.exam"),
    )
    related_teacher_ids = fields.Many2many('school.teacher', compute='_compute_related_teacher_ids')
    related_group_class_ids = fields.Many2many('group.class', compute='_compute_related_group_class_ids')
    is_teacher = fields.Boolean(default=lambda x: x._get_is_teacher())
    branch_id = fields.Many2one(comodel_name='res.branch', related='school_id.branch_id', readonly=False, string='Branch', store=True)
    teacher_id = fields.Many2one('school.teacher', string='Teacher', domain="[('id', 'in', related_teacher_ids)]")
    student_ids = fields.One2many('student.student', 'additional_exam_id', string='Student')
    ems_classes_ids = fields.One2many(comodel_name='ems.classes', inverse_name='additional_exam_id', string='EMS Classes')
    ems_classes_count = fields.Integer('Ems Classes Count', compute='_compute_ems_classes_count')
    class_already_generated = fields.Boolean("Class Already Generated")
    classroom_id = fields.Many2one('class.room', string='Classroom')

    @api.onchange('group_class')
    def get_student_ids(self):
        for exam in self:
            exam.student_ids = [(5, 0, 0)]
            if exam.group_class:
                students = exam.group_class.mapped('student_ids').mapped('student_id')
                exam.student_ids = [(6, 0, students.ids)]

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

    @api.model
    def create(self, vals):
        vals['additional_code'] = self.env['ir.sequence'].next_by_code('additional.exam')
        res = super(AdditionalExam, self).create(vals)
        res.write({'state': 'draft'})
        return res

    @api.depends('question_id')
    def _compute_exam_url(self):
        for record in self:
            record.exam_url = ""
            if record.question_id:
                record.exam_url = record.question_id.get_start_url()

    @api.onchange('group_class', 'academic_year', 'term_id')
    def _onchange_group_class(self):
        if self.group_class and self.academic_year and self.term_id:
            group_class_subject_data = self.env['group.class.subject'].search(
                [('group_class_id', 'in', self.group_class.ids), ('year_id', '=', self.academic_year.id),
                 ('term_id', '=', self.term_id.id)])
            dom = {'domain': {'subject_id': [('id', 'in', group_class_subject_data.subject_id.ids)]}}
            return dom

    @api.depends('standard_id', 'academic_year', 'term_id', 'teacher_id')
    def _compute_related_subject_ids(self):
        for rec in self:
            intake_subject_line_ids = rec.standard_id.intake_subject_line_ids.filtered(
                lambda x: x.year_id == rec.academic_year and x.term_id == rec.term_id)
            related_subject_ids = intake_subject_line_ids.mapped('subject_id')
            rec.related_subject_ids = related_subject_ids
            if self.env.user.has_group('school.group_school_teacher'):
                if rec.teacher_id:
                    rec.related_subject_ids = related_subject_ids.filtered(lambda x: x in rec.teacher_id.subject_id)
                else:
                    rec.related_subject_ids = False

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

    @api.depends('exam_date')
    def _compute_exam_day(self):
        for rec in self:
            rec.exam_day = False
            if rec.exam_date:
                rec.exam_day = rec.exam_date.strftime('%A')

    def action_open_view_assignment(self):
        domain = [('id', '=', False)]
        additional_ids = self.env['additional.exam.line'].search([('name', '=', self.name)])
        if len(additional_ids) > 0:
            domain = [('id', 'in', additional_ids.ids)]
        action = {
            'type': 'ir.actions.act_window',
            'name': 'Additional Exam',
            'res_model': 'additional.exam.line',
            'domain': domain,
            'view_mode': 'tree,form',
            'context': {'group_by': 'name'},
            'target': 'current',
        }
        return action

    def done_assignments(self):
        """Changes the state to done"""
        self.state = 'finished'
        if self.type_submission != 'hardcopy':
            for student in self.additional_exam_ids:
                if student.state == "active":
                    student.done_reject()
            self.state = "finished"
        else:
            for student in self.additional_exam_ids:
                if student.state == "active":
                    student.done_done()
            self.state = "finished"

        if self.standard_id and self.academic_year and self.term_id and self.subject_id:
            domain = [
                ('subject_id', '=', self.subject_id.id),
                ('year_id', '=', self.academic_year.id),
                ('term_id', '=', self.term_id.id),
                ('group_class', '=', self.group_class.id),
            ]
            ems_subject = self.env['subject.weightage'].search(domain)
            if ems_subject:
                ems_subject.write({'additional_ids': [(4, self.id)]})

    def active_additional(self):

        assignment_obj = self.env["additional.exam.line"]
        student_obj = self.env["student.student"]
        ir_attachment_obj = self.env["ir.attachment"]
        for rec in self:
            student_recs = student_obj.search(
                [
                    ("standard_id", "=", rec.standard_id.id),
                    ("state", "=", "done"),
                ]
            )
            if not rec.attached_homework:
                raise ValidationError(_("""Please attach the homework!"""))
            for std in student_recs and rec.group_class.student_ids:
                ass_dict = {
                    "name": rec.name,
                    "subject_id": rec.subject_id.id,
                    "standard_id": rec.standard_id.id,
                    "exam_date": rec.exam_date,
                    "state": "active",
                    "start_time": rec.start_time,
                    "end_time": rec.end_time,
                    "term_id": rec.term_id.id,
                    "academic_year": rec.academic_year.id,
                    "school_id": rec.school_id.id,
                    "program_id": rec.program_id.id,
                    "attached_homework": rec.attached_homework,
                    "attached_homework_file_name": rec.attach_files,
                    "teacher_id": rec.teacher_id.id,
                    "additional_exam_id": rec.id,
                    "student_id": std.id,
                    "stud_roll_no": std.roll_no,
                    "student_standard": std.standard_id.standard_id.id,
                    "submission_type": rec.type_submission,
                    "attachfile_format": rec.file_format.name,
                    "survey_id": rec.question_id.id,
                }
                assignment_rec = assignment_obj.create(ass_dict)
                attach = {
                    "name": "test",
                    "datas": rec.attached_homework,
                    "description": "Assignment attachment",
                    "res_model": "additional.exam.line",
                    "res_id": assignment_rec.id,
                }
                ir_attachment_obj.create(attach)
            rec.state = "running"

    def active_assignment(self):
        assignment_obj = self.env["additional.exam.line"]
        student_obj = self.env["student.student"]
        ir_attachment_obj = self.env["ir.attachment"]
        today = date.today()
        for rec in self:
            if rec.exam_date != today:
                raise ValidationError(_("User only can start the additional exam if date = today."))
            additional_rec = False
            if rec.type_submission == "online":
                student_recs = student_obj.search(
                    [
                        ("standard_id", "=", rec.standard_id.id),
                        ("state", "=", "done"),
                    ]
                )
                for std in student_recs and rec.group_class.student_ids:
                    ass_dict = {
                        "name": rec.name,
                        "subject_id": rec.subject_id.id,
                        "standard_id": rec.standard_id.id,
                        "exam_date": rec.exam_date,
                        "state": "active",
                        "start_time": rec.start_time,
                        "end_time": rec.end_time,
                        "term_id": rec.term_id.id,
                        "academic_year": rec.academic_year.id,
                        "school_id": rec.school_id.id,
                        "program_id": rec.program_id.id,
                        "attached_homework": rec.attached_homework,
                        "attached_homework_file_name": rec.attach_files,
                        "teacher_id": rec.teacher_id.id,
                        "additional_exam_id": rec.id,
                        "student_id": std.id,
                        "stud_roll_no": std.roll_no,
                        "student_standard": std.standard_id.standard_id.id,
                        "submission_type": rec.type_submission,
                        "attachfile_format": rec.file_format.name,
                        "survey_id": rec.question_id.id,
                    }
                    additional_rec = assignment_obj.create(ass_dict)
                    attach = {
                        "name": "test",
                        "datas": rec.attached_homework,
                        "description": "Assignment attachment",
                        "res_model": "additional.exam.line",
                        "res_id": additional_rec.id,
                    }
                    ir_attachment_obj.create(attach)
                rec.state = "running"
            else:
                self.active_additional()
                for record in self:
                    record.additional_exam_ids.write({'attached_homework_file_name': record.attach_files})

            for student in rec.additional_exam_ids:
                rec.academic_year = student.student_id.year
                rec.student_name = student.student_id.student_name
                additional_rec = self.env['additional.exam.line'].search(
                    [('name', '=', rec.name), ('subject_id', '=', rec.subject_id.id),
                     ('student_id', '=', student.student_id.id), ('standard_id', '=', rec.standard_id.id),
                     ('teacher_id', '=', rec.teacher_id.id), ('submission_type', '=', rec.type_submission)])
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                base_url += '/student/additional/%s-%d' % (additional_rec.name.replace(" ", "-"), additional_rec.id)
                # for template in self:
                #     template_id = self.env.ref('equip3_school_operation.student_exam_notification').id
                #     template = self.env['mail.template'].browse(template_id)
                #     template.with_context(url=base_url).send_mail(self.id, force_send=True,
                #                                                   email_values={'email_to': student.email})

    def print_result(self, partner_id=False):
        if not partner_id:
            partner_id = self.env.company.partner_id

        additional_exam_line_data = self.env['additional.exam.line'].search([('additional_exam_id', '=', self.id)])

        temp_exam_line_id = []
        temp_student = []
        temp_score = []
        temp_grade = []
        temp_result = []
        temp_group_class = []

        for record in additional_exam_line_data:
            temp_exam_line_id.append(record.id)
            temp_student.append(record.student_id.name)

        exam_score_data = self.env['additional.exam.score'].search([('student_additional_id', 'in', temp_exam_line_id)])
        for record in exam_score_data:
            temp_score.append(record.score)
            temp_grade.append(record.grade.grade)
            temp_result.append(record.result)

        for record in self.group_class:
            temp_group_class.append(record.name)

        data = {
            'additional_exam_id': self.read()[0],
            'group_class_name': temp_group_class,
            'data_student': temp_student,
            'data_score': temp_score,
            'data_grade': temp_grade,
            'data_result': temp_result,
            'company': self.env.company.read()[0],
            'address': self._get_address_details(partner_id),
            'street': self._get_street(partner_id),
            'font_family': self.env.company.font_id.family,
            'font_size': self.env.company.font_size,
            'mobile': partner_id.mobile,
            'email': partner_id.email,
            'partner': partner_id.name,
        }
        return self.env.ref('equip3_school_report.action_print_finished_additional_exam').report_action(self, data=data)

    def get_address_details(self, partner):
        return self._get_address_details(partner)

    def get_street(self, partner):
        return self._get_street(partner)

    def _get_address_details(self, partner):
        self.ensure_one()
        res = {}
        address = ''
        if partner.city:
            address = "%s" % (partner.city)
        if partner.state_id.name:
            address += ", %s" % (partner.state_id.name)
        if partner.zip:
            address += ", %s" % (partner.zip)
        if partner.country_id.name:
            address += ", %s" % (partner.country_id.name)
        # reload(sys)
        html_text = str(tools.plaintext2html(address, container_tag=True))
        data = html_text.split('p>')
        if data:
            return data[1][:-2]
        return False

    def _get_street(self, partner):
        self.ensure_one()
        res = {}
        address = ''
        if partner.street:
            address = "%s" % (partner.street)
        if partner.street2:
            address += ", %s" % (partner.street2)
        # reload(sys)
        html_text = str(tools.plaintext2html(address, container_tag=True))
        data = html_text.split('p>')
        if data:
            return data[1][:-2]
        return False
    
    def action_cancel(self):
        for exam in self:
            exam.state = "cancelled"
            
            for student_line_id in exam.additional_exam_ids.filtered(lambda x: x.state == 'active'):
                student_line_id.state = "cancelled"
            
            for ems_class in exam.ems_classes_ids:
                ems_class.state = "cancelled"
    
    def generate_exam_classes(self):
        if self.class_already_generated == False:
            exam_detail = self.env['additional.exam'].browse(self.ids)
            classes = self.env['ems.classes']
            existing_class = classes.search([
                ('school_id', '=', exam_detail.school_id.id),
                ('program_id', '=', exam_detail.program_id.id),
                ('intake_id', '=', exam_detail.standard_id.id),
                ('year_id', '=', exam_detail.academic_year.id),
                ('term_id', '=', exam_detail.term_id.id),
                ('subject_id', '=', exam_detail.subject_id.id),
                ('group_class', '=', exam_detail.group_class.ids),
                ('teacher_id', '=', exam_detail.teacher_id.id),
                ('class_date', '=', exam_detail.exam_date),
                ('study_day', '=', exam_detail.exam_day),
                ('start_time', '=', exam_detail.start_time),
                ('end_time', '=', exam_detail.end_time),
            ], limit=1)
            
            if existing_class:
                existing_class.write({'classes_type': 'exam'})
            else:
                classes_dict = {
                    'name': exam_detail.name,
                    'school_id': exam_detail.school_id.id,
                    'program_id': exam_detail.program_id.id,
                    'intake_id': exam_detail.standard_id.id,
                    'year_id': exam_detail.academic_year.id,
                    'term_id': exam_detail.term_id.id,
                    'subject_id': exam_detail.subject_id.id,
                    'group_class': exam_detail.group_class,
                    'teacher_id': exam_detail.teacher_id.id,
                    'classroom_id': exam_detail.classroom_id.id,
                    'class_date': exam_detail.exam_date,
                    'study_day': exam_detail.exam_day,
                    'start_time': exam_detail.start_time,
                    'end_time': exam_detail.end_time,
                    'classes_type': 'exam',
                    'additional_exam_id': self.id,
                    'ems_classes_line': [(0, 0, {'student_id' : id, 'is_present': True}) for id in exam_detail.group_class.student_ids.ids]
                }
                classes.create(classes_dict)
            self.class_already_generated = True
        else:
            raise ValidationError("This class has already been generated")
    
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
            'domain': [('additional_exam_id', '=', self.id)],
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
            domain += [("school_id.company_id", "in", context.get("allowed_company_ids"))]

        if context.get("allowed_branch_ids"):
            domain += [
                "|",
                ("branch_id", "in", context.get("allowed_branch_ids")),
                ("branch_id", "=", False),
            ]

        result = super(AdditionalExam, self).search_read(
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
        return super(AdditionalExam, self).read_group(
            domain,
            fields,
            groupby,
            offset=offset,
            limit=limit,
            orderby=orderby,
            lazy=lazy,
        )