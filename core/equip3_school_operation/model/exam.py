from odoo import models, api, fields, _, tools
from odoo.exceptions import ValidationError
from datetime import date

class Exam(models.Model):
    _name = "exam.exam"
    _inherit = ["exam.exam", "mail.thread", "mail.activity.mixin"]
    _description = "Regular Exam"
    _order = "create_date desc"

    student_name = fields.Char('Student Name', store=True, readonly=True, help='Student Name')
    question_id = fields.Many2one('survey.survey', string="Question", domain="[('state','=','open')]")
    exam_url = fields.Char(string='Exam URL', store=True, compute='_compute_exam_url')
    user_ids = fields.Many2many('res.users', string='User', copy=False)
    sender_name = fields.Char(string='Sender', default=lambda self:self.env.user.name)
    type = fields.Selection([('online', 'Online'), ('softcopy', 'Softcopy'), ('hardcopy', 'Hardcopy')], string='Exam Type')
    exam_attachment = fields.Binary(string='Attached Exam', attachment=False, help='Upload the file')
    term_id = fields.Many2one('academic.month', string='Term', required=True, domain="[('year_id', '=', academic_year), ('checkactive', '=', True)]")
    exam_score = fields.Many2one('subject.score', string='Score')
    exam_percentage = fields.Float(string='Exam Percentage')
    group_class = fields.Many2many('group.class', string="Group Class")
    score_result = fields.Float(string='Score Result')
    class_already_generated = fields.Boolean(string='Check', default=False)
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
    related_group_class_ids = fields.Many2many('group.class', compute='_compute_related_group_class_ids')
    student_ids = fields.One2many('student.student', 'exam_id', string='Student')

    @api.onchange('group_class')
    def get_student_ids(self):
        for exam in self:
            exam.student_ids = [(5, 0, 0)]
            if exam.group_class:
                students = exam.group_class.mapped('student_ids').mapped('student_id')
                exam.student_ids = [(6, 0, students.ids)]

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

    @api.constrains("active")
    def check_active(self):
        """if exam results is not in done state then raise an
        validation Warning"""
        result_obj = self.env["exam.result"]
        if not self.active:
            for result in result_obj.search([("s_exam_ids", "=", self.id)]):
                if result.state != "done":
                    raise ValidationError(
                        _(
                            """
                        Kindly,mark as done %s examination results!
                    """
                        )
                        % (self.name)
                    )

    active = fields.Boolean(
        "Active", default="True", help="Activate/Deactivate record"
    )
    name = fields.Char("Exam Name", required=True, help="Name of Exam")
    exam_code = fields.Char(
        "Exam Code",
        required=True,
        readonly=True,
        help="Code of exam",
        default=lambda obj: obj.env["ir.sequence"].next_by_code("exam.exam"),
    )
    standard_id = fields.Many2many(
        "standard.standard",
        "standard_standard_exam_rel",
        "standard_id",
        "event_id",
        "Participant Standards",
        help="Select Standard",
    )
    start_date = fields.Date(
        "Exam Start Date", help="Exam will start from this date"
    )
    end_date = fields.Date("Exam End date", help="Exam will end at this date")
    state = fields.Selection(
        [
            ('hide', 'Create New'),
            ("draft", "Draft"),
            ("running", "Running"),
            ("finished", "Finished"),
            ("cancelled", "Cancelled"),
        ],
        "State",
        readonly=True,
        default="draft",
        help="State of the exam",
    )
    grade_system = fields.Many2one("grade.master", "Grade System", help="Select Grade System")
    academic_year = fields.Many2one("academic.year", "Academic Year", help="Select Academic Year")
    exam_schedule_ids = fields.One2many("exam.schedule.line", "exam_id", "Exam Schedule", help="Enter exam schedule")
    subject_weightage = fields.Many2one('subject.weightage', string='Subject ID')
    branch_id = fields.Many2one(comodel_name='res.branch', related='school_id.branch_id', readonly=False, string='Branch', store=True)

    def set_to_draft(self):
        """Method to set state to draft"""
        self.state = "draft"

    def set_running(self):
        """Method to set state to running"""
        classes_running = self.env['ems.classes'].search([('name', '=', self.name)])
        classes_running.write({'state': 'active'})
        today = date.today()
        for rec in self:
            if not rec.standard_id:
                raise ValidationError(_("Please Select Standard!"))
            elif rec.exam_date != today:
                raise ValidationError(_("User only can start the exam if date = today."))
            else:
                rec.state = "running"

            # if rec.exam_schedule_ids:
            # else:
            #     raise ValidationError(_("You must add one Exam Schedule!"))

            # create exam student line
            rec.exam_student_ids = [(0,0,{'student_id': student.id, 'state': 'active'}) for student in rec.group_class.student_ids]

            # generate exam results based on student line
            rec.generate_student_result()

        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        base_url += '/student/exam'
        for i in self.standard_id:
            students = self.env['student.student'].search([('standard_id','=', i.id), ('year', '=', self.academic_year.id), ('state','!=','alumni')])
        for student in students:
            self.student_name = student.student_name
            for template in self:
                template_id = self.env.ref('equip3_school_operation.student_exam_notification').id
                template = self.env['mail.template'].browse(template_id)
                template.with_context(url=base_url).send_mail(self.id, force_send=True, email_values={'email_to': student.email})
        exam_result = self.env['exam.result'].search([('student_id', '=', self.student_name)])
        if exam_result:
            exam_result.write({'state': 'active'})

    @api.depends('intake_id')
    def _compute_student_ids(self):
        for rec in self:
            rec.student_ids = [(6,0,rec.intake_id.student_ids.ids)]

    def set_finish(self):
        """Method to set state to finish"""
        classes_running = self.env['ems.classes'].search([('name', '=', self.name)])
        classes_running.write({'state': 'done'})
        self.state = "finished"
        if self.intake_id and self.academic_year and self.term_id and self.subject_id:
            domain = [
                ('year_id', '=', self.academic_year.id),
                ('term_id', '=', self.term_id.id),
                ('subject_id', '=', self.subject_id.id),
                ('group_class', '=', self.group_class.id),
            ]
            ems_subject = self.env['subject.weightage'].search(domain)
            if ems_subject:
                ems_subject.write({'exam_ids': [(4, self.id)]})

        # set final state based on type
        if self.type == 'hardcopy':
            # set exam student line to done
            for student_line_id in self.exam_student_ids.filtered(lambda x: x.state == 'active'):
                student_line_id.button_done()
            # set exam results to done
            for result_id in self.env['exam.result'].search([('exam_code', '=', self.exam_code)]):
                result_id.set_done()

        elif self.type in ('online', 'softcopy'):
            for student_line_id in self.exam_student_ids.filtered(lambda x: x.state == 'active'):
                student_line_id.button_reject()

    def generate_result(self):
        """Method to generate result"""
        result_obj = self.env["exam.result"]
        student_obj = self.env["student.student"]
        result_list = []
        for rec in self:
            for exam_schedule in rec.exam_schedule_ids:
                domain = [
                    ("standard_id", "=", exam_schedule.standard_id.id),
                    ("year", "=", rec.academic_year.id),
                    ("state", "=", "done"),
                    ("school_id", "=", exam_schedule.standard_id.school_id.id),
                ]
                students_rec = student_obj.search(domain)
                for student in students_rec:
                    domain = [
                        ("standard_id", "=", student.standard_id.id),
                        ("student_id", "=", student.id),
                        ("s_exam_ids", "=", rec.id),
                    ]
                    exam_result_rec = result_obj.search(domain)
                    if exam_result_rec:
                        [result_list.append(res.id) for res in exam_result_rec]
                    else:
                        rs_dict = {
                            "s_exam_ids": rec.id,
                            "student_id": student.id,
                            "standard_id": student.standard_id.id,
                            "roll_no": student.roll_no,
                            "grade_system": rec.grade_system.id,
                        }
                        exam_line = []
                        timetable = exam_schedule.sudo().timetable_id
                        for line in timetable.sudo().timetable_ids:
                            min_mrks = line.subject_id.minimum_marks
                            max_mrks = line.subject_id.maximum_marks
                            sub_vals = {
                                "subject_id": line.subject_id.id,
                                "minimum_marks": min_mrks,
                                "maximum_marks": max_mrks,
                            }
                            exam_line.append((0, 0, sub_vals))
                        rs_dict.update({"result_ids": exam_line})
                        result_rec = result_obj.create(rs_dict)
                        result_list.append(result_rec.id)
        return {
            "name": _("Result Info"),
            "view_mode": "tree,form",
            "res_model": "exam.result",
            "type": "ir.actions.act_window",
            "domain": [("id", "in", result_list)],
        }

    @api.depends('question_id')
    def _compute_exam_url(self):
        for record in self:
            record.exam_url = ""
            if record.question_id:
                record.exam_url = record.question_id.get_start_url()

    exam_count = fields.Integer(string="Answer", compute="_compute_exam_count")

    @api.model
    def create(self, vals):
        vals['exam_code'] = self.env['ir.sequence'].next_by_code('exam.exam')
        res = super(Exam, self).create(vals)
        res.write({'state': 'draft'})
        return res

    def action_show_survey(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Regular Exam'),
            'res_model': 'survey.user_input',
            'view_mode': 'tree,form',
            'domain': [('exam_id', '=', self.id)],
            'context': {},
            "target": "current",
        }

    def _compute_exam_count(self):
        for record in self:
            survey_exam_count = self.env['survey.user_input'].search_count([('exam_id', '=', record.id)])
            record.exam_count = survey_exam_count

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

    # exam modification
    school_id = fields.Many2one('school.school', string='School', domain=_domainSchool)
    program_id = fields.Many2one('standard.standard', string='Program', domain="[('school_id', '=', school_id)]")
    intake_id = fields.Many2one('school.standard', string='Intake', domain="[('standard_id', '=', program_id)]")
    subject_id = fields.Many2one('subject.subject', string='Subject')
    related_subject_ids = fields.Many2many('subject.subject', string='Subject Related', compute='_compute_related_subject_ids')
    teacher_id = fields.Many2one('school.teacher', string="Teacher", domain="[('id', 'in', related_teacher_ids)]")
    classroom_id = fields.Many2one('class.room', string='Classroom')
    exam_date = fields.Date(string='Date')
    exam_day = fields.Char(string='Exam Day', compute='_compute_exam_day')
    start_time = fields.Float(string='Start Time', group_operator=False)
    end_time = fields.Float(string='End Time', group_operator=False)
    timetable_type = fields.Char(string='Time Table Type', readonly=True, default='Exam')
    exam_student_ids = fields.One2many('exam.student.line', 'exam_id', string='Students')
    timetable_id = fields.Many2one('time.table', string='Timetable')
    start_time_str = fields.Char(string='Start Time', compute='_compute_start_time_str')
    end_time_str = fields.Char(string='End Time', compute='_compute_end_time_str')
    file_name = fields.Char(string='File Name')
    is_teacher = fields.Boolean(default=lambda x: x._get_is_teacher())
    related_teacher_ids = fields.Many2many('school.teacher', compute='_compute_related_teacher_ids')
    ems_classes_ids = fields.One2many(comodel_name='ems.classes', inverse_name='exam_id', string='EMS Classes')
    ems_classes_count = fields.Integer('Ems Classes Count', compute='_compute_ems_classes_count')

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

    def set_cancel(self):
        """Method to set state to cancel"""
        self.state = "cancelled"
        exam_student = self.env["exam.student.line"].search([("exam_id", "=", self.id)])
        exam_student.write({"state": "cancelled"})
        for student_line_id in self.exam_student_ids.filtered(lambda x: x.state == 'active'):
            student_line_id.button_cancel()
        classes_cancel = self.env['ems.classes'].search([('name', '=', self.name)])
        classes_cancel.write({'state': 'cancelled'})
        exam_cancel = self.env['exam.result'].search([('exam_code', '=', self.exam_code)])
        exam_cancel.write({'state': 'cancelled'})

    @api.depends('exam_date')
    def _compute_exam_day(self):
        for rec in self:
            rec.exam_day = False
            if rec.exam_date:
                rec.exam_day = rec.exam_date.strftime('%A')

    @api.onchange('group_class', 'academic_year', 'term_id')
    def _onchange_group_class(self):
        if self.group_class and self.academic_year and self.term_id:
            group_class_subject_data = self.env['group.class.subject'].search([('group_class_id', 'in', self.group_class.ids), ('year_id', '=', self.academic_year.id), ('term_id', '=', self.term_id.id)])
            dom = {'domain': {'subject_id': [('id', 'in', group_class_subject_data.subject_id.ids)]}}
            return dom

    @api.depends('intake_id', 'academic_year', 'term_id', 'teacher_id')
    def _compute_related_subject_ids(self):
        for rec in self:
            intake_subject_line_ids = rec.intake_id.intake_subject_line_ids.filtered(lambda x: x.year_id == rec.academic_year and x.term_id == rec.term_id)
            related_subject_ids = intake_subject_line_ids.mapped('subject_id')
            rec.related_subject_ids = related_subject_ids
            if self.env.user.has_group('school.group_school_teacher'):
                if rec.teacher_id:
                    rec.related_subject_ids = related_subject_ids.filtered(lambda x: x in rec.teacher_id.subject_id)
                else:
                    rec.related_subject_ids = False


    @api.onchange('program_id')
    def _onchange_program_id(self):
        if self.program_id:
            self.standard_id = [(6,0,[self.program_id.id])]
        else:
            self.standard_id = [(5,0,0)]

    @api.onchange('intake_id')
    def _onchange_intake_id(self):
        self.exam_schedule_ids = [(5,0,0)]
        if self.intake_id:
            self.exam_schedule_ids = [(0,0,{'standard_id': self.intake_id.id})]

    @api.depends('start_time')
    def _compute_start_time_str(self):
        for rec in self:
            rec.start_time_str = '{0:02.0f}:{1:02.0f}'.format(*divmod(float(rec.start_time) * 60, 60))

    @api.depends('end_time')
    def _compute_end_time_str(self):
        for rec in self:
            rec.end_time_str = '{0:02.0f}:{1:02.0f}'.format(*divmod(float(rec.end_time) * 60, 60))

    def generate_student_result(self):
        # Method to generate exam results based on student exam line
        result_obj = self.env['exam.result']
        result = []

        for line_id in self.exam_student_ids:
            # check if exam result created before
            domain = [
                ('standard_id', '=', self.intake_id.id),
                ('student_id', '=', line_id.student_id.id),
                ('s_exam_ids', '=', self.id),
            ]
            exam_result_ids = result_obj.search(domain)
            if exam_result_ids:
                # append to result list if found
                result += exam_result_ids.ids
            else:
                # create new exam result
                value = {
                    's_exam_ids': self.id,
                    'student_id': line_id.student_id.id,
                    'standard_id': self.intake_id.id,
                    'roll_no': line_id.student_id.roll_no,
                    'grade_system': self.grade_system.id,
                    'result_ids': [(0,0,{'subject_id': self.subject_id.id})]
                }
                exam_result_id = result_obj.create(value)
                result.append(exam_result_id.id)

        return {
            "name": _("Result Info"),
            "view_mode": "tree,form",
            "res_model": "exam.result",
            "type": "ir.actions.act_window",
            "domain": [("id", "in", result)],
        }

    def generate_exam_classes(self):
        if self.class_already_generated == False:
            examdetail = self.env['exam.exam'].search([('id', '=', self.ids)])
            classes = self.env['ems.classes']
            existing_class = classes.search([
                ('school_id', '=', examdetail.school_id.id),
                ('program_id', '=', examdetail.program_id.id),
                ('intake_id', '=', examdetail.intake_id.id),
                ('year_id', '=', examdetail.academic_year.id),
                ('term_id', '=', examdetail.term_id.id),
                ('subject_id', '=', examdetail.subject_id.id),
                ('group_class', '=', examdetail.group_class.ids),
                ('teacher_id', '=', examdetail.teacher_id.id),
                ('class_date', '=', examdetail.exam_date),
                ('study_day', '=', examdetail.exam_day),
                ('start_time', '=', examdetail.start_time),
                ('end_time', '=', examdetail.end_time),
            ], limit=1)
            
            if existing_class:
                existing_class.write({'classes_type': 'exam'})
            else:
                classes_dict = {
                    'name': examdetail.name,
                    'school_id': examdetail.school_id.id,
                    'program_id': examdetail.program_id.id,
                    'intake_id': examdetail.intake_id.id,
                    'year_id': examdetail.academic_year.id,
                    'term_id': examdetail.term_id.id,
                    'subject_id': examdetail.subject_id.id,
                    'group_class': examdetail.group_class,
                    'teacher_id': examdetail.teacher_id.id,
                    'classroom_id': examdetail.classroom_id.id,
                    'class_date': examdetail.exam_date,
                    'study_day': examdetail.exam_day,
                    'start_time': examdetail.start_time,
                    'end_time': examdetail.end_time,
                    'classes_type': 'exam',
                    'exam_id': self.id,
                    'ems_classes_line': [(0, 0, {'student_id' : id, 'is_present': True}) for id in examdetail.group_class.student_ids.ids]
                }
                classes.create(classes_dict)
            self.class_already_generated = True
        else:
            raise ValidationError("This class has already been generated")

    def action_open_view_exam(self):
        domain = [('id', '=', False)]
        exam_ids = self.env['exam.result'].search([('exam_name', '=', self.name)])
        if exam_ids:
            domain = [('id', 'in', exam_ids.ids)]
        return {
            'name': _('Exam'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'exam.result',
            'type': 'ir.actions.act_window',
            'domain': domain,
        }

    def print_result(self, partner_id=False):
        if not partner_id:
            partner_id = self.env.company.partner_id

        exam_result_data = self.env['exam.result'].search([('exam_code', '=', self.exam_code)])
        temp_exam_result_id = []
        temp_student = []
        temp_score = []
        temp_grade = []
        temp_result = []

        for record in exam_result_data:
            temp_exam_result_id.append(record.id)
            temp_student.append(record.student_id.name)

        exam_subject_data = self.env['exam.subject'].search([('exam_id', 'in', temp_exam_result_id)])
        

        for record in exam_subject_data:
            temp_score.append(record.obtain_marks)            
            temp_result.append(record.result)
            temp_grade.append(record.grade.id)

        grade_data = self.env['grade.line'].search([('id', 'in', temp_grade)])
        grade_result = []

        for record in temp_grade:
            for rec in grade_data:
                if record == rec.id:
                    grade_result.append(rec.grade)

        temp_group_id = []
        for record in self.group_class:
            temp_group_id.append(record.id)

        group_class_data = self.env['group.class'].search_read([('id', 'in', temp_group_id)])

        data = {
            'exam_id': self.read()[0],
            'group_class_name': group_class_data,
            'data_student' : temp_student,
            'data_score' : temp_score,
            'data_grade' : grade_result,
            'data_result' : temp_result,
            'company': self.env.company.read()[0],
            'address': self._get_address_details(partner_id),
            'street': self._get_street(partner_id),
            'font_family': self.env.company.font_id.family,
            'font_size': self.env.company.font_size,
            'mobile': partner_id.mobile,
            'email': partner_id.email,
            'partner': partner_id.name,
        }
        return self.env.ref('equip3_school_report.action_print_finished_exam').report_action(self, data=data)

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
            'domain': [('exam_id', '=', self.id)],
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

        result = super(Exam, self).search_read(
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
        return super(Exam, self).read_group(
            domain,
            fields,
            groupby,
            offset=offset,
            limit=limit,
            orderby=orderby,
            lazy=lazy,
        )


class ExamStudentLine(models.Model):
    _name = 'exam.student.line'
    _rec_name = 'student_id'

    exam_id = fields.Many2one('exam.exam', string='Exam')
    student_id = fields.Many2one('student.student', string='Student')
    state = fields.Selection([('active', 'Active'), ('done', 'Done'), ('reject', 'Reject'), ('cancelled', 'Cancelled')], string='Status')
    score = fields.Float(string='Score')
    result = fields.Char(string='Result')

    def button_done(self):
        self.state = 'done'
        exam_result = self.env['exam.result'].search([('s_exam_ids', '=', self.exam_id.id), ('student_id', '=', self.student_id.id)])
        if exam_result:
            exam_result.write({'state': 'done'})
            exam_result.done_exam()

    def button_reject(self):
        self.state = 'reject'
        exam_result = self.env['exam.result'].search([('s_exam_ids', '=', self.exam_id.id), ('student_id', '=', self.student_id.id)])
        if exam_result:
            exam_result.write({'state': 'reject'})
            exam_result.reject_exam()

    def button_reassigned(self):
        self.state = 'active'
        exam_result = self.env['exam.result'].search(
            [('s_exam_ids', '=', self.exam_id.id), ('student_id', '=', self.student_id.id)])
        if exam_result:
            exam_result.write({'state': 'active'})
            exam_result.reassign_exam()

    def button_cancel(self):
        self.state = 'cancelled'
        exam_result = self.env['exam.result'].search(
            [('s_exam_ids', '=', self.exam_id.id), ('student_id', '=', self.student_id.id)])
        if exam_result:
            exam_result.write({'state': 'cancelled'})


class ExamSubject(models.Model):
    _inherit = 'exam.subject'

    @api.constrains(
        "obtain_marks", "minimum_marks", "maximum_marks", "marks_reeval"
    )
    def _validate_marks(self):
        """Override to remove method to validate marks"""
        return

    def _compute_grade(self):
        for rec in self:
            rec.grade_line_id = False
        return super(ExamSubject, self)._compute_grade()

    grade = fields.Many2one('grade.line', string="Grade System", compute="_compute_grade_mark")
    result = fields.Char(
        compute="_compute_result",
        string="Result",
        help="Result Obtained",
        store=True
    )

    @api.depends('obtain_marks')
    def _compute_grade_mark(self):
        for record in self:
            grade = self.env['grade.line'].search(
                [('from_mark', '<=', record.obtain_marks), ('to_mark', '>=', record.obtain_marks)], limit=1)
            record.grade = grade.id

    @api.depends("obtain_marks")
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

