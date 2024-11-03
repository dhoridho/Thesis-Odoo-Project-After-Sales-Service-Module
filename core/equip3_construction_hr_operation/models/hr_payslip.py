from odoo import models, fields, api
from datetime import datetime, timedelta, time
from odoo.exceptions import UserError, ValidationError


class HRPayslip(models.Model):
    _inherit = 'hr.payslip'

    def get_construction_basic_salary(self, payslip, date_from, date_to):
        total = 0
        self.env.cr.execute("""
                                SELECT SUM(labour_amount) FROM account_analytic_line WHERE employee_id = '%s' and date BETWEEN '%s' AND '%s' 
                            """ % (payslip.employee_id, date_from, date_to))
        query_result = self.env.cr.fetchall()
        if query_result:
            if query_result[0][0]:
                total = query_result[0][0]

        return total

    def get_construction_attendance_basic_salary(self, payslip, date_from, date_to):
        total = 0
        self.env.cr.execute("""
                                SELECT SUM(hourly_rate * worked_hours) FROM hr_attendance WHERE employee_id = '%s' and active = TRUE and start_working_date BETWEEN '%s' AND '%s' 
                            """ % (payslip.employee_id, date_from, date_to))
        query_result = self.env.cr.fetchall()
        if query_result:
            if query_result[0][0]:
                total = query_result[0][0]
        return total

    def action_payslip_done(self):
        res = super(HRPayslip, self).action_payslip_done()
        for rec in self:
            rec.set_labour_actual_used_amount(1)
        return res

    def refund_sheet(self):
        res = super(HRPayslip, self).refund_sheet()
        for rec in self:
            rec.set_labour_actual_used_amount(-1)
            rec.set_labour_actual_used_amount(-1)
        return res

    def set_labour_actual_used_amount(self, sign):
        for rec in self:
            if rec.struct_id.code == "CONS_ATT_STR":
                attendances = self.env['hr.attendance'].search([('employee_id', '=', rec.employee_id.id),
                                                                ('start_working_date', '>=', rec.date_from),
                                                                ('start_working_date', '<=', rec.date_to)])
                budget_ids = []
                for attendance in attendances:
                   if len(attendance.project_id) > 0:
                       labour_usage_line = attendance.project_task_id.labour_usage_ids.filtered(
                            lambda x: x.group_of_product_id == attendance.group_of_product_id and
                                      x.product_id == attendance.product_id and attendance.employee_id.id in x.workers_ids.ids)
                       if len(labour_usage_line) > 0:
                            cost_sheet_line = labour_usage_line.cs_labour_id
                            budget_line = labour_usage_line.bd_labour_id

                            if cost_sheet_line:
                                cost_sheet_line.actual_used_amt += attendance.rate_amount * sign
                                cost_sheet_line.actual_used_time += (attendance.rate_amount/cost_sheet_line.price_unit) * sign
                                cost_sheet_line.reserved_amt += attendance.rate_amount * (-sign)
                                cost_sheet_line.reserved_time += (attendance.rate_amount/cost_sheet_line.price_unit) * (-sign)

                                cost_sheet_line.job_sheet_id.get_gop_labour_table()

                                if budget_line:
                                    budget_line.amt_used += attendance.rate_amount * sign
                                    budget_line.time_used += (attendance.rate_amount/cost_sheet_line.price_unit) * sign
                                    budget_line.amt_res += attendance.rate_amount * (-sign)
                                    budget_line.reserved_time += (attendance.rate_amount/cost_sheet_line.price_unit) * (-sign)

                                    if cost_sheet_line.job_sheet_id.budgeting_method == 'gop_budget':
                                        if budget_line.budget_id not in budget_ids:
                                            budget_ids.append(budget_line.budget_id)

                for budget in budget_ids:
                    budget.get_gop_labour_table()

            elif rec.struct_id.code == "CONS_STR":
                timesheets = self.env['account.analytic.line'].search([('employee_id', '=', rec.employee_id.id),
                                                                       ('date', '>=', rec.date_from),
                                                                       ('date', '<=', rec.date_to)])
                budget_ids = []
                for timesheet in timesheets:
                    if timesheet.labour_name:
                        labour_keyword = timesheet.labour_name.split(" - ")
                        labour_usage_line = timesheet.task_id.labour_usage_ids.filtered(
                            lambda x: x.project_scope_id.name == labour_keyword[0] and
                                      x.section_id.name == labour_keyword[1] and
                                      x.product_id.name == labour_keyword[2])

                        if labour_usage_line:
                            cost_sheet_line = labour_usage_line.cs_labour_id
                            budget_line = labour_usage_line.bd_labour_id

                            if cost_sheet_line:
                                time = 0
                                if cost_sheet_line.uom_id.name == 'Days':
                                    time = timesheet.duration/60/timesheet.task_id.project_id.working_hour_hours
                                elif cost_sheet_line.uom_id.name == 'Hours':
                                    time = timesheet.duration/60

                                cost_sheet_line.actual_used_amt += timesheet.labour_amount * sign
                                cost_sheet_line.actual_used_time += time * sign
                                cost_sheet_line.reserved_amt += timesheet.labour_amount * (-sign)
                                cost_sheet_line.reserved_time += time * (-sign)

                                cost_sheet_line.job_sheet_id.get_gop_labour_table()

                                if budget_line:
                                    budget_line.amt_used += timesheet.labour_amount * sign
                                    budget_line.time_used += time * sign
                                    budget_line.amt_res += timesheet.labour_amount * (-sign)
                                    budget_line.reserved_time += time * (-sign)

                                    if cost_sheet_line.job_sheet_id.budgeting_method == 'gop_budget':
                                        if budget_line.budget_id not in budget_ids:
                                            budget_ids.append(budget_line.budget_id)

                for budget in budget_ids:
                    budget.get_gop_labour_table()


class HRPlaySlipRun(models.Model):
    _inherit = 'hr.payslip.run'

    def confirm_all_payslips(self):
        res = super(HRPlaySlipRun, self).confirm_all_payslips()
        for rec in self:
            for payslip in rec.slip_ids:
                payslip.set_labour_actual_used_amount(1)
        return res

    def action_refund_payslips(self):
        res = super(HRPlaySlipRun, self).action_refund_payslips()
        for rec in self:
            for payslip in rec.slip_ids:
                payslip.set_labour_actual_used_amount(-1)
        return res
