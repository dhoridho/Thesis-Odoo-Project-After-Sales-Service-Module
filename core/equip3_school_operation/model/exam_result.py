from odoo import models, api, fields, _
from odoo.exceptions import ValidationError

class ExamResult(models.Model):
    _inherit = 'exam.result'
    _rec_name = "student_id"
    _order = "create_date desc"

    exam_score = fields.Many2one('subject.score', string='Exam Score')

    # additionals
    exam_code = fields.Char(string='Exam Code', related='s_exam_ids.exam_code')
    exam_name = fields.Char(string='Exam Name', related='s_exam_ids.name', store=True)
    question_id = fields.Many2one('survey.survey', string="Question", related='s_exam_ids.question_id')
    school_id = fields.Many2one('school.school', string='School', related='s_exam_ids.school_id')
    program_id = fields.Many2one('standard.standard', string='Program', related='s_exam_ids.program_id')
    group_class = fields.Many2many('group.class', string="Group Class", domain="[('intake', '=', intake_id)]", related='s_exam_ids.group_class')
    intake_id = fields.Many2one('school.standard', string='Intake', related='s_exam_ids.intake_id', store=True)
    academic_year = fields.Many2one('academic.year', string='Academic Year', related='s_exam_ids.academic_year')
    term_id = fields.Many2one('academic.month', string='Term', related='s_exam_ids.term_id')
    exam_type = fields.Selection([('online', 'Online'), ('softcopy', 'Softcopy'), ('hardcopy', 'Hardcopy')], string='Exam Type', related='s_exam_ids.type')
    exam_attachment = fields.Binary(string='Attached Exam', related='s_exam_ids.exam_attachment')
    file_name = fields.Char(string='File Name', related='s_exam_ids.file_name')
    subject_id = fields.Many2one('subject.subject', string='Subject', related='s_exam_ids.subject_id', store=True)
    teacher_id = fields.Many2one('school.teacher', string='Teacher', related='s_exam_ids.teacher_id')
    classroom_id = fields.Many2one('class.room', string='Classroom', related='s_exam_ids.classroom_id')
    exam_date = fields.Date(string='Date', related='s_exam_ids.exam_date')
    exam_day = fields.Char(string='Exam Day', related='s_exam_ids.exam_day')
    start_time = fields.Float(string='Start Time', related='s_exam_ids.start_time')
    end_time = fields.Float(string='End Time', related='s_exam_ids.end_time')
    timetable_type = fields.Char(string='Time Table Type', related='s_exam_ids.timetable_type')
    exam_student_ids = fields.One2many('exam.student.line', 'exam_id', string='Students', related='s_exam_ids.exam_student_ids')
    timetable_id = fields.Many2one('time.table', string='Timetable', related='s_exam_ids.timetable_id')
    start_time_str = fields.Char(string='Start Time', related='s_exam_ids.start_time_str')
    end_time_str = fields.Char(string='End Time', related='s_exam_ids.end_time_str')
    exam_submission = fields.Binary(string='Exam Submission', attachment=True, help='Upload the file')
    count_answer = fields.Integer(string='Answers', compute='_compute_count_answer')
    submission_file_name = fields.Char(string='File Name')
    exam_percentage = fields.Float(string='Exam Percentage', related='s_exam_ids.exam_percentage')
    score_exam = fields.Float(string='Score', compute="_compute_score_exam", inverse='_inverse_score_exam', store=True)
    result_score_exam = fields.Float(string='Score Result', compute="_compute_result_score_exam", store=True)
    state = fields.Selection(
        [
            ('active', 'Active'),
            ('done', 'Done'),
            ('reject', 'Reject'),
            ('cancelled', 'Cancelled')
        ],
        "State",
        readonly=True,
        tracking=True,
        default="active")
    branch_id = fields.Many2one(comodel_name='res.branch', related='school_id.branch_id', readonly=True, string='Branch', store=True)

    @api.depends('result_ids', 'result_ids.obtain_marks')
    def _compute_score_exam(self):
        for record in self:
            record.score_exam = record.result_ids.obtain_marks

    def _inverse_score_exam(self):
        for record in self:
            record.result_ids.obtain_marks = record.score_exam

    @api.depends('score_exam', 'exam_percentage')
    def _compute_result_score_exam(self):
        for record in self:
            record.result_score_exam = record.score_exam * record.exam_percentage

    def set_done(self):
        res = super(ExamResult, self).set_done()
        exam = self.s_exam_ids
        if self.student_id and self.standard_id and exam and exam.academic_year \
            and exam.term_id and exam.subject_id:
            domain = [
                ('student_id', '=', self.student_id.id),
                ('intake_id', '=', self.standard_id.id),
                ('year_id', '=', exam.academic_year.id),
                ('term_id', '=', exam.term_id.id),
                ('subject_id', '=', exam.subject_id.id)
            ]

            subject_score = self.env['subject.score'].search(domain)
            if subject_score:
                subject_score.write({'exam_line_ids': [(4, self.id)]})
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
                subject_score.write({'exam_line_ids': [(4, self.id)]})

    def reject_exam(self):
        self.state = "reject"
        self._add_assignment_to_score()
        exam_line_id = self.env['exam.student.line'].search(
            [('exam_id', '=', self.s_exam_ids.id), ('student_id', '=', self.student_id.id)])
        if exam_line_id:
            exam_line_id.write({'state': 'reject'})

    def done_exam(self):
        self.state = "done"
        self._add_assignment_to_score()
        exam_line_id = self.env['exam.student.line'].search([('exam_id', '=', self.s_exam_ids.id), ('student_id', '=', self.student_id.id)])
        if exam_line_id:
            exam_line_id.write({'state': 'done'})

    def reassign_exam(self):
        self.ensure_one()
        self.state = "active"
        exam_line_id = self.env['exam.student.line'].search(
            [('exam_id', '=', self.s_exam_ids.id), ('student_id', '=', self.student_id.id)])
        if exam_line_id:
            exam_line_id.write({'state': 'active'})

    def cancel_exam(self):
        self.state = "cancelled"

    def action_show_answer(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Answers'),
            'res_model': 'survey.user_input',
            'view_mode': 'tree,form',
            'domain': [('id', '=', self.get_answer().id)],
            'context': {},
            "target": "current",
        }
    
    def _compute_count_answer(self):
        for rec in self:
            answer_id = self.get_answer()
            if len(answer_id) >= 1:
                rec.count_answer = 1
                if rec.exam_type == 'online':
                    rec.result_ids.write({'obtain_marks': answer_id.scoring_percentage, 'maximum_marks': answer_id.scoring_percentage})
            else:
                rec.count_answer = 0

    def get_answer(self):
        partner_id_by_name = self.env['res.partner'].search([('name', '=', self.student_id.name)], limit=1)
        # domain = [('exam_id', '=', self.s_exam_ids.id), ('partner_id', 'in', [self.student_id.user_id.partner_id.id, self.student_id.partner_id.id, partner_id_by_name.id])]
        domain = [('exam_id', '=', self.s_exam_ids.id), ('partner_id', 'in', [self.student_id.user_id.partner_id.id, self.student_id.partner_id.id, partner_id_by_name.id])]
        answer_id = self.env['survey.user_input'].search(domain, limit=1)
        return answer_id

    def result_confirm(self):
        """Method to confirm result"""
        for rec in self:
            # for line in rec.result_ids:
                # if line.maximum_marks == 0:
                #     # Check subject marks not greater than maximum marks
                #     raise ValidationError(
                #         _(
                #             """
                #         Kindly add maximum marks of subject "%s".
                #     """
                #         )
                #         % (line.subject_id.name)
                #     )
                # elif line.minimum_marks == 0:
                #     raise ValidationError(
                #         _(
                #             """
                #         Kindly add minimum marks of subject "%s".
                #     """
                #         )
                #         % (line.subject_id.name)
                #     )
                # elif (
                #     line.maximum_marks == 0 or line.minimum_marks == 0
                # ) and line.obtain_marks:
                #     raise ValidationError(
                #         _(
                #             """
                #         Kindly add marks details of subject "%s"!
                #     """
                #         )
                #         % (line.subject_id.name)
                #     )
            vals = {
                "grade": rec.grade,
                "percentage": rec.percentage,
                "state": "confirm",
            }
            rec.write(vals)
    
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

        result = super(ExamResult, self).search_read(
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
        return super(ExamResult, self).read_group(
            domain,
            fields,
            groupby,
            offset=offset,
            limit=limit,
            orderby=orderby,
            lazy=lazy,
        )