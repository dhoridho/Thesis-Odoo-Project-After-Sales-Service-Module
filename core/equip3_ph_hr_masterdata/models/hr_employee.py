from odoo import _, api, fields, models


class HrEmployeeInherit(models.Model):
    _inherit = "hr.employee"

    employee_id = fields.Char(string="Employee ID")
    tin = fields.Char(string="TIN", help="Tax Identification Number")
    sss_number = fields.Char(string="SSS Number", help="Social Security System")
    philhealth_number = fields.Char(
        string="Philhealth Number", help="Philippine Health Insurance Corporation"
    )
    pag_ibig_number = fields.Char(string="Pag-IBIG Number")
