from odoo import api, fields, models, _


class HrPayslipLateDeduction(models.Model):
    _name = "hr.payslip.late.deduction"
    _description = "Late Deduction"

    date_check_in = fields.Date("Date Check In")
    number_of_hours = fields.Float("Number Of Hours")
    amount = fields.Float("Amount")
    payslip_id = fields.Many2one("hr.payslip", string="Payslip")