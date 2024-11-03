from odoo import _, api, fields, models

class SchoolTeacher(models.Model):
    _inherit = 'school.teacher'

    school_id = fields.Many2one(string="School")
    student_id = fields.Many2many(compute='_compute_student_id')

    def _compute_student_id(self):
        for rec in self:
            if rec.standard_id and rec.standard_id.intake_student_line_ids:
                rec.student_id = [(6, 0, rec.standard_id.intake_student_line_ids.mapped('student_id').ids)]
            else:
                rec.student_id = [(6, 0, [])]
