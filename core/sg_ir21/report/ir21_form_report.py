import time
from datetime import datetime
from odoo import api, models
from odoo import tools
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DSDF
from odoo.tools.misc import get_lang


class Ir21Form(models.AbstractModel):
    _name = 'report.sg_ir21.report_form_ir21'
    _description = "Ir21 Form Report"

    def get_data(self, form):
        employee_obj = self.env['hr.employee']
        contract_income_tax_obj = self.env['hr.contract.income.tax']
        from_date = to_date = start_date = end_date = prev_yr_start_date = \
            prev_yr_end_date = False
        if form.get('start_date', False) and form.get('end_date', False):
            from_date = form.get('start_date', False)
            to_date = form.get('end_date', False)
            prev_yr_start = from_date.year - 1
            prev_yr_end = to_date.year - 1
            prev_yr_start_date = '%s-01-01' % tools.ustr(int(prev_yr_start))
            prev_yr_end_date = '%s-12-31' % tools.ustr(int(prev_yr_end))
            prev_yr_start_date = datetime.strptime(prev_yr_start_date, DSDF)
            prev_yr_end_date = datetime.strptime(prev_yr_end_date, DSDF)

        vals = []
        emp_ids = employee_obj.search([('id', 'in', form.get('employee_ids'))])
        for employee in emp_ids:
            res = {}
            child = {'child_name': '', 'child_gender': '', 'birth_date': ''}
            contract_ids = self.env['hr.contract'].search([
                ('employee_id', '=', employee.id)])

            payslip_id = self.env['hr.payslip'].search([
                ('employee_id', '=', employee.id),
                ('date_from', '>=', from_date),
                ('date_to', '<=', to_date),
                ('state', '=', 'done')], order='create_date desc', limit=1)
            if payslip_id:
                if payslip_id.date:
                    res['date_last_salary'] = payslip_id.date.strftime(
                    get_lang(self.env).date_format)
                else:
                    res['date_last_salary'] = ''
                res['salary_period'] = payslip_id.date_from.strftime(
                    get_lang(self.env).date_format) + ' To ' + payslip_id.date_to.strftime(
                    get_lang(self.env).date_format)
                for line_ids in payslip_id.line_ids:
                    if line_ids.code == 'GROSS':
                        res['last_salary'] = line_ids.amount

            res['name'] = employee.name or ''
            res['nationality'] = employee.country_id and \
                employee.country_id.name or ''
            if employee.birthday:
                res['birthday'] = employee.birthday.strftime(
                    get_lang(self.env).date_format)
            else:
                res['birthday'] = ''
            res['gender'] = employee.gender or ''
            if employee.identification_no == '1':
                res['nric_no'] = employee.identification_id
            else:
                res['nric_no'] = ''
            if employee.identification_no == '2':
                res['fin_no'] = employee.identification_id
            else:
                res['fin_no'] = ''
#            res['country_id'] = employee.country_id or ''
            res['marital'] = employee.marital or ''
            res['mobile_phone'] = employee.mobile_phone or ''
            res['work_email'] = employee.work_email or ''
            if employee.app_date:
                res['app_date'] = employee.app_date.strftime(
                    get_lang(self.env).date_format)
            else:
                res['app_date'] = ''
            res['join_date'] = ''
            if employee.join_date:
                res['join_date'] = employee.join_date.strftime(get_lang(self.env).date_format) or ''
            if employee.cessation_date:
                res['cessation_date'] = employee.cessation_date.strftime(
                    get_lang(self.env).date_format)
            else:
                res['cessation_date'] = ''
            if employee.last_date:
                res['last_date'] = employee.last_date.strftime(
                    get_lang(self.env).date_format)
            else:
                res['last_date'] = ''
            res['comp_house_no'] = employee.company_id.house_no or ''
            res['comp_unit_no'] = employee.company_id.unit_no or ''
            res['spouse_name'] = employee.spouse_name or ''
            if employee.spouse_dob:
                res['spouse_dob'] = employee.spouse_dob.strftime(
                    get_lang(self.env).date_format)
            else:
                res['spouse_dob'] = ''
            res['spouse_ident'] = employee.spouse_ident_no or ''
            if employee.marriage_date:
                res['marriage_date'] = employee.marriage_date.strftime(
                    get_lang(self.env).date_format)
            else:
                res['marriage_date'] = ''
            res['spouse_nationality'] = employee.spouse_nationality.name or ''
            res['bank_name'] = employee.bank_account_id.bank_id.name or ''
            res['house_no'] = employee.address_home_id.house_no or ''
            res['street'] = employee.address_home_id.street or ''
            res['street2'] = employee.address_home_id.street2 or ''
            res['designation'] = employee.job_id.name or ''
            res['company_name'] = employee.company_id.name or ''
            res['company_tax'] = employee.company_id.vat or ''
            res['cmp_street'] = employee.address_id.street or ''
#            res['cmp_street2'] = employee.address_id.street2 or ''
            res['sin_postal_code'] = employee.empnationality_id.name or ''
            child_list = []
            for dependent in employee.dependent_ids:
                child = {}
                if dependent.relation_ship == 'son' or \
                        dependent.relation_ship == 'daughter':
                    child['child_name'] = dependent.first_name
                    child['child_gender'] = dependent.gender
                    if dependent.birth_date:
                        child['birth_date'] = dependent.birth_date.strftime(
                            get_lang(self.env).date_format)
                    else:
                        child['birth_date'] = ''
                child_list.append(child)
            res['child'] = child_list
            for history in employee.history_ids:
                if history.cessation_date:
                    res['cessation_date'] = history.cessation_date.strftime(
                    get_lang(self.env).date_format)
                else:
                    res['cessation_date'] = ''
            for contract_id in contract_ids:
                income_ids = contract_income_tax_obj.search([
                    ('contract_id', '=', contract_id.id),
                    ('start_date', '>=', from_date),
                    ('end_date', '<=', to_date)], limit=1)
                for income in income_ids:
                    prev_income_tax_rec = income.search([
                                ('start_date', '>=', prev_yr_start_date),
                                ('end_date', '<=', prev_yr_end_date)])
                    prev_allowances = (
                            prev_income_tax_rec.entertainment_allowance +
                            prev_income_tax_rec.other_allowance +
                            prev_income_tax_rec.pension)
                    prev_sub_total = int(prev_allowances) + (
                            int(prev_income_tax_rec.gross_commission) +
                            int(prev_income_tax_rec.gratuity_payment_amt) +
                            int(prev_income_tax_rec.compensation_loss_office)
                            + int(prev_income_tax_rec.retirement_benifit_up)
                            + int(prev_income_tax_rec.contribution_employer)
                    + int(prev_income_tax_rec.excess_voluntary_contribution_cpf_employer))
                    prev_total = (int(prev_income_tax_rec.director_fee) +
                                  int(prev_income_tax_rec.payslip_net_amount) +
                                  prev_sub_total)
                    res['pre_dir_fees'] = prev_income_tax_rec.director_fee
                    res['prev_allowance'] = int(prev_allowances) or 0.0
                    res['prev_gratuity_payment_amt'] = (
                            prev_income_tax_rec.gratuity_payment_amt)
                    res['prev_retirement_benifit_up'] = (
                                prev_income_tax_rec.retirement_benifit_up)
                    res['prev_contribution_employer'] = (
                                prev_income_tax_rec.contribution_employer)
                    res['prev_compensation_loss_office'] = (
                            prev_income_tax_rec.compensation_loss_office)
                    res['prev_excess_voluntary_contribution_cpf_employer'
                        ] = (
                    prev_income_tax_rec.excess_voluntary_contribution_cpf_employer)
                    res['prev_donation'] = (prev_income_tax_rec.donation)
                    res['prev_start_date'] = prev_income_tax_rec.start_date
                    res['prev_end_date'] = prev_income_tax_rec.end_date
                    res['prev_gross'] = \
                        prev_income_tax_rec.payslip_net_amount or 0.0
                    res['prev_gross_commission'] = \
                        prev_income_tax_rec.gross_commission or 0.0
                    res['prev_sub_total'] = int(prev_sub_total) or 0.0
                    res['prev_total'] = int(prev_total) or 0.0
                    allowances = (income.entertainment_allowance +
                                  income.other_allowance + income.pension)
                    sub_total = (int(allowances) + int(
                        income.gross_commission) + int(
                            income.gratuity_payment_amt) + int(
                            income.compensation_loss_office) + int(
                            income.retirement_benifit_up) + int(
                            income.contribution_employer) + int(
                        income.excess_voluntary_contribution_cpf_employer))
                    total = (int(income.director_fee) +
                             int(income.payslip_net_amount) + sub_total)
                    res['director_fee'] = income.director_fee
                    res['allowance'] = int(allowances) or 0.0
                    res['gratuity_payment_amt'] = (
                        income.gratuity_payment_amt)
                    res['compensation_loss_office'] = (
                            income.compensation_loss_office)
                    res['fund_name'] = income.fund_name
                    res['retirement_benifit_up'] = (
                            income.retirement_benifit_up)
                    res['contribution_employer'] = (
                            income.contribution_employer)
                    res['excess_voluntary_contribution_cpf_employer'] = (
                        income.excess_voluntary_contribution_cpf_employer)
                    res['donation'] = income.donation
                    res['start_date'] = income.start_date
                    res['end_date'] = income.end_date
                    res['sub_total'] = int(sub_total) or 0.0
                    res['total'] = int(total) or 0.0
                    res['current_gross'] = income.payslip_net_amount or 0.0
                    res['curr_gross_commission'] = income.gross_commission or 0.0
                    res['compensation'] = income.compensation or ''
            vals.append(res)
        return vals

    @api.model
    def _get_report_values(self, docids, data=None):
        model = self.env.context.get('active_model')
        docs = self.env[model].browse(self.env.context.get('active_id'))
        datas = docs.read([])
        report_lines = self.get_data(datas[0])
        return {'doc_ids': self.ids,
                'doc_model': model,
                'data': datas,
                'docs': docs,
                'time': time,
                'get_data': report_lines}
