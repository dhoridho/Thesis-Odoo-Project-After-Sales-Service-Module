from odoo import models, fields, api


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    @api.depends('employee_id.user_id', 'date_from', 'date_to', 'employee_id')
    def _get_salary_computation_ytd_total(self):
        user = self.env['res.users'].browse(self._uid)
        year_start_date = user.company_id.period_start or False
        year_end_date = user.company_id.period_end or False
        for data in self:
            total_ytd_gross = 0.0
            total_ytd_bonus = 0.0
            total_ytd_allowance = 0.0
            total_ytd_cpf_employee = 0.0
            total_ytd_cpf_employer = 0.0
            al_leave_balance = 0.0
            if year_start_date and year_end_date:
                domain = [('employee_id', '=', data.employee_id.id),
                          ('date_from', '>=', year_start_date),
                          ('date_to', '<=', year_end_date)]
                payslip_ids = self.env['hr.payslip'].search(domain)
                for payslip in payslip_ids:
                    leave_cofig = payslip.employee_id.leave_config_id
                    if leave_cofig:
                        for leave in leave_cofig.holiday_group_config_line_ids:
                            if leave.leave_type_id.name == 'AL':
                                leave_days = \
                                    leave.leave_type_id.get_employees_days(
                                        [payslip.employee_id.id])
                                al_leave_balance = leave_days.get(
                                    'virtual_remaining_leaves')
                    for line in payslip.line_ids:
                        if line.category_id.code == 'GROSS':
                            total_ytd_gross += line.total
                        if line.code == 'SC121':
                            total_ytd_bonus += line.total
                        if line.category_id.code == 'ALW':
                            total_ytd_allowance += line.total
                        if line.category_id.code == 'CAT_CPF_EMPLOYEE':
                            total_ytd_cpf_employee += line.total
                        if line.category_id.code == 'CAT_CPF_EMPLOYER':
                            total_ytd_cpf_employer += line.total
            data.total_ytd_gross = total_ytd_gross
            data.total_ytd_bonus = total_ytd_bonus
            data.total_ytd_allowance = total_ytd_allowance
            data.total_ytd_cpf_employee = total_ytd_cpf_employee
            data.total_ytd_cpf_employer = total_ytd_cpf_employer
            data.al_leave_balance = al_leave_balance

    total_ytd_gross = fields.Float(
                    compute=_get_salary_computation_ytd_total,
                    string='Total YTD Gross',
                    help="Total YTD(Year To Date Gross amount")
    total_ytd_bonus = fields.Float(
                    compute=_get_salary_computation_ytd_total,
                    string="Total YTD Bonus",
                    help="Total YTD(Year to Date Bonus amount)")
    total_ytd_allowance = fields.Float(
                    compute=_get_salary_computation_ytd_total,
                    string="Total YTD Allowance",
                    help="Total YTD(Year to Date Allowance amount)")
    total_ytd_cpf_employee = fields.Float(
                    compute=_get_salary_computation_ytd_total,
                    string="Total YTD CPF Employee",
                    help="Total YTD(Year to Date CPF Employee amount)")
    total_ytd_cpf_employer = fields.Float(
                    compute=_get_salary_computation_ytd_total,
                    string="Total YTD CPF Employer",
                    help="Total YTD(Year to Date CPF Employer amount)")
    al_leave_balance = fields.Float(
                    compute=_get_salary_computation_ytd_total,
                    string="Total AL Leave Balance",
                    help="Total AL Leave Balance")
