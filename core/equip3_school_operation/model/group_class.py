from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError, Warning


class GroupClass(models.Model):
    _name = 'group.class'
    _description = 'Group Class'
    _order = "create_date desc"

    name = fields.Char(string='Name')
    intake = fields.Many2one('school.standard', string='Intake')
    pic = fields.Many2one('school.teacher', string='PIC')
    students = fields.One2many(comodel_name='group.class.line',
                               inverse_name='group_class_id',
                               string='Student')
    student_ids = fields.Many2many('student.student', string='Students')
    related_student_ids = fields.Many2many('student.student', 'class_id', 'related_student_id',
                                           string='Related Students', compute='_compute_related_student')
    unselected_student_ids = fields.Many2many('student.student', compute='_compute_unselected_student_ids')
    state = fields.Selection([('draft', 'Draft'), ('validated', 'Validated')], string='State', default='draft')
    subject_ids = fields.One2many('group.class.subject', 'group_class_id', string='Subjects')
    subject_weightage_already_generated = fields.Boolean(string='Check', default=False)
    active = fields.Boolean(default=True, help="Activate/Deactivate Group Class")

    def generate_subject_weightage(self):
        for group_class in self:
            if group_class.subject_ids and group_class.subject_weightage_already_generated == False:
                for subject in group_class.subject_ids:
                    if subject.subject_status == 'active':
                        subject_score_vals = {
                            'subject_id': subject.subject_id and subject.subject_id.id,
                            'teacher_id': subject.teacher_id and subject.teacher_id.id,
                            'program_id': group_class.intake and group_class.intake.id,
                            'year_id': subject.year_id and subject.year_id.id,
                            'term_id': subject.term_id and subject.term_id.id,
                            'group_class': group_class.id,
                        }
                        subject_weightage = self.env['subject.weightage'].create(subject_score_vals)
                        group_class.subject_weightage_already_generated = True

            else:
                raise Warning(_('Subject weightage already generated'))

    _sql_constraints = [
        (
            'unique_name_group',
            'unique (name)',
            'Name already exist'
        )
    ]

    def button_validate(self):
        self.state = 'validated'
        for subject in self.subject_ids:
            if subject.teacher_id:
                self.env['teacher.group.class'].create({
                    'teacher_id': subject.teacher_id.id,
                    'intake_id': self.intake and self.intake.id,
                    'group_class_id': self.id,
                    'subject_id': subject.subject_id and subject.subject_id.id,
                })

        if self.student_ids and self.subject_ids:
            for student in self.student_ids:
                for subject in self.subject_ids:
                    subject_score_vals = {
                        'year': subject.year,
                        'student_id': student and student.id,
                        'subject_id': subject.subject_id and subject.subject_id.id,
                        'teacher_id': subject.teacher_id and subject.teacher_id.id,
                        'program_id': self.intake.standard_id and self.intake.standard_id.id,
                        'intake_id': self.intake and self.intake.id,
                        'year_id': subject.year_id and subject.year_id.id,
                        'term_id': subject.term_id and subject.term_id.id,
                        'group_class_id': self.id,
                    }
                    subject_score = self.env['subject.score'].create(subject_score_vals)
                    filtered_subject_score = []
                    if subject.year_id.id == student.year.id and subject.year_id.current == True and subject.term_id.checkactive == True:
                        filtered_subject_score.append(subject_score.id)
                    academic_vals = {
                        'all_score_subject_ids': [(4, subject_score.id)],
                        'current_score_subject_ids': [(4, id) for id in filtered_subject_score],
                    }
                    self.env['academic.tracking'].search(
                        [('student_id', '=', student.id), ('program_id', '=', self.intake.standard_id.id)]).write(
                        academic_vals)

                if self.intake:
                    self.env['intake.student.line'].search(
                        [('intake_id', '=', self.intake.id), ('student_id', '=', student.id)]).write(
                        {'group_class_id': self.id})
                    academic_trackings = self.env['academic.tracking'].search([('student_id', '=', student.id)])
                    for tracking in academic_trackings:
                        self.env['academic.tracking.intake'].search(
                            [('intake_id', '=', self.intake.id), ('academic_tracking_id', '=', tracking.id)]).write(
                            {'group_class_id': self.id})
                    self.env['student.history'].search(
                        [('student_id', '=', student.id), ('standard_id', '=', self.intake.id)]).write(
                        {'group_class_id': self.id})

    def action_classes_btn(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Classes',
            'res_model': 'ems.classes',
            'view_mode': 'tree,form',
            'domain': [('group_class', '=', self.id)],
            'context': {},
            "target": "current",
        }

    def action_subject_weightage_btn(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Subject Weightage',
            'res_model': 'subject.weightage',
            'view_mode': 'tree,form',
            'domain': [('group_class', '=', self.id)],
            'context': {},
            "target": "current",
        }

    @api.depends('intake')
    def _compute_related_student(self):
        for rec in self:
            rec.related_student_ids = self.env['intake.student.line'].search(
                [('intake_id', '=', rec.intake.id)]).mapped('student_id')

    @api.depends('related_student_ids')
    def _compute_unselected_student_ids(self):
        for rec in self:
            group_class_id = self.search([('name', '!=', rec.name), ('intake', '=', rec.intake.id),
                                          ('related_student_ids.ids', 'in', rec.related_student_ids.ids)])
            data = []
            for line in group_class_id:
                data += line.student_ids.ids
            students = [id for id in rec.related_student_ids.ids if not id in data]
            rec.unselected_student_ids = students

    @api.constrains('student_ids')
    def _check_existing_student(self):
        for rec in self:
            if rec.student_ids:
                group_class_id = self.search([('id', '!=', rec.id), ('student_ids', 'in', rec.student_ids.ids)],
                                             limit=1)
                if group_class_id:
                    raise Warning("Student already selected in other group class.")

    @api.onchange('intake')
    def _onchange_intake(self):
        for record in self:
            record.subject_ids.unlink()
        self.subject_ids = [(0, 0, {'subject_id': subject.subject_id.id,
                                    'year': subject.year,
                                    'subject_type': subject.subject_type,
                                    'year_id': subject.year_id.id,
                                    'term_id': subject.term_id.id,
                                    }) for subject in self.intake.intake_subject_line_ids]


class GroupClassLines(models.Model):
    _name = 'group.class.line'
    _description = 'Group Class Lines'

    student_name = fields.Many2one(comodel_name='student.student', string='Name', required=True)
    group_class_id = fields.Many2one(comodel_name='group.class', string='Group Class')
    intake_id = fields.Many2one('school.standard', related='group_class_id.intake')
    related_student_ids = fields.Many2many('student.student', string='Related Student',
                                           compute='_compute_related_student_ids')

    @api.depends('intake_id', 'group_class_id')
    def _compute_related_student_ids(self):
        for rec in self:
            intake_student_line_ids = self.env['intake.student.line'].search([('intake_id', '=', rec.intake_id.id)])
            rec.related_student_ids = intake_student_line_ids.mapped('student_id')


class GroupClassSubject(models.Model):
    _name = 'group.class.subject'
    _description = 'Group Class Subject'

    group_class_id = fields.Many2one('group.class', string='Group Class')
    year = fields.Char(string='Year')
    subject_id = fields.Many2one('subject.subject', string='Subject')
    subject_type = fields.Selection([('core', 'Core'), ('elective', 'Elective')], string='Subject Type')
    year_id = fields.Many2one('academic.year', string='Year')
    term_id = fields.Many2one('academic.month', string='Term')
    teacher_id = fields.Many2one('school.teacher', string='Teacher')
    subject_status = fields.Selection(
        [('active', 'Active'), ('unactive', 'Unactive'), ('pending', 'Pending'), ('pass', 'Pass'), ('fail', 'Fail')],
        string="Status", compute="_compute_subject_status")
    intake_id = fields.Many2one('school.standard', related='group_class_id.intake')
    related_subject_ids = fields.Many2many('subject.subject', string='Related Subject',
                                           compute='_compute_related_subject_ids')

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
                elif current_term_id and current_term_id.date_stop > term_id.date_stop:
                    rec.subject_status = 'unactive'

    @api.depends('intake_id', 'group_class_id')
    def _compute_related_subject_ids(self):
        for rec in self:
            intake_subject_line_ids = self.env['intake.subject.line'].search([('intake_id', '=', rec.intake_id.id)])
            rec.related_subject_ids = intake_subject_line_ids.mapped('subject_id')
