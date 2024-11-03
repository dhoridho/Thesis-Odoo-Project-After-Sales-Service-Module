from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, time

class PayslipComputeSheetWizard(models.TransientModel):
    _name = 'payslip.compute.sheet.wizard'

    message = fields.Text(string="Text", default="Warning! Please do the necessary action for actual overtime that has not been approved")
    payslip_id = fields.Many2one('hr.payslip')
    batch_active_id = fields.Integer('Batch Active Id')
    employee_ids = fields.Many2many('hr.employee', string='Employees')
    is_batch = fields.Boolean('Is Batch')
    payslip_period = fields.Many2one('hr.payslip.period')
    month = fields.Many2one('hr.payslip.period.line')
    date_start = fields.Date('Date From')
    date_end = fields.Date('Date To')
    credit_note = fields.Boolean('Credit Note')

    def action_continue(self):
        self.payslip_id.compute_sheet()

    def action_continue_batch(self):
        payslips = self.env['hr.payslip']
        [data] = self.read()
        active_id = self.batch_active_id
        payslip_period = self.payslip_period
        month = self.month
        from_date = self.date_start
        to_date = self.date_end
        credit_note = self.credit_note
        for employee in self.env['hr.employee'].browse(data['employee_ids']):
            payslip_name = _('Salary Slip of %s for %s-%s') % (
                employee.name, month.month, month.year)
            npwp = employee.npwp_no
            kpp_id = False
            kpp = ''
            ptkp_id = False
            ptkp = ''
            tax_calculation_method = ''
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
                'credit_note': credit_note,
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
                'is_expatriate': is_expatriate,
                'expatriate_tax': expatriate_tax,
                'tax_calculation_method': tax_calculation_method,
                'tax_period_length': tax_period_length,
                'tax_end_month': tax_end_month,
                'termination': termination,
                'termination_date': termination_date
            }
            payslips += self.env['hr.payslip'].create(res)

        for payslip in payslips:

            day_from = datetime.combine(fields.Date.from_string(from_date), time.min)
            day_to = datetime.combine(fields.Date.from_string(to_date), time.max)
            self.env.cr.execute(
                ''' select hour_from, check_in, tolerance_late from hr_attendance WHERE employee_id = %s AND check_in >= '%s' and check_in <= '%s' and checkin_status = 'late' ''' % (
                    payslip.employee_id.id, day_from, day_to))
            attendances = self.env.cr.dictfetchall()
            if attendances:
                checkin_late_deduction = []
                for att in attendances:
                    input_data = {
                        'hour_from': att.get('hour_from'),
                        'date_checkin': att.get('check_in'),
                        'tolerance_for_late': att.get('tolerance_late'),
                    }
                    checkin_late_deduction += [input_data]

                checkin_late_ded = payslip.late_deduction_ids.browse([])
                for r in checkin_late_deduction:
                    checkin_late_ded += checkin_late_ded.new(r)
                payslip.late_deduction_ids = checkin_late_ded

        payslips.compute_sheet()

        return {'type': 'ir.actions.act_window_close'}