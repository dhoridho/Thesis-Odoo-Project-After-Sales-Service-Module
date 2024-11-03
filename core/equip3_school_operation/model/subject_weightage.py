from odoo import _, api, fields, models, tools
from odoo.exceptions import UserError, ValidationError, Warning
from datetime import datetime, date


class SubjectWeightage(models.Model):
    _name = 'subject.weightage'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = 'Subject Weightage'
    _rec_name = "program_id"
    _order = "create_date desc"

    program_id = fields.Many2one("school.standard", string="Program")
    ems_program_id = fields.Many2one("standard.standard", string="Program")
    year = fields.Char(string="Year")
    core_subject_id = fields.Many2one("subject.subject", domain="[('subject_type', '=', 'core')]",
                                      string="Core Subject")
    elective_subject_ids = fields.Many2one("subject.subject", domain="[('subject_type', '=', 'elective')]",
                                           string="Elective Subject")
    year_id = fields.Many2one("academic.year", string="Academic Year")
    term_id = fields.Many2one("academic.month", string="Term", domain="[('year_id', '=', year_id)]")
    academic_year = fields.Many2one('academic.year', string='Academic Year')
    status = fields.Selection([('active', 'Active'), ('unactive', 'Unactive')], string='Status',
                              compute='_compute_status', store=True)
    group_class_tracking_id = fields.Many2one('group.class', string='All Academic Tracking')
    teacher_ids = fields.Many2many('school.teacher', string="teacher", help='Teachers of the following subject')
    all_academic_tracking_id = fields.Many2one('academic.tracking', string='All Academic Tracking')
    current_academic_tracking_id = fields.Many2one('academic.tracking', string='Current Academic Tracking')
    pass_academic_tracking_id = fields.Many2one('academic.tracking', string='Pass Academic Tracking')
    failed_academic_tracking_id = fields.Many2one('academic.tracking', string='Failed Academic Tracking')
    credits = fields.Integer(string='Credits', related='core_subject_id.credits')
    intake_id = fields.Many2one('school.standard', string='Intake')
    total_percentage_exam = fields.Float(string='Total Exam Percentage', compute='_compute_total_percentage_exam')
    total_percentage_assigment = fields.Float(string='Total Assignment Percentage')
    total_percentage_additional = fields.Float(string='Total Additional Percentage',
                                               compute='_compute_total_percentage_additional')
    final_percentage = fields.Float(string='Final Percentage', compute='_compute_final_percentage')
    assignment_ids = fields.One2many('school.teacher.assignment', 'subject_weightage', string='Assignment Line')
    additional_ids = fields.One2many('additional.exam', 'subject_weightage', string='Additional Exam')
    exam_ids = fields.One2many('exam.exam', 'subject_weightage', string='Exam Line')
    subject_id = fields.Many2one('subject.subject', string='Subject')
    core_subject_domain = fields.Many2many('subject.subject', compute='_get_core_subject_domain')
    elective_subject_domain = fields.Many2many('subject.subject', compute='_get_elective_subject_domain')
    subject_status = fields.Selection(
        [('active', 'Active'), ('unactive', 'Unactive'), ('pending', 'Pending'), ('pass', 'Pass'), ('fail', 'Fail')],
        string="Status", compute="_compute_subject_status")
    grade_type = fields.Many2one("grade.master", "Grade Type", help="Select Grade System")
    presence_persentage = fields.Float(string='Presence Percentage', compute='_compute_presence_persentage')
    grade = fields.Many2one('grade.line', string="Grade", compute="_compute_grade")
    teacher_id = fields.Many2one('school.teacher', string="Teacher")
    group_class = fields.Many2one('group.class', string='Group Class')
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
    
    @api.constrains('final_percentage')
    def _check_final_percentage(self):
        for subject in self:
            if subject.final_percentage and subject.final_percentage > 100:
                raise ValidationError(_("Final Percentage cannot be greater than 100%"))

    @api.depends('academic_year', 'term_id', 'term_id.checkactive')
    def _compute_subject_status(self):
        for rec in self:
            rec.subject_status = False
            if rec.term_id.checkactive:
                rec.subject_status = 'active'
            else:
                term_id = rec.term_id
                current_term_id = self.env['academic.month'].search(
                    [('year_id', '=', term_id.year_id.id), ('checkactive', '=', True)])
                if current_term_id and current_term_id.date_stop < term_id.date_stop:
                    rec.subject_status = 'pending'
                elif not current_term_id or current_term_id.date_stop >= term_id.date_stop:
                    score_id = self.env['subject.score'].search(
                        [('student_id', '=', rec.all_academic_tracking_id.student_id.id),
                         ('program_id', '=', rec.all_academic_tracking_id.program_id.id),
                         ('subject_id', '=', rec.subject_id.id)])
                    if date.today() == term_id.date_stop:
                        rec.subject_status = 'active'
                    else:
                        if score_id.result == 'Pass':
                            rec.subject_status = 'pass'
                            rec.failed_academic_tracking_id = False
                            rec.pass_academic_tracking_id = rec.all_academic_tracking_id
                        elif score_id.result == 'Fail':
                            rec.subject_status = 'fail'
                            rec.pass_academic_tracking_id = False
                            rec.failed_academic_tracking_id = rec.all_academic_tracking_id
                        else:
                            rec.pass_academic_tracking_id = False
                            rec.failed_academic_tracking_id = False

    @api.depends('total_percentage_exam', 'total_percentage_additional', 'total_percentage_assigment')
    def _compute_final_percentage(self):
        for record in self:
            record.final_percentage = (record.total_percentage_exam + record.total_percentage_additional + record.total_percentage_assigment) * 100

    def _compute_subject_id(self):
        for record in self:
            record.subject_id = record.core_subject_id.id or record.elective_subject_ids.id

    @api.depends('program_id.standard_id')
    def _get_core_subject_domain(self):
        for rec in self:
            rec.core_subject_domain = []
            if rec.program_id and rec.program_id.standard_id:
                program = rec.program_id.standard_id
                core_subject_ids = program.program_subject_ids.mapped('subject_type')
                rec.core_subject_domain = [(6, 0, core_subject_ids)]

    @api.depends('program_id.standard_id')
    def _get_elective_subject_domain(self):
        for rec in self:
            rec.elective_subject_domain = []
            if rec.program_id and rec.program_id.standard_id:
                program = rec.program_id.standard_id
                elective_subject_ids = program.program_subject_ids.mapped('subject_type')
                rec.elective_subject_domain = [(6, 0, elective_subject_ids)]

    @api.depends('year_id', 'year_id.current', 'term_id', 'term_id.checkactive')
    def _compute_status(self):
        for record in self:
            if record.year_id and record.term_id and record.year_id.current and record.term_id.checkactive:
                record.status = 'active'
            else:
                record.status = 'unactive'

    @api.depends('exam_ids.exam_percentage')
    def _compute_total_percentage_exam(self):
        for record in self:
            record.total_percentage_exam = sum(line.exam_percentage for line in record.exam_ids)

    @api.depends('additional_ids.percentage')
    def _compute_total_percentage_additional(self):
        for record in self:
            record.total_percentage_additional = sum(line.percentage for line in record.additional_ids)

    @api.depends('core_subject_id', 'elective_subject_ids', 'all_academic_tracking_id',
                 'all_academic_tracking_id.student_id')
    def _compute_presence_persentage(self):
        for record in self:
            attendance_line = self.env["daily.attendance.line"]
            subject_id = record.core_subject_id.id or record.elective_subject_ids.id
            domain = [('subject_id', '=', subject_id),
                      ('student_id', '=', record.all_academic_tracking_id.student_id.id)]
            total_attendance = attendance_line.search_count(domain)
            if total_attendance:
                total_present = attendance_line.search_count(domain + [('is_present', '=', True)])
                record.presence_persentage = total_present / total_attendance
            else:
                record.presence_persentage = 0

    @api.depends('intake_id', 'core_subject_id', 'elective_subject_ids', 'all_academic_tracking_id',
                 'all_academic_tracking_id.student_id')
    def _compute_grade(self):
        for record in self:
            subject_id = record.core_subject_id.id or record.elective_subject_ids.id
            subject_score = self.env["subject.score"].search(
                [('subject_id', '=', subject_id), ('student_id', '=', record.all_academic_tracking_id.student_id.id),
                 ('intake_id', '=', record.intake_id.id)])
            record.grade = subject_score.grade.id

    @api.model
    def create(self, vals):
        res = super(SubjectWeightage, self).create(vals)
        domain = []
        duplicate = False
        if res.ems_program_id:
            domain = [('ems_program_id', '=', res.ems_program_id.id)]
            subject = res.core_subject_id or res.elective_subject_ids
            if subject:
                if res.ems_program_id not in subject.standard_ids:
                    subject.write({'standard_ids': [(4, res.ems_program_id.id)]})
        elif res.program_id:
            domain = [('program_id', '=', res.program_id.id)]

        if domain:
            if res.core_subject_id:
                domain.append(('core_subject_id', '=', res.core_subject_id.id))
            elif res.elective_subject_ids:
                domain.append(('elective_subject_ids', '=', res.elective_subject_ids.id))
            # if len(self.search(domain)) > 1:
            #     raise ValidationError("Can't have duplicate subjects")
        return res

    def write(self, vals):
        if 'core_subject_id' in vals:
            for fee in self.env['subject.subject'].browse(vals.get('core_subject_id')):
                message_body = "Program Changed Core Subject %s to %s" % (self.core_subject_id.name, fee.name)
                if self.ems_program_id:
                    self.ems_program_id.message_post(body=message_body)
                elif self.program_id:
                    self.program_id.message_post(body=message_body)

        if 'year' in vals:
            for fee in self.env['standard.standard'].browse(vals['year']):
                message_body = "Program Changed Year from %s to %s" % (self.year, vals.get('year') or self.year)
                if self.ems_program_id:
                    self.ems_program_id.message_post(body=message_body)
                elif self.program_id:
                    self.program_id.message_post(body=message_body)

        subject_is_change = vals.get('core_subject_id', False) or vals.get('elective_subject_ids', False)
        if self.ems_program_id and subject_is_change:
            old_subject = self.core_subject_id or self.elective_subject_ids
            if old_subject and self.ems_program_id in old_subject.standard_ids:
                old_subject.write({'standard_ids': [(3, self.ems_program_id.id)]})

        res = super(SubjectWeightage, self).write(vals)

        domain = []
        duplicate = False
        if self.ems_program_id:
            domain = [('ems_program_id', '=', self.ems_program_id.id)]
            subject = self.core_subject_id or self.elective_subject_ids
            if subject:
                if self.ems_program_id not in subject.standard_ids:
                    subject.write({'standard_ids': [(4, self.ems_program_id.id)]})
        elif self.program_id:
            domain = [('program_id', '=', self.program_id.id)]

        if domain:
            if self.core_subject_id:
                domain.append(('core_subject_id', '=', self.core_subject_id.id))
            elif self.elective_subject_ids:
                domain.append(('elective_subject_ids', '=', self.elective_subject_ids.id))
            # if len(self.search(domain)) > 1:
            #     raise ValidationError("Can't have duplicate subjects")
        return res

    def unlink(self):
        if self.ems_program_id:
            subject = self.core_subject_id or self.elective_subject_ids
            if subject:
                if self.ems_program_id in subject.standard_ids:
                    subject.write({'standard_ids': [(3, self.ems_program_id.id)]})
        return super(SubjectWeightage, self).unlink()

    def name_get(self):
        result = []
        for record in self:
            if self.env.context.get('display_subject_name', False):
                result.append((record.id, record.subject_id.name))
            else:
                result.append((record.id, record.program_id.name))
        return result

    def subject_score_action_form_btn(self):
        domain = [('subject_id', '=', self.subject_id.id), ('intake_id', '=', self.program_id.id),
                  ('year_id', '=', self.year_id.id), ('term_id', '=', self.term_id.id)]
        action = {
            'type': 'ir.actions.act_window',
            'name': 'Subject Score',
            'res_model': 'subject.score',
            'domain': domain,
            'view_mode': 'tree,form',
            'context': {'search_default_groupby_program': 1, 'search_default_groupby_student': 1,
                        'search_default_groupby_year': 1, 'search_default_groupby_term': 1},
        }
        return action

    def print_result(self, partner_id=False):
        if not partner_id:
            partner_id = self.env.company.partner_id

        all_percentage = [self.total_percentage_assigment * 100, self.total_percentage_exam * 100,
                          self.total_percentage_additional * 100, self.final_percentage]
        scoring_data = self.env['subject.score'].search(
            [('subject_id', '=', self.subject_id.id), ('intake_id', '=', self.program_id.id),
             ('year_id', '=', self.year_id.id), ('term_id', '=', self.term_id.id)])
        temp_student = []
        temp_assignment = []
        temp_exam = []
        temp_additional = []
        temp_final_score = []
        temp_grade = []
        counter = 0
        total_score_assignment = 0

        for record in scoring_data:
            try:
                total_score_assignment = sum(record.assignment_line_ids.mapped('assignment_score')) / len(
                    record.assignment_line_ids)
            except ZeroDivisionError:
                total_score_assignment = 0

            temp_student.append(record.student_id.name)
            temp_assignment.append(total_score_assignment * record.total_percentage_assigment)
            temp_exam.append(sum(line.result_score_exam for line in record.exam_line_ids))
            temp_additional.append(sum(line.result_additional_exam for line in record.additional_line_ids))
            temp_final_score.append((temp_exam[counter] + temp_assignment[counter] + temp_additional[counter]))
            temp_grade.append(record.grade.grade)
            counter = counter + 1

        data = {
            'subject': self.subject_id.name,
            'program': self.program_id.name,
            'year': self.year_id.name,
            'term': self.term_id.name,
            'group_class': self.group_class.name,
            'program_data': self.program_id.standard_id.name,
            'all_percentage_data': all_percentage,
            'student_data': temp_student,
            'assignment_data': temp_assignment,
            'exam_data': temp_exam,
            'additional_exam_data': temp_additional,
            'final_score_data': temp_final_score,
            'grade_data': temp_grade,
            'company': self.env.company.read()[0],
            'address': self._get_address_details(partner_id),
            'street': self._get_street(partner_id),
            'font_family': self.env.company.font_id.family,
            'font_size': self.env.company.font_size,
            'mobile': partner_id.mobile,
            'email': partner_id.email,
            'partner': partner_id.name,
        }
        return self.env.ref(
            'equip3_school_report.action_print_final_grade_subject_weightage'
        ).report_action(self, data=data)

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
