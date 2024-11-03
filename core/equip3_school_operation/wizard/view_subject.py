from odoo import _, models, fields, api


class ViewSubject(models.Model):
    _name = 'view.subject'
    _description = "View Subject"
    _rec_name = "school_id"

    academic_id = fields.Many2one('generate.academic', string='Generate Academic')
    academic_student_id = fields.Many2one('generate.academic.student', string='Generate Academic Student')
    school_id = fields.Many2one('school.school', related='academic_id.school_id', string='School')
    program_id = fields.Many2one('standard.standard', related='academic_id.program_id', string='Program',
                                 domain="[('school_id', '=', school_id)]", readonly=True)
    intake_id = fields.Many2one('school.standard', related='academic_id.intake', string='Intake', readonly=True)
    academic_year_id = fields.Many2one('academic.year', related='academic_id.academic_year_id', string='Academic Year',
                                       readonly=True)
    term_id = fields.Many2one('academic.month', related='academic_id.term_id', string='Term',
                              domain="[('year_id', '=', academic_year_id)]", readonly=True)
    view_subject_ids = fields.One2many("view.subject.line", 'view_subject_id', string="Subject")

    def save_view_subject(self):
        self.academic_student_id.view_subject_id = self.id

    @api.onchange('intake_id')
    def _onchange_intake_id(self):
        data = [(5, 0, 0)]
        if self.intake_id and self.intake_id.intake_subject_line_ids:
            for student in self.intake_id.intake_subject_line_ids.filtered(
                    lambda r: r.year_id.id == self.academic_year_id.id and r.term_id.id == self.term_id.id):
                data.append((0, 0, {
                    'ems_subject_id': student.id,
                    'core_subject_id': student.subject_id.id,
                    'status': self.academic_student_id.status
                }))
        self.view_subject_ids = data


class ViewSubjectLine(models.Model):
    _name = 'view.subject.line'
    _description = "View Subject Line"

    view_subject_id = fields.Many2one("view.subject", string="View Subject")
    ems_subject_id = fields.Many2one('ems.subject', string='Ems Subject')
    core_subject_id = fields.Many2one("subject.subject", string="Core Subject")
    elective_subject_ids = fields.Many2one("subject.subject", string="Elective Subject")
    status = fields.Selection([('pass', 'Pass'), ('fail', 'Fail')], string='Status', default='pass')
