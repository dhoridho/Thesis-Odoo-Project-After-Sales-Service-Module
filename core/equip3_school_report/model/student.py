from odoo import _, api, fields, models


class StudentStudent(models.Model):
    _inherit = 'student.student'

    company_id = fields.Many2one('res.company', 'Company', readonly=True)
