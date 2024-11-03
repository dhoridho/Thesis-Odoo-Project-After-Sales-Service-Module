# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import date, datetime, time
from odoo.exceptions import UserError, ValidationError
from dateutil.relativedelta import relativedelta

class HrPayslipEmployees(models.TransientModel):
    _inherit = 'hr.payslip.employees'

    @api.model
    def get_contract(self, date_from, date_to):
        # a contract is valid if it ends between the given dates
        clause_1 = ['&', ('date_end', '<=', date_to), ('date_end', '>=', date_from)]
        # OR if it starts between the given dates
        clause_2 = ['&', ('date_start', '<=', date_to), ('date_start', '>=', date_from)]
        # OR if it starts before the date_from and finish after the date_end (or never finish)
        clause_3 = ['&', ('date_start', '<=', date_from), '|', ('date_end', '=', False), ('date_end', '>=', date_to)]
        clause_final = [('state', 'in', ['open','close']), '|',
                        '|'] + clause_1 + clause_2 + clause_3
        return self.env['hr.contract'].search(clause_final).ids
    
    @api.model
    def get_contract_employee(self, employee, date_from, date_to):
        # a contract is valid if it ends between the given dates
        clause_1 = ['&', ('date_end', '<=', date_to), ('date_end', '>=', date_from)]
        # OR if it starts between the given dates
        clause_2 = ['&', ('date_start', '<=', date_to), ('date_start', '>=', date_from)]
        # OR if it starts before the date_from and finish after the date_end (or never finish)
        clause_3 = ['&', ('date_start', '<=', date_from), '|', ('date_end', '=', False), ('date_end', '>=', date_to)]
        clause_final = [('employee_id', '=', employee.id), ('state', 'in', ['open']), '|',
                        '|'] + clause_1 + clause_2 + clause_3
        clause_finals = [('employee_id', '=', employee.id), ('state', 'in', ['close'])
                        ] + clause_1
        if self.env['hr.contract'].search(clause_final):
            return self.env['hr.contract'].search(clause_final).ids
        elif self.env['hr.contract'].search(clause_finals):
            return self.env['hr.contract'].search(clause_finals).ids
        else:
            return self.env['hr.contract'].search(clause_final).ids

    @api.model
    def _default_date_start(self):
        active_id = self.env.context.get('active_id')
        if active_id:
            [run_data] = self.env['hr.payslip.run'].browse(active_id).read(['date_start'])
            date_start = run_data.get('date_start')
            return date_start
    
    @api.model
    def _default_date_end(self):
        active_id = self.env.context.get('active_id')
        if active_id:
            [run_data] = self.env['hr.payslip.run'].browse(active_id).read(['date_end'])
            date_end = run_data.get('date_end')
            return date_end

    @api.model
    def _default_employee_tax_status(self):
        active_id = self.env.context.get('active_id')
        if active_id:
            [run_data] = self.env['hr.payslip.run'].browse(active_id).read(['employee_tax_status'])
            employee_tax_status = run_data.get('employee_tax_status')
            return employee_tax_status

    employee_ids = fields.Many2many('hr.employee', 'hr_employee_group_rel', 'payslip_id', 'employee_id', 'Employees')
    date_start = fields.Date(string="Start Date", default=lambda r: r._default_date_start())
    date_end = fields.Date(string="End Date", default=lambda r: r._default_date_end())
    employee_tax_status = fields.Selection(
        [('pegawai_tetap', 'Pegawai Tetap'), ('pegawai_tidak_tetap', 'Pegawai Tidak Tetap')],
        string='Employee Tax Status', default=lambda r: r._default_employee_tax_status())

    @api.onchange('employee_ids')
    def _onchange_employee_ids(self):
        from_date = self.date_start
        to_date = self.date_end
        contract_ids = self.get_contract(from_date, to_date)
        employees = []
        if contract_ids:
            contract_run = self.env['hr.contract'].search([('id','in',contract_ids)])
            employee_ids = []
            for rec in contract_run:
                employee_ids.append(rec.employee_id)
            if employee_ids:
                for emp in employee_ids:
                    contracts = self.get_contract_employee(emp, from_date, to_date)
                    contract_emp = self.env['hr.contract'].browse(contracts[0]) if contracts else False
                    if contract_emp and contract_emp.employee_id.employee_tax_status == self.employee_tax_status:
                        employees.append(emp.id)
        return {
            'domain': {'employee_ids': [('id', 'in', employees)]},
        }
    
    def compute_sheet(self):
        employees = []
        employees_draft = []
        for emp in self.employee_ids:
            if not emp.contract_ids:
                employees.append(emp.name)

            self.env.cr.execute("""select id from hr_contract where employee_id = %s AND state = 'draft'""" % (emp.id))
            contract_drafts = self.env.cr.dictfetchall()
            if contract_drafts:
                employees_draft.append(emp.name)

        if employees:
            error_message = ''
            num = 1
            for employee in employees:
                error_message += str(num) + '. ' + employee + '\n'
                num += 1
            raise ValidationError(
                ("Contract is not found for below employees : \n %s") %
                (error_message))

        if employees_draft:
            error_message = ''
            num = 1
            for employee in employees_draft:
                error_message += str(num) + '. ' + employee + '\n'
                num += 1
            raise ValidationError(
                ("Contract is not running for below employees : \n %s") %
                (error_message))

        payslips = self.env['hr.payslip']
        [data] = self.read()
        active_id = self.env.context.get('active_id')
        if active_id:
            [run_data] = self.env['hr.payslip.run'].browse(active_id).read(['date_start', 'date_end', 'credit_note', 'payslip_period_id', 'month'])
        payslip_period = self.env['hr.payslip.period'].search(
            [('id', '=', run_data.get('payslip_period_id')[0])], limit=1)
        month = self.env['hr.payslip.period.line'].search(
            [('id', '=', run_data.get('month')[0])], limit=1)
        from_date = run_data.get('date_start')
        to_date = run_data.get('date_end')

        payslip_exist = []
        for emp in self.employee_ids:
            self.env.cr.execute("""select id from hr_payslip where employee_id = %s AND date_from <= '%s' AND date_to > '%s' AND state in %s""" % (emp.id, to_date, from_date, ('draft', 'done')))
            payslip_emp = self.env.cr.dictfetchall()
            if payslip_emp:
                payslip_exist.append(emp.id)

        if not data['employee_ids']:
            raise UserError(_("You must select employee(s) to generate payslip(s)."))
        for employee in self.env['hr.employee'].browse(data['employee_ids']):
            payslip_name = _('Salary Slip of %s for %s-%s') % (
                employee.name, month.month, month.year)
            npwp = employee.npwp_no
            kpp_id = False
            kpp = ''
            ptkp_id = False
            ptkp = ''
            tax_calculation_method = ''
            employee_payment_method = ''
            if employee.kpp_id:
                kpp_id = employee.kpp_id.id
                kpp = employee.kpp_id.name
            if employee.ptkp_id:
                ptkp_id = employee.ptkp_id.id
                ptkp = employee.ptkp_id.ptkp_name
            if employee.tax_calculation_method:
                tax_calculation_methods = dict(
                    self.env['hr.employee'].fields_get(allfields=['tax_calculation_method'])['tax_calculation_method'][
                        'selection'])[employee.tax_calculation_method]
                tax_calculation_method = tax_calculation_methods
            if employee.employee_tax_status:
                employee_tax_status_ = dict(
                    self.env['hr.employee'].fields_get(allfields=['employee_tax_status'])['employee_tax_status'][
                        'selection'])[employee.employee_tax_status]
                employee_tax_status = employee_tax_status_
                emp_tax_status = employee.employee_tax_status
                if employee.employee_tax_status == "pegawai_tidak_tetap":
                    employee_payment_method = employee.employee_payment_method
            if employee.is_expatriate:
                is_expatriate = employee.is_expatriate
            else:
                is_expatriate = False
            if employee.expatriate_tax:
                expatriate_tax_ = \
                dict(self.env['hr.employee'].fields_get(allfields=['expatriate_tax'])['expatriate_tax']['selection'])[
                    employee.expatriate_tax]
                expatriate_tax = expatriate_tax_
            else:
                expatriate_tax = ''
            date_join = employee.date_of_joining
            tax_period_length = 0
            date_join_month = datetime.strptime(str(date_join), '%Y-%m-%d').date().month
            date_join_year = datetime.strptime(str(date_join), '%Y-%m-%d').date().year
            if payslip_period:
                if payslip_period.start_period_based_on == 'start_date':
                    this_month = datetime.strptime(str(from_date), '%Y-%m-%d').date().month
                    this_year = datetime.strptime(str(from_date), '%Y-%m-%d').date().year
                    payslip_report_date = from_date
                elif payslip_period.start_period_based_on == 'end_date':
                    this_month = datetime.strptime(str(to_date), '%Y-%m-%d').date().month
                    this_year = datetime.strptime(str(to_date), '%Y-%m-%d').date().year
                    payslip_report_date = to_date

                if this_year == date_join_year:
                    if (this_month >= date_join_month):
                        tax_period_length = (int(this_month) - int(date_join_month)) + 1
                    tax_period_length = tax_period_length
                    tax_end_month = (12 - int(date_join_month)) + 1
                else:
                    tax_period_length = this_month
                    tax_end_month = 12

                self.env.cr.execute(''' select id from career_transition_category WHERE name = '%s' ''' % ('Termination'))
                transition_category = self.env.cr.dictfetchall()
                self.env.cr.execute(
                    ''' select transition_date from hr_career_transition WHERE employee_id = %s AND status = 'approve' and transition_category_id = %s AND transition_date >= '%s' AND transition_date <= '%s' ORDER BY id DESC LIMIT 1 ''' % (
                    employee.id, transition_category[0].get('id'), from_date, to_date))
                term = self.env.cr.dictfetchall()
                if term:
                    termination = True
                    termination_date = term[0].get('transition_date')
                    date_resign = term[0].get('transition_date')
                    date_resign_month = datetime.strptime(str(date_resign), '%Y-%m-%d').date().month
                    date_resign_year = datetime.strptime(str(date_resign), '%Y-%m-%d').date().year
                    if this_year == date_resign_year:
                        if (this_month >= date_resign_month):
                            tax_end_month = int(date_resign_month)
                elif employee.contract_id.state == "close":
                    termination = True
                    termination_date = employee.contract_id.date_end
                    date_resign = employee.contract_id.date_end
                    date_resign_month = datetime.strptime(str(date_resign), '%Y-%m-%d').date().month
                    date_resign_year = datetime.strptime(str(date_resign), '%Y-%m-%d').date().year
                    if this_year == date_resign_year:
                        if (this_month >= date_resign_month):
                            tax_end_month = int(date_resign_month)
                else:
                    termination = False
                    termination_date = False

            slip_data = self.env['hr.payslip'].onchange_employee_id(from_date, to_date, employee.id, contract_id=False)
            contract_ids = slip_data['value'].get('contract_id')
            # computation of the salary other input
            contracts = self.env['hr.contract'].browse(contract_ids)
            other_input_entries = []
            self.env.cr.execute(
                ''' select other_input_id, code, amount from hr_other_input_entries WHERE employee = %s AND payslip_period_id = %s and month = %s ''' % (
                    employee.id, payslip_period.id, month.id))
            other_input_ids = self.env.cr.dictfetchall()
            for contract in contracts:
                if other_input_ids:
                    for input in other_input_ids:
                        other_input = self.env['hr.other.inputs'].browse(input.get('other_input_id'))[0]
                        input_data = {
                            'name': other_input.name,
                            'code': input.get('code'),
                            'amount': input.get('amount'),
                            'contract_id': contract.id,
                        }
                        other_input_entries += [input_data]

                input_data_overtime = {
                    'name': 'Overtime',
                    'code': 'OVT',
                    'amount': 0.0,
                    'contract_id': contract.id,
                }
                other_input_entries += [input_data_overtime]

                input_meal = {
                    'name': 'Overtime Meal',
                    'code': 'OVT_MEAL',
                    'amount': 0.0,
                    'contract_id': contract.id,
                }
                other_input_entries += [input_meal]

                attendance_alw = {
                    'name': "Attendance's Allowance",
                    'code': 'ATT_ALW',
                    'amount': 0.0,
                    'contract_id': contract.id,
                }
                other_input_entries += [attendance_alw]

            res = {
                'employee_id': employee.id,
                'name': payslip_name,
                'struct_id': slip_data['value'].get('struct_id'),
                'contract_id': slip_data['value'].get('contract_id'),
                'payslip_run_id': active_id,
                'input_line_ids': [(0, 0, x) for x in other_input_entries],
                'worked_days_line_ids': [(0, 0, x) for x in slip_data['value'].get('worked_days_line_ids')],
                'date_from': from_date,
                'date_to': to_date,
                'credit_note': run_data.get('credit_note'),
                'department_id': employee.department_id.id,
                'job_id': employee.job_id.id,
                'company_id': employee.company_id.id,
                'payslip_period_id': payslip_period.id,
                'payslip_report_date': payslip_report_date,
                'month': month.id,
                'month_name': month.month,
                'year': month.year,
                'npwp': npwp,
                'kpp_id': kpp_id,
                'kpp': kpp,
                'ptkp_id': ptkp_id,
                'ptkp': ptkp,
                'employee_tax_status': employee_tax_status,
                'emp_tax_status': emp_tax_status,
                'employee_payment_method': employee_payment_method,
                'is_expatriate': is_expatriate,
                'expatriate_tax': expatriate_tax,
                'tax_calculation_method': tax_calculation_method,
                'tax_period_length': tax_period_length,
                'tax_end_month': tax_end_month,
                'termination': termination,
                'termination_date': termination_date
            }
            if employee.id not in payslip_exist:
                payslips += self.env['hr.payslip'].create(res)

        for payslip in payslips:

            day_from = datetime.combine(fields.Date.from_string(from_date), time.min)
            day_to = datetime.combine(fields.Date.from_string(to_date), time.max)
            self.env.cr.execute(
                ''' select hour_from, check_in, tolerance_late, attendance_formula_id from hr_attendance WHERE employee_id = %s AND check_in >= '%s' and check_in <= '%s' and checkin_status = 'late' and active = 'true' ''' % (
                    payslip.employee_id.id, day_from, day_to))
            attendances = self.env.cr.dictfetchall()
            if attendances:
                checkin_late_deduction = []
                for att in attendances:
                    input_data = {
                        'hour_from': att.get('hour_from'),
                        'date_checkin': att.get('check_in'),
                        'tolerance_for_late': att.get('tolerance_late'),
                        'attendance_formula_id': att.get('attendance_formula_id'),
                    }
                    checkin_late_deduction += [input_data]

                checkin_late_ded = payslip.late_deduction_ids.browse([])
                for r in checkin_late_deduction:
                    checkin_late_ded += checkin_late_ded.new(r)
                payslip.late_deduction_ids = checkin_late_ded
            
            att_alw_amount = 0
            attendance_formula_setting = self.env['hr.config.settings'].sudo().search([],limit=1)
            if attendance_formula_setting.use_attendance_formula:
                self.env.cr.execute(
                    ''' select id, check_in, attendance_formula_id from hr_attendance WHERE employee_id = %s AND check_in >= '%s' and check_in <= '%s' and attendance_status = 'present' and active = 'true' ''' % (
                        payslip.employee_id.id, day_from, day_to))
                attendance_alw = self.env.cr.dictfetchall()
                if attendance_alw:
                    for att_alw in attendance_alw:
                        if att_alw.get('attendance_formula_id'):
                            att_formula_obj = self.env['hr.attendance.formula'].browse(int(att_alw.get('attendance_formula_id')))
                            amount = att_formula_obj._execute_formula_alw()
                            att_alw_amount += amount
            
            for rec in payslip.input_line_ids:
                if rec.code == 'ATT_ALW':
                    rec.amount = att_alw_amount

        payslips.compute_sheet()

        return {'type': 'ir.actions.act_window_close'}
