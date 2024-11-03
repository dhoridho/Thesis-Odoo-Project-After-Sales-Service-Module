import time
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo import api, models, _
from odoo.tools.misc import formatLang
from odoo.exceptions import ValidationError


class Ir8aForm(models.AbstractModel):
    _name = "report.sg_income_tax_report.ir8a_incometax_form_report"
    _description = "Ir8aForm"

    def get_data(self, form):
        employee_obj = self.env['hr.employee']
        from_date = to_date = start_date = end_date = False

        if form.get('start_date', False) and form.get('end_date', False):
            from_date = form.get('start_date', False)
            to_date = form.get('end_date', False)
            start_date = from_date + relativedelta(month=1, day=1, years=-1)
            end_date = to_date + relativedelta(month=12, day=31, years=-1)

        previous_year = form.get('start_date', False).year - 1
        total_detail_record = 0
        vals = []
        emp_ids = employee_obj.search([
            ('id', 'in', form.get('employee_ids'))], order='name ASC')
        contract_obj = self.env['hr.contract']
        incometax_obj = self.env['hr.contract.income.tax']
        payslip_obj = self.env['hr.payslip']
        resource_obj = self.env['resource.resource']
        for employee in emp_ids:
            res = {}
            contract_ids = contract_obj.search([
                ('employee_id', '=', employee.id)])
            income_tax_rec = incometax_obj.search([
                ('contract_id', 'in', contract_ids.ids),
                ('start_date', '>=', from_date),
                ('end_date', '<=', to_date)], limit=1)

            if not income_tax_rec.ids:
                raise ValidationError(
                    _('No Income Tax Record found for Selected Dates'))
            for contract_income_tax_rec in income_tax_rec:
                total_detail_record += 1
                sex = birthday = join_date = cessation_date = \
                    fromdate = todate = approval_date = ''
                res['employee'] = employee.name
                if employee.gender == 'male':
                    sex = 'M'
                if employee.gender == 'female':
                    sex = 'F'
                if employee.birthday:
                    birthday = employee.birthday.strftime('%Y-%m-%d')
                if employee.join_date:
                    join_date = employee.join_date.strftime('%Y-%m-%d')
                if contract_income_tax_rec.contract_id.date_end:
                    cessation_date = (
                        contract_income_tax_rec.contract_id.date_end.strftime(
                            '%Y-%m-%d'))
                if contract_income_tax_rec.approval_date:
                    approval_date = (
                        contract_income_tax_rec.approval_date.strftime(
                            '%Y-%m-%d'))
                transport_allowance = other_allowance = other_data = \
                    donation_amt = bonus_amt = gross_amt = \
                    gross_commission = 0

                payslip_ids = payslip_obj.search([
                    ('date_from', '>=', start_date),
                    ('date_from', '<=', end_date),
                    ('employee_id', '=', employee.id),
                    ('state', 'in', ['draft', 'done', 'verify'])])
                for payslip in payslip_ids:
                    fromdate = payslip.date_from.strftime('%Y')
                    todate = payslip.date_to.strftime('%Y')

                    for line in payslip.line_ids:
                        if line.code in ['CPFSINDA', 'CPFCDAC', 'CPFECF']:
                            donation_amt += line.total
                        if line.code == 'TA':
                            transport_allowance += line.total
                        if line.code == 'SC121':
                            bonus_amt += line.total
                        if line.category_id.code == 'GROSS':
                            gross_amt += line.total
                        if line.code in ['SC102', 'SC103']:
                            gross_amt += line.total
                        if line.code in ['SC104', 'SC105']:
                            gross_commission += line.total
                        if line.category_id.code == 'ALW' and line.code != 'TA':
                            other_allowance += line.total

                bonus_amt = bonus_amt
                insurance = director_fee = benifits_in_kinds = \
                    gains_profit_share_option = \
                    excess_voluntary_contribution_cpf_employer \
                    = contribution_employer = retirement_benifit_from = \
                    retirement_benifit_up = compensation_loss_office = \
                    gratuity_payment_amt = entertainment_allowance = \
                    pension = lum_sum_total = 0
                insurance = contract_income_tax_rec.insurance
                director_fee = contract_income_tax_rec.director_fee
                pension = contract_income_tax_rec.pension or 0.0
                entertainment_allowance = \
                    contract_income_tax_rec.entertainment_allowance
                gratuity_payment_amt = \
                    contract_income_tax_rec.gratuity_payment_amt * 1
                notice_pay_amt = contract_income_tax_rec.notice_pay * 1
                ex_gratia_amt = contract_income_tax_rec.ex_gratia * 1
                others_amt = contract_income_tax_rec.others * 1
                compensation_loss_office = \
                    contract_income_tax_rec.compensation_loss_office
                retirement_benifit_up = \
                    contract_income_tax_rec.retirement_benifit_up
                retirement_benifit_from = \
                    contract_income_tax_rec.retirement_benifit_from
                contribution_employer = \
                    contract_income_tax_rec.contribution_employer
                excess_voluntary_contribution_cpf_employer = \
                    contract_income_tax_rec.\
                    excess_voluntary_contribution_cpf_employer
                CPF_designated_pension_provident_fund = \
                    contract_income_tax_rec.\
                    CPF_designated_pension_provident_fund
                gains_profit_share_option = \
                    contract_income_tax_rec.gains_profit_share_option
                benifits_in_kinds = contract_income_tax_rec.benifits_in_kinds
                other_allowance += contract_income_tax_rec.other_allowance
                lum_sum_total = compensation_loss_office + \
                    gratuity_payment_amt + notice_pay_amt + ex_gratia_amt + \
                    others_amt
                total_d_2 = (transport_allowance) + \
                    (entertainment_allowance) + (other_allowance)
                other_data += total_d_2 + gross_commission + pension + \
                    lum_sum_total + retirement_benifit_from + \
                    contribution_employer + \
                    excess_voluntary_contribution_cpf_employer + \
                    gains_profit_share_option + benifits_in_kinds

                domain = [('user_id', '=', int(form.get('payroll_user')))]
                resource_ids = resource_obj.search(domain)
                emp_domain = [('resource_id', 'in', resource_ids.ids)]
                employee_rec = employee_obj.search(emp_domain)
                res['autho_user'] = ''
                res['designation'] = ''
                res['tel_no'] = ''
                res['partially_borne'] = res['employee_fixed_amount'] = 0.0
                res['exempt_remission'] = res['exempt_not_taxble'] = 0.0
                for emp_rec in employee_rec:
                    res['autho_user'] = emp_rec.name
                    res['designation'] = emp_rec.job_id and \
                        emp_rec.job_id.name or ''
                    res['tel_no'] = emp_rec.mobile_phone or ''
                res['date_today'] = datetime.today().strftime('%d-%m-%Y')
                res['is_income'] = 'YES'
                res['partially_borne'] = \
                    contract_income_tax_rec.employee_income
                res['employee_fixed_amount'] = \
                    contract_income_tax_rec.employment_income
                if contract_income_tax_rec.exempt_remission == '1':
                    res['exempt_remission'] = \
                        contract_income_tax_rec.exempt_income or 0.0
                else:
                    res['exempt_not_taxble'] = \
                        contract_income_tax_rec.exempt_income or 0.0
                #  Round down
                res['gross_amt'] = int(gross_amt) * 1.00
                res['fund_name'] = contract_income_tax_rec.fund_name or ''
                res['identification_id'] = employee.identification_id
                res['employeer_tax'] = employee.company_id.vat
                employee_address = ''
                if employee.address_home_id:
                    employee_address = \
                        employee.address_home_id._display_address(
                            without_company=True)
                res['address_home'] = employee_address
                res['cessation_date'] = cessation_date
                res['sex'] = sex
                res['birthday'] = birthday
                res['bonus_amt'] = int(bonus_amt) * 1.00
                res['director_fee'] = \
                    formatLang(self.env, int(abs(director_fee)) * 1.00 or 0.0)
                res['pension'] = \
                    formatLang(self.env, int(pension) * 1.00 or 0.0)
                res['transport_allowance'] = \
                    formatLang(self.env, int(transport_allowance) * 1.00)
                res['entertainment_allowance'] = \
                    formatLang(self.env, int(entertainment_allowance) * 1.00)
                res['other_allowance'] = \
                    formatLang(self.env, int(other_allowance) * 1.00)
                res['total_d_2'] = int(total_d_2) * 1.00
                res['gratuity_payment_amt'] = int(gratuity_payment_amt) * 1.00
                res['notice_pay'] = int(notice_pay_amt) * 1.00
                res['ex_gratia'] = int(ex_gratia_amt) * 1.00
                res['others'] = int(others_amt) * 1.00
                res['nationality'] = employee.empnationality_id.name or ''
                res['other_data'] = \
                    formatLang(self.env, int(other_data) * 1.00 or 0.0)
                res['mbf'] = contract_income_tax_rec.mbf or 0.0
                res['contribution_employer'] = contribution_employer

                if CPF_designated_pension_provident_fund:
                    CPF_designated_pension_provident_fund = \
                        CPF_designated_pension_provident_fund % 1 > 0.00 and \
                        (int(CPF_designated_pension_provident_fund) + 1) or \
                        CPF_designated_pension_provident_fund
                res['CPF_designated_pension_provident_fund'] = \
                    formatLang(self.env, int(
                        CPF_designated_pension_provident_fund) * 1.00 or 0.0)

                if donation_amt:
                    donation_amt = \
                        donation_amt % 1 > 0.00 and (int(donation_amt) + 1) \
                        or donation_amt
                res['donation_amt'] = \
                    formatLang(self.env, int(donation_amt) * 1.00 or 0.0)
                if gross_commission:
                    fromdate = '01/01/%s' % str(fromdate)
                    todate = '31/12/%s' % str(todate)

                res['insurance'] = \
                    formatLang(self.env, int(insurance) * 1.00 or 0.0)
                res['fromdate'] = fromdate or ''
                res['todate'] = todate or ''
                res['gross_commission'] = \
                    formatLang(self.env, int(gross_commission) * 1.00 or 0.0)
                res['approval_date'] = approval_date or ''
                res['compensation_loss_office'] = \
                    formatLang(self.env, int(
                        compensation_loss_office) * 1.00 or 0.0)
                res['approve_obtain_iras'] = \
                    contract_income_tax_rec.approve_obtain_iras or ''
                res['retirement_benifit_up'] = \
                    formatLang(self.env, int(
                        retirement_benifit_up) * 1.00 or 0.0)
                res['retirement_benifit_from'] = \
                    formatLang(self.env, int(
                        retirement_benifit_from) * 1.00 or 0.0)
                res['excess_voluntary_contribution_cpf_employer'] = \
                    formatLang(self.env, int(
                        excess_voluntary_contribution_cpf_employer) *
                    1.00 or 0.0)
                res['gains_profit_share_option'] = \
                    formatLang(self.env, int(
                        gains_profit_share_option) * 1.00 or 0.0)
                res['benifits_in_kinds'] = \
                    formatLang(self.env, int(benifits_in_kinds) * 1.00 or 0.0)
                res['job_name'] = employee.job_id.name or ''
                res['join_date'] = join_date or ''
                res['fund_name'] = contract_income_tax_rec.fund_name or ''
                res['previous_year'] = previous_year or ''
                res['company_name'] = employee.company_id.name or ''
                res['company_street'] = employee.company_id.street or ''
                res['lum_sum_total'] = lum_sum_total
                if form.get('start_date'):
                    year = form.get('start_date', False).year
                res['year'] = year or ''
                res['joined_year'] = employee.joined_year
                res['reason'] = contract_income_tax_rec.reason
                res['contribution_mandetory'] = \
                    contract_income_tax_rec.contribution_mandetory
                res['contribution_charged'] = \
                    contract_income_tax_rec.contribution_charged
                res['bank_name'] = employee.bank_account_id and \
                    employee.bank_account_id.bank_id and \
                    employee.bank_account_id.bank_id.name or ''
                res['contribution_amount'] = 0
                if contract_income_tax_rec.contribution_mandetory == 'Yes':
                    res['contribution_amount'] = \
                        contract_income_tax_rec.contribution_amount
                vals.append(res)
        return vals

    @api.model
    def _get_report_values(self, docids, data=None):
        model = self.env.context.get('active_model')
        docs = self.env[model].browse(self.env.context.get('active_id'))
        data = docs.read([])[0]
        report_lines = self.get_data(data)
        return {'doc_ids': self.ids,
                'doc_model': model,
                'data': data,
                'docs': docs,
                'time': time,
                'get_data': report_lines}
