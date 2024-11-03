from odoo import _, api, fields, models, tools
from odoo.exceptions import ValidationError
from datetime import date


class SchoolStudentAssignment(models.Model):
    _inherit = "school.student.assignment"
    _order = "create_date desc"

    submission_type = fields.Selection(selection_add=[('online', 'Online')])
    survey_id = fields.Many2one('survey.survey', string="Survey")
    attached_homework_file_name = fields.Char(string="File Name")
    attached_homework = fields.Binary(attachment=True)
    state = fields.Selection(selection_add=[
        ('reject', 'Rejected'),
        ('cancelled', 'Cancelled')
    ])
    answers_count = fields.Integer(string="Answer", compute="_compute_answers_count")
    school_id = fields.Many2one('school.school', string="School", related="teacher_assignment_id.school_id", store=True)
    program_id = fields.Many2one('standard.standard', string="Program", related="teacher_assignment_id.program_id",
                                 store=True)
    year_id = fields.Many2one('academic.year', string="Academic Year", related="teacher_assignment_id.year_id",
                              store=True)
    term_ids = fields.Many2one('academic.month', string="Term", related="teacher_assignment_id.term_ids", store=True)
    group_class = fields.Many2many('group.class', string="Group Class", domain="[('intake', '=', standard_id)]",
                                   related="teacher_assignment_id.group_class")
    score_assignment = fields.Many2one('subject.score', string="Score Assignment")
    teacher_assignment_ids = fields.One2many('student.assignment.line', 'student_assignment_id',
                                             string="Teacher Assignment")
    scoring_percentage = fields.One2many('survey.user_input', 'assignment_id', string="Score")
    assignment_score = fields.Float(string='Score', compute="_compute_score_assignment",
                                    inverse='_inverse_assignment_score')
    score = fields.Float(string="Score")
    branch_id = fields.Many2one(comodel_name='res.branch', related='school_id.branch_id', readonly=True,
                                string='Branch', store=True)

    @api.depends('teacher_assignment_ids', 'teacher_assignment_ids.scoring_percentage')
    def _compute_score_assignment(self):
        for record in self:
            record.assignment_score = record.teacher_assignment_ids.scoring_percentage

    def _inverse_assignment_score(self):
        for record in self:
            if record.submission_type != 'online':
                record.score = record.assignment_score
            else:
                pass

    def _compute_answers_count(self):
        for record in self:
            survey_answer_count = self.env['survey.user_input'].search_count([('assignment_id', '=', record.id)])
            record.answers_count = survey_answer_count

    def action_show_survey(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Student Assignment'),
            'res_model': 'survey.user_input',
            'view_mode': 'tree,form',
            'domain': [('assignment_id', '=', self.id)],
            'context': {},
            "target": "current",
        }

    def done_reject(self):
        self.state = "reject"
        self._add_assignment_to_score()

    def done_done(self):
        self.state = "done"
        self._add_assignment_to_score()

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
        res = super(SchoolStudentAssignment, self).done_assignment()
        self._add_assignment_to_score()
        return res

    def _add_assignment_to_score(self):
        if self.student_id and self.standard_id and self.year_id and self.term_ids and self.subject_id:
            domain = [
                ('student_id', '=', self.student_id.id),
                ('intake_id', '=', self.standard_id.id),
                ('year_id', '=', self.year_id.id),
                ('term_id', '=', self.term_ids.id),
                ('subject_id', '=', self.subject_id.id)
            ]

            subject_score = self.env['subject.score'].search(domain)
            if subject_score:
                subject_score.write({'assignment_line_ids': [(4, self.id)]})

    @api.model
    def create(self, vals):
        res = super(SchoolStudentAssignment, self).create(vals)
        self.env['student.assignment.line'].create({
            'student_assignment_id': res.id,
            'subject_id': res.subject_id.id,
        })
        return res

    def write(self, vals):
        res = super(SchoolStudentAssignment, self).write(vals)
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

        result = super(SchoolStudentAssignment, self).search_read(
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
        return super(SchoolStudentAssignment, self).read_group(
            domain,
            fields,
            groupby,
            offset=offset,
            limit=limit,
            orderby=orderby,
            lazy=lazy,
        )


class StudentAssignmentLine(models.Model):
    _name = "student.assignment.line"

    student_assignment_id = fields.Many2one('school.student.assignment', string="Student Assignment")
    scoring_percentage = fields.Float(string="Scoring Percentage", compute="_compute_scoring_percentage")
    score = fields.Float(string="Score")
    subject_id = fields.Many2one('subject.subject', string="Subject")
    grade = fields.Many2one('grade.line', string="Grade System", compute="_compute_grade")
    result = fields.Char(
        compute="_compute_result",
        string="Result",
        help="Result Obtained",
    )

    def _compute_scoring_percentage(self):
        for record in self:
            record.scoring_percentage = \
                sum(record.student_assignment_id.scoring_percentage.mapped(
                    'scoring_percentage')) + record.student_assignment_id.score

    @api.depends('scoring_percentage')
    def _compute_grade(self):
        for record in self:
            grade = self.env['grade.line'].search(
                [('from_mark', '<=', record.scoring_percentage), ('to_mark', '>=', record.scoring_percentage)], limit=1)
            record.grade = grade.id

    @api.depends("scoring_percentage")
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


class StudentAssignmentRejectReason(models.TransientModel):
    _inherit = 'reject.reason'

    def save_reason(self):
        res = super(StudentAssignmentRejectReason, self).save_reason()
        assignment = self.env['school.student.assignment'].browse(self.env.context.get('active_id'))
        if assignment:
            assignment._add_assignment_to_score()
        return res


class SchoolTeacherAssignment(models.Model):
    _inherit = "school.teacher.assignment"
    _order = "create_date desc"

    @api.model
    def _domainSchool(self):
        allowed_branch_ids = self.env.branches.ids
        return [('school_branch_ids','in',allowed_branch_ids)]

    year = fields.Many2one('academic.year', 'Academic Year', readonly=True, help='Select academic year')
    student_name = fields.Char('Student Name', store=True, readonly=True, help='Student Name')
    type_submission = fields.Selection(selection_add=[('online', 'Online')])
    survey_id = fields.Many2one('survey.survey', string="Question", domain="[('state','=','open')]")
    school_id = fields.Many2one('school.school', string="School", domain=_domainSchool)
    program_id = fields.Many2one('standard.standard', string="Program", domain="[('school_id', '=', school_id)]")
    year_id = fields.Many2one('academic.year', string="Academic Year", domain="[('current', '=', True)]")
    group_class = fields.Many2many('group.class', string="Group Class")
    term_ids = fields.Many2one('academic.month', string="Term",
                               domain="[('year_id', '=', year_id), ('checkactive', '=', True)]")
    subject_ids = fields.Many2many('subject.subject', string="Subject", compute="_compute_subject_ids", store=True)
    grade_system = fields.Many2one('grade.master', string="Grade System")
    subject_weightage = fields.Many2one('subject.weightage', string='Subject ID')
    student_assignment_id = fields.Many2one('school.student.assignment', string="Student Assignment")
    percentage = fields.Float(string="Percentage")
    related_subject_ids = fields.Many2many('subject.subject', string='Subject Related',
                                           compute='_compute_related_subject_ids')
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
        help="State of teacher assignment",
    )
    assign_code = fields.Char(
        "Exam Code",
        readonly=True,
        help="Code of exam",
        default=lambda obj: obj.env["ir.sequence"].next_by_code("school.teacher.assignment"),
    )
    related_group_class_ids = fields.Many2many('group.class', compute='_compute_related_group_class_ids')
    branch_id = fields.Many2one(comodel_name='res.branch', related='school_id.branch_id', readonly=False,
                                string='Branch', store=True)
    related_teacher_ids = fields.Many2many('school.teacher', compute='_compute_related_teacher_ids')
    teacher_id = fields.Many2one('school.teacher', string="Teacher")
    student_ids = fields.One2many('student.student', 'teacher_assignment_id', string='Student')

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
        vals['assign_code'] = self.env['ir.sequence'].next_by_code('school.teacher.assignment')
        res = super(SchoolTeacherAssignment, self).create(vals)
        res.write({'state': 'draft'})
        return res

    def action_open_view_assignment(self):
        domain = [('id', '=', False)]
        assignment_ids = self.env['school.student.assignment'].search([('name', '=', self.name)])
        if len(assignment_ids) > 0:
            domain = [('id', 'in', assignment_ids.ids)]
        action = {
            'type': 'ir.actions.act_window',
            'name': 'Student Assignment',
            'res_model': 'school.student.assignment',
            'domain': domain,
            'view_mode': 'tree,form',
            'context': {'group_by': 'name'},
            'target': 'current',
        }
        return action

    @api.onchange('group_class', 'year_id', 'term_ids')
    def _onchange_group_class(self):
        if self.group_class and self.year_id and self.term_ids:
            group_class_subject_data = self.env['group.class.subject'].search(
                [('group_class_id', 'in', self.group_class.ids), ('year_id', '=', self.year_id.id),
                 ('term_id', '=', self.term_ids.id)])
            dom = {'domain': {'subject_id': [('id', 'in', group_class_subject_data.subject_id.ids)]}}
            return dom

    @api.depends('standard_id', 'year_id', 'term_ids', 'teacher_id')
    def _compute_related_subject_ids(self):
        for rec in self:
            intake_subject_line_ids = rec.standard_id.intake_subject_line_ids.filtered(
                lambda x: x.year_id == rec.year_id and x.term_id == rec.term_ids)
            related_subject_ids = intake_subject_line_ids.mapped('subject_id')
            rec.related_subject_ids = related_subject_ids
            if self.env.user.has_group('school.group_school_teacher'):
                if rec.teacher_id:
                    rec.related_subject_ids = related_subject_ids.filtered(lambda x: x in rec.teacher_id.subject_id)
                else:
                    rec.related_subject_ids = False

    @api.onchange('group_class', 'year_id', 'term_ids')
    def _onchange_group_class(self):
        if self.group_class and self.year_id and self.term_ids:
            group_class_subject_data = self.env['group.class.subject'].search(
                [('group_class_id', 'in', self.group_class.ids), ('year_id', '=', self.year_id.id),
                 ('term_id', '=', self.term_ids.id)])
            dom = {'domain': {'subject_id': [('id', 'in', group_class_subject_data.subject_id.ids)]}}
            return dom

    @api.depends('standard_id', 'year_id', 'term_ids', 'teacher_id')
    def _compute_subject_ids(self):
        for rec in self:
            intake_subject_line_ids = rec.standard_id.intake_subject_line_ids.filtered(
                lambda x: x.year_id == rec.year_id and x.term_id == rec.term_ids)
            subject_ids = intake_subject_line_ids.mapped('subject_id')
            rec.subject_ids = subject_ids
            if self.env.user.has_group('school.group_school_teacher'):
                if rec.teacher_id:
                    rec.subject_ids = subject_ids.filtered(lambda x: x in rec.teacher_id.subject_id)
                else:
                    rec.subject_ids = False

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

    def done_assignments(self):
        """Changes the state to done"""
        if self.type_submission != 'hardcopy':
            for student in self.student_assign_ids:
                if student.state == "active":
                    student.done_reject()
            self.state = "finished"
        else:
            for student in self.student_assign_ids:
                if student.state == "active":
                    student.done_done()
            self.state = "finished"

        if self.standard_id and self.year_id and self.term_ids and self.subject_id:
            domain = [
                ('year_id', '=', self.year_id.id),
                ('term_id', '=', self.term_ids.id),
                ('subject_id', '=', self.subject_id.id),
                ('group_class', '=', self.group_class.id),
            ]

            ems_subject = self.env['subject.weightage'].search(domain)
            if ems_subject:
                ems_subject.write({'assignment_ids': [(4, self.id)]})

    def active_assignment(self):
        assignment_obj = self.env["school.student.assignment"]
        student_obj = self.env["student.student"]
        ir_attachment_obj = self.env["ir.attachment"]
        today = date.today()
        attachment = False
        for rec in self:
            if rec.assign_date != today:
                raise ValidationError(_("User only can start the assignment if assign date = today."))

            assignment_rec = False
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
                        "assign_date": rec.assign_date,
                        "due_date": rec.due_date,
                        "state": "active",
                        "term_ids": rec.term_ids.id,
                        "year_id": rec.year_id.id,
                        "school_id": rec.school_id.id,
                        "program_id": rec.program_id.id,
                        "attached_homework": rec.attached_homework,
                        "attached_homework_file_name": rec.attach_files,
                        "teacher_id": rec.teacher_id.id,
                        "teacher_assignment_id": rec.id,
                        "student_id": std.id,
                        "stud_roll_no": std.roll_no,
                        "student_standard": std.standard_id.standard_id.id,
                        "submission_type": rec.type_submission,
                        "attachfile_format": rec.file_format.name,
                        "survey_id": rec.survey_id.id,
                    }
                    assignment_rec = assignment_obj.create(ass_dict)
                    attach = {
                        "name": "test",
                        "datas": rec.attached_homework,
                        "description": "Assignment attachment",
                        "res_model": "school.student.assignment",
                        "res_id": assignment_rec.id,
                    }
                    ir_attachment_obj.create(attach)
                rec.state = "running"
            else:
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
                        "assign_date": rec.assign_date,
                        "due_date": rec.due_date,
                        "state": "active",
                        "attached_homework": rec.attached_homework,
                        "teacher_id": rec.teacher_id.id,
                        "teacher_assignment_id": rec.id,
                        "student_id": std.id,
                        "stud_roll_no": std.roll_no,
                        "student_standard": std.standard_id.standard_id.id,
                        "submission_type": self.type_submission,
                        "attachfile_format": self.file_format.name,
                    }
                    assignment_rec = assignment_obj.create(ass_dict)
                    attach = {
                        "name": "test",
                        "datas": rec.attached_homework,
                        "description": "Assignment attachment",
                        "res_model": "school.student.assignment",
                        "res_id": assignment_rec.id,
                    }
                    attachment = ir_attachment_obj.create(attach)
                rec.state = "running"
                for record in self:
                    record.student_assign_ids.write({'attached_homework_file_name': record.attach_files})

            for student in rec.student_assign_ids:
                rec.year = student.student_id.year
                rec.student_name = student.student_id.student_name
                assignment_rec = self.env['school.student.assignment'].search(
                    [('name', '=', rec.name), ('subject_id', '=', rec.subject_id.id),
                     ('student_id', '=', student.student_id.id),
                     ('standard_id', '=', rec.standard_id.id),
                     ('teacher_id', '=', rec.teacher_id.id),
                     ('submission_type', '=', rec.type_submission)])
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                base_url += '/student/assignment/%s-%d' % (assignment_rec.name.replace(" ", "-"), assignment_rec.id)                
                for template in self:
                    template_id = self.env.ref('equip3_school_operation.student_assignment_notification').id
                    template = self.env['mail.template'].browse(template_id)
                    if attachment:
                        template.attachment_ids = [(6, 0, [attachment.id])]
                    else:
                        template.attachment_ids = [(5, 0, 0)]
                    template.with_context(url=base_url).send_mail(self.id, force_send=True,
                                                                  email_values={'email_to': student.student_id.email})

    def print_result(self, partner_id=False):
        if not partner_id:
            partner_id = self.env.company.partner_id

        student_assignment_data = self.env['school.student.assignment'].search(
            [('teacher_assignment_id', '=', self.id)])

        temp_assignment_id = []
        temp_student = []
        temp_score = []
        temp_grade = []
        temp_result = []
        temp_group_class = []

        for record in student_assignment_data:
            temp_assignment_id.append(record.id)
            temp_student.append(record.student_id.name)

        assignment_line_data = self.env['student.assignment.line'].search(
            [('student_assignment_id', 'in', temp_assignment_id)])
        for record in assignment_line_data:
            temp_score.append(record.scoring_percentage)
            temp_grade.append(record.grade.grade)
            temp_result.append(record.result)

        for record in self.group_class:
            temp_group_class.append(record.name)

        data = {
            'assignment_id': self.read()[0],
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
        return self.env.ref('equip3_school_report.action_print_finished_assignment').report_action(self, data=data)

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
    
    @api.onchange('group_class')
    def get_student_ids(self):
        for assignment in self:
            assignment.student_ids = [(5, 0, 0)]
            if assignment.group_class:
                students = assignment.group_class.mapped('student_ids').mapped('student_id')
                assignment.student_ids = [(6, 0, students.ids)]
    
    @api.onchange('program_id')
    def _get_intake_domain(self):
        for rec in self:
            if rec.program_id and rec.program_id.intake_ids:
                domain = {'domain': {'standard_id': [('id', 'in', rec.program_id.intake_ids.ids)]}}
            else:
                domain = {'domain': {'standard_id': []}}

        return domain
    
    def action_cancel(self):
        for assignment in self:
            for student_assignment in assignment.student_assign_ids:
                student_assignment.state = "cancelled"
            
            assignment.state = "cancelled"
    
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

        result = super(SchoolTeacherAssignment, self).search_read(
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
        return super(SchoolTeacherAssignment, self).read_group(
            domain,
            fields,
            groupby,
            offset=offset,
            limit=limit,
            orderby=orderby,
            lazy=lazy,
        )