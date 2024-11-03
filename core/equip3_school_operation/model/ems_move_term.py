from odoo import api, fields, models, _

class EmsMoveTerm(models.Model):
    _name = 'ems.move.term'
    _description = "EMS Move Term"
    _rec_name = 'school_id'

    school_id = fields.Many2one('school.school', string='School', required=True)
    academic_year_id = fields.Many2one('academic.year', string='Academic Year', required=True)
    term_id = fields.Many2one('academic.month', string='Term', required=True)
    related_program_ids = fields.One2many('standard.standard', string='Program', related='school_id.school_program_ids')
    program_id = fields.Many2one('standard.standard', string='Program', required=True)
    intake_id = fields.Many2one('school.standard', string='Intake', required=True)
    state = fields.Selection([('draft', 'Draft'), ('moved', 'Moved')], default='draft')
    student_line_ids = fields.One2many('ems.move.term.student.line', 'move_term_id', string='Student')

    def button_move(self):
        return self.write({'state': 'moved'})

    @api.onchange('intake_id')
    def _onchange_intake_id(self):
        self.student_line_ids = [(5,0,0)] + [(0,0,{'move_term_id': self.id, 'student_id': s.id}) for s in self.intake_id.student_ids]

class EmsMoveTermStudentLine(models.Model):
    _name = 'ems.move.term.student.line'

    move_term_id = fields.Many2one('ems.move.term', string='Move Term')
    student_id = fields.Many2one('student.student', string='Student')
    current_term_id = fields.Many2one('academic.month', string='Current Term')
    update_term_id = fields.Many2one('academic.month', string='Update Term')
    current_intake_id = fields.Many2one('school.standard', string='Current Intake')
    update_intake_id = fields.Many2one('school.standard', string='Update Intake')