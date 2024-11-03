import time
import base64
import tempfile
from odoo.tools.misc import get_lang
from time import gmtime, strftime
from xml.dom import minidom
from dateutil.relativedelta import relativedelta

from odoo import tools
from odoo import fields, models, _
from odoo.exceptions import ValidationError


class EmpIr8sTextFile(models.TransientModel):
    _name = 'emp.ir8s.text.file'
    _description = "EmpIr8s TextFile"

    def _get_payroll_user_name(self):
        supervisors_list = [(False, '')]
        data_obj = self.env['ir.model.data']
        result_data = data_obj._get_id(
            'l10n_sg_hr_payroll', 'group_hr_payroll_admin')
        model_data = data_obj.browse(result_data)
        group_data = self.env['res.groups'].browse(model_data.res_id)
        for user in group_data.users:
            supervisors_list.append(
                (tools.ustr(user.id), tools.ustr(user.name)))
        return supervisors_list

    employee_ids = fields.Many2many(
        'hr.employee', 'hr_employe_ir8s_txt_rel', 'emp_id', 'employee_id',
        'Employee', required=True)
    start_date = fields.Date('Start Date', required=True,
                             default=lambda *a: time.strftime('%Y-01-01'))
    end_date = fields.Date('End Date', required=True,
                           default=lambda *a: time.strftime('%Y-12-31'))
    source = fields.Selection([('1', 'Mindef'),
                               ('2', 'Government Department'),
                               ('5', 'Statutory Board'),
                               ('6', 'Private Sector'),
                               ('9', 'Others')], 'Source',
                              default='6', required=True)
    batch_indicatior = fields.Selection([('O', 'Original'),
                                         ('A', 'Amendment')], default='O',
                                        string='Batch Indicator',
                                        required=True)
    batch_date = fields.Date('Batch Date', required=True)
    payroll_user = fields.Selection(_get_payroll_user_name,
                                    string='Name of authorised person',
                                    required=True)
    print_type = fields.Selection(selection=[('text', 'Text'),
                                             ('pdf', 'PDF'),
                                             ('xml', 'XML')],
                                  string='Print as', required=True,
                                  default='text')

    def download_ir8s_txt_file(self):
        context = dict(self._context) or {}
        context.update({'active_test': False})
        employee_obj = self.env['hr.employee']
        contract_obj = self.env['hr.contract']
        hr_contract_income_tax_obj = self.env['hr.contract.income.tax']
        payslip_obj = self.env['hr.payslip']
        data = self.read([])[0]
        emp_ids = data.get('employee_ids', []) or []

        if 'start_date' in data and 'end_date' in data and \
                data.get('start_date', False) >= data.get('end_date', False):
            raise ValidationError(
                _("You must be enter start date less than end date !"))

        date_start = data.get('start_date', False)
        date_end = data.get('end_date', False)
        start_date_year = date_start + relativedelta(month=1, day=1)
        end_date_year = date_end + relativedelta(month=12, day=31)
        start_date = start_date_year + relativedelta(years=-1)
        end_date = end_date_year + relativedelta(years=-1)

        if len(emp_ids) == 0:
            raise ValidationError(_("Please select employee"))
        for employee in employee_obj.browse(emp_ids):
            emp_name = employee and employee.name or ''
            emp_id = employee and employee.id or False
            check_error_str = _("One of the following configuration is still missing from employee\'s profile.\nPlease configure all the "
                      "following details for employee %s. \n" % (emp_name))
            check_emp_condition = False

            if not employee.bank_account_id:
                check_emp_condition = True
                check_error_str += "\n * Bank Account"
            if not employee.gender:
                check_emp_condition = True
                check_error_str += "\n * Gender"
            if not employee.birthday:
                check_emp_condition = True
                check_error_str += "\n * Birth Day"
            if not employee.identification_id:
                check_emp_condition = True
                check_error_str += "\n * Identification No"
            if not (employee.work_phone or not employee.work_email):
                check_emp_condition = True
                check_error_str += "\n * Email or Contact"

            if check_emp_condition:
                raise ValidationError(_(check_error_str))

            contract_ids = contract_obj.search([('employee_id', '=', emp_id)])
            contract_income_tax_rec = hr_contract_income_tax_obj.search([
                ('contract_id', 'in', contract_ids.ids),
                ('start_date', '>=', self.start_date),
                ('end_date', '<=', self.end_date)
            ])
            if not contract_income_tax_rec.ids:
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
                    _("There is no payslip details available between selected "
                      "date %s and %s for the %s employee." % (
                            self.start_date.strftime(
                                get_lang(self.env).date_format),
                            self.end_date.strftime(
                                get_lang(self.env).date_format), emp_name)))
        context.update({'employe_id': data['employee_ids'], 'datas': data})
        if data.get('print_type', '') == 'text':
            tgz_tmp_filename = tempfile.mktemp(suffix='.txt')
            tmp_file = current_year = False
            start_date = context.get('datas', {}).get('start_date', False)
            end_date = context.get('datas', {}).get('end_date', False)
            if start_date and end_date:
                current_year = start_date.year - 1
                start_date = start_date + relativedelta(month=1, day=1,
                                                        years=-1)
                end_date = end_date + relativedelta(month=12, day=31,
                                                    years=-1)
            try:
                tmp_file = open(tgz_tmp_filename, "w")
                server_date = strftime("%Y%m%d", gmtime())
                emp_id = employee_obj.search(
                    [('user_id', '=', int(context.get('datas')['payroll_user']
                                          ))])
                emp_designation = emp_email = emp_contact = ''
                emp_pay_user = self.env['res.users'].browse(
                    int(context.get('datas')['payroll_user']))
                payroll_admin_user_name = emp_pay_user.name
                company_name = emp_pay_user.company_id.name
                user_rec = self.env['res.users'].browse(self._uid)
                organization_id_type = user_rec.company_id.organization_id_type
                organization_id_no = user_rec.company_id.organization_id_no
                for emp in emp_id:
                    emp_designation = emp.job_id.name
                    emp_email = emp.work_email
                    emp_contact = emp.work_phone
                header_record = '0'.ljust(1) + \
                                tools.ustr(context.get('datas')['source'] or ''
                                           ).ljust(1) + \
                                tools.ustr(current_year or '').ljust(4) + \
                                tools.ustr(organization_id_type or ''
                                           ).ljust(1) + \
                                tools.ustr(organization_id_no or '').ljust(12
                                                                           ) +\
                                tools.ustr(payroll_admin_user_name or ''
                                           )[:30].ljust(30) + \
                                tools.ustr(emp_designation)[:30].ljust(30) + \
                                tools.ustr(company_name)[:60].ljust(60) + \
                                tools.ustr(emp_contact).ljust(20) + \
                                tools.ustr(emp_email).ljust(60) + \
                                tools.ustr(context.get('datas')[
                                    'batch_indicatior'] or '').ljust(1) + \
                                tools.ustr(server_date).ljust(8) + \
                                ''.ljust(30) + \
                                ''.ljust(10) + \
                                ''.ljust(932) + "\r\n"
                tmp_file.write(header_record)
                contract_ids = contract_obj.search(
                    [('employee_id', 'in', context.get('employe_id'))])
                for contract in contract_ids:
                    incometaxrec = hr_contract_income_tax_obj.search(
                        [('contract_id', '=', contract.id),
                         ('start_date', '>=', start_date_year),
                         ('end_date', '<=', end_date_year)
                         ])
                    for income_tax_rec in incometaxrec:
                        payslip_rec = payslip_obj.search([
                            ('date_from', '>=', start_date),
                            ('date_from', '<=', end_date),
                            ('employee_id', '=', contract.employee_id.id),
                            ('state', 'in', ['draft', 'done', 'verify'])])

                        jan_gross_amt = feb_gross_amt = march_gross_amt = \
                            apr_gross_amt = may_gross_amt = june_gross_amt = \
                            july_gross_amt = aug_gross_amt = sept_gross_amt = \
                            oct_gross_amt = nov_gross_amt = dec_gross_amt = 0
                        jan_empoyer_amt = feb_empoyer_amt = \
                            march_empoyer_amt = apr_empoyer_amt = \
                            may_empoyer_amt = june_empoyer_amt = \
                            july_empoyer_amt = aug_empoyer_amt = \
                            sept_empoyer_amt = oct_empoyer_amt = \
                            nov_empoyer_amt = dec_empoyer_amt = 0

                        jan_empoyee_amt = feb_empoyee_amt = \
                            march_empoyee_amt = apr_empoyee_amt = \
                            may_empoyee_amt = june_empoyee_amt = \
                            july_empoyee_amt = aug_empoyee_amt = \
                            sept_empoyee_amt = oct_empoyee_amt = \
                            nov_empoyee_amt = dec_empoyee_amt = 0

                        tot_gross_amt = tot_empoyee_amt = tot_empoyer_amt = 0

                        additional_wage_from_date = additional_wage_to_date =\
                            fromdate = todate = add_wage_date = \
                            eyer_date = eyee_date = ''

                        if income_tax_rec.start_date:
                            form_year = income_tax_rec.start_date.year - 1
                            fromdate = str(form_year) + \
                                income_tax_rec.start_date.strftime('%m%d')
                        if income_tax_rec.end_date:
                            to_year = income_tax_rec.end_date.year - 1
                            todate = str(to_year) +\
                                income_tax_rec.end_date.strftime('%m%d')
                        if income_tax_rec.add_wage_pay_date:
                            add_wage_date = (
                                income_tax_rec.add_wage_pay_date.strftime(
                                    '%Y%m%d'))
                        if income_tax_rec.refund_eyers_date:
                            eyer_date = (
                                income_tax_rec.refund_eyers_date.strftime(
                                    '%Y%m%d'))
                        if income_tax_rec.refund_eyees_date:
                            eyee_date = (
                                income_tax_rec.refund_eyees_date.strftime(
                                    '%Y%m%d'))

                        eyer_contibution = eyee_contibution =\
                            additional_wage = refund_eyers_contribution = \
                            refund_eyers_interest_contribution = \
                            refund_eyees_contribution = \
                            refund_eyees_interest_contribution = 0
                        eyer_contibution = '%0*d' % (
                            7, int(abs(income_tax_rec.eyer_contibution)))
                        eyee_contibution = '%0*d' % (
                            7, int(abs(income_tax_rec.eyee_contibution)))
                        additional_wage = '%0*d' % (
                            7, int(abs(income_tax_rec.additional_wage)))
                        refund_eyers_contribution = '%0*d' % (
                            7, int(abs(income_tax_rec.refund_eyers_contribution)))
                        refund_eyers_interest_contribution = '%0*d' % (
                            7, int(abs(income_tax_rec.refund_eyers_interest_contribution)))
                        refund_eyees_contribution = '%0*d' % (
                            7, int(abs(
                                income_tax_rec.refund_eyees_contribution)))
                        refund_eyees_interest_contribution = '%0*d' % (
                            7, int(abs(
                                income_tax_rec.refund_eyees_interest_contribution)))
                        if income_tax_rec.additional_wage:
                            additional_wage_from_date = fromdate
                            additional_wage_to_date = todate
                        for payslip in payslip_rec:
                            payslip_month = ''
                            payslip_month = payslip.date_from.strftime('%m')
                            gross_amt = empoyer_amt = empoyee_amt = 0
                            for line in payslip.line_ids:
                                if line.code == 'GROSS':
                                    gross_amt = line.total
                                if line.category_id.code == 'CAT_CPF_EMPLOYER':
                                    empoyer_amt += line.total
                                if line.category_id.code == 'CAT_CPF_EMPLOYEE':
                                    empoyee_amt += line.total
                            tot_gross_amt += gross_amt
                            tot_empoyer_amt += empoyer_amt
                            tot_empoyee_amt += empoyee_amt

                            if payslip_month == '01':
                                jan_gross_amt = gross_amt
                                jan_empoyer_amt = empoyer_amt
                                jan_empoyee_amt = empoyee_amt
                            if payslip_month == '02':
                                feb_gross_amt = gross_amt
                                feb_empoyer_amt = empoyer_amt
                                feb_empoyee_amt = empoyee_amt
                            if payslip_month == '03':
                                march_gross_amt = gross_amt
                                march_empoyer_amt = empoyer_amt
                                march_empoyee_amt = empoyee_amt
                            if payslip_month == '04':
                                apr_gross_amt = gross_amt
                                apr_empoyer_amt = empoyer_amt
                                apr_empoyee_amt = empoyee_amt
                            if payslip_month == '05':
                                may_gross_amt = gross_amt
                                may_empoyer_amt = empoyer_amt
                                may_empoyee_amt = empoyee_amt
                            if payslip_month == '06':
                                june_gross_amt = gross_amt
                                june_empoyer_amt = empoyer_amt
                                june_empoyee_amt = empoyee_amt
                            if payslip_month == '07':
                                july_gross_amt = gross_amt
                                july_empoyer_amt = empoyer_amt
                                july_empoyee_amt = empoyee_amt
                            if payslip_month == '08':
                                aug_gross_amt = gross_amt
                                aug_empoyer_amt = empoyer_amt
                                aug_empoyee_amt = empoyee_amt
                            if payslip_month == '09':
                                sept_gross_amt = gross_amt
                                sept_empoyer_amt = empoyer_amt
                                sept_empoyee_amt = empoyee_amt
                            if payslip_month == '10':
                                oct_gross_amt = gross_amt
                                oct_empoyer_amt = empoyer_amt
                                oct_empoyee_amt = empoyee_amt
                            if payslip_month == '11':
                                nov_gross_amt = gross_amt
                                nov_empoyer_amt = empoyer_amt
                                nov_empoyee_amt = empoyee_amt
                            if payslip_month == '12':
                                dec_gross_amt = gross_amt
                                dec_empoyer_amt = empoyer_amt
                                dec_empoyee_amt = empoyee_amt

                        jan_gross_amt = '%0*d' % (9,
                                                  int(abs(
                                                      jan_gross_amt * 100)))
                        jan_empoyer_amt = '%0*d' % (9,
                                                    int(abs(
                                                        jan_empoyer_amt * 100)
                                                        ))
                        jan_empoyee_amt = '%0*d' % (9,
                                                    int(abs(
                                                        jan_empoyee_amt * 100)
                                                        ))

                        feb_gross_amt = '%0*d' % (9,
                                                  int(abs(
                                                      feb_gross_amt * 100)))
                        feb_empoyer_amt = '%0*d' % (9,
                                                    int(abs(
                                                        feb_empoyer_amt * 100)
                                                        ))
                        feb_empoyee_amt = '%0*d' % (9,
                                                    int(abs(
                                                        feb_empoyee_amt * 100)
                                                        ))

                        march_gross_amt = '%0*d' % (9,
                                                    int(abs(
                                                        march_gross_amt * 100)
                                                        ))
                        march_empoyer_amt = '%0*d' % (9, int(abs(
                            march_empoyer_amt * 100)))
                        march_empoyee_amt = '%0*d' % (9, int(abs(
                                                      march_empoyee_amt * 100)))

                        apr_gross_amt = '%0*d' % (9, int(abs(
                                                      apr_gross_amt * 100)))
                        apr_empoyer_amt = '%0*d' % (9, int(abs(
                                                    apr_empoyer_amt * 100)))
                        apr_empoyee_amt = '%0*d' % (9, int(abs(
                                                    apr_empoyee_amt * 100)))

                        may_gross_amt = '%0*d' % (9, int(abs(
                                                      may_gross_amt * 100)))
                        may_empoyer_amt = '%0*d' % (9, int(abs(
                                                    may_empoyer_amt * 100)))
                        may_empoyee_amt = '%0*d' % (9, int(abs(
                                                    may_empoyee_amt * 100)))

                        june_gross_amt = '%0*d' % (9, int(abs(
                                                   june_gross_amt * 100)))
                        june_empoyer_amt = '%0*d' % (9, int(abs(
                                                     june_empoyer_amt * 100)))
                        june_empoyee_amt = '%0*d' % (9, int(abs(
                                                     june_empoyee_amt * 100)))

                        july_gross_amt = '%0*d' % (9, int(abs(
                                                       july_gross_amt * 100)))
                        july_empoyer_amt = '%0*d' % (9, int(abs(
                                                     july_empoyer_amt * 100)))
                        july_empoyee_amt = '%0*d' % (9, int(abs(
                                                     july_empoyee_amt * 100)))

                        aug_gross_amt = '%0*d' % (9, int(abs(
                                                      aug_gross_amt * 100)))
                        aug_empoyer_amt = '%0*d' % (9, int(abs(
                                                    aug_empoyer_amt * 100)))
                        aug_empoyee_amt = '%0*d' % (9, int(abs(
                                                    aug_empoyee_amt * 100)))

                        sept_gross_amt = '%0*d' % (9, int(abs(
                                                       sept_gross_amt * 100)))
                        sept_empoyer_amt = '%0*d' % (9, int(abs(
                                                     sept_empoyer_amt * 100)))
                        sept_empoyee_amt = '%0*d' % (9, int(abs(
                                                     sept_empoyee_amt * 100)))

                        oct_gross_amt = '%0*d' % (9, int(abs(
                                                      oct_gross_amt * 100)))
                        oct_empoyer_amt = '%0*d' % (9, int(abs(
                                                    oct_empoyer_amt * 100)))
                        oct_empoyee_amt = '%0*d' % (9, int(abs(
                                                    oct_empoyee_amt * 100)))

                        nov_gross_amt = '%0*d' % (9, int(abs(
                                                      nov_gross_amt * 100)))
                        nov_empoyer_amt = '%0*d' % (9, int(abs(
                                                    nov_empoyer_amt * 100)))
                        nov_empoyee_amt = '%0*d' % (9, int(abs(
                                                    nov_empoyee_amt * 100)))

                        dec_gross_amt = '%0*d' % (9, int(abs(
                                                      dec_gross_amt * 100)))
                        dec_empoyer_amt = '%0*d' % (9, int(abs(
                                                    dec_empoyer_amt * 100)))
                        dec_empoyee_amt = '%0*d' % (9, int(abs(
                                                    dec_empoyee_amt * 100)))

                        tot_gross_amt = '%0*d' % (7, int(abs(tot_gross_amt)))
                        tot_empoyer_amt = '%0*d' % (7,
                                                    int(abs(tot_empoyer_amt)))
                        tot_empoyee_amt = '%0*d' % (7,
                                                    int(abs(tot_empoyee_amt)))
                        detail_record = '1'.ljust(1) + \
                                        tools.ustr(
                                        contract.employee_id.identification_no
                                         or '').ljust(1) + \
                                        tools.ustr(
                                        contract.employee_id.identification_id
                                         or '')[:12].ljust(12) + \
                                        tools.ustr(contract.employee_id.name
                                                   or '')[:80].ljust(80) + \
                                        tools.ustr(
                                            jan_gross_amt)[:9].ljust(9) + \
                                        tools.ustr(
                                            jan_empoyer_amt)[:9].ljust(9) + \
                                        tools.ustr(
                                            jan_empoyee_amt)[:9].ljust(9) + \
                                        ''.ljust(9) + \
                                        ''.ljust(9) + \
                                        ''.ljust(9) + \
                                        tools.ustr(
                                            feb_gross_amt)[:9].ljust(9) + \
                                        tools.ustr(
                                            feb_empoyer_amt)[:9].ljust(9) + \
                                        tools.ustr(
                                            feb_empoyee_amt)[:9].ljust(9) + \
                                        ''.ljust(9) + \
                                        ''.ljust(9) + \
                                        ''.ljust(9) + \
                                        tools.ustr(
                                            march_gross_amt)[:9].ljust(9) + \
                                        tools.ustr(
                                            march_empoyer_amt)[:9].ljust(9) + \
                                        tools.ustr(
                                            march_empoyee_amt)[:9].ljust(9) + \
                                        ''.ljust(9) + \
                                        ''.ljust(9) + \
                                        ''.ljust(9) + \
                                        tools.ustr(
                                            apr_gross_amt)[:9].ljust(9) + \
                                        tools.ustr(
                                            apr_empoyer_amt)[:9].ljust(9) + \
                                        tools.ustr(
                                            apr_empoyee_amt)[:9].ljust(9) + \
                                        ''.ljust(9) + \
                                        ''.ljust(9) + \
                                        ''.ljust(9) + \
                                        tools.ustr(
                                            may_gross_amt)[:9].ljust(9) + \
                                        tools.ustr(
                                            may_empoyer_amt)[:9].ljust(9) + \
                                        tools.ustr(
                                            may_empoyee_amt)[:9].ljust(9) + \
                                        ''.ljust(9) + \
                                        ''.ljust(9) + \
                                        ''.ljust(9) + \
                                        tools.ustr(
                                            june_gross_amt)[:9].ljust(9) + \
                                        tools.ustr(
                                            june_empoyer_amt)[:9].ljust(9) + \
                                        tools.ustr(
                                            june_empoyee_amt)[:9].ljust(9) + \
                                        ''.ljust(9) + \
                                        ''.ljust(9) + \
                                        ''.ljust(9) + \
                                        tools.ustr(
                                            july_gross_amt)[:9].ljust(9) + \
                                        tools.ustr(
                                            july_empoyer_amt)[:9].ljust(9) + \
                                        tools.ustr(
                                            july_empoyee_amt)[:9].ljust(9) + \
                                        ''.ljust(9) + \
                                        ''.ljust(9) + \
                                        ''.ljust(9) + \
                                        tools.ustr(
                                            aug_gross_amt)[:9].ljust(9) + \
                                        tools.ustr(
                                            aug_empoyer_amt)[:9].ljust(9) + \
                                        tools.ustr(
                                            aug_empoyee_amt)[:9].ljust(9) + \
                                        ''.ljust(9) + \
                                        ''.ljust(9) + \
                                        ''.ljust(9) + \
                                        tools.ustr(
                                            sept_gross_amt)[:9].ljust(9) + \
                                        tools.ustr(
                                            sept_empoyer_amt)[:9].ljust(9) + \
                                        tools.ustr(
                                            sept_empoyee_amt)[:9].ljust(9) + \
                                        ''.ljust(9) + \
                                        ''.ljust(9) + \
                                        ''.ljust(9) + \
                                        tools.ustr(
                                            oct_gross_amt)[:9].ljust(9) + \
                                        tools.ustr(
                                            oct_empoyer_amt)[:9].ljust(9) + \
                                        tools.ustr(
                                            oct_empoyee_amt)[:9].ljust(9) + \
                                        ''.ljust(9) + \
                                        ''.ljust(9) + \
                                        ''.ljust(9) + \
                                        tools.ustr(
                                            nov_gross_amt)[:9].ljust(9) + \
                                        tools.ustr(
                                            nov_empoyer_amt)[:9].ljust(9) + \
                                        tools.ustr(
                                            nov_empoyee_amt)[:9].ljust(9) + \
                                        ''.ljust(9) + \
                                        ''.ljust(9) + \
                                        ''.ljust(9) + \
                                        tools.ustr(
                                            dec_gross_amt)[:9].ljust(9) + \
                                        tools.ustr(
                                            dec_empoyer_amt)[:9].ljust(9) + \
                                        tools.ustr(
                                            dec_empoyee_amt)[:9].ljust(9) + \
                                        ''.ljust(9) + \
                                        ''.ljust(9) + \
                                        ''.ljust(9) + \
                                        tools.ustr(
                                            tot_gross_amt)[:7].ljust(7) + \
                                        tools.ustr(
                                            tot_empoyer_amt)[:7].ljust(7) + \
                                        tools.ustr(
                                            tot_empoyee_amt)[:7].ljust(7) + \
                                        ''.ljust(7) + \
                                        ''.ljust(7) + \
                                        ''.ljust(7) + \
                                        tools.ustr('').ljust(8) + \
                                        tools.ustr('').ljust(8) + \
                                        tools.ustr('').ljust(1) + \
                                        tools.ustr('').ljust(1) + \
                                        tools.ustr(
                                        income_tax_rec.singapore_permanent_resident_status\
                                         or '').ljust(1) + \
                                        tools.ustr(
                                        income_tax_rec.approval_has_been_obtained_CPF_board\
                                         or '').ljust(1) + \
                                        tools.ustr(
                                            eyer_contibution)[:7].ljust(7) + \
                                        tools.ustr(
                                            eyee_contibution)[:7].ljust(7) + \
                                        tools.ustr(
                                            additional_wage)[:7].ljust(7) + \
                                        tools.ustr(
                                        additional_wage_from_date).ljust(8) + \
                                        tools.ustr(
                                        additional_wage_to_date).ljust(8) + \
                                        tools.ustr(add_wage_date).ljust(8) + \
                                        tools.ustr(
                                        refund_eyers_contribution)[:7].ljust(7) + \
                                        tools.ustr(
                                        refund_eyers_interest_contribution)\
                                        [:7].ljust(7) + \
                                        tools.ustr(eyer_date).ljust(8) + \
                                        tools.ustr(
                                        refund_eyees_contribution)\
                                        [:7].ljust(7) + \
                                        tools.ustr(
                                        refund_eyees_interest_contribution)\
                                        [:7].ljust(7) + \
                                        tools.ustr(eyee_date).ljust(8) + \
                                        tools.ustr(
                                        additional_wage)[:7].ljust(7) + \
                                        tools.ustr(
                                        additional_wage_from_date).ljust(8) + \
                                        tools.ustr(
                                        additional_wage_to_date).ljust(8) + \
                                        tools.ustr(add_wage_date).ljust(8) + \
                                        tools.ustr(
                                        refund_eyers_contribution)\
                                        [:7].ljust(7) + \
                                        tools.ustr(
                                        refund_eyers_interest_contribution)\
                                        [:7].ljust(7) + \
                                        tools.ustr(eyer_date).ljust(8) + \
                                        tools.ustr(
                                        refund_eyees_contribution)\
                                        [:7].ljust(7) + \
                                        tools.ustr(
                                        refund_eyees_interest_contribution)\
                                        [:7].ljust(7) + \
                                        tools.ustr(eyee_date).ljust(8) + \
                                        tools.ustr(
                                            additional_wage)[:7].ljust(7) + \
                                        tools.ustr(
                                        additional_wage_from_date).ljust(8) + \
                                        tools.ustr(
                                        additional_wage_to_date).ljust(8) + \
                                        tools.ustr(add_wage_date).ljust(8) + \
                                        tools.ustr(
                                        refund_eyers_contribution)\
                                        [:7].ljust(7) + \
                                        tools.ustr(
                                        refund_eyers_interest_contribution)\
                                        [:7].ljust(7) + \
                                        tools.ustr(eyer_date).ljust(8) + \
                                        tools.ustr(
                                        refund_eyees_contribution)\
                                        [:7].ljust(7) + \
                                        tools.ustr(
                                        refund_eyees_interest_contribution)\
                                        [:7].ljust(7) + \
                                        tools.ustr(eyee_date).ljust(8) + \
                                        ''.ljust(107) + \
                                        ''.ljust(50) + \
                            "\r\n"
                        tmp_file.write(detail_record)
            finally:
                if tmp_file:
                    tmp_file.close()
            ir8s_file = open(tgz_tmp_filename, "rb")
            out = ir8s_file.read()
            ir8s_file.close()
            res = base64.b64encode(out)
            module_rec = self.env['binary.ir8s.text.file.wizard'].create(
                {'name': 'IR8S.txt', 'ir8s_txt_file': res})
            return {
                'name': _('Binary'),
                'res_id': module_rec.id,
                "view_mode": 'form',
                'res_model': 'binary.ir8s.text.file.wizard',
                'type': 'ir.actions.act_window',
                'target': 'new',
                'context': context}
        elif data.get('print_type', '') == 'xml':

            doc = minidom.Document()
            root = doc.createElement('IR8S')
            root.setAttribute('xmlns', 'http://www.iras.gov.sg/IR8SDef')
            doc.appendChild(root)

            current_year = False
            start_date = context.get('datas').get('start_date', False) or False
            end_date = context.get('datas').get('end_date', False) or False
            if start_date and end_date:
                current_year = start_date.year - 1
                start_date = start_date + relativedelta(month=1, day=1,
                                                        years=-1)
                end_date = end_date + relativedelta(month=12, day=31,
                                                    years=-1)

            server_date = strftime("%Y%m%d", gmtime())
            emp_id = employee_obj.search([
                ('user_id', '=', int(context.get('datas')['payroll_user']))])
            emp_designation = emp_email = emp_contact = ''
            emp_pay_user = self.env['res.users'].browse(
                int(context.get('datas')['payroll_user']))
            payroll_admin_user_name = emp_pay_user.name
            company_name = emp_pay_user.company_id.name
            user_rec = self.env['res.users'].browse(self._uid)
            organization_id_type = user_rec.company_id.organization_id_type
            organization_id_no = user_rec.company_id.organization_id_no
            for emp in emp_id:
                emp_designation = emp.job_id.name
                emp_email = emp.work_email
                emp_contact = emp.work_phone
                if not emp_email and not emp_contact:
                    raise ValidationError(
                        _("Please configure Email or Contact for %s employee." % (emp.name)))

            """ Header for IR8S """

            header = doc.createElement('IR8SHeader')
            root.appendChild(header)

            ESubmissionSDSC = doc.createElement('ESubmissionSDSC')
            ESubmissionSDSC.setAttribute('xmlns',
                                     'http://tempuri.org/ESubmissionSDSC.xsd')
            header.appendChild(ESubmissionSDSC)

            FileHeaderST = doc.createElement('FileHeaderST')
            ESubmissionSDSC.appendChild(FileHeaderST)

            RecordType = doc.createElement('RecordType')
            RecordType.appendChild(doc.createTextNode('0'))
            FileHeaderST.appendChild(RecordType)

            Source = doc.createElement('Source')
            if context.get('datas') and context.get('datas')['source']:
                Source.appendChild(doc.createTextNode(
                                            context.get('datas')['source']))
            FileHeaderST.appendChild(Source)

            BasisYear = doc.createElement('BasisYear')
            if current_year:
                BasisYear.appendChild(doc.createTextNode(str(current_year)))
            FileHeaderST.appendChild(BasisYear)

            OrganizationID = doc.createElement('OrganizationID')
            if organization_id_type:
                OrganizationID.appendChild(doc.createTextNode(str(
                                                        organization_id_type)))
            FileHeaderST.appendChild(OrganizationID)

            OrganizationIDNo = doc.createElement('OrganizationIDNo')
            if organization_id_no:
                OrganizationIDNo.appendChild(doc.createTextNode(
                                                        organization_id_no))
            FileHeaderST.appendChild(OrganizationIDNo)

            AuthorisedPersonName = doc.createElement('AuthorisedPersonName')
            if payroll_admin_user_name:
                AuthorisedPersonName.appendChild(doc.createTextNode(str(
                                                    payroll_admin_user_name)))
            FileHeaderST.appendChild(AuthorisedPersonName)

            AuthorisedPersonDesignation = doc.createElement(
                                                'AuthorisedPersonDesignation')
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
            if context.get('datas') and context.get('datas')[
                    'batch_indicatior']:
                BatchIndicator.appendChild(doc.createTextNode(str(
                                    context.get('datas')['batch_indicatior'])))
            FileHeaderST.appendChild(BatchIndicator)

            BatchDate = doc.createElement('BatchDate')
            if server_date:
                BatchDate.appendChild(doc.createTextNode(str(server_date)))
            FileHeaderST.appendChild(BatchDate)

            DivisionOrBranchName = doc.createElement('DivisionOrBranchName')
            FileHeaderST.appendChild(DivisionOrBranchName)

            Details = doc.createElement('Details')
            root.appendChild(Details)

            contract_ids = contract_obj.search([
                ('employee_id', 'in', context.get('employe_id'))])
            for contract in contract_ids:
                contract_income_tax_rec = hr_contract_income_tax_obj.search([
                    ('contract_id', '=', contract.id),
                    ('start_date', '>=', start_date_year),
                    ('end_date', '<=', end_date_year)])
                for income_tax_rec in contract_income_tax_rec:
                    payslip_rec = payslip_obj.search([
                        ('date_from', '>=', start_date),
                        ('date_from', '<=', end_date),
                        ('employee_id', '=', contract.employee_id.id),
                        ('state', 'in', ['draft', 'done', 'verify'])])
                    jan_gross_amt = feb_gross_amt = march_gross_amt = \
                        apr_gross_amt = may_gross_amt = june_gross_amt = \
                        july_gross_amt = aug_gross_amt = sept_gross_amt = \
                        oct_gross_amt = nov_gross_amt = dec_gross_amt = 0

                    jan_empoyer_amt = feb_empoyer_amt = march_empoyer_amt =\
                        apr_empoyer_amt = may_empoyer_amt = june_empoyer_amt =\
                        july_empoyer_amt = aug_empoyer_amt =\
                        sept_empoyer_amt = oct_empoyer_amt = nov_empoyer_amt =\
                        dec_empoyer_amt = 0

                    jan_empoyee_amt = feb_empoyee_amt = march_empoyee_amt =\
                        apr_empoyee_amt = may_empoyee_amt = june_empoyee_amt =\
                        july_empoyee_amt = aug_empoyee_amt =\
                        sept_empoyee_amt = oct_empoyee_amt = nov_empoyee_amt =\
                        dec_empoyee_amt = 0

                    tot_gross_amt = tot_empoyee_amt = tot_empoyer_amt = 0

                    additional_wage_from_date = additional_wage_to_date = \
                        fromdate = todate = add_wage_date = eyer_date =\
                        eyee_date = ''

                    if income_tax_rec.start_date:
                        form_year = income_tax_rec.start_date.year - 1
                        fromdate = str(form_year) +\
                            income_tax_rec.start_date.strftime('%m%d')
                    if income_tax_rec.end_date:
                        to_year = income_tax_rec.end_date.year - 1
                        todate = str(to_year) +\
                            income_tax_rec.end_date.strftime('%m%d')
                    if income_tax_rec.add_wage_pay_date:
                        add_wage_date = (
                            income_tax_rec.add_wage_pay_date.strftime('%Y%m%d')
                            )
                    if income_tax_rec.refund_eyers_date:
                        eyer_date = income_tax_rec.refund_eyers_date.strftime(
                            '%Y%m%d')
                    if income_tax_rec.refund_eyees_date:
                        eyee_date = income_tax_rec.refund_eyees_date.strftime(
                            '%Y%m%d')

                    eyer_contibution = eyee_contibution = additional_wage = \
                        refund_eyers_contribution = \
                        refund_eyers_interest_contribution = \
                        refund_eyees_contribution = \
                        refund_eyees_interest_contribution = 0

                    eyer_contibution = int(abs(income_tax_rec.eyer_contibution)
                                           )
                    eyee_contibution = int(abs(income_tax_rec.eyee_contibution)
                                           )
                    additional_wage = int(abs(income_tax_rec.additional_wage))
                    refund_eyers_contribution = int(abs(
                                    income_tax_rec.refund_eyers_contribution))
                    refund_eyers_interest_contribution = int(abs(
                            income_tax_rec.refund_eyers_interest_contribution))
                    refund_eyees_contribution = int(abs(
                                    income_tax_rec.refund_eyees_contribution))
                    refund_eyees_interest_contribution = int(abs(
                            income_tax_rec.refund_eyees_interest_contribution))
                    if income_tax_rec.additional_wage:
                        additional_wage_from_date = fromdate
                        additional_wage_to_date = todate
                    for payslip in payslip_rec:
                        payslip_month = ''
                        payslip_month = payslip.date_from.strftime('%m')
                        gross_amt = empoyer_amt = empoyee_amt = 0
                        for line in payslip.line_ids:
                            if line.code == 'GROSS':
                                gross_amt = line.total
                            if line.category_id.code == 'CAT_CPF_EMPLOYER':
                                empoyer_amt += line.total
                            if line.category_id.code == 'CAT_CPF_EMPLOYEE':
                                empoyee_amt += line.total
                        tot_gross_amt += gross_amt
                        tot_empoyer_amt += empoyer_amt
                        tot_empoyee_amt += empoyee_amt

                        if payslip_month == '01':
                            jan_gross_amt = gross_amt
                            jan_empoyer_amt = empoyer_amt
                            jan_empoyee_amt = empoyee_amt
                        elif payslip_month == '02':
                            feb_gross_amt = gross_amt
                            feb_empoyer_amt = empoyer_amt
                            feb_empoyee_amt = empoyee_amt
                        elif payslip_month == '03':
                            march_gross_amt = gross_amt
                            march_empoyer_amt = empoyer_amt
                            march_empoyee_amt = empoyee_amt
                        elif payslip_month == '04':
                            apr_gross_amt = gross_amt
                            apr_empoyer_amt = empoyer_amt
                            apr_empoyee_amt = empoyee_amt
                        elif payslip_month == '05':
                            may_gross_amt = gross_amt
                            may_empoyer_amt = empoyer_amt
                            may_empoyee_amt = empoyee_amt
                        elif payslip_month == '06':
                            june_gross_amt = gross_amt
                            june_empoyer_amt = empoyer_amt
                            june_empoyee_amt = empoyee_amt
                        elif payslip_month == '07':
                            july_gross_amt = gross_amt
                            july_empoyer_amt = empoyer_amt
                            july_empoyee_amt = empoyee_amt
                        elif payslip_month == '08':
                            aug_gross_amt = gross_amt
                            aug_empoyer_amt = empoyer_amt
                            aug_empoyee_amt = empoyee_amt
                        elif payslip_month == '09':
                            sept_gross_amt = gross_amt
                            sept_empoyer_amt = empoyer_amt
                            sept_empoyee_amt = empoyee_amt
                        elif payslip_month == '10':
                            oct_gross_amt = gross_amt
                            oct_empoyer_amt = empoyer_amt
                            oct_empoyee_amt = empoyee_amt
                        elif payslip_month == '11':
                            nov_gross_amt = gross_amt
                            nov_empoyer_amt = empoyer_amt
                            nov_empoyee_amt = empoyee_amt
                        elif payslip_month == '12':
                            dec_gross_amt = gross_amt
                            dec_empoyer_amt = empoyer_amt
                            dec_empoyee_amt = empoyee_amt

                    jan_gross_amt = jan_gross_amt
                    jan_empoyer_amt = jan_empoyer_amt
                    jan_empoyee_amt = jan_empoyee_amt

                    feb_gross_amt = feb_gross_amt
                    feb_empoyer_amt = feb_empoyer_amt
                    feb_empoyee_amt = feb_empoyee_amt

                    march_gross_amt = march_gross_amt
                    march_empoyer_amt = march_empoyer_amt
                    march_empoyee_amt = march_empoyee_amt

                    apr_gross_amt = apr_gross_amt
                    apr_empoyer_amt = apr_empoyer_amt
                    apr_empoyee_amt = apr_empoyee_amt

                    may_gross_amt = may_gross_amt
                    may_empoyer_amt = may_empoyer_amt
                    may_empoyee_amt = may_empoyee_amt

                    june_gross_amt = june_gross_amt
                    june_empoyer_amt = june_empoyer_amt
                    june_empoyee_amt = june_empoyee_amt

                    july_gross_amt = july_gross_amt
                    july_empoyer_amt = july_empoyer_amt
                    july_empoyee_amt = july_empoyee_amt

                    aug_gross_amt = aug_gross_amt
                    aug_empoyer_amt = aug_empoyer_amt
                    aug_empoyee_amt = aug_empoyee_amt

                    sept_gross_amt = sept_gross_amt
                    sept_empoyer_amt = sept_empoyer_amt
                    sept_empoyee_amt = sept_empoyee_amt

                    oct_gross_amt = oct_gross_amt
                    oct_empoyer_amt = oct_empoyer_amt
                    oct_empoyee_amt = oct_empoyee_amt

                    nov_gross_amt = nov_gross_amt
                    nov_empoyer_amt = nov_empoyer_amt
                    nov_empoyee_amt = nov_empoyee_amt

                    dec_gross_amt = dec_gross_amt
                    dec_empoyer_amt = dec_empoyer_amt
                    dec_empoyee_amt = dec_empoyee_amt

                    tot_gross_amt = tot_gross_amt
                    tot_empoyer_amt = tot_empoyer_amt
                    tot_empoyee_amt = tot_empoyee_amt

                    IR8SRecord = doc.createElement('IR8SRecord')
                    Details.appendChild(IR8SRecord)

                    ESubmissionSDSC = doc.createElement('ESubmissionSDSC')
                    ESubmissionSDSC.setAttribute('xmlns',
                                     'http://tempuri.org/ESubmissionSDSC.xsd')
                    IR8SRecord.appendChild(ESubmissionSDSC)

                    record1 = doc.createElement('IR8SST')
                    ESubmissionSDSC.appendChild(record1)

                    RecordType = doc.createElement('RecordType')
                    RecordType.setAttribute('xmlns',
                                            'http://www.iras.gov.sg/IR8S')
                    RecordType.appendChild(doc.createTextNode('1'))
                    record1.appendChild(RecordType)

                    IDType = doc.createElement('IDType')
                    IDType.setAttribute('xmlns', 'http://www.iras.gov.sg/IR8S')
                    if contract.employee_id.identification_no:
                        IDType.appendChild(doc.createTextNode(str(
                                    contract.employee_id.identification_no)))
                    record1.appendChild(IDType)

                    IDNo = doc.createElement('IDNo')
                    IDNo.setAttribute('xmlns', 'http://www.iras.gov.sg/IR8S')
                    if contract.employee_id.identification_id:
                        IDNo.appendChild(doc.createTextNode(str(
                                    contract.employee_id.identification_id)))
                    record1.appendChild(IDNo)

                    NameLine1 = doc.createElement('NameLine1')
                    NameLine1.setAttribute('xmlns',
                                           'http://www.iras.gov.sg/IR8S')
                    if contract.employee_id.name:
                        NameLine1.appendChild(doc.createTextNode(str(
                                                contract.employee_id.name)))
                    record1.appendChild(NameLine1)

                    NameLine2 = doc.createElement('NameLine2')
                    NameLine2.setAttribute('xmlns',
                                                'http://www.iras.gov.sg/IR8S')
                    record1.appendChild(NameLine2)

                    JanOW1 = doc.createElement('JanuaryOrdinaryWages')
                    JanOW1.setAttribute('xmlns', 'http://www.iras.gov.sg/IR8S')
                    if jan_gross_amt:
                        JanOW1.appendChild(doc.createTextNode(
                                                        str(jan_gross_amt)))
                    record1.appendChild(JanOW1)

                    JanOW2 = doc.createElement(
                                'JanuaryEmployersContributionToCPFOrdWages')
                    JanOW2.setAttribute('xmlns', 'http://www.iras.gov.sg/IR8S')
                    if jan_empoyer_amt:
                        JanOW2.appendChild(doc.createTextNode(str(
                                                            jan_empoyer_amt)))
                    record1.appendChild(JanOW2)

                    JanOW3 = doc.createElement(
                                'JanuaryEmployeesContributionToCPFOrdWages')
                    JanOW3.setAttribute('xmlns', 'http://www.iras.gov.sg/IR8S')
                    if jan_empoyee_amt:
                        JanOW3.appendChild(doc.createTextNode(str(
                                                            jan_empoyee_amt)))
                    record1.appendChild(JanOW3)

                    JanOW4 = doc.createElement('JanuaryAdditionalWages')
                    JanOW4.setAttribute('xmlns', 'http://www.iras.gov.sg/IR8S')
                    record1.appendChild(JanOW4)

                    JanOW5 = doc.createElement(
                                'JanuaryEmployersContributionToCPFAddWages')
                    JanOW5.setAttribute('xmlns', 'http://www.iras.gov.sg/IR8S')
                    record1.appendChild(JanOW5)

                    JanOW6 = doc.createElement(
                                'JanuaryEmployeesContributionToCPFAddWages')
                    JanOW6.setAttribute('xmlns', 'http://www.iras.gov.sg/IR8S')
                    record1.appendChild(JanOW6)


                    febOW1 = doc.createElement('FebruaryOrdinaryWages')
                    febOW1.setAttribute('xmlns', 'http://www.iras.gov.sg/IR8S')
                    if feb_gross_amt:
                        febOW1.appendChild(doc.createTextNode(str(
                                                            feb_gross_amt)))
                    record1.appendChild(febOW1)

                    febOW2 = doc.createElement(
                                'FebruaryEmployersContributionToCPFOrdWages')
                    febOW2.setAttribute('xmlns', 'http://www.iras.gov.sg/IR8S')
                    if feb_empoyer_amt:
                        febOW2.appendChild(doc.createTextNode(str(
                                                            feb_empoyer_amt)))
                    record1.appendChild(febOW2)

                    febOW3 = doc.createElement(
                                'FebruaryEmployeesContributionToCPFOrdWages')
                    febOW3.setAttribute('xmlns', 'http://www.iras.gov.sg/IR8S')
                    if feb_empoyee_amt:
                        febOW3.appendChild(doc.createTextNode(str(
                                                            feb_empoyee_amt)))
                    record1.appendChild(febOW3)

                    febOW4 = doc.createElement('FebruaryAdditionalWages')
                    febOW4.setAttribute('xmlns', 'http://www.iras.gov.sg/IR8S')
                    record1.appendChild(febOW4)

                    febOW5 = doc.createElement(
                                 'FebruaryEmployersContributionToCPFAddWages')
                    febOW5.setAttribute('xmlns', 'http://www.iras.gov.sg/IR8S')
                    record1.appendChild(febOW5)

                    febOW6 = doc.createElement(
                                'FebruaryEmployeesContributionToCPFAddWages')
                    febOW6.setAttribute('xmlns', 'http://www.iras.gov.sg/IR8S')
                    record1.appendChild(febOW6)

                    mrchOW1 = doc.createElement('MarchOrdinaryWages')
                    mrchOW1.setAttribute('xmlns',
                                                'http://www.iras.gov.sg/IR8S')
                    if march_gross_amt:
                        mrchOW1.appendChild(doc.createTextNode(str(
                                                            march_gross_amt)))
                    record1.appendChild(mrchOW1)

                    mrchOW2 = doc.createElement(
                                    'MarchEmployersContributionToCPFOrdWages')
                    mrchOW2.setAttribute('xmlns',
                                                'http://www.iras.gov.sg/IR8S')
                    if march_empoyer_amt:
                        mrchOW2.appendChild(doc.createTextNode(str(
                                                        march_empoyer_amt)))
                    record1.appendChild(mrchOW2)

                    mrchOW3 = doc.createElement(
                                    'MarchEmployeesContributionToCPFOrdWages')
                    mrchOW3.setAttribute('xmlns',
                                                'http://www.iras.gov.sg/IR8S')
                    if march_empoyee_amt:
                        mrchOW3.appendChild(doc.createTextNode(str(
                                                        march_empoyee_amt)))
                    record1.appendChild(mrchOW3)

                    mrchOW4 = doc.createElement('MarchAdditionalWages')
                    mrchOW4.setAttribute('xmlns',
                                                'http://www.iras.gov.sg/IR8S')
                    record1.appendChild(mrchOW4)

                    mrchOW5 = doc.createElement(
                                    'MarchEmployersContributionToCPFAddWages')
                    mrchOW5.setAttribute('xmlns',
                                                'http://www.iras.gov.sg/IR8S')
                    record1.appendChild(mrchOW5)

                    mrchOW6 = doc.createElement(
                                    'MarchEmployeesContributionToCPFAddWages')
                    mrchOW6.setAttribute('xmlns', 'http://www.iras.gov.sg/IR8S')
                    record1.appendChild(mrchOW6)

                    aprOW1 = doc.createElement('AprilOrdinaryWages')
                    aprOW1.setAttribute('xmlns', 'http://www.iras.gov.sg/IR8S')
                    if apr_gross_amt:
                        aprOW1.appendChild(doc.createTextNode(str(
                                                            apr_gross_amt)))
                    record1.appendChild(aprOW1)

                    aprOW2 = doc.createElement(
                                    'AprilEmployersContributionToCPFOrdWages')
                    aprOW2.setAttribute('xmlns', 'http://www.iras.gov.sg/IR8S')
                    if apr_empoyer_amt:
                        aprOW2.appendChild(doc.createTextNode(str(
                                                            apr_empoyer_amt)))
                    record1.appendChild(aprOW2)

                    aprOW3 = doc.createElement(
                                    'AprilEmployeesContributionToCPFOrdWages')
                    aprOW3.setAttribute('xmlns', 'http://www.iras.gov.sg/IR8S')
                    if apr_empoyee_amt:
                        aprOW3.appendChild(doc.createTextNode(str(
                                                            apr_empoyee_amt)))
                    record1.appendChild(aprOW3)

                    aprOW4 = doc.createElement('AprilAdditionalWages')
                    aprOW4.setAttribute('xmlns', 'http://www.iras.gov.sg/IR8S')
                    record1.appendChild(aprOW4)

                    aprOW5 = doc.createElement(
                                    'AprilEmployersContributionToCPFAddWages')
                    aprOW5.setAttribute('xmlns', 'http://www.iras.gov.sg/IR8S')
                    record1.appendChild(aprOW5)

                    aprOW6 = doc.createElement(
                                    'AprilEmployeesContributionToCPFAddWages')
                    aprOW6.setAttribute('xmlns', 'http://www.iras.gov.sg/IR8S')
                    record1.appendChild(aprOW6)

                    mayOW1 = doc.createElement('MayOrdinaryWages')
                    mayOW1.setAttribute('xmlns', 'http://www.iras.gov.sg/IR8S')
                    if may_gross_amt:
                        mayOW1.appendChild(doc.createTextNode(str(may_gross_amt)))
                    record1.appendChild(mayOW1)

                    mayOW2 = doc.createElement(
                                    'MayEmployersContributionToCPFOrdWages')
                    mayOW2.setAttribute('xmlns', 'http://www.iras.gov.sg/IR8S')
                    if may_empoyer_amt:
                        mayOW2.appendChild(doc.createTextNode(str(
                                                            may_empoyer_amt)))
                    record1.appendChild(mayOW2)

                    mayOW3 = doc.createElement(
                                    'MayEmployeesContributionToCPFOrdWages')
                    mayOW3.setAttribute('xmlns', 'http://www.iras.gov.sg/IR8S')
                    if may_empoyee_amt:
                        mayOW3.appendChild(doc.createTextNode(str(
                                                            may_empoyee_amt)))
                    record1.appendChild(mayOW3)

                    mayOW4 = doc.createElement('MayAdditionalWages')
                    mayOW4.setAttribute('xmlns', 'http://www.iras.gov.sg/IR8S')
                    record1.appendChild(mayOW4)

                    mayOW5 = doc.createElement(
                                    'MayEmployersContributionToCPFAddWages')
                    mayOW5.setAttribute('xmlns', 'http://www.iras.gov.sg/IR8S')
                    record1.appendChild(mayOW5)

                    mayOW6 = doc.createElement(
                                      'MayEmployeesContributionToCPFAddWages')
                    mayOW6.setAttribute('xmlns', 'http://www.iras.gov.sg/IR8S')
                    record1.appendChild(mayOW6)

                    juneOW1 = doc.createElement('JuneOrdinaryWages')
                    juneOW1.setAttribute('xmlns', 'http://www.iras.gov.sg/IR8S')
                    if june_gross_amt:
                        juneOW1.appendChild(doc.createTextNode(str(
                                                            june_gross_amt)))
                    record1.appendChild(juneOW1)

                    juneOW2 = doc.createElement(
                                    'JuneEmployersContributionToCPFOrdWages')
                    juneOW2.setAttribute('xmlns', 'http://www.iras.gov.sg/IR8S')
                    if june_empoyer_amt:
                        juneOW2.appendChild(doc.createTextNode(str(
                                                            june_empoyer_amt)))
                    record1.appendChild(juneOW2)

                    juneOW3 = doc.createElement(
                                    'JuneEmployeesContributionToCPFOrdWages')
                    juneOW3.setAttribute('xmlns', 'http://www.iras.gov.sg/IR8S')
                    if june_empoyee_amt:
                        juneOW3.appendChild(doc.createTextNode(str(
                                                            june_empoyee_amt)))
                    record1.appendChild(juneOW3)

                    juneOW4 = doc.createElement('JuneAdditionalWages')
                    juneOW4.setAttribute('xmlns', 'http://www.iras.gov.sg/IR8S')
                    record1.appendChild(juneOW4)

                    juneOW5 = doc.createElement(
                                    'JuneEmployersContributionToCPFAddWages')
                    juneOW5.setAttribute('xmlns', 'http://www.iras.gov.sg/IR8S')
                    record1.appendChild(juneOW5)

                    juneOW6 = doc.createElement(
                                    'JuneEmployeesContributionToCPFAddWages')
                    juneOW6.setAttribute('xmlns', 'http://www.iras.gov.sg/IR8S')
                    record1.appendChild(juneOW6)

                    julyOW1 = doc.createElement('JulyOrdinaryWages')
                    julyOW1.setAttribute('xmlns', 'http://www.iras.gov.sg/IR8S')
                    if july_gross_amt:
                        julyOW1.appendChild(doc.createTextNode(str(july_gross_amt)))
                    record1.appendChild(julyOW1)

                    julyOW2 = doc.createElement(
                                    'JulyEmployersContributionToCPFOrdWages')
                    julyOW2.setAttribute('xmlns', 'http://www.iras.gov.sg/IR8S')
                    if july_empoyer_amt:
                        julyOW2.appendChild(doc.createTextNode(str(
                                                            july_empoyer_amt)))
                    record1.appendChild(julyOW2)

                    julyOW3 = doc.createElement(
                                    'JulyEmployeesContributionToCPFOrdWages')
                    julyOW3.setAttribute('xmlns', 'http://www.iras.gov.sg/IR8S')
                    if july_empoyee_amt:
                        julyOW3.appendChild(doc.createTextNode(str(
                                                            july_empoyee_amt)))
                    record1.appendChild(julyOW3)

                    julyOW4 = doc.createElement('JulyAdditionalWages')
                    julyOW4.setAttribute('xmlns', 'http://www.iras.gov.sg/IR8S')
                    record1.appendChild(julyOW4)

                    julyOW5 = doc.createElement(
                                    'JulyEmployersContributionToCPFAddWages')
                    julyOW5.setAttribute('xmlns', 'http://www.iras.gov.sg/IR8S')
                    record1.appendChild(julyOW5)

                    julyOW6 = doc.createElement(
                                    'JulyEmployeesContributionToCPFAddWages')
                    julyOW6.setAttribute('xmlns', 'http://www.iras.gov.sg/IR8S')
                    record1.appendChild(julyOW6)

                    augOW1 = doc.createElement('AugustOrdinaryWages')
                    augOW1.setAttribute('xmlns', 'http://www.iras.gov.sg/IR8S')
                    if aug_gross_amt:
                        augOW1.appendChild(doc.createTextNode(str(
                                                            aug_gross_amt)))
                    record1.appendChild(augOW1)

                    augOW2 = doc.createElement(
                                    'AugustEmployersContributionToCPFOrdWages')
                    augOW2.setAttribute('xmlns', 'http://www.iras.gov.sg/IR8S')
                    if aug_empoyer_amt:
                        augOW2.appendChild(doc.createTextNode(str(
                                                            aug_empoyer_amt)))
                    record1.appendChild(augOW2)

                    augOW3 = doc.createElement(
                                    'AugustEmployeesContributionToCPFOrdWages')
                    augOW3.setAttribute('xmlns', 'http://www.iras.gov.sg/IR8S')
                    if aug_empoyer_amt:
                        augOW3.appendChild(doc.createTextNode(str(
                                                            aug_empoyee_amt)))
                    record1.appendChild(augOW3)

                    augOW4 = doc.createElement('AugustAdditionalWages')
                    augOW4.setAttribute('xmlns', 'http://www.iras.gov.sg/IR8S')
                    record1.appendChild(augOW4)

                    augOW5 = doc.createElement(
                                    'AugustEmployersContributionToCPFAddWages')
                    augOW5.setAttribute('xmlns', 'http://www.iras.gov.sg/IR8S')
                    record1.appendChild(augOW5)

                    augOW6 = doc.createElement(
                                    'AugustEmployeesContributionToCPFAddWages')
                    augOW6.setAttribute('xmlns', 'http://www.iras.gov.sg/IR8S')
                    record1.appendChild(augOW6)


                    septOW1 = doc.createElement('SeptemberOrdinaryWages')
                    septOW1.setAttribute('xmlns', 'http://www.iras.gov.sg/IR8S')
                    if sept_gross_amt:
                        septOW1.appendChild(doc.createTextNode(str(
                                                            sept_gross_amt)))
                    record1.appendChild(septOW1)

                    septOW2 = doc.createElement(
                                'SeptemberEmployersContributionToCPFOrdWages')
                    septOW2.setAttribute('xmlns', 'http://www.iras.gov.sg/IR8S')
                    if sept_empoyer_amt:
                        septOW2.appendChild(doc.createTextNode(str(
                                                            sept_empoyer_amt)))
                    record1.appendChild(septOW2)

                    septOW3 = doc.createElement(
                                'SeptemberEmployeesContributionToCPFOrdWages')
                    septOW3.setAttribute('xmlns', 'http://www.iras.gov.sg/IR8S')
                    if sept_empoyee_amt:
                        septOW3.appendChild(doc.createTextNode(str(
                                                            sept_empoyee_amt)))
                    record1.appendChild(septOW3)

                    septOW4 = doc.createElement('SeptemberAdditionalWages')
                    septOW4.setAttribute('xmlns', 'http://www.iras.gov.sg/IR8S')
                    record1.appendChild(septOW4)

                    septOW5 = doc.createElement(
                                'SeptemberEmployersContributionToCPFAddWages')
                    septOW5.setAttribute('xmlns', 'http://www.iras.gov.sg/IR8S')
                    record1.appendChild(septOW5)

                    septOW6 = doc.createElement(
                                'SeptemberEmployeesContributionToCPFAddWages')
                    septOW6.setAttribute('xmlns', 'http://www.iras.gov.sg/IR8S')
                    record1.appendChild(septOW6)

                    octOW1 = doc.createElement('OctoberOrdinaryWages')
                    octOW1.setAttribute('xmlns', 'http://www.iras.gov.sg/IR8S')
                    if oct_gross_amt:
                        octOW1.appendChild(doc.createTextNode(str(
                                                            oct_gross_amt)))
                    record1.appendChild(octOW1)

                    octOW2 = doc.createElement(
                                'OctoberEmployersContributionToCPFOrdWages')
                    octOW2.setAttribute('xmlns', 'http://www.iras.gov.sg/IR8S')
                    if oct_empoyer_amt:
                        octOW2.appendChild(doc.createTextNode(str(
                                                            oct_empoyer_amt)))
                    record1.appendChild(octOW2)

                    octOW3 = doc.createElement(
                                'OctoberEmployeesContributionToCPFOrdWages')
                    octOW3.setAttribute('xmlns', 'http://www.iras.gov.sg/IR8S')
                    if oct_empoyee_amt:
                        octOW3.appendChild(doc.createTextNode(str(
                                                            oct_empoyee_amt)))
                    record1.appendChild(octOW3)

                    octOW4 = doc.createElement('OctoberAdditionalWages')
                    octOW4.setAttribute('xmlns', 'http://www.iras.gov.sg/IR8S')
                    record1.appendChild(octOW4)

                    octOW5 = doc.createElement(
                                'OctoberEmployersContributionToCPFAddWages')
                    octOW5.setAttribute('xmlns', 'http://www.iras.gov.sg/IR8S')
                    record1.appendChild(octOW5)

                    octOW6 = doc.createElement(
                                'OctoberEmployeesContributionToCPFAddWages')
                    octOW6.setAttribute('xmlns', 'http://www.iras.gov.sg/IR8S')
                    record1.appendChild(octOW6)


                    novOW1 = doc.createElement('NovemberOrdinaryWages')
                    novOW1.setAttribute('xmlns', 'http://www.iras.gov.sg/IR8S')
                    if nov_gross_amt:
                        novOW1.appendChild(doc.createTextNode(str(
                                                            nov_gross_amt)))
                    record1.appendChild(novOW1)

                    novOW2 = doc.createElement(
                                'NovemberEmployersContributionToCPFOrdWages')
                    novOW2.setAttribute('xmlns', 'http://www.iras.gov.sg/IR8S')
                    if nov_empoyer_amt:
                        novOW2.appendChild(doc.createTextNode(str(
                                                            nov_empoyer_amt)))
                    record1.appendChild(novOW2)

                    novOW3 = doc.createElement(
                                'NovemberEmployeesContributionToCPFOrdWages')
                    novOW3.setAttribute('xmlns', 'http://www.iras.gov.sg/IR8S')
                    if nov_empoyee_amt:
                        novOW3.appendChild(doc.createTextNode(str(
                                                            nov_empoyee_amt)))
                    record1.appendChild(novOW3)

                    novOW4 = doc.createElement('NovemberAdditionalWages')
                    novOW4.setAttribute('xmlns', 'http://www.iras.gov.sg/IR8S')
                    record1.appendChild(novOW4)

                    novOW5 = doc.createElement(
                                'NovemberEmployersContributionToCPFAddWages')
                    novOW5.setAttribute('xmlns', 'http://www.iras.gov.sg/IR8S')
                    record1.appendChild(novOW5)

                    novOW6 = doc.createElement(
                                'NovemberEmployeesContributionToCPFAddWages')
                    novOW6.setAttribute('xmlns', 'http://www.iras.gov.sg/IR8S')
                    record1.appendChild(novOW6)

                    decOW1 = doc.createElement('DecemberOrdinaryWages')
                    decOW1.setAttribute('xmlns', 'http://www.iras.gov.sg/IR8S')
                    if dec_gross_amt:
                        decOW1.appendChild(doc.createTextNode(str(
                                                            dec_gross_amt)))
                    record1.appendChild(decOW1)

                    decOW2 = doc.createElement(
                                'DecemberEmployersContributionToCPFOrdWages')
                    decOW2.setAttribute('xmlns', 'http://www.iras.gov.sg/IR8S')
                    if dec_empoyer_amt:
                        decOW2.appendChild(doc.createTextNode(str(
                                                            dec_empoyer_amt)))
                    record1.appendChild(decOW2)

                    decOW3 = doc.createElement(
                                'DecemberEmployeesContributionToCPFOrdWages')
                    decOW3.setAttribute('xmlns', 'http://www.iras.gov.sg/IR8S')
                    if dec_empoyee_amt:
                        decOW3.appendChild(doc.createTextNode(str(
                                                            dec_empoyee_amt)))
                    record1.appendChild(decOW3)

                    decOW4 = doc.createElement('DecemberAdditionalWages')
                    decOW4.setAttribute('xmlns', 'http://www.iras.gov.sg/IR8S')
                    record1.appendChild(decOW4)

                    decOW5 = doc.createElement(
                                'DecemberEmployersContributionToCPFAddWages')
                    decOW5.setAttribute('xmlns', 'http://www.iras.gov.sg/IR8S')
                    record1.appendChild(decOW5)

                    decOW6 = doc.createElement(
                                'DecemberEmployeesContributionToCPFAddWages')
                    decOW6.setAttribute('xmlns', 'http://www.iras.gov.sg/IR8S')
                    record1.appendChild(decOW6)

                    totgrossamt = doc.createElement('GrantTotalOrdinaryWages')
                    totgrossamt.setAttribute('xmlns',
                                             'http://www.iras.gov.sg/IR8S')
                    if tot_gross_amt:
                        totgrossamt.appendChild(doc.createTextNode(str(int(
                                                            tot_gross_amt))))
                    record1.appendChild(totgrossamt)

                    toteplyramt = doc.createElement(
                                'GrantTotalEmployersContributionToCPFOrdWages')
                    toteplyramt.setAttribute('xmlns',
                                                'http://www.iras.gov.sg/IR8S')
                    if tot_empoyer_amt:
                        toteplyramt.appendChild(doc.createTextNode(str(int(
                                                            tot_empoyer_amt))))
                    record1.appendChild(toteplyramt)

                    totempleeamt = doc.createElement(
                                'GrantTotalEmployeesContributionToCPFOrdWages')
                    totempleeamt.setAttribute('xmlns',
                                              'http://www.iras.gov.sg/IR8S')
                    if tot_empoyee_amt:
                        totempleeamt.appendChild(doc.createTextNode(str(int(
                                                            tot_empoyee_amt))))
                    record1.appendChild(totempleeamt)

                    grandtot1 = doc.createElement('GrantTotalAdditionalWages')
                    grandtot1.setAttribute('xmlns',
                                           'http://www.iras.gov.sg/IR8S')
                    record1.appendChild(grandtot1)

                    grandtot2 = doc.createElement(
                                'GrantTotalEmployersContributionToCPFAddWages')
                    grandtot2.setAttribute('xmlns',
                                           'http://www.iras.gov.sg/IR8S')
                    record1.appendChild(grandtot2)

                    grandtot3 = doc.createElement(
                                'GrantTotalEmployeesContributionToCPFAddWages')
                    grandtot3.setAttribute('xmlns',
                                           'http://www.iras.gov.sg/IR8S')
                    record1.appendChild(grandtot3)

                    OverseasPostingFromDate = doc.createElement(
                                                    'OverseasPostingFromDate')
                    OverseasPostingFromDate.setAttribute('xmlns',
                                                 'http://www.iras.gov.sg/IR8S')
                    record1.appendChild(OverseasPostingFromDate)

                    OverseasPostingToDate = doc.createElement(
                                                    'OverseasPostingToDate')
                    OverseasPostingToDate.setAttribute('xmlns',
                                                'http://www.iras.gov.sg/IR8S')
                    record1.appendChild(OverseasPostingToDate)

                    ObligatoryCPFContribution = doc.createElement(
                                                'ObligatoryCPFContribution')
                    ObligatoryCPFContribution.setAttribute('xmlns',
                                                'http://www.iras.gov.sg/IR8S')
                    record1.appendChild(ObligatoryCPFContribution)

                    CPFCappingApplied = doc.createElement('CPFCappingApplied')
                    CPFCappingApplied.setAttribute('xmlns',
                                               'http://www.iras.gov.sg/IR8S')
                    record1.appendChild(CPFCappingApplied)

                    SgPermanentResidentStatusApproved = doc.createElement(
                                        'SgPermanentResidentStatusApproved')
                    SgPermanentResidentStatusApproved.setAttribute('xmlns',
                                               'http://www.iras.gov.sg/IR8S')
                    if income_tax_rec.singapore_permanent_resident_status:
                        SgPermanentResidentStatusApproved.appendChild(
                            doc.createTextNode(str(
                        income_tax_rec.singapore_permanent_resident_status)))
                    record1.appendChild(SgPermanentResidentStatusApproved)

                    CPFBoardApprovalForFullContribution = doc.createElement(
                                        'CPFBoardApprovalForFullContribution')
                    CPFBoardApprovalForFullContribution.setAttribute('xmlns',
                                                 'http://www.iras.gov.sg/IR8S')
                    if income_tax_rec.approval_has_been_obtained_CPF_board:
                        CPFBoardApprovalForFullContribution.appendChild(
                            doc.createTextNode(str(
                        income_tax_rec.approval_has_been_obtained_CPF_board)))
                    record1.appendChild(CPFBoardApprovalForFullContribution)

                    EmployersContribution = doc.createElement(
                                                    'EmployersContribution')
                    EmployersContribution.setAttribute('xmlns',
                                               'http://www.iras.gov.sg/IR8S')
                    if eyer_contibution:
                        EmployersContribution.appendChild(
                                    doc.createTextNode(str(eyer_contibution)))
                    record1.appendChild(EmployersContribution)

                    EmployeesContribution = doc.createElement(
                                                    'EmployeesContribution')
                    EmployeesContribution.setAttribute('xmlns',
                                               'http://www.iras.gov.sg/IR8S')
                    if eyee_contibution:
                        EmployeesContribution.appendChild(
                                    doc.createTextNode(str(eyee_contibution)))
                    record1.appendChild(EmployeesContribution)

                    RefundDetails1AdditionalWages = doc.createElement(
                                            'RefundDetails1AdditionalWages')
                    RefundDetails1AdditionalWages.setAttribute('xmlns',
                                               'http://www.iras.gov.sg/IR8S')
                    if additional_wage:
                        RefundDetails1AdditionalWages.appendChild(
                                    doc.createTextNode(str(additional_wage)))
                    record1.appendChild(RefundDetails1AdditionalWages)

                    RefundDetails1AdditionalWagesPaymentPeriodFromDate = \
                        doc.createElement(
                        'RefundDetails1AdditionalWagesPaymentPeriodFromDate')
                    RefundDetails1AdditionalWagesPaymentPeriodFromDate.setAttribute(
                                        'xmlns', 'http://www.iras.gov.sg/IR8S')
                    if additional_wage_from_date:
                        RefundDetails1AdditionalWagesPaymentPeriodFromDate.appendChild(
                            doc.createTextNode(str(additional_wage_from_date)))
                    record1.appendChild(
                            RefundDetails1AdditionalWagesPaymentPeriodFromDate)

                    RefundDetails1AdditionalWagesPaymentPeriodToDate = \
                        doc.createElement(
                            'RefundDetails1AdditionalWagesPaymentPeriodToDate')
                    RefundDetails1AdditionalWagesPaymentPeriodToDate.setAttribute(
                        'xmlns', 'http://www.iras.gov.sg/IR8S')
                    if additional_wage_to_date:
                        RefundDetails1AdditionalWagesPaymentPeriodToDate.appendChild(
                            doc.createTextNode(str(additional_wage_to_date)))
                    record1.appendChild(
                            RefundDetails1AdditionalWagesPaymentPeriodToDate)

                    RefundDetails1AdditionalWagesPaymentDate = \
                        doc.createElement(
                                    'RefundDetails1AdditionalWagesPaymentDate')
                    RefundDetails1AdditionalWagesPaymentDate.setAttribute(
                                        'xmlns', 'http://www.iras.gov.sg/IR8S')
                    if add_wage_date:
                        RefundDetails1AdditionalWagesPaymentDate.appendChild(
                                        doc.createTextNode(str(add_wage_date)))
                    record1.appendChild(
                                    RefundDetails1AdditionalWagesPaymentDate)

                    RefundDetails1RefundAmtToEmployersContribution = \
                        doc.createElement(
                            'RefundDetails1RefundAmtToEmployersContribution')
                    RefundDetails1RefundAmtToEmployersContribution.setAttribute(
                                        'xmlns', 'http://www.iras.gov.sg/IR8S')
                    if refund_eyers_contribution:
                        RefundDetails1RefundAmtToEmployersContribution.appendChild(
                            doc.createTextNode(str(refund_eyers_contribution)))
                    record1.appendChild(
                                RefundDetails1RefundAmtToEmployersContribution)

                    RefundDetails1RefundAmtToEmployersContributionInterest = \
                        doc.createElement(
                      'RefundDetails1RefundAmtToEmployersContributionInterest')
                    RefundDetails1RefundAmtToEmployersContributionInterest.setAttribute(
                                        'xmlns', 'http://www.iras.gov.sg/IR8S')
                    if refund_eyers_interest_contribution:
                        RefundDetails1RefundAmtToEmployersContributionInterest.appendChild(
                            doc.createTextNode(str(
                                        refund_eyers_interest_contribution)))
                    record1.appendChild(
                        RefundDetails1RefundAmtToEmployersContributionInterest)

                    RefundDetails1EmployerRefundDate = doc.createElement(
                                            'RefundDetails1EmployerRefundDate')
                    RefundDetails1EmployerRefundDate.setAttribute('xmlns',
                                                'http://www.iras.gov.sg/IR8S')
                    if eyer_date:
                        RefundDetails1EmployerRefundDate.appendChild(
                                            doc.createTextNode(str(eyer_date)))
                    record1.appendChild(RefundDetails1EmployerRefundDate)

                    RefundDetails1RefundAmtToEmployeesContribution = \
                        doc.createElement(
                            'RefundDetails1RefundAmtToEmployeesContribution')
                    RefundDetails1RefundAmtToEmployeesContribution.setAttribute(
                                    'xmlns', 'http://www.iras.gov.sg/IR8S')
                    if refund_eyees_contribution:
                        RefundDetails1RefundAmtToEmployeesContribution.appendChild(
                            doc.createTextNode(str(refund_eyees_contribution)))
                    record1.appendChild(
                                RefundDetails1RefundAmtToEmployeesContribution)

                    RefundDetails1RefundAmtToEmployeesContributionInterest = \
                        doc.createElement(
                      'RefundDetails1RefundAmtToEmployeesContributionInterest')
                    RefundDetails1RefundAmtToEmployeesContributionInterest.setAttribute(
                                        'xmlns', 'http://www.iras.gov.sg/IR8S')
                    if refund_eyees_interest_contribution:
                        RefundDetails1RefundAmtToEmployeesContributionInterest.appendChild(
                            doc.createTextNode(str(
                                        refund_eyees_interest_contribution)))
                    record1.appendChild(
                        RefundDetails1RefundAmtToEmployeesContributionInterest)

                    RefundDetails1EmployeeRefundDate = doc.createElement(
                                            'RefundDetails1EmployeeRefundDate')
                    RefundDetails1EmployeeRefundDate.setAttribute(
                                        'xmlns', 'http://www.iras.gov.sg/IR8S')
                    if eyee_date:
                        RefundDetails1EmployeeRefundDate.appendChild(
                                            doc.createTextNode(str(eyee_date)))
                    record1.appendChild(RefundDetails1EmployeeRefundDate)


                    RefundDetails2AdditionalWages = doc.createElement(
                                            'RefundDetails2AdditionalWages')
                    RefundDetails2AdditionalWages.setAttribute('xmlns',
                                                'http://www.iras.gov.sg/IR8S')
                    if additional_wage:
                        RefundDetails2AdditionalWages.appendChild(
                                    doc.createTextNode(str(additional_wage)))
                    record1.appendChild(RefundDetails2AdditionalWages)

                    RefundDetails2AdditionalWagesPaymentPeriodFromDate = \
                        doc.createElement(
                        'RefundDetails2AdditionalWagesPaymentPeriodFromDate')
                    RefundDetails2AdditionalWagesPaymentPeriodFromDate.setAttribute(
                                        'xmlns', 'http://www.iras.gov.sg/IR8S')
                    if additional_wage_from_date:
                        RefundDetails2AdditionalWagesPaymentPeriodFromDate.appendChild(
                            doc.createTextNode(str(additional_wage_from_date)))
                    record1.appendChild(
                            RefundDetails2AdditionalWagesPaymentPeriodFromDate)

                    RefundDetails2AdditionalWagesPaymentPeriodToDate = \
                        doc.createElement(
                            'RefundDetails2AdditionalWagesPaymentPeriodToDate')
                    RefundDetails2AdditionalWagesPaymentPeriodToDate.setAttribute(
                                        'xmlns', 'http://www.iras.gov.sg/IR8S')
                    if additional_wage_to_date:
                        RefundDetails2AdditionalWagesPaymentPeriodToDate.appendChild(
                            doc.createTextNode(str(additional_wage_to_date)))
                    record1.appendChild(
                            RefundDetails2AdditionalWagesPaymentPeriodToDate)

                    RefundDetails2AdditionalWagesPaymentDate = \
                        doc.createElement(
                                    'RefundDetails2AdditionalWagesPaymentDate')
                    RefundDetails2AdditionalWagesPaymentDate.setAttribute(
                                        'xmlns', 'http://www.iras.gov.sg/IR8S')
                    if add_wage_date:
                        RefundDetails2AdditionalWagesPaymentDate.appendChild(
                                        doc.createTextNode(str(add_wage_date)))
                    record1.appendChild(RefundDetails2AdditionalWagesPaymentDate)


                    RefundDetails2RefundAmtToEmployersContribution = \
                        doc.createElement(
                            'RefundDetails2RefundAmtToEmployersContribution')
                    RefundDetails2RefundAmtToEmployersContribution.setAttribute(
                                        'xmlns', 'http://www.iras.gov.sg/IR8S')
                    if refund_eyers_contribution:
                        RefundDetails2RefundAmtToEmployersContribution.appendChild(
                            doc.createTextNode(str(refund_eyers_contribution)))
                    record1.appendChild(
                                RefundDetails2RefundAmtToEmployersContribution)

                    RefundDetails2RefundAmtToEmployersContributionInterest = \
                        doc.createElement(
                      'RefundDetails2RefundAmtToEmployersContributionInterest')
                    RefundDetails2RefundAmtToEmployersContributionInterest.setAttribute(
                                        'xmlns', 'http://www.iras.gov.sg/IR8S')
                    if refund_eyers_interest_contribution:
                        RefundDetails2RefundAmtToEmployersContributionInterest.appendChild(
                            doc.createTextNode(str(
                                        refund_eyers_interest_contribution)))
                    record1.appendChild(
                        RefundDetails2RefundAmtToEmployersContributionInterest)

                    RefundDetails2EmployerRefundDate = \
                        doc.createElement('RefundDetails2EmployerRefundDate')
                    RefundDetails2EmployerRefundDate.setAttribute('xmlns',
                                                 'http://www.iras.gov.sg/IR8S')
                    if eyer_date:
                        RefundDetails2EmployerRefundDate.appendChild(
                                            doc.createTextNode(str(eyer_date)))
                    record1.appendChild(RefundDetails2EmployerRefundDate)


                    RefundDetails2RefundAmtToEmployeesContribution = \
                        doc.createElement(
                            'RefundDetails2RefundAmtToEmployeesContribution')
                    RefundDetails2RefundAmtToEmployeesContribution.setAttribute(
                                        'xmlns', 'http://www.iras.gov.sg/IR8S')
                    if refund_eyees_contribution:
                        RefundDetails2RefundAmtToEmployeesContribution.appendChild(
                            doc.createTextNode(str(refund_eyees_contribution)))
                    record1.appendChild(
                                RefundDetails2RefundAmtToEmployeesContribution)

                    RefundDetails2RefundAmtToEmployeesContributionInterest = \
                        doc.createElement(
                      'RefundDetails2RefundAmtToEmployeesContributionInterest')
                    RefundDetails2RefundAmtToEmployeesContributionInterest.setAttribute(
                                        'xmlns', 'http://www.iras.gov.sg/IR8S')
                    if refund_eyees_interest_contribution:
                        RefundDetails2RefundAmtToEmployeesContributionInterest.appendChild(
                            doc.createTextNode(str(
                                          refund_eyees_interest_contribution)))
                    record1.appendChild(
                        RefundDetails2RefundAmtToEmployeesContributionInterest)

                    RefundDetails2EmployeeRefundDate = doc.createElement(
                                            'RefundDetails2EmployeeRefundDate')
                    RefundDetails2EmployeeRefundDate.setAttribute('xmlns',
                                                 'http://www.iras.gov.sg/IR8S')
                    if eyee_date:
                        RefundDetails2EmployeeRefundDate.appendChild(
                                            doc.createTextNode(str(eyee_date)))
                    record1.appendChild(RefundDetails2EmployeeRefundDate)

                    RefundDetails3AdditionalWages = doc.createElement(
                                            'RefundDetails3AdditionalWages')
                    RefundDetails3AdditionalWages.setAttribute('xmlns',
                                               'http://www.iras.gov.sg/IR8S')
                    if additional_wage:
                        RefundDetails3AdditionalWages.appendChild(
                                    doc.createTextNode(str(additional_wage)))
                    record1.appendChild(RefundDetails3AdditionalWages)

                    RefundDetails3AdditionalWagesPaymentPeriodFromDate = \
                        doc.createElement(
                        'RefundDetails3AdditionalWagesPaymentPeriodFromDate')
                    RefundDetails3AdditionalWagesPaymentPeriodFromDate.setAttribute(
                                        'xmlns', 'http://www.iras.gov.sg/IR8S')
                    if additional_wage_from_date:
                        RefundDetails3AdditionalWagesPaymentPeriodFromDate.appendChild(
                            doc.createTextNode(str(additional_wage_from_date)))
                    record1.appendChild(
                            RefundDetails3AdditionalWagesPaymentPeriodFromDate)

                    RefundDetails3AdditionalWagesPaymentPeriodToDate = \
                        doc.createElement(
                            'RefundDetails3AdditionalWagesPaymentPeriodToDate')
                    RefundDetails3AdditionalWagesPaymentPeriodToDate.setAttribute(
                                        'xmlns', 'http://www.iras.gov.sg/IR8S')
                    if additional_wage_to_date:
                        RefundDetails3AdditionalWagesPaymentPeriodToDate.appendChild(
                            doc.createTextNode(str(additional_wage_to_date)))
                    record1.appendChild(
                            RefundDetails3AdditionalWagesPaymentPeriodToDate)

                    RefundDetails3AdditionalWagesPaymentDate = doc.createElement(
                                    'RefundDetails3AdditionalWagesPaymentDate')
                    RefundDetails3AdditionalWagesPaymentDate.setAttribute(
                                        'xmlns', 'http://www.iras.gov.sg/IR8S')
                    if add_wage_date:
                        RefundDetails3AdditionalWagesPaymentDate.appendChild(
                                        doc.createTextNode(str(add_wage_date)))
                    record1.appendChild(
                                    RefundDetails3AdditionalWagesPaymentDate)


                    RefundDetails3RefundAmtToEmployersContribution = \
                            doc.createElement(
                            'RefundDetails3RefundAmtToEmployersContribution')
                    RefundDetails3RefundAmtToEmployersContribution.setAttribute(
                                        'xmlns', 'http://www.iras.gov.sg/IR8S')
                    if refund_eyers_contribution:
                        RefundDetails3RefundAmtToEmployersContribution.appendChild(
                            doc.createTextNode(str(refund_eyers_contribution)))
                    record1.appendChild(
                                RefundDetails3RefundAmtToEmployersContribution)

                    RefundDetails3RefundAmtToEmployersContributionInterest = \
                            doc.createElement(
                      'RefundDetails3RefundAmtToEmployersContributionInterest')
                    RefundDetails3RefundAmtToEmployersContributionInterest.setAttribute(
                                        'xmlns', 'http://www.iras.gov.sg/IR8S')
                    if refund_eyers_interest_contribution:
                        RefundDetails3RefundAmtToEmployersContributionInterest.appendChild(
                            doc.createTextNode(str(
                                        refund_eyers_interest_contribution)))
                    record1.appendChild(
                        RefundDetails3RefundAmtToEmployersContributionInterest)

                    RefundDetails3EmployerRefundDate = doc.createElement(
                                            'RefundDetails3EmployerRefundDate')
                    RefundDetails3EmployerRefundDate.setAttribute(
                                        'xmlns', 'http://www.iras.gov.sg/IR8S')
                    if eyer_date:
                        RefundDetails3EmployerRefundDate.appendChild(
                                            doc.createTextNode(str(eyer_date)))
                    record1.appendChild(RefundDetails3EmployerRefundDate)


                    RefundDetails3RefundAmtToEmployeesContribution = \
                            doc.createElement(
                            'RefundDetails3RefundAmtToEmployeesContribution')
                    RefundDetails3RefundAmtToEmployeesContribution.setAttribute(
                                        'xmlns', 'http://www.iras.gov.sg/IR8S')
                    if refund_eyees_contribution:
                        RefundDetails3RefundAmtToEmployeesContribution.appendChild(
                            doc.createTextNode(str(refund_eyees_contribution)))
                    record1.appendChild(RefundDetails3RefundAmtToEmployeesContribution)

                    RefundDetails3RefundAmtToEmployeesContributionInterest = \
                        doc.createElement(
                      'RefundDetails3RefundAmtToEmployeesContributionInterest')
                    RefundDetails3RefundAmtToEmployeesContributionInterest.setAttribute(
                                        'xmlns', 'http://www.iras.gov.sg/IR8S')
                    if refund_eyees_interest_contribution:
                        RefundDetails3RefundAmtToEmployeesContributionInterest.appendChild(
                            doc.createTextNode(str(
                                        refund_eyees_interest_contribution)))
                    record1.appendChild(
                        RefundDetails3RefundAmtToEmployeesContributionInterest)

                    RefundDetails3EmployeeRefundDate = doc.createElement(
                                            'RefundDetails3EmployeeRefundDate')
                    RefundDetails3EmployeeRefundDate.setAttribute('xmlns',
                                                'http://www.iras.gov.sg/IR8S')
                    if eyee_date:
                        RefundDetails3EmployeeRefundDate.appendChild(
                                            doc.createTextNode(str(eyee_date)))
                    record1.appendChild(RefundDetails3EmployeeRefundDate)

                    Filler = doc.createElement('Filler')
                    Filler.setAttribute('xmlns', 'http://www.iras.gov.sg/IR8S')
                    record1.appendChild(Filler)

                    Remarks = doc.createElement('Remarks')
                    Remarks.setAttribute('xmlns', 'http://www.iras.gov.sg/IR8S'
                                         )
                    record1.appendChild(Remarks)

            result = doc.toprettyxml(indent='   ')
            res = base64.b64encode(result.encode('UTF-8'))
            module_rec = self.env['binary.ir8s.xml.file.wizard'
                                  ].create({'name': 'IR8S.xml',
                                            'ir8s_xml_file': res
                                            })
            return {
                  'name': _('Binary'),
                  'res_id': module_rec.id,
                  "view_mode": 'form',
                  'res_model': 'binary.ir8s.xml.file.wizard',
                  'type': 'ir.actions.act_window',
                  'target': 'new',
                  'context': context
            }
        elif data.get('print_type', '') == 'pdf':
            report_id = self.env.ref(
                'sg_income_tax_report.ir8s_form_income_tax_report')
            return report_id.report_action(self, data=data, config=False)


class BinaryIr8sTextFileWizard(models.TransientModel):
    _name = 'binary.ir8s.text.file.wizard'
    _description = "ir8s text file"

    name = fields.Char('Name', default='IR8S.txt')
    ir8s_txt_file = fields.Binary(
        'Click On Download Link To Download File', readonly=True)


class BinaryIr8sXmlFileWizard(models.TransientModel):
    _name = 'binary.ir8s.xml.file.wizard'
    _description = "ir8s xml file"

    name = fields.Char('Name', default='IR8S.xml')
    ir8s_xml_file = fields.Binary('Click On Download Link To Download File',
                                  readonly=True)
