import time
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo import api, models
from odoo.tools.misc import formatLang
from odoo.tools.misc import get_lang


class Ir8sForm(models.AbstractModel):
    _name = "report.sg_income_tax_report.ir8s_incometax_form_report"
    _description = "Ir8sForm"

    def get_data(self, form):
        vals = []
        start_date = form.get('start_date', False) or False
        end_date = form.get('end_date', False) or False
        wiz_start_date = form.get('start_date', False) or False
        wiz_end_date = form.get('end_date', False) or False
        if start_date and end_date:
            start_date = start_date + relativedelta(month=1, day=1, years=-1)
            end_date = end_date + relativedelta(month=12, day=31, years=-1)
        previous_year = start_date.year - 1
        year = start_date.year

        contract_obj = self.env['hr.contract']
        incometax_obj = self.env['hr.contract.income.tax']
        emp_obj = self.env['hr.employee']
        user_obj = self.env['res.users']
        contract_rec = contract_obj.search([
            ('employee_id', 'in', form.get('employee_ids'))])
        for contract in contract_rec:
            income_tax_rec = incometax_obj.search([
                ('contract_id', '=', contract.id),
                ('start_date', '>=', wiz_start_date),
                ('end_date', '<=', wiz_end_date)])
            for contract_income_tax in income_tax_rec:
                res = {}
                birthday = cessation_date = ''
                if contract.employee_id.birthday:
                    birthday = contract.employee_id.birthday.strftime(
                        '%d/%m/%Y')
                if contract.employee_id.cessation_date:
                    cessation_date = (
                        contract.employee_id.cessation_date.strftime(
                            '%d/%m/%Y'))
                emp_domain = [('user_id', '=', int(form.get('payroll_user')))]
                employee_rec = emp_obj.search(emp_domain)
                emp_designation = ''
                pay_user_brw = user_obj.browse(int(form.get('payroll_user')))
                payroll_admin_user_name = pay_user_brw.name
                signature = pay_user_brw.signature
                for emp in employee_rec:
                    emp_designation = emp.job_id.name
                res['emp_designation'] = emp_designation
                res['signature'] = signature
                res['payroll_admin_user_name'] = payroll_admin_user_name

                payslip_obj = self.env['hr.payslip']
                for income_tax_rec in contract_income_tax:
                    p_domain = [('date_from', '>=', start_date),
                                ('date_from', '<=', end_date),
                                ('employee_id', '=', contract.employee_id.id),
                                ('state', 'in', ['draft', 'done', 'verify'])]
                    payslip_rec = payslip_obj.search(p_domain)
                    jan_gross_amt = feb_gross_amt = march_gross_amt = \
                        apr_gross_amt = may_gross_amt = june_gross_amt = \
                        july_gross_amt = aug_gross_amt = sept_gross_amt = \
                        oct_gross_amt = nov_gross_amt = dec_gross_amt = 0
                    jan_empoyer_amt = feb_empoyer_amt = march_empoyer_amt = \
                        apr_empoyer_amt = may_empoyer_amt = \
                        june_empoyer_amt = july_empoyer_amt = \
                        aug_empoyer_amt = sept_empoyer_amt = \
                        oct_empoyer_amt = nov_empoyer_amt = dec_empoyer_amt = 0
                    jan_empoyee_amt = feb_empoyee_amt = march_empoyee_amt = \
                        apr_empoyee_amt = may_empoyee_amt = \
                        june_empoyee_amt = july_empoyee_amt = \
                        aug_empoyee_amt = sept_empoyee_amt = \
                        oct_empoyee_amt = nov_empoyee_amt = dec_empoyee_amt = 0
                    tot_gross_amt = tot_empoyee_amt = tot_empoyer_amt = 0
                    for payslip in payslip_rec:
                        payslip_month = ''
                        payslip_month = payslip.date_from.strftime('%m')
                        gross_amt = empoyer_amt = empoyee_amt = 0
                        for line in payslip.line_ids:
                            if line.code == 'NET':
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
                    res['emp_name'] = contract.employee_id.name
                    res['identification_id'] = \
                        contract.employee_id.identification_id
                    res['work_phone'] = contract.employee_id.work_phone
                    res['birthday'] = birthday
                    res['cessation_date'] = cessation_date
                    res['jan_gross_amt'] = formatLang(self.env, jan_gross_amt)
                    res['feb_gross_amt'] = formatLang(self.env, feb_gross_amt)
                    res['march_gross_amt'] = \
                        formatLang(self.env, march_gross_amt)
                    res['apr_gross_amt'] = formatLang(self.env, apr_gross_amt)
                    res['may_gross_amt'] = formatLang(self.env, may_gross_amt)
                    res['june_gross_amt'] = \
                        formatLang(self.env, june_gross_amt)
                    res['july_gross_amt'] = \
                        formatLang(self.env, july_gross_amt)
                    res['aug_gross_amt'] = formatLang(self.env, aug_gross_amt)
                    res['sept_gross_amt'] = \
                        formatLang(self.env, sept_gross_amt)
                    res['oct_gross_amt'] = formatLang(self.env, oct_gross_amt)
                    res['nov_gross_amt'] = formatLang(self.env, nov_gross_amt)
                    res['dec_gross_amt'] = formatLang(self.env, dec_gross_amt)

                    res['jan_empoyee_amt'] = \
                        formatLang(self.env, jan_empoyee_amt)
                    res['feb_empoyee_amt'] = \
                        formatLang(self.env, feb_empoyee_amt)
                    res['march_empoyee_amt'] = \
                        formatLang(self.env, march_empoyee_amt)
                    res['apr_empoyee_amt'] = \
                        formatLang(self.env, apr_empoyee_amt)
                    res['may_empoyee_amt'] = \
                        formatLang(self.env, may_empoyee_amt)
                    res['june_empoyee_amt'] = \
                        formatLang(self.env, june_empoyee_amt)
                    res['july_empoyee_amt'] = \
                        formatLang(self.env, july_empoyee_amt)
                    res['aug_empoyee_amt'] = \
                        formatLang(self.env, aug_empoyee_amt)
                    res['sept_empoyee_amt'] = \
                        formatLang(self.env, sept_empoyee_amt)
                    res['oct_empoyee_amt'] = \
                        formatLang(self.env, oct_empoyee_amt)
                    res['nov_empoyee_amt'] = \
                        formatLang(self.env, nov_empoyee_amt)
                    res['dec_empoyee_amt'] = \
                        formatLang(self.env, dec_empoyee_amt)

                    res['jan_empoyer_amt'] = \
                        formatLang(self.env, jan_empoyer_amt)
                    res['feb_empoyer_amt'] = \
                        formatLang(self.env, feb_empoyer_amt)
                    res['march_empoyer_amt'] = \
                        formatLang(self.env, march_empoyer_amt)
                    res['apr_empoyer_amt'] = \
                        formatLang(self.env, apr_empoyer_amt)
                    res['may_empoyer_amt'] = \
                        formatLang(self.env, may_empoyer_amt)
                    res['june_empoyer_amt'] = \
                        formatLang(self.env, june_empoyer_amt)
                    res['july_empoyer_amt'] = \
                        formatLang(self.env, july_empoyer_amt)
                    res['aug_empoyer_amt'] = \
                        formatLang(self.env, aug_empoyer_amt)
                    res['sept_empoyer_amt'] = \
                        formatLang(self.env, sept_empoyer_amt)
                    res['oct_empoyer_amt'] = \
                        formatLang(self.env, oct_empoyer_amt)
                    res['nov_empoyer_amt'] = \
                        formatLang(self.env, nov_empoyer_amt)
                    res['dec_empoyer_amt'] = \
                        formatLang(self.env, dec_empoyer_amt)

                    res['eyer_contibution'] = \
                        formatLang(self.env, income_tax_rec.eyer_contibution)
                    res['eyee_contibution'] = \
                        formatLang(self.env, income_tax_rec.eyee_contibution)

                    res['additional_wage'] = \
                        formatLang(self.env, income_tax_rec.additional_wage)
                    res['add_wage_pay_date'] = income_tax_rec.add_wage_pay_date
                    res['refund_eyers_contribution'] = \
                        formatLang(self.env,
                                   income_tax_rec.refund_eyers_contribution)
                    res['refund_eyees_contribution'] = \
                        formatLang(self.env,
                                   income_tax_rec.refund_eyees_contribution)
                    res['refund_eyers_date'] = income_tax_rec.refund_eyers_date
                    res['refund_eyees_date'] = income_tax_rec.refund_eyees_date
                    name1 = income_tax_rec.refund_eyers_interest_contribution
                    res['refund_eyers_interest_contribution'] = \
                        formatLang(self.env, name1)
                    name2 = income_tax_rec.refund_eyees_interest_contribution
                    res['refund_eyees_interest_contribution'] = \
                        formatLang(self.env, name2)
                    res['date_today'] = datetime.today().date().strftime(get_lang(self.env).date_format) or ''
                    res['previous_year'] = previous_year
                    res['year'] = year
                    res['tot_gross_amt'] = tot_gross_amt
                    res['tot_empoyer_amt'] = tot_empoyer_amt
                    res['tot_empoyee_amt'] = tot_empoyee_amt
                vals.append(res)
        return vals

    @api.model
    def _get_report_values(self, docids, data):
        self.model = self.env.context.get('active_model')
        docs = self.env[self.model].browse(self.env.context.get('active_id'))
        datas = docs.read([])[0]
        report_lines = self.get_data(datas)
        return {'doc_ids': self.ids,
                'doc_model': self.model,
                'data': datas,
                'docs': docs,
                'time': time,
                'get_data': report_lines}
