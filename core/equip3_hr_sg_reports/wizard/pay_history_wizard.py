from datetime import datetime
from dateutil.relativedelta import relativedelta as rv

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from collections import defaultdict


class HrSgPayHistoryReport(models.TransientModel):
    _name = 'pay.history.report'
    _description = "Pay History"

    pay_history_by = fields.Selection([
        ('by_employee', 'By Employee'),
        ('by_company', 'By Company')
    ], default='by_employee', string='Pay History By')
    all_employees = fields.Boolean(string='All Employees', default=False)
    employee_ids = fields.Many2many(
        comodel_name='hr.employee',
        string='Employee'
    )
    from_date = fields.Date(
        string='From Date',
        default=lambda self: fields.Date.today()
    )
    to_date = fields.Date(
        string='To Date',
        default=lambda self: fields.Date.today()
    )
    all_salary_rules = fields.Boolean(string='All Salary Rules', default=False)
    salary_rule_ids = fields.Many2many(
        comodel_name='hr.salary.rule',
        string='Salary Rule',
    )
    salary_rule_domain_ids = fields.Many2many(
        'hr.salary.rule', 'name', 'code', 'category_id',
        string='Salary Rule Domain',
    )

    @api.onchange('pay_history_by', 'from_date', 'to_date')
    def _onchange_salary_rule_ids(self):
        if self.pay_history_by == 'by_company' and not self.salary_rule_ids:
            company_id = self.env.user.company_id.id
            employee_ids = self.env['hr.employee'].search(
                [('company_id', '=', company_id)]).ids
            from_month_first, to_month_end = self.get_period_ranges(self.from_date, self.to_date)
            payslips = self.env['hr.payslip'].search([
                ('employee_id', 'in', employee_ids),
                ('state', '=', 'done'),
                ('date_from', '>=', from_month_first),
                ('date_from', '<=', to_month_end),
            ], order='date_from desc')

            all_salary_rules_applied = []
            for payslip in payslips:
                for line in payslip.line_ids.filtered(lambda pl: pl.salary_rule_id is not False):
                    if line.salary_rule_id.id not in all_salary_rules_applied:
                        all_salary_rules_applied.append(line.salary_rule_id.id)

            self.salary_rule_domain_ids = [(6, 0, all_salary_rules_applied)]
    
    @api.constrains('pay_history_by')
    def _check_pay_history_by(self):
        if not self.pay_history_by:
            raise ValidationError("The pay histor by field cannot be empty!")

    @api.constrains('employee_ids')
    def _check_contraint_employee_ids(self):
        from_month_first, to_month_end = self.get_period_ranges(self.from_date, self.to_date)
        if self.employee_ids and self.pay_history_by == 'by_employee' and not self.all_employees:
            for employee in self.employee_ids:
                payslips = self.env['hr.payslip'].search([
                    ('employee_id', '=', employee.id),
                    ('date_from', '>=', from_month_first),
                    ('date_from', '<=', to_month_end),
                    ('state', '=', 'done'),
                ])
                if not payslips:
                    raise ValidationError(
                        'There is no payslip details for employee %s' % (employee.name))
        elif self.pay_history_by == 'by_employee' and self.all_employees:
            company_id = self.env.user.company_id.id
            employee_ids = self.env['hr.employee'].search(
                [('company_id', '=', company_id)]
            ).ids
            payslips = self.env['hr.payslip'].search([
                ('employee_id', 'in', employee_ids),
                ('date_from', '>=', from_month_first),
                ('date_from', '<=', to_month_end),
                ('state', '=', 'done'),
            ])
            if not payslips:
                raise ValidationError(
                    'There is no payslip details in selected date')
        elif not self.employee_ids and not self.all_employees and self.pay_history_by == 'by_employee':
            raise ValidationError("Please select employee first!")

    @api.constrains('salary_rule_ids')
    def _check_salary_rule_ids(self):
        if self.pay_history_by == 'by_company' and not self.all_salary_rules and not self.salary_rule_ids:
            raise ValidationError("Please select salary rule first!")

    @api.constrains('from_date', 'to_date')
    def _check_date_ranges(self):
        for rec in self:
            if not rec.from_date and not rec.to_date:
                raise ValidationError("The to date and from date field cannot be empty!")
            elif rec.to_date < rec.from_date:
                raise ValidationError("The to date must be greater than from date!")
    
    def get_period_ranges(self, from_date, to_date):
        from_date_first_of_month = from_date.replace(day=1)
        to_date_end_of_month = (to_date + rv(day=31)).replace(day=to_date.day)

        return from_date_first_of_month, to_date_end_of_month

    def get_employees(self):
        if not self.all_employees:
            employee_ids = self.employee_ids.ids
            return employee_ids
        elif self.all_employees or self.pay_history_by == 'by_company':
            company_id = self.env.user.company_id.id
            employee_ids = self.env['hr.employee'].search(
                [('company_id', '=', company_id)]
            ).ids
            return employee_ids

    def get_report_data(self):
        pay_histories = {}
        month_dict = {
            '1': 'January', '2': 'February', '3': 'March',
            '4': 'April', '5': 'May', '6': 'June',
            '7': 'July', '8': 'August', '9': 'September',
            '10': 'October', '11': 'November', '12': 'December'
        }
        from_date_year, from_date_month, _ = self.from_date.strftime(
            DEFAULT_SERVER_DATE_FORMAT).split('-')
        to_date_year, to_date_month, _ = self.to_date.strftime(
            DEFAULT_SERVER_DATE_FORMAT).split('-')
        from_month_first, to_month_end = self.get_period_ranges(self.from_date, self.to_date)
        if self.pay_history_by == 'by_employee':
            employee_ids = self.get_employees()
            payslips = self.env['hr.payslip'].search([
                ('employee_id', 'in', employee_ids),
                ('date_from', '>=', from_month_first),
                ('date_from', '<=', to_month_end),
                ('state', '=', 'done'),
            ], order='date_from desc')

            for payslip in payslips:
                employee_id = str(payslip.employee_id.id)
                pay_histories[employee_id] = {
                    'employee_id': payslip.employee_id.identification_id,
                    'employee_name': payslip.employee_id.name,
                    'pay_history_by': 'EMPLOYEE',
                    'period_from': '%s%s' % (from_date_year, from_date_month,),
                    'period_to': '%s%s' % (to_date_year, to_date_month,),
                    'department': payslip.employee_id.department_id.name,
                    'payslip_data': {month: {} for month in month_dict.values()},
                    'line_names': []
                }

            for payslip in payslips:
                employee_id = str(payslip.employee_id.id)
                month_key = payslip.date_from.strftime(
                    DEFAULT_SERVER_DATE_FORMAT).split('-')[1]

                pay_histories[employee_id]['line_names'] += [
                    line.name for line in payslip.line_ids.filtered(
                        lambda pl: pl.salary_rule_id is not False and
                        pl.name not in pay_histories[employee_id]['line_names']
                    )
                ]

                for line in payslip.line_ids.filtered(lambda pl: pl.salary_rule_id is not False):
                    pay_histories[employee_id]['payslip_data'][month_dict.get(
                        str(int(month_key)))][line.name] = line.total

            if payslips:
                pay_histories[employee_id]['line_names'] = list(
                    dict.fromkeys(pay_histories[employee_id]['line_names']))

        elif self.pay_history_by == 'by_company':
            company_id = self.env.user.company_id.id
            employee_ids = self.env['hr.employee'].search(
                [('company_id', '=', company_id)]
            ).ids
            payslips = self.env['hr.payslip'].search([
                ('employee_id', 'in', employee_ids),
                ('date_from', '>=', from_month_first),
                ('date_from', '<=', to_month_end),
                ('state', '=', 'done'),
            ], order='date_from desc')

            pay_histories['company'] = {
                'employee_id': None,
                'employee_name': 'Company Total',
                'period_from': '%s%s' % (from_date_year, from_date_month,),
                'period_to': '%s%s' % (to_date_year, to_date_month,),
                'pay_history_by': 'COMPANY',
                'department': 'All Departments',
                'payslip_data': {month: {} for month in month_dict.values()},
                'line_names': []
            }

            all_salary_rules_applied = []
            for payslip in payslips:
                for line in payslip.line_ids.filtered(lambda pl: pl.salary_rule_id is not False):
                    if line.name not in all_salary_rules_applied:
                        all_salary_rules_applied.append(line.name)

            if self.all_salary_rules:
                pay_histories['company']['line_names'] += all_salary_rules_applied
            else:
                pay_histories['company']['line_names'] += [
                    line.name for line in self.salary_rule_ids.filtered(
                        lambda r: r.name not in pay_histories['company']['line_names']
                    )
                ]

            for payslip in payslips:
                month_key = payslip.date_from.strftime(
                    DEFAULT_SERVER_DATE_FORMAT).split('-')[1]

                for line in payslip.line_ids.filtered(lambda pl: pl.salary_rule_id is not False):
                    pay_histories['company']['payslip_data'][month_dict.get(
                        str(int(month_key)))][line.name] = pay_histories['company']['payslip_data'][month_dict.get(
                            str(int(month_key)))].get(line.name, 0) + line.total

            pay_histories['company']['line_names'] = list(
                dict.fromkeys(pay_histories['company']['line_names']))

        pay_histories_list = list(pay_histories.values())
        return pay_histories_list

    def action_print(self):
        report_id = self.env.ref('equip3_hr_sg_reports.pay_history_report_pdf')
        from_date_year, _, _ = self.from_date.strftime(
            DEFAULT_SERVER_DATE_FORMAT
        ).split('-')
        file_name = False

        if self.pay_history_by == 'by_employee':
            file_name = "'Pay History Report By Employee %s'" % (from_date_year)
        else:
            file_name = "'Pay History Report By Company %s'" % (from_date_year)
        
        report_id.write({'print_report_name': file_name})
        return report_id.report_action(self)
