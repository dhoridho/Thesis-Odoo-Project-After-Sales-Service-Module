from odoo import fields, models, api
from datetime import datetime, date

class SubjectScore(models.Model):
    _name = 'subject.score'
    _description = 'Subject Score'
    _rec_name = 'student_id'
    _order = "create_date desc"

    student_id = fields.Many2one('student.student', string='Student')
    subject_id = fields.Many2one('subject.subject', string='Subject')
    credits = fields.Integer(string='Credits', related='subject_id.credits')
    teacher_id = fields.Many2one('school.teacher', string="Teacher")
    standard_id = fields.Many2one('standard.standard', string='Standard')
    intake_id = fields.Many2one('school.standard', string='Intake')
    year_id = fields.Many2one('academic.year', string='Academic Year')
    term_id = fields.Many2one('academic.month', string='Term')
    program_id = fields.Many2one('standard.standard', string='Program')
    ems_subject_id = fields.Many2one('subject.weightage', string='Ems Subject', compute='_compute_ems_subject_id')
    total_score_assignment = fields.Float(string='Total Score Assignment', compute='_compute_total_score_assignment')
    total_percentage_exam = fields.Float(string='Total Exam Percentage', related='ems_subject_id.total_percentage_exam')
    total_percentage_assigment = fields.Float(string='Total Assigment Percentage', related='ems_subject_id.total_percentage_assigment')
    total_percentage_additional = fields.Float(string='Total Additional Exam', related='ems_subject_id.total_percentage_additional')
    final_score_exam = fields.Float(string='Final Score Exam', compute='_compute_final_score_exam')
    final_score_assignment = fields.Float(string='Final Score Assignment', compute='_compute_final_score_assignment')
    final_score_additional_exam = fields.Float(string='Final Score Additional Exam', compute='_compute_final_score_additional_exam')
    grade = fields.Many2one('grade.line', string="Grade", compute="_compute_grade")
    year = fields.Char('Year')
    exam_line_ids = fields.One2many('exam.result', 'exam_score', string='Exam Line')
    assignment_line_ids = fields.One2many('school.student.assignment', 'score_assignment', string='Assignment Line')
    additional_line_ids = fields.One2many('additional.exam.line', 'score_id', string='Additional Score')
    final_percentage = fields.Float(string='Final Percentage', compute='_compute_final_percentage')
    final_score = fields.Float(string='Final Score', compute='_compute_final_score')
    grade_type = fields.Many2one("grade.master", "Grade Type", help="Select Grade System", related="ems_subject_id.grade_type")
    presence_persentage = fields.Float(string='Presence Percentage', compute='_compute_presence_persentage')
    subject_status = fields.Selection(
        [('active', 'Active'), ('unactive', 'Unactive'), ('pending', 'Pending'), ('pass', 'Pass'), ('fail', 'Fail')],
        string="Status", compute='_compute_subject_status')
    all_academic_tracking_id = fields.Many2one('academic.tracking', string='All Academic Tracking')
    current_academic_tracking_id = fields.Many2one('academic.tracking', string='Current Academic Tracking')
    pass_academic_tracking_id = fields.Many2one('academic.tracking', string='Pass Academic Tracking')
    failed_academic_tracking_id = fields.Many2one('academic.tracking', string='Failed Academic Tracking')
    result = fields.Char(
        compute="_compute_result",
        string="Result",
        help="Result Obtained",
        store=True,
    )
    group_class_id = fields.Many2one('group.class', string='Group Class')
    
    @api.depends("final_score")
    def _compute_result(self):
        """Method to compute result"""
        for rec in self:
            flag = False
            if rec.grade:
                if rec.grade.fail == True:
                    rec.result = "Fail"
                else:
                    rec.result = "Pass"

    @api.depends('final_score')
    def _compute_grade(self):
        for record in self:
            grade = self.env['grade.line'].search(
                [('from_mark', '<=', record.final_score), ('to_mark', '>=', record.final_score)], limit=1)
            record.grade = grade.id

    @api.depends('total_percentage_exam', 'total_percentage_assigment', 'total_percentage_additional')
    def _compute_final_percentage(self):
        for rec in self:
            rec.final_percentage = (rec.total_percentage_exam + rec.total_percentage_assigment + rec.total_percentage_additional)*100

    @api.depends('final_score_exam', 'final_score_assignment', 'final_score_additional_exam')
    def _compute_final_score(self):
        for rec in self:
            rec.final_score = (rec.final_score_exam + rec.final_score_assignment + rec.final_score_additional_exam)

    @api.depends('subject_id', 'intake_id', 'year_id', 'term_id')
    def _compute_ems_subject_id(self):
        for record in self:
            ems_subject_id = self.env['subject.weightage'].search([('subject_id', '=', record.subject_id.id),('program_id', '=', record.intake_id.id),('year_id', '=', record.year_id.id),('term_id', '=', record.term_id.id)], limit=1)
            record.ems_subject_id = ems_subject_id.id

    @api.depends('assignment_line_ids', 'assignment_line_ids.assignment_score')
    def _compute_total_score_assignment(self):
        try:
            self.total_score_assignment = sum(self.assignment_line_ids.mapped('assignment_score')) / len(self.assignment_line_ids)
        except ZeroDivisionError:
            self.total_score_assignment = 0

    @api.depends('total_score_assignment','total_percentage_assigment')
    def _compute_final_score_assignment(self):
        for record in self:
            record.final_score_assignment = record.total_score_assignment * record.total_percentage_assigment

    @api.depends('additional_line_ids', 'additional_line_ids.result_additional_exam')
    def _compute_final_score_additional_exam(self):
        for record in self:
            record.final_score_additional_exam = sum(line.result_additional_exam for line in record.additional_line_ids)

    @api.depends('exam_line_ids', 'exam_line_ids.result_score_exam')
    def _compute_final_score_exam(self):
        for record in self:
            record.final_score_exam = sum(line.result_score_exam for line in record.exam_line_ids)

    @api.depends('subject_id', 'student_id')
    def _compute_presence_persentage(self):
        for record in self:
            attendance_line = self.env["daily.attendance.line"]
            domain = [('subject_id', '=', record.subject_id.id),
                      ('student_id', '=', record.student_id.id)]
            total_attendance = attendance_line.search_count(domain)
            if total_attendance:
                total_present = attendance_line.search_count(domain + [('is_present', '=', True)])
                record.presence_persentage = total_present / total_attendance
            else:
                record.presence_persentage = 0

    @api.depends('year_id', 'term_id', 'term_id.checkactive')
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
                         ('subject_id', '=', rec.subject_id.id)], limit=1, order='id desc')
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
