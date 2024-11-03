from datetime import datetime, timedelta

from odoo import api, fields, models, tools, _
from odoo import tools
from odoo.exceptions import ValidationError

import logging
_logger = logging.getLogger(__name__)


class PayrollVarianceReport(models.TransientModel):

    _name = "payroll.variance.report"
    _description = "Payroll Variance Report"

    name = fields.Char('name')
    # Fields
    payroll_variance_by = fields.Selection([
        ('basic_salary', 'By Basic Salary'),
        ('by_company', 'By Company')
        ], string='Payroll Variance By', default='basic_salary', required=True)
    all_employees = fields.Boolean(
        string='All Employees',
        help='Visible if Payroll Variance By = By Basic Salary')
    employee_ids = fields.Many2many(
        'hr.employee',
        string='Employees',
        help='Visible if Payroll Variance By = By Basic Salary and All Employees = False')
    date = fields.Date(
        string='Current Month',
        # required=True, default=lambda self: fields.Datetime.now())
        default=lambda self: fields.Date.today())
    previous_date = fields.Date(
        string='Previous Month',
        required=True,
        compute='_compute_previous_date',
        help='Autofills from selected Current Month. Editable by the user.')
    all_salary_rules = fields.Boolean(
        string='All Salary Rules',
        help='Visible if Payroll Variance By = By Company',
        default=False)
    salary_rule_ids = fields.Many2many(
        'hr.salary.rule',
        string='Salary Rules',
        help='Visible if Payroll Variance By = By Company and All Salary Rules = False')
    salary_rule_domain_ids = fields.Many2many(
        'hr.salary.rule', 'name', 'category_id', 'code', 
        string='Salary Rule Domain'
    )

    @api.onchange('payroll_variance_by', 'date', 'previous_date', 'all_salary_rules')
    def _onchange_get_salary_rule_domain_ids(self):
        domain = []
        domain = [('state', '=', 'done')]

        if not self.all_employees:
            domain += [('employee_id', 'in', self.employee_ids.ids)]

        prev_date_from, prev_date_to = self._compute_first_last_dates(self.previous_date)
        prev_period_date_domain = [('date_from', '>=', prev_date_from), ('date_to', '<=', prev_date_to)]
        
        curr_date_from, curr_date_to = self._compute_first_last_dates(self.date)
        curr_period_date_domain = [('date_from', '>=', curr_date_from), ('date_to', '<=', curr_date_to)]

        prev_payslips = self.env['hr.payslip'].search(domain + prev_period_date_domain)
        curr_payslips = self.env['hr.payslip'].search(domain + curr_period_date_domain)
        
        available_salary_rule_ids = []

        if self.payroll_variance_by == 'by_company' and not self.all_salary_rules:
            for x in prev_payslips:
                for y in x.line_ids:
                    if y.salary_rule_id.id not in available_salary_rule_ids:
                        available_salary_rule_ids.append(y.salary_rule_id.id)

            for x in curr_payslips:
                for y in x.line_ids:
                    if y.salary_rule_id.id not in available_salary_rule_ids:
                        available_salary_rule_ids.append(y.salary_rule_id.id)
        
            self.salary_rule_domain_ids = [(6, 0, available_salary_rule_ids)]

    @api.depends('date')
    def _compute_previous_date(self):
        if self.date:
            current_date = self.date.day
            current_month_with_same_day = self.date.replace(day=current_date)
            previous_month_with_same_day = current_month_with_same_day - timedelta(days=30)
            self.previous_date = previous_month_with_same_day

    @api.onchange('payroll_variance_by')
    def _onchange_payroll_variance_by(self):
        if self.payroll_variance_by:
            if self.payroll_variance_by == 'basic_salary':
                self.all_employees = True
                self.all_salary_rules = False
            elif self.payroll_variance_by == 'by_company':
                self.all_employees = True
                self.all_salary_rules = True

    def _compute_first_last_dates(self, date):
        # Get the first day of the month
        first_day = date.replace(day=1)
        first_date_of_month = fields.Date.to_string(first_day)

        # Calculate the last day of the month
        last_day = (
                datetime(date.year, date.month, 1) +
                timedelta(days=32)
            ).replace(day=1) - timedelta(days=1)

        last_date_of_month = fields.Date.to_string(last_day)

        return first_date_of_month, last_date_of_month

    def action_print(self):
        report_id = self.env.ref('equip3_hr_sg_reports.payroll_variance_report')
        data = {}
        data_lines_dict = {}
        domain = []
        domain = [('state', '=', 'done')]

        if not self.all_employees:
            domain += [('employee_id', 'in', self.employee_ids.ids)]

        prev_date_from, prev_date_to = self._compute_first_last_dates(self.previous_date)
        prev_period_date_domain = [('date_from', '>=', prev_date_from), ('date_to', '<=', prev_date_to)]
        
        curr_date_from, curr_date_to = self._compute_first_last_dates(self.date)
        curr_period_date_domain = [('date_from', '>=', curr_date_from), ('date_to', '<=', curr_date_to)]

        prev_payslips = self.env['hr.payslip'].search(domain + prev_period_date_domain)
        curr_payslips = self.env['hr.payslip'].search(domain + curr_period_date_domain)

        if self.payroll_variance_by == 'basic_salary':
            for x in prev_payslips:
                if data_lines_dict.get(x.employee_id.name, False):
                    data_lines_dict[x.employee_id.name]['prev_period_salary'] += sum(x.line_ids.mapped('total'))
                else:
                    data_lines_dict[x.employee_id.name] = {
                        'emp_number' : '',
                        'emp_name' : x.employee_id.name,
                        'department' : x.employee_id.department_id.name,        
                        'prev_period_salary' : sum(x.line_ids.mapped('total')) ,
                        'curr_period_salary' : 0,
                    }

            for x in curr_payslips:
                if data_lines_dict.get(x.employee_id.name, False):
                    data_lines_dict[x.employee_id.name]['curr_period_salary'] += sum(x.line_ids.mapped('total'))
                else:
                    data_lines_dict[x.employee_id.name] = {
                        'emp_number' : '',
                        'emp_name' : x.employee_id.name,
                        'department' : x.employee_id.department_id.name,        
                        'prev_period_salary' : 0,
                        'curr_period_salary' : sum(x.line_ids.mapped('total')) ,
                    }
        else:
            for x in prev_payslips:
                for y in x.line_ids:
                    if y.salary_rule_id.id in self.salary_rule_ids.ids or self.all_salary_rules == True:
                        if data_lines_dict.get(y.salary_rule_id.name, False):
                            data_lines_dict[y.salary_rule_id.name]['prev_period_salary'] += y.total
                        else :
                            data_lines_dict[y.salary_rule_id.name] = {
                                'name' : y.salary_rule_id.name,
                                'prev_period_salary' : y.total,
                                'curr_period_salary' : 0 ,
                            }

            for x in curr_payslips:
                for y in x.line_ids:
                    if y.salary_rule_id.id in self.salary_rule_ids.ids or self.all_salary_rules == True:
                        if data_lines_dict.get(y.salary_rule_id.name, False):
                            data_lines_dict[y.salary_rule_id.name]['curr_period_salary'] += y.total
                        else :
                            data_lines_dict[y.salary_rule_id.name] = {
                                'name' : y.salary_rule_id.name,
                                'prev_period_salary' : 0,
                                'curr_period_salary' : y.total ,
                            }

        data['name'] = (
                'Payment Variance Report '
                + ('Comapared By Basic Salary' if self.payroll_variance_by == 'basic_salary' else 'By Company')
                + f' ({self.previous_date.strftime("%m/%Y")} vs {self.date.strftime("%m/%Y")})'
            )
        data['payroll_variance_by'] = self.payroll_variance_by
        data['prev_period'] = self.previous_date.strftime("%m/%Y")
        data['curr_period'] = self.date.strftime("%m/%Y")
        data['prev_total'] = sum([x['prev_period_salary'] for k, x in data_lines_dict.items()])
        data['curr_total'] = sum([x['curr_period_salary'] for k, x in data_lines_dict.items()])
        data['data_lines'] = data_lines_dict
        print_report_name = (
            'Payroll Variance By Basic Salary Report' 
            if self.payroll_variance_by == 'basic_salary' 
            else 'Payroll Variance By Company Report'
        )
        report_id.write({'name': print_report_name})
        return report_id.report_action(self, data=data)
