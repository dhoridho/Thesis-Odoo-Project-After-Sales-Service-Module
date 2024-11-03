import time
import base64
import tempfile
from datetime import datetime
from odoo.tools.misc import get_lang
from time import gmtime, strftime
from dateutil.relativedelta import relativedelta as RV
from xml.dom import minidom

from odoo import tools
from odoo import fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DSDF


class EmpIr8aTextFile(models.TransientModel):
    _name = 'emp.ir8a.text.file'
    _description = "EmpIr8a TextFile"

    def _get_payroll_user_name(self):
        supervisors_list = [(False, '')]
        payroll_admin_rec = self.env['res.users'].search([])
        payroll_admin_group = 'l10n_sg_hr_payroll.group_hr_payroll_admin'
        payroll_admin_ids = payroll_admin_rec.filtered(
            lambda x: x.has_group(payroll_admin_group))
        for user in payroll_admin_ids:
            supervisors_list.append((tools.ustr(user.id),
                                     tools.ustr(user.name)))
        return supervisors_list

    employee_ids = fields.Many2many(
        'hr.employee', 'hr_employe_ir8a_text_rel',
        'emp_id', 'employee_id', 'Employee')
    start_date = fields.Date('Start Date', required=True,
                             default=lambda *a: time.strftime('%Y-01-01'))
    end_date = fields.Date('End Date', required=True,
                           default=lambda *a: time.strftime('%Y-12-31'))
    source = fields.Selection([('1', 'Mindef'),
                               ('4', 'Government Department'),
                               ('5', 'Statutory Board'),
                               ('6', 'Private Sector'),
                               ('9', 'Others')],
                              string='Source', default='6', required=True)
    batch_indicatior = fields.Selection([('O', 'Original'),
                                         ('A', 'Amendment')],
                                        string='Batch Indicator', required=True)
    batch_date = fields.Date('Batch Date', required=True)
    payroll_user = fields.Selection(
        _get_payroll_user_name, string='Name of authorised person',
        required=True)
    print_type = fields.Selection([('text', 'Text'),
                                   ('pdf', 'PDF'),
                                   ('xml', 'XML')], string='Print as',
                                  required=True, default='text')

    def download_ir8a_txt_file(self):
        context = dict(self._context) or {}
        context.update({'active_test': False})
        employee_obj = self.env['hr.employee']
        data = self.read([])[0]
        emp_ids = data.get('employee_ids', []) or []
        date_start = data.get('start_date', False)
        date_end = data.get('end_date', False)

        #  convert start and end date into start and end date of year.
        start_date_year = date_start + RV(month=1, day=1)
        end_date_year = date_end + RV(month=12, day=31)

        #  fetch 1st date of Jan and last date of Dec of previous year
        start_date = start_date_year + RV(years=-1)
        end_date = end_date_year + RV(years=-1)

        incometax_obj = self.env['hr.contract.income.tax']
        contract_obj = self.env['hr.contract']
        payslip_obj = self.env['hr.payslip']

        if 'start_date' in data and 'end_date' in data and \
                data.get('start_date', False) >= data.get('end_date', False):
            raise ValidationError(
                _("You must be enter start date less than end date !"))
        if emp_ids and emp_ids is not False:
            for employee in employee_obj.browse(emp_ids):
                emp_name = employee and employee.name or ''
                emp_id = employee and employee.id or False

                contract_ids = contract_obj.search([
                    ('employee_id', '=', emp_id)])
                tax_domain = [('contract_id', 'in', contract_ids.ids),
                              ('start_date', '>=', self.start_date),
                              ('end_date', '<=', self.end_date)]
                contract_income_tax_ids = incometax_obj.search(tax_domain)
                if not contract_income_tax_ids.ids:
                    raise ValidationError(
                        _("There is no Income tax details available between "
                          "selected date %s and %s for the %s employee for "
                          "contract." % (
                            self.start_date.strftime(
                                get_lang(self.env).date_format),
                            self.end_date.strftime(
                                get_lang(self.env).date_format), emp_name)))
                payslip_ids = payslip_obj.search([
                    ('date_from', '>=', self.start_date),
                    ('date_from', '<=', self.end_date),
                    ('employee_id', '=', emp_id),
                    ('state', 'in', ['draft', 'done', 'verify'])])
                if not payslip_ids.ids:
                    raise ValidationError(
                        _("There is no payslip details available between "
                          "selected date %s and %s for the %s employee." % (
                            self.start_date.strftime(
                                get_lang(self.env).date_format),
                            self.end_date.strftime(
                                get_lang(self.env).date_format), emp_name)))
            context.update({'employe_id': data['employee_ids'], 'datas': data})
            if data.get('print_type', '') == 'text':
                payslip_obj = self.env['hr.payslip']
                tgz_tmp_filename = tempfile.mktemp(suffix='.txt')
                tmp_file = False
                start_date = end_date = False
                from_date = context.get('datas', {}).get('start_date', False)
                to_date = context.get('datas', {}).get('end_date', False)
                if from_date and to_date:
                    basis_year = str(from_date.year - 1)

                    start_date = from_date + RV(month=1, day=1, years=-1)
                    fiscal_start_date = start_date
                    end_date = to_date + RV(month=12, day=31, years=-1)
                    fiscal_end_date = end_date
                try:
                    tmp_file = open(tgz_tmp_filename, "w")
                    batchdate = context.get('datas')['batch_date'].strftime(
                        '%Y%m%d')
                    server_date = basis_year + strftime("%m%d", gmtime())
                    emp_id = employee_obj.search(
                        [('user_id', '=',
                          int(context.get('datas')['payroll_user']))])
                    emp_designation = emp_contact = emp_email = ''
                    payrolluser = self.env['res.users'].browse(
                        int(context.get('datas')['payroll_user']))
                    payroll_admin_user_name = payrolluser.name
                    company_name = payrolluser.company_id.name

                    user_rec = self.env['res.users'].browse(self._uid)
                    if user_rec.company_id and \
                            user_rec.company_id.organization_id_type:
                        organization_id_type = user_rec.company_id.organization_id_type
                    else:
                        raise ValidationError(_(
                            "Please configure Organization Id in company"))
                    if user_rec.company_id and \
                            user_rec.company_id.organization_id_no:
                        organization_id_no = user_rec.company_id.organization_id_no
                    else:
                        raise ValidationError(_(
                            "Please configure Organization Id No in company"))
                    for emp in emp_id:
                        emp_designation = emp.job_id.name
                        emp_contact = emp.work_phone
                        emp_email = emp.work_email
                    header_record = '0'.ljust(1) + \
                                    tools.ustr(context.get('datas')['source'] or '').ljust(1) + \
                                    tools.ustr(basis_year).ljust(4) + '08'.ljust(2) + \
                                    tools.ustr(
                                        organization_id_type or '').ljust(1) + \
                                    tools.ustr(
                                        organization_id_no or '').ljust(12) + \
                                    tools.ustr(
                                        payroll_admin_user_name or '')[:30].ljust(
                                            30) + \
                                    tools.ustr(emp_designation)[:30].ljust(30) + \
                                    tools.ustr(company_name)[:60].ljust(60) + \
                                    tools.ustr(emp_contact)[:20].ljust(20) + \
                                    tools.ustr(emp_email)[:60].ljust(60) + \
                                    tools.ustr(
                                        context.get('datas')
                                        ['batch_indicatior'] or '').ljust(1) + \
                                    tools.ustr(server_date or '').ljust(8) + \
                                    ''.ljust(30) + \
                                    ''.ljust(10) + \
                                    ''.ljust(930) + \
                                    "\r\n"
                    tmp_file.write(header_record)
                    total_detail_record = 0
                    tot_prv_yr_gross_amt = tot_payment_amount = tot_insurance = \
                        tot_employment_income = tot_exempt_income = \
                        tot_other_data = tot_director_fee = tot_mbf_amt = \
                        tot_donation_amt = tot_catemp_amt = tot_net_amt = \
                        tot_salary_amt = tot_bonus_amt = 0
                    contract_ids = self.env['hr.contract'].search(
                        [('employee_id', 'in', context.get('employe_id'))])
                    incometax_obj = self.env['hr.contract.income.tax']
                    for contract in contract_ids:
                        c_domain = [('contract_id', '=', contract.id),
                                    ('start_date', '>=', start_date_year),
                                    ('end_date', '<=', end_date_year)]
                        contract_income_tax_ids = incometax_obj.search(c_domain)
                        emp_id = contract.employee_id
                        if contract_income_tax_ids:
                            for emp in contract_income_tax_ids[0]:
                                total_detail_record += 1
                                sex = birthday = join_date = cessation_date = \
                                    bonus_declare_date = \
                                    approve_director_fee_date = fromdate = \
                                    approval_date = ''
                                if emp_id.empnationality_id and \
                                        str(emp_id.empnationality_id.code) == '301':
                                    if str(emp_id.identification_no) != '1':
                                        raise ValidationError(_(
                                            "Id type of employee must be NRIC "
                                            "when employee is singapore citizen"))
                                if emp_id.gender == 'male':
                                    sex = 'M'
                                if emp_id.gender == 'female':
                                    sex = 'F'
                                if emp_id.birthday:
                                    birthday = emp_id.birthday.strftime('%Y%m%d')
                                if emp_id.join_date:
                                    join_date = emp_id.join_date
                                    if emp_id.cessation_provisions \
                                        == 'Y' and join_date.year > 1969 or \
                                        emp_id.cessation_provisions \
                                            != 'Y' and join_date.year < 1969:
                                        raise ValidationError(
                                            _("One of the following configuration is still missing from employee "
                                              "\nPlease configure all the following details for employee %s. "
                                              "\n\n * Date must be before 1969/01/01 when Cessation "
                                              "Provisions Indicator = Y \n* Provisions Indicator must be Y "
                                              "when join date before "
                                              "1969/01/01" % (emp_id.name)))
                                    else:
                                        join_date = join_date.strftime(
                                            '%Y%m%d')
                                if contract.date_end:
                                    cessation_date = (
                                        contract.date_end.strftime('%Y%m%d'))
                                if emp.bonus_declaration_date:
                                    bonus_declare_date = (
                                        emp.bonus_declaration_date.strftime(
                                            '%Y%m%d'))
                                if emp.director_fee_approval_date:
                                    approve_director_fee_date = (
                                        emp.director_fee_approval_date.strftime(
                                            DSDF))
                                    if (str(emp.director_fee_approval_date.year
                                            ) != basis_year):
                                        raise ValidationError(_(
                                            "Director fees approval date must"
                                            " be between income year"))
                                    else:
                                        approve_director_fee_date = (
                                            emp.director_fee_approval_date.strftime('%Y%m%d'))
                                if emp.approval_date:
                                    approval_date = datetime.strptime(
                                        emp.approval_date.strftime(DSDF), DSDF)
                                    approval_date = approval_date.strftime(
                                        '%Y%m%d')
                                entertainment_allowance = transport_allowance = \
                                    salary_amt = other_allowance = other_data = \
                                    amount_data = mbf_amt = donation_amt = \
                                    catemp_amt = net_amt = bonus_amt = \
                                    prv_yr_gross_amt = gross_comm = 0
                                pay_domain = [('date_from', '>=', start_date),
                                              ('date_from', '<=', end_date),
                                              ('employee_id', '=', emp_id.id),
                                              ('state', 'in',
                                               ['draft', 'done', 'verify'])]
                                payslip_ids = payslip_obj.search(
                                    pay_domain, order="date_from")
                                for payslip in payslip_ids:
                                    basic_flag = False
                                    for line in payslip.line_ids:
                                        if line.code == 'BASIC':
                                            basic_flag = True
                                    if basic_flag and emp.contract_id.wage:
                                        salary_amt += contract.wage
                                    for line in payslip.line_ids:
                                        if not contract.wage and \
                                            contract.rate_per_hour and \
                                                line.code == 'SC100':
                                            salary_amt += line.total
                                        if line.code == 'CPFMBMF':
                                            mbf_amt += line.total
                                        if line.code in \
                                                ['CPFSINDA', 'CPFCDAC', 'CPFECF']:
                                            donation_amt += line.total
                                        if line.category_id.code == \
                                                'CAT_CPF_EMPLOYEE':
                                            catemp_amt += line.total
                                        if line.code == 'GROSS':
                                            net_amt += line.total
                                        if line.code == 'SC121':
                                            salary_amt -= line.total
                                            bonus_amt += line.total
                                            net_amt -= line.total
                                        if line.code in ['SC106', 'SC108',
                                                         'SC123', 'FA']:
                                            other_allowance += line.total
                                            net_amt -= line.total
                                        if line.category_id.code in ['ADD',
                                                                     'ALW']:
                                            other_data += line.total
                                            salary_amt += line.total
                                        if line.code in ['SC200', 'SC206']:
                                            salary_amt -= line.total
                                        if line.code in ['SC104', 'SC105']:
                                            salary_amt -= line.total
                                            if not fromdate:
                                                fromdate = (
                                                    payslip.date_from.strftime(
                                                        '%Y%m%d'))
                                            gross_comm += line.total
                                            net_amt -= line.total
                                        if line.code == 'TA':
                                            transport_allowance += line.total
                                other_allowance += emp.other_allowance
                                other_data = gross_comm + emp.pension + \
                                    transport_allowance + \
                                    emp.entertainment_allowance + \
                                    other_allowance + emp.notice_pay + \
                                    emp.ex_gratia + emp.others + \
                                    emp.gratuity_payment_amt + \
                                    emp.retirement_benifit_from + \
                                    emp.contribution_employer + \
                                    emp.gains_profit_share_option + \
                                    emp.benifits_in_kinds + \
                                    emp.excess_voluntary_contribution_cpf_employer
                                mbf_amt = '%0*d' % (5, int(abs(round(mbf_amt,
                                                                     0))))
                                donation_amt = \
                                    '%0*d' % (5, int(abs(round(donation_amt,
                                                               0))))
                                catemp_amt = \
                                    '%0*d' % (7, int(abs(round(catemp_amt,
                                                               0))))
                                net_amt = '%0*d' % (9, int(abs(net_amt)))
                                salary_amt = '%0*d' % (9, int(abs(salary_amt)))
                                bonus_amt = '%0*d' % (9, int(abs(bonus_amt)))
                                insurance = director_fee = gain_profit = \
                                    exempt_income = gross_commission = \
                                    benifits_in_kinds = \
                                    gains_profit_share_option = \
                                    excess_voluntary_contribution_cpf_employer = \
                                    contribution_employer = \
                                    retirement_benifit_from = \
                                    retirement_benifit_up = \
                                    compensation_loss_office = \
                                    gratuity_payment_amt = \
                                    entertainment_allowance = \
                                    pension = employee_income = \
                                    tot_employee_income = \
                                    gratuity_payment_amt = 0
                                insurance = '%0*d' % (5, int(abs(emp.insurance
                                                                 )))
                                tot_insurance += int(insurance[:5])
                                if emp.director_fee_approval_date and \
                                        emp.director_fee <= 0:
                                    raise ValidationError(_(
                                        "Director Fee can not be zero when "
                                        "director fees approval date is "
                                        "not blank"))
                                else:
                                    director_fee = \
                                        '%0*d' % (9, int(abs(emp.director_fee
                                                             )))
                                gain_profit = '%0*d' % (9,
                                                        int(abs(emp.gain_profit
                                                                )))
                                exempt_income = \
                                    '%0*d' % (9, int(abs(emp.exempt_income)))
                                employment_income = \
                                    '%0*d' % (9, int(abs(emp.employment_income
                                                         )))
                                if emp.employee_income_tax in ['P']:
                                    tot_employment_income += \
                                        int('%0*d' % (9, int(abs(emp.employment_income))))
                                if emp.employee_income_tax in ['H']:
                                    tot_employee_income += \
                                        int('%0*d' % (9, int(abs(emp.employee_income))))
                                gross_commission = \
                                    '%0*d' % (11,
                                              int(abs(gross_comm * 100)))
                                pension = '%0*d' % (11,
                                                    int(abs(emp.pension * 100
                                                            )))
                                transport_allowance = '%0*d' % (
                                    11, int(abs(transport_allowance * 100)))
                                entertainment_allowance = '%0*d' % (
                                    11, int(abs(
                                        emp.entertainment_allowance * 100)))
                                gratuity_payment_amt += (emp.gratuity_payment_amt)
                                gratuity_payment_amt += emp.notice_pay
                                gratuity_payment_amt += emp.ex_gratia
                                gratuity_payment_amt += emp.others
                                if emp.gratuity_payment == 'Y' and \
                                        gratuity_payment_amt == 0:
                                    raise ValidationError(_(
                                        "Gratuity/ Notice Pay/ Ex-gratia "
                                        "payment/ Others can not be zero when "
                                        "Gratuity/ Notice Pay/Ex-gratia "
                                        "payment/ Others indicator is Y"))
                                else:
                                    gratuity_payment_amt = '%0*d' % (
                                        11, int(abs(gratuity_payment_amt * 100
                                                    )))
                                if emp.compensation == 'Y' and \
                                        emp.compensation_loss_office <= 0:
                                    raise ValidationError(_("Compensation for loss of office can not be zero when Compensation for loss of office indicator is Y"))
                                else:
                                    compensation_loss_office = '%0*d' % (
                                        11, int(abs(emp.compensation_loss_office * 100)))
                                retirement_benifit_up = '%0*d' % (
                                    11, int(abs(emp.retirement_benifit_up * 100
                                                )))
                                retirement_benifit_from = '%0*d' % (
                                    11, int(abs(
                                        emp.retirement_benifit_from * 100)))
                                contribution_employer = '%0*d' % (
                                    11, int(abs(emp.contribution_employer * 100
                                                )))
                                e1 = emp.excess_voluntary_contribution_cpf_employer
                                excess_voluntary_contribution_cpf_employer = \
                                    '%0*d' % (11, int(abs(e1 * 100)))
                                gains_profit_share_option = '%0*d' % (
                                    11, int(abs(
                                        emp.gains_profit_share_option * 100)))
                                benifits_in_kinds = '%0*d' % (
                                    11, int(abs(emp.benifits_in_kinds * 100)))
                                if emp.employee_income_tax in ['F', 'H']:
                                    employment_income = ''
                                elif emp.employee_income_tax in ['P']:
                                    if emp.employment_income <= 0:
                                        raise ValidationError(_(
                                            "Employment income must be "
                                            "greater than zero"))
                                    else:
                                        employment_income = '%0*d' % (
                                            9, int(abs(emp.employment_income)))
                                if emp.employee_income_tax in ['F', 'P']:
                                    employee_income = ''
                                elif emp.employee_income_tax in ['H']:
                                    if emp.employee_income <= 0:
                                        raise ValidationError(_(
                                            "Employee income must be greater "
                                            "than zero"))
                                    else:
                                        employee_income = \
                                            '%0*d' % (9, int(abs(emp.employee_income)))
                                other_allowance = \
                                    '%0*d' % (11, int(abs(other_allowance * 100
                                                          )))
                                amount_data = other_data + \
                                    int(salary_amt) + \
                                    int(emp.director_fee) + int(bonus_amt)
                                tot_other_data += other_data
                                other_data = '%0*d' % (9, int(abs(other_data)))
                                amount_data = '%0*d' % (9, int(abs(amount_data
                                                                   )))
                                if prv_yr_gross_amt != '':
                                    tot_prv_yr_gross_amt += int(
                                        prv_yr_gross_amt)
                                tot_mbf_amt += int(mbf_amt[:5])
                                tot_donation_amt += int(donation_amt[:5])
                                tot_catemp_amt += int(catemp_amt[:7])
                                tot_net_amt += int(net_amt[:9])
                                tot_salary_amt += int(salary_amt[:9])
                                tot_bonus_amt += int(bonus_amt[:9])
                                tot_director_fee += int(director_fee[:9])
                                tot_exempt_income += int(exempt_income[:9])
                                house_no = street = level_no = unit_no = \
                                    street2 = postal_code = countrycode = \
                                    nationalitycode = unformatted_postal_code = \
                                    employee_income_tax_born = \
                                    exempt_remission_selection = \
                                    gratuity_payment_selection = \
                                    compensation_office = from_ir8s_selection = \
                                    section_applicable_s = benefits_kind_y = \
                                    approve_iras_obtain = \
                                    cessation_provisions_selection = ''
                                if emp.employee_income > 0 and \
                                    emp.employee_income_tax not in ['P', 'H'] or \
                                    emp.employment_income > 0 and \
                                        emp.employee_income_tax not in ['P',
                                                                        'H']:
                                    raise ValidationError(
                                        _("Employees Income Tax borne by "
                                          "employer must be P or H for %s "
                                          "employee." % (emp_id.name)))
                                if emp.exempt_remission == '6':
                                    exempt_income = ''
                                if emp.exempt_income != 0:
                                    if emp.exempt_remission not in \
                                            ['1', '3', '4', '5', '7']:
                                        raise ValidationError(_('Exempt/ Remission income Indicator must be in \n'
                                        '* Tax Remission on Overseas Cost of Living Allowance (OCLA)\n'
                                        '* Seaman \n'
                                        '* Exemption \n'
                                        '* Overseas Pension Fund with Tax Concession \n'
                                        '* Income from Overseas Employment and Overseas Pension Fund with Tax Concession for %s employee.' % (emp_id.name)))
                                if emp.employee_income_tax == 'N':
                                    employee_income_tax_born = ''
                                if emp.employee_income_tax != 'N':
                                    employee_income_tax_born = \
                                        emp.employee_income_tax
                                if emp.gratuity_payment == 'Y':
                                    gratuity_payment_selection = \
                                        emp.gratuity_payment
                                if emp.gratuity_payment == 'N':
                                    gratuity_payment_amt = ''
                                if emp.gratuity_payment_amt != 0:
                                    if emp.gratuity_payment != 'Y':
                                        raise ValidationError(
                                            _("Gratuity/ Notice Pay/ Ex-gratia "
                                              "payment/ Others indicator must "
                                              "be Y for %s employee." % (
                                                  emp_id.name)))
                                if emp.approve_obtain_iras == 'Y' and (not emp.compensation or emp.compensation == 'N'):
                                    raise ValidationError(
                                        "Compensation for loss of office must "
                                        "be Y when Approval obtained from IRAS")
                                if emp.compensation == 'Y':
                                    compensation_office = emp.compensation
                                if not emp.approve_obtain_iras or \
                                        emp.compensation_loss_office != 0:
                                    if emp.compensation != 'Y':
                                        raise ValidationError(
                                            _("Compensation for loss of "
                                              "office indicator must be Y for "
                                              "%s employee." % (emp_id.name)))
                                if emp.exempt_remission != 'N':
                                    exempt_remission_selection = \
                                        emp.exempt_remission
                                if emp.from_ir8s != 'Y' and \
                                        emp.emp_voluntary_contribution_cpf > 0:
                                    raise ValidationError(
                                        _("Form IR8S must be applicable for "
                                          "%s employee." % (emp_id.name)))
                                else:
                                    from_ir8s_selection = emp.from_ir8s
                                if emp_id.empnationality_id.code != \
                                        '301':
                                    section_applicable_s = 'Y'
                                elif emp_id.empnationality_id.code \
                                        == '301':
                                    section_applicable_s = 'N'
                                elif emp.section_applicable == 'Y':
                                    section_applicable_s = emp.section_applicable
                                else:
                                    section_applicable_s = 'N'
                                if emp.benefits_kind == 'Y':
                                    benefits_kind_y = emp.benefits_kind
                                if emp.benefits_kind == 'N':
                                    benifits_in_kinds = ''
                                if emp.benifits_in_kinds > 0 and not \
                                        emp.benefits_kind or emp.approval_date\
                                        and emp.approve_obtain_iras != 'Y':
                                    raise ValidationError(
                                        _("One of the following configuration "
                                          "is still missing from employee"
                                          ".\nPlease configure all the "
                                          "following details for employee %s. "
                                          "\n\n * Benefits-in-kind indicator "
                                          "must be Y \n* Approval obtained "
                                          "from IRAS must be Y" % (
                                              emp_id.name)))
                                approve_iras_obtain = emp.approve_obtain_iras
                                if emp.approve_obtain_iras == 'Y':
                                    if not emp.approval_date:
                                        raise ValidationError(
                                            "You must be configure approval date")
                                    else:
                                        approval_date = (
                                            emp.approval_date.strftime(
                                                '%Y%m%d'))
                                else:
                                    approval_date = ''
                                if emp_id.cessation_provisions == \
                                        'Y':
                                    cessation_provisions_selection = \
                                        emp_id.cessation_provisions
                                if emp_id.address_type != "N":
                                    if not emp_id.address_home_id \
                                        or \
                                        emp_id.address_home_id.zip \
                                            and len(emp_id.address_home_id.zip) < 6:
                                        raise ValidationError(
                                            _("One of the following "
                                              "configuration is still missing "
                                              "from employee\'s profile.\n"
                                              "Please configure all the "
                                              "following details for "
                                              "employee %s. \n\n * Home "
                                              "Address \n* Postal code must "
                                              "be 6 numeric digits" % (
                                                  emp_id.name)))
                                    street2 = emp_id.address_home_id.street2
                                    level_no = emp_id.address_home_id.level_no
                                    unit_no = emp_id.address_home_id.unit_no
                                    if emp_id.address_type in ['F', 'C'] and \
                                            not street2:
                                        raise ValidationError(
                                            _("You must be configure street2 "
                                              "for %s employee home address." % (emp_id.name)))
                                    if emp_id.address_type == "F":
                                        house_no = ''
                                        street = ''
                                        postal_code = ''
                                        level_no = ''
                                        unit_no = ''
                                        countrycode = \
                                            emp_id.empcountry_id.code
                                    if emp_id.address_type == "L":
                                        unformatted_postal_code = ''
                                        countrycode = ''
                                        street2 = ''
                                        if not emp_id.address_home_id.street \
                                            or not \
                                            emp_id.address_home_id.house_no \
                                                or not emp_id.address_home_id.zip:
                                            raise ValidationError(
                                                _("One of the following configuration is still missing from employee\'s profile. \n "
                                                  "Please configure all the following details for employee %s. \n\n * Street \n* House No "
                                                  "\n* Postal Code" % (emp_id.name)))
                                        street = emp_id.address_home_id.street
                                        house_no = emp_id.address_home_id.house_no
                                        postal_code = emp_id.address_home_id.zip
                                    if emp_id.address_type == 'C':
                                        if not postal_code:
                                            raise ValidationError(
                                                _('You must be configure postal code for %s employee home address.' % (emp_id.name)))
                                        house_no = ''
                                        street = ''
                                        postal_code = ''
                                        unformatted_postal_code = postal_code
                                        countrycode = ''

                                if not emp_id.empnationality_id or \
                                    (emp_id.address_home_id.level_no and not
                                        emp_id.address_home_id.unit_no
                                     ) or \
                                    (emp_id.address_type == "F" and
                                        not emp_id.empcountry_id) \
                                        or \
                                        (emp_id.address_home_id.unit_no and not
                                            emp_id.address_home_id.level_no):
                                    raise ValidationError(_("One of the following configuration is still missing from employee\'s profile.\nPlease configure all the following details for "
                                                            "employee %s. \n\n* Nationality Code \n* Unit no of home address \n* Country Code \n* Level no of home address "
                                                            % (emp_id.name)))

                                if emp_id.empnationality_id:
                                    nationalitycode = (
                                        emp_id.empnationality_id.code)
                                payment_period_form_date = fiscal_start_date
                                payment_period_to_date = fiscal_end_date
                                if cessation_date:
                                    payment_period_to_date = cessation_date
                                if emp.employee_income_tax == 'F' or \
                                        emp.employee_income_tax == 'H':
                                    employment_income = ''
                                period_date_start = period_date_end = \
                                    gross_comm_indicator = ''
                                if emp.gross_commission > 0:
                                    gorss_comm_period_from = (
                                        emp.gorss_comm_period_from.strftime(
                                            '%Y%m%d'))
                                    gorss_comm_period_to = (
                                        emp.gorss_comm_period_to.strftime(
                                            '%Y%m%d'))
                                    period_date_start = gorss_comm_period_from
                                    period_date_end = gorss_comm_period_to
                                    gross_comm_indicator = (
                                        emp.gross_comm_indicator)
                                else:
                                    period_date_start = ''
                                    period_date_end = ''
                                    gross_comm_indicator = ''
                                selection = cessation_provisions_selection
                                emp1 = (
                                    excess_voluntary_contribution_cpf_employer)
                                option = gains_profit_share_option
                                approve_date = approve_director_fee_date
                                detail_record = '1'.ljust(1) + \
                                                tools.ustr(
                                                    emp_id.identification_no or
                                                    '').ljust(1) + \
                                                tools.ustr(
                                                    emp_id.identification_id or
                                                    '')[:12].ljust(12) + \
                                                tools.ustr(
                                                    emp_id.name or
                                                        '')[:80].ljust(80) + \
                                                tools.ustr(emp_id.address_type or
                                                           '')[:1].ljust(1) + \
                                                tools.ustr(house_no or
                                                           '')[:10].ljust(10) + \
                                                tools.ustr(street or
                                                           '')[:32].ljust(32) + \
                                                tools.ustr(level_no or
                                                            '')[:3].ljust(3) + \
                                                tools.ustr(unit_no or
                                                            '')[:5].ljust(5) + \
                                                tools.ustr(postal_code or
                                                            '')[:6].ljust(6) + \
                                                tools.ustr(street2 or
                                                            '')[:30].ljust(30) + \
                                                ''.ljust(30) + \
                                                ''.ljust(30) + \
                                                tools.ustr(
                                                    unformatted_postal_code or
                                                        '')[:6].ljust(6) + \
                                                tools.ustr(countrycode or
                                                            '')[:3].ljust(3) + \
                                                tools.ustr(nationalitycode or
                                                            '')[:3].ljust(3) + \
                                                tools.ustr(sex).ljust(1) + \
                                                tools.ustr(birthday).ljust(8) + \
                                                tools.ustr(
                                                    amount_data)[:9].ljust(9) + \
                                                tools.ustr(payment_period_form_date
                                                           ).ljust(8) + \
                                                tools.ustr(payment_period_to_date
                                                           ).ljust(8) + \
                                                tools.ustr(
                                                    mbf_amt)[:5].ljust(5) + \
                                                tools.ustr(
                                                    donation_amt)[:5].ljust(5) + \
                                                tools.ustr(
                                                    catemp_amt)[:7].ljust(7) + \
                                                tools.ustr(
                                                    insurance)[:5].ljust(5) + \
                                                tools.ustr(
                                                    salary_amt)[:9].ljust(9) + \
                                                tools.ustr(
                                                    bonus_amt)[:9].ljust(9) + \
                                                tools.ustr(
                                                    director_fee)[:9].ljust(9) + \
                                                tools.ustr(
                                                    other_data)[:9].ljust(9) + \
                                                tools.ustr(
                                                    gain_profit)[:9].ljust(9) + \
                                                tools.ustr(
                                                    exempt_income)[:9].ljust(9) + \
                                                tools.ustr(
                                                    employment_income or
                                                    '')[:9].ljust(9) + \
                                                tools.ustr(employee_income
                                                           )[:9].ljust(9) + \
                                                tools.ustr(benefits_kind_y or
                                                            '').ljust(1) + \
                                                tools.ustr(section_applicable_s or
                                                            '').ljust(1) + \
                                                tools.ustr(
                                                    employee_income_tax_born or
                                                    '').ljust(1) + \
                                                tools.ustr(
                                                    gratuity_payment_selection or
                                                    '').ljust(1) + \
                                                tools.ustr(compensation_office or
                                                            '').ljust(1) + \
                                                tools.ustr(approve_iras_obtain or
                                                            '').ljust(1) + \
                                                tools.ustr(
                                                    approval_date).ljust(8) + \
                                                tools.ustr(selection or
                                                            '').ljust(1) + \
                                                tools.ustr(
                                                    from_ir8s_selection or
                                                    '').ljust(1) + \
                                                tools.ustr(
                                                    exempt_remission_selection or
                                                    '').ljust(1) + \
                                                ''.ljust(1) + \
                                                tools.ustr(
                                                    gross_commission)[:11].ljust(
                                                    11) + \
                                                tools.ustr(
                                                    period_date_start).ljust(8) + \
                                                tools.ustr(
                                                    period_date_end).ljust(8) + \
                                                tools.ustr(
                                                    gross_comm_indicator).ljust(
                                                    1) + \
                                                tools.ustr(
                                                    pension)[:11].ljust(11) + \
                                                tools.ustr(transport_allowance
                                                           )[:11].ljust(11) + \
                                                tools.ustr(entertainment_allowance
                                                           )[:11].ljust(11) + \
                                                tools.ustr(other_allowance
                                                           )[:11].ljust(11) + \
                                                tools.ustr(gratuity_payment_amt
                                                           )[:11].ljust(11) + \
                                                tools.ustr(compensation_loss_office
                                                           )[:11].ljust(11) + \
                                                tools.ustr(retirement_benifit_up
                                                           )[:11].ljust(11) + \
                                                tools.ustr(retirement_benifit_from
                                                           )[:11].ljust(11) + \
                                                tools.ustr(contribution_employer
                                                           )[:11].ljust(11) + \
                                                tools.ustr(
                                                    emp1)[:11].ljust(11) + \
                                                tools.ustr(option
                                                           )[:11].ljust(11) + \
                                                tools.ustr(benifits_in_kinds
                                                           )[:11].ljust(11) + \
                                                ''.ljust(7) + \
                                                tools.ustr(emp_id.job_id.name or
                                                            '')[:30].ljust(30) + \
                                                tools.ustr(join_date).ljust(8) + \
                                                tools.ustr(
                                                    cessation_date).ljust(8) + \
                                                tools.ustr(bonus_declare_date
                                                           ).ljust(8) + \
                                                tools.ustr(
                                                    approve_date).ljust(8) + \
                                                tools.ustr(emp.fund_name or ''
                                                           ).ljust(60) + \
                                                tools.ustr(emp.deginated_pension or
                                                            '').ljust(60) + \
                                                ''.ljust(1) + \
                                                ''.ljust(8) + \
                                                ''.ljust(393) + \
                                                ''.ljust(50) + \
                                    "\r\n"
                                tmp_file.write(detail_record)
                    tot_payment_amount = tot_salary_amt + \
                        tot_bonus_amt + tot_director_fee + tot_other_data

                    total_detail_record = '%0*d' % (6,
                                                    int(abs(total_detail_record)))
                    tot_payment_amount = '%0*d' % (12,
                                                   int(abs(tot_payment_amount)))
                    tot_mbf_amt = '%0*d' % (12, int(abs(tot_mbf_amt)))
                    tot_donation_amt = '%0*d' % (12, int(abs(tot_donation_amt)))
                    tot_catemp_amt = '%0*d' % (12, int(abs(tot_catemp_amt)))
                    tot_net_amt = '%0*d' % (12, int(abs(tot_net_amt)))
                    tot_salary_amt = '%0*d' % (12, int(abs(tot_salary_amt)))
                    tot_bonus_amt = '%0*d' % (12, int(abs(tot_bonus_amt)))
                    tot_director_fee = '%0*d' % (12, int(abs(tot_director_fee)))
                    tot_other_data = '%0*d' % (12, int(abs(tot_other_data)))
                    tot_exempt_income = '%0*d' % (12, int(abs(tot_exempt_income)))
                    tot_employment_income = \
                        '%0*d' % (12, int(abs(tot_employment_income)))
                    tot_insurance = '%0*d' % (12, int(abs(tot_insurance)))
                    tot_employee_income = '%0*d' % (12,
                                                    int(abs(tot_employee_income)))
                    footer_record = '2'.ljust(1) + \
                                    tools.ustr(
                                        total_detail_record)[:6].ljust(6) + \
                                    tools.ustr(
                                        tot_payment_amount)[:12].ljust(12) + \
                                    tools.ustr(tot_salary_amt)[:12].ljust(12) + \
                                    tools.ustr(tot_bonus_amt)[:12].ljust(12) + \
                                    tools.ustr(tot_director_fee)[:12].ljust(12) + \
                                    tools.ustr(tot_other_data)[:12].ljust(12) + \
                                    tools.ustr(
                                        tot_exempt_income)[:12].ljust(12) + \
                                    tools.ustr(
                                        tot_employment_income)[:12].ljust(12) + \
                                    tools.ustr(
                                        tot_employee_income)[:12].ljust(12) + \
                                    tools.ustr(tot_donation_amt)[:12].ljust(12) + \
                                    tools.ustr(tot_catemp_amt)[:12].ljust(12) + \
                                    tools.ustr(tot_insurance)[:12].ljust(12) + \
                                    tools.ustr(tot_mbf_amt)[:12].ljust(12) + \
                                    ' '.ljust(1049) + "\r\n"
                    tmp_file.write(footer_record)
                finally:
                    if tmp_file:
                        tmp_file.close()
                filemap = open(tgz_tmp_filename, "rb")
                out = filemap.read()
                filemap.close()
                res = base64.b64encode(out)
                module_rec = self.env['binary.ir8a.text.file.wizard'].create(
                    {'name': 'IR8A.txt', 'ir8a_txt_file': res})
                return {
                    'name': _('Binary'),
                    'res_id': module_rec.id,
                    "view_mode": 'form',
                    'res_model': 'binary.ir8a.text.file.wizard',
                    'type': 'ir.actions.act_window',
                    'target': 'new',
                    'context': context,
                }
            elif data.get('print_type', '') == 'xml':
                doc = minidom.Document()
                root = doc.createElement('IR8A')
                root.setAttribute('xmlns', 'http://www.iras.gov.sg/IR8ADef')
                doc.appendChild(root)
                payslip_obj = self.env['hr.payslip']

                start_date = end_date = False
                from_date = context.get('datas', False).get('start_date', False) or False
                to_date = context.get('datas', False).get('end_date', False
                                                          ) or False
                if from_date and to_date:
                    basis_year = tools.ustr(from_date.year - 1)
                    start_date = from_date + RV(month=1, day=1, years=-1)
                    fiscal_start_date = start_date
                    end_date = to_date + RV(month=12, day=31, years=-1)
                    fiscal_end_date = end_date
                batchdate = context.get('datas')['batch_date'].strftime(
                    '%Y%m%d')
                server_date = basis_year + strftime("%m%d", gmtime())
                emp_id = employee_obj.search([
                    ('user_id', '=', int(context.get('datas')['payroll_user']))])
                emp_designation = emp_contact = emp_email = ''
                user_obj = self.env['res.users']
                payroll_admin_user_name = user_obj.browse(
                    int(context.get('datas')['payroll_user'])).name
                company_name = user_obj.browse(
                    int(context.get('datas')['payroll_user'])).company_id.name
                user_rec = self.env['res.users'].browse(self._uid)
                organization_id_type = user_rec.company_id.organization_id_type
                organization_id_no = user_rec.company_id.organization_id_no
                for emp in emp_id:
                    emp_designation = emp.job_id.name
                    emp_contact = emp.work_phone
                    emp_email = emp.work_email
                    if not emp_email and not emp_contact:
                        raise ValidationError(_('Please configure Email or Contact for %s employee.' % (emp.name)))

                """ Header for IR8A """

                header = doc.createElement('IR8AHeader')
                root.appendChild(header)

                ESubmissionSDSC = doc.createElement('ESubmissionSDSC')
                ESubmissionSDSC.setAttribute(
                    'xmlns', 'http://tempuri.org/ESubmissionSDSC.xsd')
                header.appendChild(ESubmissionSDSC)

                FileHeaderST = doc.createElement('FileHeaderST')
                ESubmissionSDSC.appendChild(FileHeaderST)

                RecordType = doc.createElement('RecordType')
                RecordType.appendChild(doc.createTextNode('0'))
                FileHeaderST.appendChild(RecordType)

                Source = doc.createElement('Source')
                if context.get('datas') and context.get('datas')['source']:
                    Source.appendChild(doc.createTextNode(context.get('datas')
                                                          ['source']))
                FileHeaderST.appendChild(Source)

                BasisYear = doc.createElement('BasisYear')
                if basis_year:
                    BasisYear.appendChild(doc.createTextNode(str(basis_year)))
                FileHeaderST.appendChild(BasisYear)

                PaymentType = doc.createElement('PaymentType')
                PaymentType.appendChild(doc.createTextNode('08'))
                FileHeaderST.appendChild(PaymentType)

                OrganizationID = doc.createElement('OrganizationID')
                if organization_id_type:
                    OrganizationID.appendChild(
                        doc.createTextNode(str(organization_id_type)))
                FileHeaderST.appendChild(OrganizationID)

                OrganizationIDNo = doc.createElement('OrganizationIDNo')
                if organization_id_no:
                    OrganizationIDNo.appendChild(
                        doc.createTextNode(organization_id_no))
                FileHeaderST.appendChild(OrganizationIDNo)

                AuthorisedPersonName = doc.createElement('AuthorisedPersonName')
                if payroll_admin_user_name:
                    AuthorisedPersonName.appendChild(
                        doc.createTextNode(str(payroll_admin_user_name)))
                FileHeaderST.appendChild(AuthorisedPersonName)

                AuthorisedPersonDesignation = doc.createElement('AuthorisedPersonDesignation')
                if emp_designation:
                    AuthorisedPersonDesignation.appendChild(
                        doc.createTextNode(str(emp_designation)))
                FileHeaderST.appendChild(AuthorisedPersonDesignation)

                EmployerName = doc.createElement('EmployerName')
                if company_name:
                    EmployerName.appendChild(doc.createTextNode(str(company_name)))
                FileHeaderST.appendChild(EmployerName)

                Telephone = doc.createElement('Telephone')
                if emp_contact:
                    Telephone.appendChild(doc.createTextNode(str(emp_contact)))
                FileHeaderST.appendChild(Telephone)

                aut_email = doc.createElement('AuthorisedPersonEmail')
                if emp_email:
                    aut_email.appendChild(doc.createTextNode(str(emp_email)))
                FileHeaderST.appendChild(aut_email)

                BatchIndicator = doc.createElement('BatchIndicator')
                if context.get('datas') and context.get('datas')['batch_indicatior']:
                    BatchIndicator.appendChild(
                        doc.createTextNode(str(
                            context.get('datas')['batch_indicatior'])))
                FileHeaderST.appendChild(BatchIndicator)

                BatchDate = doc.createElement('BatchDate')
                if batchdate:
                    BatchDate.appendChild(doc.createTextNode(str(batchdate)))
                FileHeaderST.appendChild(BatchDate)

                DivisionOrBranchName = doc.createElement('DivisionOrBranchName')
                FileHeaderST.appendChild(DivisionOrBranchName)

                Details = doc.createElement('Details')
                root.appendChild(Details)

                total_detail_record = 0
                tot_prv_yr_gross_amt = tot_payment_amount = tot_insurance = \
                    tot_employment_income = tot_exempt_income = \
                    tot_other_data = tot_director_fee = tot_mbf_amt = \
                    tot_donation_amt = tot_employee_income = tot_catemp_amt = \
                    tot_net_amt = tot_salary_amt = tot_bonus_amt = 0
                contract_ids = self.env['hr.contract'].search([
                    ('employee_id', 'in', context.get('employe_id'))])
                for contract in contract_ids:
                    income_tax_obj = self.env['hr.contract.income.tax']
                    contract_income_tax_ids = income_tax_obj.search([
                        ('contract_id', '=', contract.id),
                        ('start_date', '>=', start_date_year),
                        ('end_date', '<=', end_date_year)])
                    if contract_income_tax_ids:
                        for emp in contract_income_tax_ids[0]:
                            total_detail_record += 1
                            sex = birthday = join_date = cessation_date = \
                                bonus_declare_date = fromdate = \
                                approve_director_fee_date = \
                                approval_date = ''
                            if contract.employee_id.gender == 'male':
                                sex = 'M'
                            if contract.employee_id.gender == 'female':
                                sex = 'F'
                            if contract.employee_id.birthday:
                                birthday = (
                                    contract.employee_id.birthday.strftime(
                                        '%Y%m%d'))
                            if contract.employee_id.join_date:
                                join_date = contract.employee_id.join_date
                                if (contract.employee_id.cessation_provisions == 'Y' and join_date.year > 1969 or contract.employee_id.cessation_provisions != 'Y' and join_date.year < 1969):
                                    raise ValidationError(
                                        _("One of the following configuration is still missing from employee\nPlease configure all the "
                                          "following details for employee %s. \n\n * Date must be before 1969/01/01 when "
                                          "Cessation Provisions Indicator = Y \n* Provisions Indicator must be Y when join "
                                          "date before 1969/01/01" % (contract.employee_id.name)))
                                join_date = join_date.strftime('%Y%m%d')
                            if contract.date_end:
                                cessation_date = contract.date_end.strftime('%Y%m%d')
                            if emp.bonus_declaration_date:
                                bonus_declare_date = (
                                    emp.bonus_declaration_date.strftime('%Y%m%d'))
                            if emp.director_fee_approval_date:
                                approve_director_fee_date = (
                                    emp.director_fee_approval_date.strftime('%Y%m%d'))
                            if emp.approval_date:
                                approval_date = emp.approval_date.strftime('%Y%m%d')
                            entertainment_allowance = transport_allowance = \
                                salary_amt = other_allowance = other_data = \
                                amount_data = mbf_amt = donation_amt = \
                                catemp_amt = net_amt = bonus_amt = \
                                prv_yr_gross_amt = gross_comm = 0
                            payslip_ids = payslip_obj.search([
                                ('date_from', '>=', start_date),
                                ('date_from', '<=', end_date),
                                ('employee_id', '=', contract.employee_id.id),
                                ('state', 'in', ['draft', 'done', 'verify'])],
                                order="date_from")
                            for payslip in payslip_ids:
                                basic_flag = False
                                for line in payslip.line_ids:
                                    if line.code == 'BASIC':
                                        basic_flag = True
                                if basic_flag and emp.contract_id.wage:
                                    salary_amt += contract.wage
                                for line in payslip.line_ids:
                                    if not contract.wage and \
                                        contract.rate_per_hour and \
                                            line.code == 'SC100':
                                        salary_amt += line.total
                                    if line.code == 'CPFMBMF':
                                        mbf_amt += line.total
                                    if line.code in ['CPFSINDA',
                                                     'CPFCDAC', 'CPFECF']:
                                        donation_amt += line.total
                                    if line.category_id.code == \
                                            'CAT_CPF_EMPLOYEE':
                                        catemp_amt += line.total
                                    if line.code == 'GROSS':
                                        net_amt += line.total
                                    if line.code == 'SC121':
                                        bonus_amt += line.total
                                        net_amt -= line.total
                                    if line.code in ['SC106', 'SC108',
                                                     'SC123', 'FA']:
                                        other_allowance += line.total
                                        net_amt -= line.total
                                    if line.category_id.code in ['ADD', 'ALW']:
                                        other_data += line.total
                                        salary_amt += line.total
                                    if line.code in ['SC200', 'SC206']:
                                        salary_amt -= line.total
                                    if line.code in ['SC104', 'SC105']:
                                        if not fromdate:
                                            fromdate = (payslip.date_from.strftime('%Y%m%d'))
                                        gross_comm += line.total
                                        net_amt -= line.total
                                    if line.code == 'TA':
                                        transport_allowance += line.total
                            other_allowance += emp.other_allowance
                            other_data = (
                                gross_comm + emp.pension + transport_allowance +
                                emp.entertainment_allowance + other_allowance +
                                emp.notice_pay + emp.ex_gratia + emp.others +
                                emp.gratuity_payment_amt +
                                emp.retirement_benifit_from +
                                emp.contribution_employer +
                                emp.excess_voluntary_contribution_cpf_employer +
                                emp.gains_profit_share_option +
                                emp.benifits_in_kinds)

                            mbf_amt = int(abs(round(mbf_amt, 0)))
                            donation_amt = int(abs(round(donation_amt, 0)))
                            catemp_amt = catemp_amt
                            net_amt = int(abs(net_amt))
                            salary_amt = int(abs(salary_amt))
                            bonus_amt = int(abs(bonus_amt))

                            insurance = director_fee = gain_profit = \
                                exempt_income = gross_commission = \
                                benifits_in_kinds = gains_profit_share_option = \
                                excess_voluntary_contribution_cpf_employer = \
                                contribution_employer = \
                                retirement_benifit_from = retirement_benifit_up = \
                                compensation_loss_office = \
                                gratuity_payment_amt = entertainment_allowance = \
                                pension = employee_income = 0

                            insurance = int(abs(emp.insurance))
                            tot_insurance += int(insurance)
                            director_fee = int(abs(emp.director_fee))
                            gain_profit = int(abs(emp.gain_profit))
                            exempt_income = int(abs(emp.exempt_income))
                            employment_income = int(abs(emp.employment_income))
                            if emp.employee_income_tax in ['P']:
                                tot_employment_income += int(
                                    abs(emp.employment_income))
                            if emp.employee_income_tax in ['H']:
                                tot_employee_income += int(
                                    abs(emp.employee_income))
                            gross_commission = gross_comm
                            pension = emp.pension
                            transport_allowance = transport_allowance
                            entertainment_allowance = emp.entertainment_allowance

                            gratuity_payment_amt += emp.gratuity_payment_amt
                            gratuity_payment_amt += emp.notice_pay
                            gratuity_payment_amt += emp.ex_gratia
                            gratuity_payment_amt += emp.others
                            gratuity_payment_amt = gratuity_payment_amt

                            compensation_loss_office = (emp.compensation_loss_office)
                            retirement_benifit_up = emp.retirement_benifit_up
                            retirement_benifit_from = (
                                emp.retirement_benifit_from)
                            contribution_employer = emp.contribution_employer
                            excess_voluntary_contribution_cpf_employer = \
                                emp.excess_voluntary_contribution_cpf_employer
                            gains_profit_share_option = (emp.gains_profit_share_option)
                            benifits_in_kinds = emp.benifits_in_kinds
                            if emp.employee_income_tax in ['F', 'H']:
                                employment_income = ''
                            elif emp.employee_income_tax in ['P']:
                                if emp.employment_income < 0:
                                    raise ValidationError('Employment income must be greater than zero')
                                employment_income = int(abs(
                                                        emp.employment_income))
                            if emp.employee_income_tax in ['F', 'P']:
                                employee_income = ''
                            elif emp.employee_income_tax in ['H']:
                                if emp.employee_income < 0:
                                    raise ValidationError('Employee income must be greater than zero')
                                employee_income = int(abs(emp.employee_income))

                            other_allowance = other_allowance

                            amount_data = int(other_data) + int(salary_amt) + \
                                int(emp.director_fee) + int(bonus_amt)
                            tot_other_data += other_data
                            other_data = int(abs(other_data))
                            amount_data = amount_data
                            if prv_yr_gross_amt != '':
                                tot_prv_yr_gross_amt += int(prv_yr_gross_amt)
                            tot_mbf_amt += int(mbf_amt)
                            tot_donation_amt += int(donation_amt)
                            tot_catemp_amt += int(catemp_amt)
                            tot_net_amt += int(net_amt)
                            tot_salary_amt += int(salary_amt)
                            tot_bonus_amt += int(bonus_amt)
                            tot_director_fee += int(director_fee)
                            tot_exempt_income += int(exempt_income)

                            house_no = street = level_no = unit_no = street2 = \
                                postal_code = countrycode = nationalitycode = \
                                unformatted_postal_code = \
                                employee_income_tax_born = \
                                exempt_remission_selection = \
                                gratuity_payment_selection = compensation_office = \
                                from_ir8s_selection = section_applicable_s = \
                                benefits_kind_Y = approve_iras_obtain = \
                                cessation_provisions_selection = ''
                            if emp.employee_income > 0 and emp.employee_income_tax not in ['P', 'H'] \
                                    or emp.employment_income > 0 and emp.employee_income_tax not in ['P', 'H']:
                                raise ValidationError(_('Employees Income Tax borne by employer must be P or H for %s employee.' % (contract.employee_id.name)))
                            if emp.exempt_remission == '6':
                                exempt_income = ''
                            if emp.exempt_income != 0:
                                if emp.exempt_remission not in ['1', '3', '4', '5', '7']:
                                    raise ValidationError(_('Exempt/ Remission income Indicator must be in \n'
                                        '* Tax Remission on Overseas Cost of Living Allowance (OCLA)\n'
                                        '* Seaman \n'
                                        '* Exemption \n'
                                        '* Overseas Pension Fund with Tax Concession \n'
                                        '* Income from Overseas Employment and Overseas Pension Fund with Tax Concession for %s employee.' % (contract.employee_id.name)))
                            if emp.employee_income_tax == 'N':
                                employee_income_tax_born = ''
                            if emp.employee_income_tax != 'N':
                                employee_income_tax_born = (
                                    emp.employee_income_tax)
                            if emp.gratuity_payment == 'Y':
                                gratuity_payment_selection = (
                                    emp.gratuity_payment)
                            if emp.gratuity_payment == 'N':
                                gratuity_payment_amt = ''
                            if emp.gratuity_payment_amt != 0:
                                if emp.gratuity_payment != 'Y':
                                    raise ValidationError(_('Gratuity/ Notice Pay/ Ex-gratia payment/ Others indicator must be Y for %s employee.' % (
                                        contract.employee_id.name)))
                            if emp.compensation == 'Y':
                                compensation_office = emp.compensation
                            if not emp.approve_obtain_iras != '' or emp.compensation_loss_office != 0:
                                if emp.compensation != 'Y':
                                    raise ValidationError(_('Compensation for loss of office indicator must be Y for %s employee.' % (contract.employee_id.name)))
                            if emp.exempt_remission != 'N':
                                exempt_remission_selection = emp.exempt_remission
                            if emp.from_ir8s != 'Y' and emp.emp_voluntary_contribution_cpf > 0:
                                raise ValidationError(_('Form IR8S must be applicable for %s employee.' % (
                                    contract.employee_id.name)))
                            else:
                                from_ir8s_selection = emp.from_ir8s
                            if contract.employee_id.empnationality_id.code != '301':
                                job_name = contract.employee_id.job_id.name
                                if job_name and 'director' in job_name.lower():
                                    section_applicable_s = 'Y'
                            elif contract.employee_id.empnationality_id.code == '301':
                                section_applicable_s = ' '
                            elif emp.section_applicable == 'Y':
                                section_applicable_s = emp.section_applicable
                            else:
                                section_applicable_s = ' '

                            if emp.benefits_kind == 'Y':
                                benefits_kind_Y = emp.benefits_kind
                            else:
                                benefits_kind_Y = ' '

                            if emp.benifits_in_kinds > 0 and not emp.benefits_kind or emp.approval_date and emp.approve_obtain_iras != 'Y':
                                raise ValidationError(_("One of the following configuration is still missing from employee.\nPlease configure all the following details "
                                                        "for employee %s. \n\n * Benefits-in-kind indicator must be Y \n* Approval obtained "
                                                        "from IRAS must be Y" % (contract.employee_id.name)))
                            approve_iras_obtain = emp.approve_obtain_iras
                            if emp.approve_obtain_iras == 'Y':
                                if not emp.approval_date:
                                    raise ValidationError('You must be configure approval date')
                                else:
                                    approval_date = emp.approval_date.strftime('%Y%m%d')
                            else:
                                approval_date = ''
                            if contract.employee_id.cessation_provisions == 'Y':
                                cessation_provisions_selection = \
                                    contract.employee_id.cessation_provisions
                            if contract.employee_id.address_type != "N":
                                if not contract.employee_id.address_home_id or \
                                    contract.employee_id.address_home_id.zip and\
                                    len(contract.employee_id.address_home_id.zip
                                        ) < 6:
                                    raise ValidationError(
                                        _("One of the following configuration is still missing from employee\'s profile.\nPlease configure all the "
                                          "following details for employee %s. \n\n * Home Address \n* Postal code must be 6 numeric digits" % (contract.employee_id.name)))
                                street2 = contract.employee_id.address_home_id.street2
                                level_no = contract.employee_id.address_home_id.level_no
                                unit_no = contract.employee_id.address_home_id.unit_no
                                if contract.employee_id.address_type in ['F', 'C'] and not contract.employee_id.address_home_id.street2:
                                    raise ValidationError(
                                        _('You must be configure street2 for %s employee home address.' % (contract.employee_id.name)))
                                if contract.employee_id.address_type == "F":
                                    house_no = ''
                                    street = ''
                                    postal_code = ''
                                    level_no = ''
                                    unit_no = ''
                                    countrycode = \
                                        contract.employee_id.empcountry_id.code
                                if contract.employee_id.address_type == "L":
                                    unformatted_postal_code = ''
                                    countrycode = ''
                                    street2 = ''
                                    if not contract.employee_id.address_home_id.street or not \
                                        contract.employee_id.address_home_id.house_no or not \
                                            contract.employee_id.address_home_id.zip:
                                        raise ValidationError(_("One of the following configuration is still missing from employee\'s profile.\nPlease "
                                                                "configure all the following details for employee %s. \n\n* Street \n* House No \n* Postal Code" % (contract.employee_id.name)))
                                    street = contract.employee_id.address_home_id.street
                                    house_no = contract.employee_id.address_home_id.house_no
                                    postal_code = contract.employee_id.address_home_id.zip
                                if contract.employee_id.address_type == 'C':
                                    if not contract.employee_id.address_home_id.zip:
                                        raise ValidationError(
                                            _('You must be configure postal code for %s employee home address.' % (contract.employee_id.name)))
                                    house_no = ''
                                    street = ''
                                    postal_code = ''
                                    unformatted_postal_code = \
                                        contract.employee_id.address_home_id.zip
                                    countrycode = ''

                            if not contract.employee_id.empnationality_id or (
                                contract.employee_id.address_home_id.level_no is not False and not
                                contract.employee_id.address_home_id.unit_no) or \
                                (contract.employee_id.address_type == "F" and not contract.employee_id.empcountry_id) or \
                                    (contract.employee_id.address_home_id.unit_no is not False and not contract.employee_id.address_home_id.level_no):
                                raise ValidationError(
                                    _("One of the following configuration is still missing from employee\'s"
                                      "profile.\nPlease configure all the following details for employee %s. \n\n"
                                      "* Nationality Code \n* Unit no of home address \n* Country Code \n* Level no of home address " % (contract.employee_id.name)))
                            if contract.employee_id.empnationality_id:
                                nationalitycode = \
                                    contract.employee_id.empnationality_id.code
                            payment_period_form_date = fiscal_start_date
                            payment_period_to_date = fiscal_end_date
                            if cessation_date:
                                payment_period_to_date = cessation_date
                            if emp.employee_income_tax == 'F' or emp.employee_income_tax == 'H':
                                employment_income = ''
                            period_date_start = period_date_end = gross_comm_indicator = ''
                            if emp.gross_commission > 0:
                                gorss_comm_period_from = (
                                    emp.gorss_comm_period_from.strftime(
                                        '%Y%m%d'))
                                gorss_comm_period_to = (emp.gorss_comm_period_to.strftime('%Y%m%d'))
                                period_date_start = gorss_comm_period_from
                                period_date_end = gorss_comm_period_to
                                gross_comm_indicator = emp.gross_comm_indicator
                            else:
                                period_date_start = ''
                                period_date_end = ''
                                gross_comm_indicator = ''

                            IR8ARecord = doc.createElement('IR8ARecord')
                            Details.appendChild(IR8ARecord)

                            ESubmissionSDSC = doc.createElement('ESubmissionSDSC')
                            ESubmissionSDSC.setAttribute(
                                'xmlns', 'http://tempuri.org/ESubmissionSDSC.xsd')
                            IR8ARecord.appendChild(ESubmissionSDSC)

                            record1 = doc.createElement('IR8AST')
                            ESubmissionSDSC.appendChild(record1)

                            RecordType = doc.createElement('RecordType')
                            RecordType.setAttribute(
                                'xmlns', 'http://www.iras.gov.sg/IR8A')
                            RecordType.appendChild(doc.createTextNode('1'))
                            record1.appendChild(RecordType)

                            IDType = doc.createElement('IDType')
                            IDType.setAttribute('xmlns',
                                                'http://www.iras.gov.sg/IR8A')
                            if contract.employee_id.identification_no:
                                IDType.appendChild(doc.createTextNode(str(contract.employee_id.identification_no)))
                            record1.appendChild(IDType)

                            IDNo = doc.createElement('IDNo')
                            IDNo.setAttribute('xmlns',
                                              'http://www.iras.gov.sg/IR8A')
                            if contract.employee_id.identification_id:
                                IDNo.appendChild(doc.createTextNode(str(
                                    contract.employee_id.identification_id)))
                            record1.appendChild(IDNo)

                            NameLine1 = doc.createElement('NameLine1')
                            NameLine1.setAttribute(
                                'xmlns', 'http://www.iras.gov.sg/IR8A')
                            if contract.employee_id.name:
                                NameLine1.appendChild(doc.createTextNode(
                                    str(contract.employee_id.name)))
                            record1.appendChild(NameLine1)

                            NameLine2 = doc.createElement('NameLine2')
                            NameLine2.setAttribute(
                                'xmlns', 'http://www.iras.gov.sg/IR8A')
                            record1.appendChild(NameLine2)

                            AddressType = doc.createElement('AddressType')
                            AddressType.setAttribute(
                                'xmlns', 'http://www.iras.gov.sg/IR8A')
                            if contract.employee_id.address_type:
                                AddressType.appendChild(doc.createTextNode(
                                    str(contract.employee_id.address_type)))
                            record1.appendChild(AddressType)

                            BlockNo = doc.createElement('BlockNo')
                            BlockNo.setAttribute('xmlns',
                                                 'http://www.iras.gov.sg/IR8A')
                            if house_no:
                                BlockNo.appendChild(
                                    doc.createTextNode(str(house_no)))
                            record1.appendChild(BlockNo)

                            StName = doc.createElement('StName')
                            StName.setAttribute('xmlns',
                                                'http://www.iras.gov.sg/IR8A')
                            if street:
                                StName.appendChild(
                                    doc.createTextNode(str(street)))
                            record1.appendChild(StName)

                            LevelNo = doc.createElement('LevelNo')
                            LevelNo.setAttribute('xmlns',
                                                 'http://www.iras.gov.sg/IR8A')
                            if level_no:
                                LevelNo.appendChild(
                                    doc.createTextNode(str(level_no)))
                            record1.appendChild(LevelNo)

                            UnitNo = doc.createElement('UnitNo')
                            UnitNo.setAttribute('xmlns',
                                                'http://www.iras.gov.sg/IR8A')
                            if unit_no:
                                UnitNo.appendChild(doc.createTextNode(str(unit_no)))
                            record1.appendChild(UnitNo)

                            PostalCode = doc.createElement('PostalCode')
                            PostalCode.setAttribute(
                                'xmlns', 'http://www.iras.gov.sg/IR8A')
                            if postal_code:
                                PostalCode.appendChild(doc.createTextNode(str(postal_code)))
                            record1.appendChild(PostalCode)

                            AddressLine1 = doc.createElement('AddressLine1')
                            AddressLine1.setAttribute(
                                'xmlns', 'http://www.iras.gov.sg/IR8A')
                            if street2:
                                AddressLine1.appendChild(doc.createTextNode(str(street2)))
                            record1.appendChild(AddressLine1)

                            AddressLine2 = doc.createElement('AddressLine2')
                            AddressLine2.setAttribute(
                                'xmlns', 'http://www.iras.gov.sg/IR8A')
                            record1.appendChild(AddressLine2)

                            AddressLine3 = doc.createElement('AddressLine3')
                            AddressLine3.setAttribute(
                                'xmlns', 'http://www.iras.gov.sg/IR8A')
                            record1.appendChild(AddressLine3)

                            TX_UF_POSTAL_CODE = doc.createElement('TX_UF_POSTAL_CODE')
                            TX_UF_POSTAL_CODE.setAttribute(
                                'xmlns', 'http://www.iras.gov.sg/IR8A')
                            if unformatted_postal_code:
                                TX_UF_POSTAL_CODE.appendChild(doc.createTextNode(str(unformatted_postal_code)))
                            record1.appendChild(TX_UF_POSTAL_CODE)

                            CountryCode = doc.createElement('CountryCode')
                            CountryCode.setAttribute(
                                'xmlns', 'http://www.iras.gov.sg/IR8A')
                            if countrycode:
                                CountryCode.appendChild(doc.createTextNode(str(countrycode)))
                            record1.appendChild(CountryCode)

                            Nationality = doc.createElement('Nationality')
                            Nationality.setAttribute(
                                'xmlns', 'http://www.iras.gov.sg/IR8A')
                            if nationalitycode:
                                Nationality.appendChild(
                                    doc.createTextNode(str(nationalitycode)))
                            record1.appendChild(Nationality)

                            Sex = doc.createElement('Sex')
                            Sex.setAttribute('xmlns',
                                             'http://www.iras.gov.sg/IR8A')
                            if sex:
                                Sex.appendChild(doc.createTextNode(str(sex)))
                            record1.appendChild(Sex)

                            DateOfBirth = doc.createElement('DateOfBirth')
                            DateOfBirth.setAttribute(
                                'xmlns', 'http://www.iras.gov.sg/IR8A')
                            if birthday:
                                DateOfBirth.appendChild(
                                    doc.createTextNode(str(birthday)))
                            record1.appendChild(DateOfBirth)

                            Amount = doc.createElement('Amount')
                            Amount.setAttribute('xmlns',
                                                'http://www.iras.gov.sg/IR8A')
                            if amount_data:
                                Amount.appendChild(
                                    doc.createTextNode(str(int(amount_data))))
                            record1.appendChild(Amount)

                            PaymentPeriodFromDate = doc.createElement('PaymentPeriodFromDate')
                            PaymentPeriodFromDate.setAttribute(
                                'xmlns', 'http://www.iras.gov.sg/IR8A')
                            if payment_period_form_date:
                                PaymentPeriodFromDate.appendChild(
                                    doc.createTextNode(str(payment_period_form_date)))
                            record1.appendChild(PaymentPeriodFromDate)

                            PaymentPeriodToDate = doc.createElement('PaymentPeriodToDate')
                            PaymentPeriodToDate.setAttribute(
                                'xmlns', 'http://www.iras.gov.sg/IR8A')
                            if payment_period_to_date:
                                PaymentPeriodToDate.appendChild(
                                    doc.createTextNode(str(payment_period_to_date)))
                            record1.appendChild(PaymentPeriodToDate)

                            MBF = doc.createElement('MBF')
                            MBF.setAttribute('xmlns',
                                             'http://www.iras.gov.sg/IR8A')
                            if mbf_amt:
                                MBF.appendChild(doc.createTextNode(str
                                                                   (mbf_amt)))
                            record1.appendChild(MBF)

                            Donation = doc.createElement('Donation')
                            Donation.setAttribute(
                                'xmlns', 'http://www.iras.gov.sg/IR8A')
                            if donation_amt:
                                Donation.appendChild(
                                    doc.createTextNode(str(donation_amt)))
                            record1.appendChild(Donation)

                            CPF = doc.createElement('CPF')
                            CPF.setAttribute('xmlns',
                                             'http://www.iras.gov.sg/IR8A')
                            if catemp_amt:
                                CPF.appendChild(doc.createTextNode(str(catemp_amt)))
                            record1.appendChild(CPF)

                            Insurance = doc.createElement('Insurance')
                            Insurance.setAttribute(
                                'xmlns', 'http://www.iras.gov.sg/IR8A')
                            if insurance:
                                Insurance.appendChild(doc.createTextNode(str(insurance)))
                            record1.appendChild(Insurance)

                            Salary = doc.createElement('Salary')
                            Salary.setAttribute('xmlns',
                                                'http://www.iras.gov.sg/IR8A')
                            if salary_amt:
                                Salary.appendChild(
                                    doc.createTextNode(str(salary_amt)))
                            record1.appendChild(Salary)

                            Bonus = doc.createElement('Bonus')
                            Bonus.setAttribute('xmlns',
                                               'http://www.iras.gov.sg/IR8A')
                            if bonus_amt:
                                Bonus.appendChild(
                                    doc.createTextNode(str(bonus_amt)))
                            record1.appendChild(Bonus)

                            DirectorsFees = doc.createElement('DirectorsFees')
                            DirectorsFees.setAttribute(
                                'xmlns', 'http://www.iras.gov.sg/IR8A')
                            if director_fee:
                                DirectorsFees.appendChild(
                                    doc.createTextNode(str(director_fee)))
                            record1.appendChild(DirectorsFees)

                            Others = doc.createElement('Others')
                            Others.setAttribute('xmlns',
                                                'http://www.iras.gov.sg/IR8A')
                            if other_data:
                                Others.appendChild(
                                    doc.createTextNode(str(other_data)))
                            record1.appendChild(Others)

                            ShareOptionGainsS101g = doc.createElement('ShareOptionGainsS101g')
                            ShareOptionGainsS101g.setAttribute(
                                'xmlns', 'http://www.iras.gov.sg/IR8A')
                            if gain_profit:
                                ShareOptionGainsS101g.appendChild(
                                    doc.createTextNode(str(gain_profit)))
                            record1.appendChild(ShareOptionGainsS101g)

                            ExemptIncome = doc.createElement('ExemptIncome')
                            ExemptIncome.setAttribute('xmlns',
                                                      'http://www.iras.gov.sg/IR8A')
                            if exempt_income:
                                ExemptIncome.appendChild(doc.createTextNode(
                                    str(exempt_income)))
                            record1.appendChild(ExemptIncome)

                            IncomeForTaxBorneByEmployer = doc.createElement('IncomeForTaxBorneByEmployer')
                            IncomeForTaxBorneByEmployer.setAttribute(
                                'xmlns', 'http://www.iras.gov.sg/IR8A')
                            if employment_income:
                                IncomeForTaxBorneByEmployer.appendChild(
                                    doc.createTextNode(str(employment_income)))
                            record1.appendChild(IncomeForTaxBorneByEmployer)

                            IncomeForTaxBorneByEmployee = doc.createElement('IncomeForTaxBorneByEmployee')
                            IncomeForTaxBorneByEmployee.setAttribute(
                                'xmlns', 'http://www.iras.gov.sg/IR8A')
                            if employee_income:
                                IncomeForTaxBorneByEmployee.appendChild(
                                    doc.createTextNode(str(employee_income)))
                            record1.appendChild(IncomeForTaxBorneByEmployee)

                            BenefitsInKind = doc.createElement('BenefitsInKind')
                            BenefitsInKind.setAttribute(
                                'xmlns', 'http://www.iras.gov.sg/IR8A')
                            if benefits_kind_Y and benefits_kind_Y not in ('', ' '):
                                BenefitsInKind.appendChild(doc.createTextNode(str(benefits_kind_Y)))
                            record1.appendChild(BenefitsInKind)

                            S45Applicable = doc.createElement('S45Applicable')
                            S45Applicable.setAttribute('xmlns', 'http://www.iras.gov.sg/IR8A')
                            if section_applicable_s:
                                S45Applicable.appendChild(doc.createTextNode(
                                    str(section_applicable_s)))
                            record1.appendChild(S45Applicable)

                            IncomeTaxBorneByEmployer = doc.createElement('IncomeTaxBorneByEmployer')
                            IncomeTaxBorneByEmployer.setAttribute(
                                'xmlns', 'http://www.iras.gov.sg/IR8A')
                            if employee_income_tax_born:
                                IncomeTaxBorneByEmployer.appendChild(
                                    doc.createTextNode(str(employee_income_tax_born)))
                            record1.appendChild(IncomeTaxBorneByEmployer)

                            GratuityNoticePymExGratiaPaid = doc.createElement('GratuityNoticePymExGratiaPaid')
                            GratuityNoticePymExGratiaPaid.setAttribute(
                                'xmlns', 'http://www.iras.gov.sg/IR8A')
                            if gratuity_payment_selection:
                                GratuityNoticePymExGratiaPaid.appendChild(
                                    doc.createTextNode(str(
                                        gratuity_payment_selection)))
                            record1.appendChild(GratuityNoticePymExGratiaPaid)

                            CompensationRetrenchmentBenefitsPaid = \
                                doc.createElement('CompensationRetrenchmentBenefitsPaid')
                            CompensationRetrenchmentBenefitsPaid.setAttribute(
                                'xmlns', 'http://www.iras.gov.sg/IR8A')
                            if compensation_office:
                                CompensationRetrenchmentBenefitsPaid.appendChild(
                                    doc.createTextNode(str(compensation_office)))
                            record1.appendChild(CompensationRetrenchmentBenefitsPaid)

                            ApprovalObtainedFromIRAS = doc.createElement('ApprovalObtainedFromIRAS')
                            ApprovalObtainedFromIRAS.setAttribute(
                                'xmlns', 'http://www.iras.gov.sg/IR8A')
                            if approve_iras_obtain:
                                ApprovalObtainedFromIRAS.appendChild(
                                    doc.createTextNode(str
                                                       (approve_iras_obtain)))
                            record1.appendChild(ApprovalObtainedFromIRAS)

                            ApprovalDate = doc.createElement('ApprovalDate')
                            ApprovalDate.setAttribute('xmlns', 'http://www.iras.gov.sg/IR8A')
                            if approval_date:
                                ApprovalDate.appendChild(
                                    doc.createTextNode(str(approval_date)))
                            record1.appendChild(ApprovalDate)

                            CessationProvisions = doc.createElement('CessationProvisions')
                            CessationProvisions.setAttribute('xmlns', 'http://www.iras.gov.sg/IR8A')
                            if cessation_provisions_selection:
                                CessationProvisions.appendChild(
                                    doc.createTextNode(str(cessation_provisions_selection)))
                            record1.appendChild(CessationProvisions)

                            IR8SApplicable = doc.createElement('IR8SApplicable')
                            IR8SApplicable.setAttribute('xmlns',
                                                        'http://www.iras.gov.sg/IR8A')
                            if from_ir8s_selection:
                                IR8SApplicable.appendChild(doc.createTextNode(
                                    str(from_ir8s_selection)))
                            record1.appendChild(IR8SApplicable)

                            ExemptOrRemissionIncomeIndicator = doc.createElement('ExemptOrRemissionIncomeIndicator')
                            ExemptOrRemissionIncomeIndicator.setAttribute('xmlns',
                                                                          'http://www.iras.gov.sg/IR8A')
                            if exempt_remission_selection:
                                ExemptOrRemissionIncomeIndicator.appendChild(
                                    doc.createTextNode(str
                                                       (exempt_remission_selection)))
                            record1.appendChild(ExemptOrRemissionIncomeIndicator)

                            CompensationAndGratuity = doc.createElement(
                                'CompensationAndGratuity')
                            CompensationAndGratuity.setAttribute('xmlns',
                                                                 'http://www.iras.gov.sg/IR8A')
                            record1.appendChild(CompensationAndGratuity)

                            GrossCommissionAmount = doc.createElement(
                                'GrossCommissionAmount')
                            GrossCommissionAmount.setAttribute('xmlns',
                                                               'http://www.iras.gov.sg/IR8A')
                            if gross_commission:
                                GrossCommissionAmount.appendChild(
                                    doc.createTextNode(str(gross_commission)))
                            record1.appendChild(GrossCommissionAmount)

                            GrossCommissionPeriodFrom = doc.createElement(
                                'GrossCommissionPeriodFrom')
                            GrossCommissionPeriodFrom.setAttribute('xmlns',
                                                                   'http://www.iras.gov.sg/IR8A')
                            if period_date_start:
                                GrossCommissionPeriodFrom.appendChild(
                                    doc.createTextNode(str(period_date_start)))
                            record1.appendChild(GrossCommissionPeriodFrom)

                            GrossCommissionPeriodTo = doc.createElement(
                                'GrossCommissionPeriodTo')
                            GrossCommissionPeriodTo.setAttribute('xmlns',
                                                                 'http://www.iras.gov.sg/IR8A')
                            if period_date_end:
                                GrossCommissionPeriodTo.appendChild(
                                    doc.createTextNode(str(period_date_end)))
                            record1.appendChild(GrossCommissionPeriodTo)

                            GrossCommissionIndicator = doc.createElement(
                                'GrossCommissionIndicator')
                            GrossCommissionIndicator.setAttribute('xmlns',
                                                                  'http://www.iras.gov.sg/IR8A')
                            if gross_comm_indicator:
                                GrossCommissionIndicator.appendChild(
                                    doc.createTextNode(str
                                                       (gross_comm_indicator)))
                            record1.appendChild(GrossCommissionIndicator)

                            Pension = doc.createElement('Pension')
                            Pension.setAttribute('xmlns',
                                                 'http://www.iras.gov.sg/IR8A')
                            if pension:
                                Pension.appendChild(doc.createTextNode(str
                                                                       (pension)))
                            record1.appendChild(Pension)

                            TransportAllowance = doc.createElement(
                                'TransportAllowance')
                            TransportAllowance.setAttribute('xmlns',
                                                            'http://www.iras.gov.sg/IR8A')
                            if transport_allowance:
                                TransportAllowance.appendChild(
                                    doc.createTextNode(str
                                                       (transport_allowance)))
                            record1.appendChild(TransportAllowance)

                            EntertainmentAllowance = doc.createElement(
                                'EntertainmentAllowance')
                            EntertainmentAllowance.setAttribute('xmlns',
                                                                'http://www.iras.gov.sg/IR8A')
                            if entertainment_allowance:
                                EntertainmentAllowance.appendChild(
                                    doc.createTextNode(str
                                                       (entertainment_allowance)))
                            record1.appendChild(EntertainmentAllowance)

                            OtherAllowance = doc.createElement('OtherAllowance')
                            OtherAllowance.setAttribute('xmlns',
                                                        'http://www.iras.gov.sg/IR8A')
                            if other_allowance:
                                OtherAllowance.appendChild(
                                    doc.createTextNode(str(other_allowance)))
                            record1.appendChild(OtherAllowance)

                            GratuityNoticePymExGratia = doc.createElement(
                                'GratuityNoticePymExGratia')
                            GratuityNoticePymExGratia.setAttribute('xmlns',
                                                                   'http://www.iras.gov.sg/IR8A')
                            if gratuity_payment_amt:
                                GratuityNoticePymExGratia.appendChild(
                                    doc.createTextNode(str
                                                       (gratuity_payment_amt)))
                            record1.appendChild(GratuityNoticePymExGratia)

                            RetrenchmentBenefits = doc.createElement(
                                'RetrenchmentBenefits')
                            RetrenchmentBenefits.setAttribute('xmlns',
                                                              'http://www.iras.gov.sg/IR8A')
                            if compensation_loss_office:
                                RetrenchmentBenefits.appendChild(
                                    doc.createTextNode(str
                                                       (compensation_loss_office)))
                            record1.appendChild(RetrenchmentBenefits)

                            RetrenchmentBenefitsUpto311292 = doc.createElement(
                                'RetrenchmentBenefitsUpto311292')
                            RetrenchmentBenefitsUpto311292.setAttribute('xmlns',
                                                                        'http://www.iras.gov.sg/IR8A')
                            if retirement_benifit_up:
                                RetrenchmentBenefitsUpto311292.appendChild(
                                    doc.createTextNode(str
                                                       (retirement_benifit_up)))
                            record1.appendChild(RetrenchmentBenefitsUpto311292)

                            RetrenchmentBenefitsFrom1993 = doc.createElement(
                                'RetrenchmentBenefitsFrom1993')
                            RetrenchmentBenefitsFrom1993.setAttribute('xmlns',
                                                                      'http://www.iras.gov.sg/IR8A')
                            if retirement_benifit_from:
                                RetrenchmentBenefitsFrom1993.appendChild(
                                    doc.createTextNode(str
                                                       (retirement_benifit_from)))
                            record1.appendChild(RetrenchmentBenefitsFrom1993)

                            EmployerContributionToPensionOrPFOutsideSg = \
                                doc.createElement(
                                    'EmployerContributionToPensionOrPFOutsideSg')
                            EmployerContributionToPensionOrPFOutsideSg.setAttribute(
                                'xmlns', 'http://www.iras.gov.sg/IR8A')
                            if contribution_employer:
                                EmployerContributionToPensionOrPFOutsideSg.appendChild(
                                    doc.createTextNode(str(contribution_employer)))
                            record1.appendChild(
                                EmployerContributionToPensionOrPFOutsideSg)

                            ExcessEmployerContributionToCPF = doc.createElement(
                                'ExcessEmployerContributionToCPF')
                            ExcessEmployerContributionToCPF.setAttribute('xmlns',
                                                                         'http://www.iras.gov.sg/IR8A')
                            if excess_voluntary_contribution_cpf_employer:
                                ExcessEmployerContributionToCPF.appendChild(
                                    doc.createTextNode(str(
                                        excess_voluntary_contribution_cpf_employer)))
                            record1.appendChild(ExcessEmployerContributionToCPF)

                            ShareOptionGainsS101b = doc.createElement(
                                'ShareOptionGainsS101b')
                            ShareOptionGainsS101b.setAttribute('xmlns',
                                                               'http://www.iras.gov.sg/IR8A')
                            if gains_profit_share_option:
                                ShareOptionGainsS101b.appendChild(
                                    doc.createTextNode(str
                                                       (gains_profit_share_option)))
                            record1.appendChild(ShareOptionGainsS101b)

                            BenefitsInKindValue = doc.createElement(
                                'BenefitsInKindValue')
                            BenefitsInKindValue.setAttribute('xmlns',
                                                             'http://www.iras.gov.sg/IR8A')
                            if benifits_in_kinds:
                                BenefitsInKindValue.appendChild(
                                    doc.createTextNode(str(benifits_in_kinds)))
                            record1.appendChild(BenefitsInKindValue)

                            EmployeesVoluntaryContributionToCPF = \
                                doc.createElement(
                                    'EmployeesVoluntaryContributionToCPF')
                            EmployeesVoluntaryContributionToCPF.setAttribute(
                                'xmlns', 'http://www.iras.gov.sg/IR8A')
                            record1.appendChild(
                                EmployeesVoluntaryContributionToCPF)

                            Designation = doc.createElement('Designation')
                            Designation.setAttribute('xmlns',
                                                     'http://www.iras.gov.sg/IR8A')
                            if contract.employee_id.job_id and contract.employee_id.job_id.id:
                                Designation.appendChild(doc.createTextNode(str(
                                    contract.employee_id.job_id.name)))
                            record1.appendChild(Designation)

                            CommencementDate = doc.createElement(
                                'CommencementDate')
                            CommencementDate.setAttribute('xmlns',
                                                          'http://www.iras.gov.sg/IR8A')
                            if join_date:
                                CommencementDate.appendChild(
                                    doc.createTextNode(str(join_date)))
                            record1.appendChild(CommencementDate)

                            CessationDate = doc.createElement('CessationDate')
                            CessationDate.setAttribute('xmlns',
                                                       'http://www.iras.gov.sg/IR8A')
                            if cessation_date:
                                CessationDate.appendChild(doc.createTextNode(
                                    str(cessation_date)))
                            record1.appendChild(CessationDate)

                            BonusDecalrationDate = doc.createElement(
                                'BonusDecalrationDate')
                            BonusDecalrationDate.setAttribute('xmlns',
                                                              'http://www.iras.gov.sg/IR8A')
                            if bonus_declare_date:
                                BonusDecalrationDate.appendChild(
                                    doc.createTextNode(str
                                                       (bonus_declare_date)))
                            record1.appendChild(BonusDecalrationDate)

                            DirectorsFeesApprovalDate = doc.createElement(
                                'DirectorsFeesApprovalDate')
                            DirectorsFeesApprovalDate.setAttribute('xmlns',
                                                                   'http://www.iras.gov.sg/IR8A')
                            if approve_director_fee_date:
                                DirectorsFeesApprovalDate.appendChild(
                                    doc.createTextNode(str
                                                       (approve_director_fee_date)))
                            record1.appendChild(DirectorsFeesApprovalDate)

                            RetirementBenefitsFundName = doc.createElement(
                                'RetirementBenefitsFundName')
                            RetirementBenefitsFundName.setAttribute('xmlns',
                                                                    'http://www.iras.gov.sg/IR8A')
                            if emp.fund_name:
                                RetirementBenefitsFundName.appendChild(
                                    doc.createTextNode(str(emp.fund_name)))
                            record1.appendChild(RetirementBenefitsFundName)

                            DesignatedPensionOrProvidentFundName = \
                                doc.createElement(
                                    'DesignatedPensionOrProvidentFundName')
                            DesignatedPensionOrProvidentFundName.setAttribute(
                                'xmlns', 'http://www.iras.gov.sg/IR8A')
                            if emp.deginated_pension:
                                DesignatedPensionOrProvidentFundName.appendChild(
                                    doc.createTextNode(str(emp.deginated_pension)))
                            record1.appendChild(
                                DesignatedPensionOrProvidentFundName)

                            BankName = doc.createElement('BankName')
                            BankName.setAttribute('xmlns',
                                                  'http://www.iras.gov.sg/IR8A')
                            record1.appendChild(BankName)

                            PayrollDate = doc.createElement('PayrollDate')
                            PayrollDate.setAttribute('xmlns',
                                                     'http://www.iras.gov.sg/IR8A')
                            record1.appendChild(PayrollDate)

                            Filler = doc.createElement('Filler')
                            Filler.setAttribute('xmlns',
                                                'http://www.iras.gov.sg/IR8A')
                            record1.appendChild(Filler)

                            GratuityOrCompensationDetailedInfo = \
                                doc.createElement(
                                    'GratuityOrCompensationDetailedInfo')
                            GratuityOrCompensationDetailedInfo.setAttribute(
                                'xmlns', 'http://www.iras.gov.sg/IR8A')
                            record1.appendChild(
                                GratuityOrCompensationDetailedInfo)

                            ShareOptionGainsDetailedInfo = doc.createElement(
                                'ShareOptionGainsDetailedInfo')
                            ShareOptionGainsDetailedInfo.setAttribute('xmlns',
                                                                      'http://www.iras.gov.sg/IR8A')
                            record1.appendChild(ShareOptionGainsDetailedInfo)

                            Remarks = doc.createElement('Remarks')
                            Remarks.setAttribute('xmlns',
                                                 'http://www.iras.gov.sg/IR8A')
                            record1.appendChild(Remarks)

                tot_payment_amount = tot_salary_amt + tot_bonus_amt + tot_director_fee + tot_other_data
                total_detail_record = int(abs(total_detail_record))
                tot_payment_amount = int(abs(tot_payment_amount))
                tot_mbf_amt = int(abs(tot_mbf_amt))
                tot_donation_amt = int(abs(tot_donation_amt))
                tot_catemp_amt = int(abs(tot_catemp_amt))
                tot_net_amt = int(abs(tot_net_amt))
                tot_salary_amt = int(abs(tot_salary_amt))
                tot_bonus_amt = int(abs(tot_bonus_amt))
                tot_director_fee = int(abs(tot_director_fee))
                tot_other_data = int(abs(tot_other_data))
                tot_exempt_income = int(abs(tot_exempt_income))
                tot_employment_income = int(abs(tot_employment_income))
                tot_insurance = int(abs(tot_insurance))
                tot_employee_income = int(abs(tot_employee_income))

                IR8ATrailer = doc.createElement('IR8ATrailer')
                root.appendChild(IR8ATrailer)

                ESubmissionSDSC_t = doc.createElement('ESubmissionSDSC')
                ESubmissionSDSC_t.setAttribute('xmlns',
                                               'http://tempuri.org/ESubmissionSDSC.xsd')
                IR8ATrailer.appendChild(ESubmissionSDSC_t)

                record_t = doc.createElement('IR8ATrailerST')
                ESubmissionSDSC_t.appendChild(record_t)

                RecordType_t = doc.createElement('RecordType')
                RecordType_t.appendChild(doc.createTextNode('2'))
                record_t.appendChild(RecordType_t)

                NoOfRecords_t = doc.createElement('NoOfRecords')
                NoOfRecords_t.appendChild(doc.createTextNode(str
                                                             (total_detail_record)))
                record_t.appendChild(NoOfRecords_t)

                TotalPayment_t = doc.createElement('TotalPayment')
                TotalPayment_t.appendChild(doc.createTextNode(str
                                                              (tot_payment_amount)))
                record_t.appendChild(TotalPayment_t)

                TotalSalary_t = doc.createElement('TotalSalary')
                TotalSalary_t.appendChild(doc.createTextNode(str
                                                             (tot_salary_amt)))
                record_t.appendChild(TotalSalary_t)

                TotalBonus_t = doc.createElement('TotalBonus')
                TotalBonus_t.appendChild(doc.createTextNode(str
                                                            (tot_bonus_amt)))
                record_t.appendChild(TotalBonus_t)

                TotalDirectorsFees_t = doc.createElement('TotalDirectorsFees')
                TotalDirectorsFees_t.appendChild(doc.createTextNode(str
                                                                    (tot_director_fee)))
                record_t.appendChild(TotalDirectorsFees_t)

                TotalOthers_t = doc.createElement('TotalOthers')
                TotalOthers_t.appendChild(doc.createTextNode(str
                                                             (tot_other_data)))
                record_t.appendChild(TotalOthers_t)

                TotalExemptIncome_t = doc.createElement('TotalExemptIncome')
                TotalExemptIncome_t.appendChild(doc.createTextNode(str
                                                                   (tot_exempt_income)))
                record_t.appendChild(TotalExemptIncome_t)

                TotalIncomeForTaxBorneByEmployer_t = doc.createElement(
                    'TotalIncomeForTaxBorneByEmployer')
                TotalIncomeForTaxBorneByEmployer_t.appendChild(
                    doc.createTextNode(str(tot_employment_income)))
                record_t.appendChild(TotalIncomeForTaxBorneByEmployer_t)

                TotalIncomeForTaxBorneByEmployee_t = doc.createElement(
                    'TotalIncomeForTaxBorneByEmployee')
                TotalIncomeForTaxBorneByEmployee_t.appendChild(
                    doc.createTextNode(str(tot_employee_income)))
                record_t.appendChild(TotalIncomeForTaxBorneByEmployee_t)

                TotalDonation_t = doc.createElement('TotalDonation')
                TotalDonation_t.appendChild(doc.createTextNode(str
                                                               (tot_donation_amt)))
                record_t.appendChild(TotalDonation_t)

                TotalCPF_t = doc.createElement('TotalCPF')
                TotalCPF_t.appendChild(doc.createTextNode(str(tot_catemp_amt)))
                record_t.appendChild(TotalCPF_t)

                TotalInsurance_t = doc.createElement('TotalInsurance')
                TotalInsurance_t.appendChild(doc.createTextNode(str
                                                                (tot_insurance)))
                record_t.appendChild(TotalInsurance_t)

                TotalMBF_t = doc.createElement('TotalMBF')
                TotalMBF_t.appendChild(doc.createTextNode(str(tot_mbf_amt)))
                record_t.appendChild(TotalMBF_t)

                Filler_t = doc.createElement('Filler')
                record_t.appendChild(Filler_t)

                result = doc.toprettyxml(indent='   ')
                res = base64.b64encode(result.encode('UTF-8'))
                module_rec = self.env['binary.ir8a.xml.file.wizard'
                                      ].create({'name': 'IR8A.xml',
                                                'ir8a_xml_file': res})
                return {
                    'name': _('Binary'),
                    'res_id': module_rec.id,
                    "view_mode": 'form',
                    'res_model': 'binary.ir8a.xml.file.wizard',
                    'type': 'ir.actions.act_window',
                    'target': 'new',
                    'context': context,
                }
            elif data.get('print_type', '') == 'pdf':
                if not employee.bank_account_id or not employee.gender or not \
                    employee.birthday or not employee.identification_id or not \
                        (employee.work_phone or not employee.work_email):
                    raise ValidationError(
                        _("One of the following configuration is still missing from employee\'s profile.\nPlease configure all the "
                          "following details for employee %s. \n\n * Bank Account \n* Gender \n* Birth Day \n* "
                          "Identification No \n* Email or Contact " % (emp_name)))
                report_id = self.env.ref(
                    'sg_income_tax_report.ir8a_form_income_tax_report')
                return report_id.report_action(self, data=data, config=False)
        else:
            raise ValidationError("Please select employee")


class BinaryIr8aTextFileWizard(models.TransientModel):
    _name = 'binary.ir8a.text.file.wizard'
    _description = "ir8a text file"

    name = fields.Char('Name', default='IR8A.txt')
    ir8a_txt_file = fields.Binary(
        'Click On Download Link To Download File', readonly=True)


class BinaryIr8aXmlFileWizard(models.TransientModel):
    _name = 'binary.ir8a.xml.file.wizard'
    _description = "ir8a xml file"

    name = fields.Char('Name', default='IR8A.xml')
    ir8a_xml_file = fields.Binary('Click On Download Link To Download File',
                                  readonly=True)
