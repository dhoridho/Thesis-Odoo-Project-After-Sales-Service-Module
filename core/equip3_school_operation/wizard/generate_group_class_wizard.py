from odoo import _, models, fields, api
from odoo.exceptions import ValidationError

import math
from string import ascii_uppercase as group_names


class GenerateGroupClassWizard(models.TransientModel):
    _name = "generate.group.class.wizard"

    number = fields.Integer(string='Divide to', required=True)
    student_ids = fields.Many2many('intake.student.line', string='Intake Student Line',
                                   compute='_compute_intake_student_line')
    available_student_ids = fields.Many2many('intake.student.line', 'line_id', 'wizard_id',
                                             string='Intake Student Line', compute='_compute_intake_student_line')
    count_available = fields.Integer(string='Count Available', compute='_compute_intake_student_line')
    show_warning = fields.Boolean(string='Show Warning', compute='_compute_intake_student_line')

    @api.depends('number')
    def _compute_intake_student_line(self):
        for rec in self:
            context = dict(self._context) or {}
            intake_id = self.env['school.standard'].browse(context.get('active_id'))
            intake_student_line_ids = intake_id.intake_student_line_ids
            rec.student_ids = intake_student_line_ids
            rec.available_student_ids = intake_student_line_ids.filtered(lambda x: not x.group_class_id)
            rec.count_available = len(rec.available_student_ids)
            rec.show_warning = rec.count_available % rec.number > 0 if rec.number > 0 else False

    def button_generate(self):
        pass
        context = dict(self._context) or {}
        intake_id = self.env['school.standard'].browse(context.get('active_id'))
        if self.number == 0:
            raise ValidationError('Number cannot be 0!')
        elif self.number > self.count_available:
            raise ValidationError('Number cannot exceed available student number (%s)!' % (self.count_available))
        else:
            student_list = self.prepare_student(self.available_student_ids)
            i = 0
            for group_name in group_names[:self.number]:
                intake_student_line_ids = student_list[i][0]
                group_vals = {
                    'name': 'Intake (%s:%s) - Class %s' % (intake_id.id, intake_id.name, group_name),
                    'intake': intake_id.id,
                }

                # create group
                group_id = self.env['group.class'].create(group_vals)

                # update intake student line group class
                for intake_student_line_id in intake_student_line_ids:
                    intake_student_line_id.write({'group_class_id': group_id.id})
                    group_id.write({'students': [(0, 0, {'student_name': intake_student_line_id.student_id.id})]})
                    academic_tracking = self.env['academic.tracking'].search(
                        [('student_id', '=', intake_student_line_id.student_id.id)])
                    for tracking in academic_tracking:
                        self.env['academic.tracking.intake'].search(
                            [('intake_id', '=', intake_id.id), ('academic_tracking_id', '=', tracking.id)]).write(
                            {'group_class_id': group_id.id})
                    self.env['student.history'].search([('student_id', '=', intake_student_line_id.student_id.id),
                                                        ('standard_id', '=', intake_id.id)]).write(
                        {'group_class_id': group_id.id})
                group_id.write({'student_ids': [(6, 0, intake_student_line_ids.mapped('student_id').ids)]})

                # increment
                i += 1
                group_id.write({'subject_ids': [(0, 0, {'subject_id': subject.subject_id.id,
                                                        'year': subject.year,
                                                        'subject_type': subject.subject_type,
                                                        'year_id': subject.year_id.id,
                                                        'term_id': subject.term_id.id,
                                                        }) for subject in
                                                intake_id.intake_subject_line_ids]})

    def prepare_student(self, intake_student_line_ids):
        student_per_group = math.floor(self.count_available / self.number)
        group_mod = self.count_available % self.number
        student_list = []
        start = 0
        end = student_per_group + group_mod

        for i in range(self.number):
            current_list = [intake_student_line_ids[start:end]]
            start = end
            end += student_per_group
            student_list.append(current_list)
        return student_list
