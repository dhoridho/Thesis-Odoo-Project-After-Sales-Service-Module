from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError


class GenerateAcademic(models.Model):
    _name = "generate.academic"
    _rec_name = "academic_year_id"
    _order = "create_date desc"

    @api.model
    def _domain_school(self):
        allowed_branch_ids = self.env.branches.ids
        return [("school_branch_ids", "in", allowed_branch_ids)]

    academic_year_id = fields.Many2one('academic.year', string='Academic Year', required=True)
    term_id = fields.Many2one('academic.month', string='Term', required=True, domain="[('year_id', '=', academic_year_id)]")
    school_id = fields.Many2one('school.school', string='School', required=True, domain=_domain_school)
    program_id = fields.Many2one('standard.standard', string='Program', domain="[('school_id', '=', school_id)]", required=True)
    intake = fields.Many2one('school.standard', string='Intake', required=True, domain="[('standard_id', '=', program_id)]")
    student_ids = fields.One2many('generate.academic.student', 'academic_id', string='Generate Academic Student')
    state = fields.Selection([('draft', 'Draft'), ('moved', 'Moved')], string='State', default='draft')

    def button_move(self):
        for record in self:
            for student in record.student_ids:
                academic_tracking_id = self.env['academic.tracking'].search([
                        ('student_id', '=', student.student_id.id),
                        ('program_id', '=', record.program_id.id),
                        ('school_id', '=', record.school_id.id),
                    ], limit=1
                )
                if student.status == 'fail':
                    if not student.failed_intake_id:
                        raise UserError(_("Next intake cannot be empty!"))

                    student.student_id.history_ids.write({
                        'status': 'unactive'
                    })

                    student.student_id.write({
                        'standard_id': student.failed_intake_id.id,
                        'history_ids': [(0, 0, {
                            'academice_year_id': record.academic_year_id.id,
                            'school_id': record.school_id.id or False,
                            'program_id': record.program_id.id or False,
                            'standard_id': student.failed_intake_id.id or False,
                            'fees_ids': record.program_id.fees_ids.id or False,
                            'status': 'active',
                        })]
                    })

                if not academic_tracking_id:
                    academic_tracking_vals = {
                        "student_id": (
                            student.student_id.id
                            if student.student_id.student_type == "new_student"
                            else student.student_id.student_id.id
                        ),
                        "program_id": record.program_id.id,
                        "school_id": record.school_id.id,
                    }
                    academic_tracking_id = self.env['academic.tracking'].create(academic_tracking_vals)
                else:
                    if student.status == 'fail':
                        academic_tracking_id.intake_ids.write({
                            'status': 'unactive'
                        })
                        academic_tracking_id.all_score_subject_ids.write({
                            'subject_status': 'unactive',
                        })

                academic_tracking_vals = {}
                academic_tracking_id.current_score_subject_ids.write({
                    'subject_status': 'unactive',
                })

                if student.status == 'fail':
                    ems_ids = student.failed_intake_id.intake_subject_line_ids.filtered(
                        lambda x: x.year_id == record.academic_year_id
                        and x.term_id == record.term_id
                        and x.year_id.current == True
                        and x.term_id.checkactive == True
                    )
                    academic_tracking_vals.update({
                        'intake_ids': [(0, 0, {
                            'intake_id': student.failed_intake_id.id,
                            'status': 'active',
                        })],
                        'all_score_subject_ids': [(0, 0, {
                            'intake_id': student.failed_intake_id.id,
                            'year': subject.year,
                            'subject_id': subject.subject_id and subject.subject_id.id or False,
                            'year_id': subject.year_id and subject.year_id.id or False,
                            'term_id': subject.term_id and subject.term_id.id or False,
                            'subject_status': 'active',
                        }) for subject in student.failed_intake_id.intake_subject_line_ids],
                        'current_score_subject_ids': [(0, 0, {
                            'year': ems_id.year,
                            'subject_id': ems_id.subject_id and ems_id.subject_id.id or False,
                            'year_id': ems_id.year_id and ems_id.year_id.id or False,
                            'term_id': ems_id.term_id and ems_id.term_id.id or False,
                            'subject_status': 'active',
                            }) for ems_id in ems_ids]
                    })
                academic_tracking_id.pass_score_subject_ids.write({
                    'subject_status': 'unactive',
                })
                academic_tracking_id.failed_score_subject_ids.write({
                    'subject_status': 'unactive',
                })

                if not student.view_subject_id:
                    ems_ids = record.intake.intake_subject_line_ids.filtered(
                        lambda x: x.year_id == record.academic_year_id
                        and x.term_id == record.term_id
                        and x.year_id.current == True
                        and x.term_id.checkactive == True
                    )
                    academic_tracking_vals.update(
                        {
                            "pass_score_subject_ids": [
                                (
                                    0,
                                    0,
                                    {
                                        "year": subject.year,
                                        "subject_id": subject.subject_id and subject.subject_id.id or False,
                                        "year_id": subject.year_id and subject.year_id.id or False,
                                        "term_id": subject.term_id and subject.term_id.id or False,
                                        "subject_status": "active",
                                    },
                                )
                                for subject in record.intake.intake_subject_line_ids.filtered(
                                    lambda r: r.year_id.id == record.academic_year_id.id
                                    and r.term_id.id == record.term_id.id
                                )
                            ],
                            "current_score_subject_ids": [
                                (
                                    0,
                                    0,
                                    {
                                        "year": ems_id.year,
                                        "subject_id": ems_id.subject_id and ems_id.subject_id.id or False,
                                        "year_id": ems_id.year_id and ems_id.year_id.id or False,
                                        "term_id": ems_id.term_id and ems_id.term_id.id or False,
                                        "subject_status": "active",
                                    },
                                )
                                for ems_id in ems_ids
                            ],
                        }
                    )
                else:
                    pass_subject_ids = student.view_subject_id.view_subject_ids.filtered(lambda r: r.status == 'pass')
                    fail_subject_ids = student.view_subject_id.view_subject_ids.filtered(lambda r: r.status == 'fail')
                    if pass_subject_ids:
                        p_subject_ids = pass_subject_ids.mapped('ems_subject_id').ids
                        academic_tracking_vals.update({
                            'pass_score_subject_ids': [(0, 0, {
                                'year': subject.year,
                                'subject_id': subject.subject_id and subject.subject_id.id or False,
                                'year_id': subject.year_id and subject.year_id.id or False,
                                'term_id': subject.term_id and subject.term_id.id or False,
                                'subject_status': 'active',
                            }) for subject in record.intake.intake_subject_line_ids.filtered(lambda r: r.id in p_subject_ids)]
                        })
                    if fail_subject_ids:
                        f_subject_ids = fail_subject_ids.mapped('ems_subject_id').ids
                        academic_tracking_vals.update({
                            'failed_score_subject_ids': [(0, 0, {
                                'year': subject.year,
                                'subject_id': subject.subject_id and subject.subject_id.id or False,
                                'year_id': subject.year_id and subject.year_id.id or False,
                                'term_id': subject.term_id and subject.term_id.id or False,
                                'subject_status': 'active',
                            }) for subject in record.intake.intake_subject_line_ids.filtered(lambda r: r.id in f_subject_ids)]
                        })
                academic_tracking_id.write(academic_tracking_vals)

            record.state = 'moved'

    @api.onchange('intake')
    def _onchange_intake(self):
        data = [(5, 0, 0)]
        if self.intake and self.intake.student_ids:
            for student in self.intake.student_ids:
                data.append((0, 0, {
                    'student_id': student.id,
                }))
        self.student_ids = data

class GenerateAcademicStudent(models.Model):
    _name = 'generate.academic.student'

    academic_id = fields.Many2one('generate.academic', string='Generate Academic')
    intake_id = fields.Many2one(related='academic_id.intake')
    student_id = fields.Many2one('student.student', string='Student')
    status = fields.Selection([('pass', 'Pass'), ('fail', 'Fail')], string='Status', default='pass')
    program_id = fields.Many2one('standard.standard', string='Program', related='academic_id.program_id', store=True)
    failed_intake_id = fields.Many2one('school.standard', string='Next Intake', domain="[('standard_id', '=', program_id), ('id', '!=', intake_id)]")
    view_subject_id = fields.Many2one('view.subject', string='View Subject')

    @api.onchange('status')
    def _onchange_status(self):
        self.failed_intake_id = False
        self.view_subject_id = False

    def subject_details(self):
        context = dict(self.env.context) or {}
        context.update({
            'default_academic_id': self.academic_id.id,
            'default_academic_student_id': self.id,
        })
        if self.view_subject_id:
            return {
                'type': 'ir.actions.act_window',
                'name': _('View'),
                'res_model': 'view.subject',
                'view_mode': 'form',
                'res_id': self.view_subject_id.id,
                'context': context,
                "target": "new",
            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': _('View'),
                'res_model': 'view.subject',
                'view_mode': 'form',
                'context': context,
                "target": "new",
            }
