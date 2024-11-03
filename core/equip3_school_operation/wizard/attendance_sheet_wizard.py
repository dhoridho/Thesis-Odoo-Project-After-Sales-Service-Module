from odoo import fields, models, api


class MonthlyAttendanceSheet(models.TransientModel):

    _inherit = "monthly.attendance.sheet"

    program_id = fields.Many2one('standard.standard', string='Program', required=True)
    intake_id = fields.Many2one('school.standard', string="Intake", required=False)
    school_id = fields.Many2one('school.school', string='School')
    standard_id = fields.Many2one(
        "school.standard", "Academic Class", required=False
    )

class MonthlyAttendance(models.TransientModel):

    _name = "monthly.attendance"

    program_id = fields.Many2one('standard.standard', string='Program')
    intake_id = fields.Many2one('school.standard', string="Intake")
    school_id = fields.Many2one('school.school', string='School')
    year_id = fields.Many2one("academic.year", "Academic Year")
    month_id = fields.Many2one("academic.month", "Term")