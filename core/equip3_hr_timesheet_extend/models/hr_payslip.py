# -*- coding: utf-8 -*-
from odoo import models, fields, api, tools, _

class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def get_timesheet_hour(self, payslip, date_from, date_to):
        payslip_rec = self.sudo().browse(payslip)[0]
        timesheet_line = self.env['hr.timesheet.line'].search([('employee_id', '=', payslip_rec.employee_id.id),('date','>=',date_from),('date','<=',date_to),('state','=','approved')])
        total_hour = 0.0
        for rec in timesheet_line:
            total_hour += rec.unit_amount
        return total_hour
