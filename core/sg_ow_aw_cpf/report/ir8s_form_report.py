import time
from datetime import datetime, date
from odoo.tools.misc import formatLang, get_lang
from odoo import tools
from odoo import api, models
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DSDF


class Ir8sForm(models.AbstractModel):
    _name = "report.sg_income_tax_report.ir8s_incometax_form_report"
    _description = "Ir8s Income tax Report"

    def get_data(self, form):
        vals = []
        user_obj = self.env['res.users']
        contract_brw = self.env['hr.contract']
        incometax_brw = self.env['hr.contract.income.tax']
        start_date = form.get('start_date', False) or False
        end_date = form.get('end_date', False) or False
        wiz_start_date = form.get('start_date', False) or False
        wiz_end_date = form.get('end_date', False) or False
        if start_date and end_date:
            year = start_date.year
            start_year = start_date.year - 1
            end_year = end_date.year - 1
            start_date = '%s-01-01' % tools.ustr(int(start_year))
            end_date = '%s-12-31' % tools.ustr(int(end_year))
#            wiz_start_date = '%s-01-01' % tools.ustr(int(start_year))
#            wiz_end_date = '%s-12-31' % tools.ustr(int(end_year))
            start_date = datetime.strptime(start_date, DSDF)
            end_date = datetime.strptime(end_date, DSDF)
            previous_year = start_year
        contract_rec = contract_brw.search([
            ('employee_id', 'in', form.get('employee_ids'))])
        for contract in contract_rec:
            income_tax_rec = incometax_brw.search([
                ('contract_id', '=', contract.id),
                ('start_date', '>=', wiz_start_date),
                ('end_date', '<=', wiz_end_date)])
            employee_id = contract.employee_id
            for contract_income_tax in income_tax_rec:
                res = {}
                birthday = cessation_date = ''
                if employee_id.birthday:
                    birthday = employee_id.birthday.strftime(
                                get_lang(self.env).date_format)
                if employee_id.cessation_date:
                    cessation_date = datetime.strptime(
                                            employee_id.cessation_date, DSDF)
                    cessation_date = cessation_date.strftime('%d/%m/%Y')
                employee_rec = self.env['hr.employee'].search([
                    ('user_id', '=', int(form.get('payroll_user')))])
                emp_designation = ''
                payroll_admin_user_name = user_obj.\
                    browse(int(form.get('payroll_user'))).name
                signature = user_obj.\
                    browse(int(form.get('payroll_user'))).signature
                for emp in employee_rec:
                    emp_designation = emp.job_id.name
                res['emp_designation'] = emp_designation
                res['signature'] = signature
                res['payroll_admin_user_name'] = payroll_admin_user_name
                cpf_data = {}
                for income_tax_rec in contract_income_tax:
                    months = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
                    payslip_rec = self.env['hr.payslip'].search([
                                ('date_from', '>=', start_date),
                                ('date_from', '<=', end_date),
                                ('employee_id', '=', contract.employee_id.id),
                                ('state', 'in', ['draft', 'done', 'verify'])])
                    for payslip in payslip_rec:
                        payslip_dt = payslip.date_from
                        payslip_month = payslip_dt.month or ''
#                         added new features
                        ow_wages = aw_wages = ow_empyr_amt = ow_emp_amt = \
                            temp_aw = temp_ow = aw_empyr_amt = aw_emp_amt = 0
                        obj_rule = self.env['hr.salary.rule']
                        ow_ids = obj_rule.search([('is_cpf', '=', 'ow')])
                        aw_ids = obj_rule.search([('is_cpf', '=', 'aw')])
                        for line in payslip.line_ids:
                            if line.salary_rule_id.is_cpf == 'ow':
                                ow_wages += line.total
                            if line.salary_rule_id.is_cpf == 'aw':
                                aw_wages += line.total
                            if line.code == 'CPFEE_SPR_SIN_OW':
                                temp_ow = line.total
                            if line.code == 'CPFEE_SPR_SIN_AW':
                                temp_aw = line.total
                            if line.code == 'CPFEE_SPR_SIN_OW_EMP':
                                ow_emp_amt = line.total
                                ow_empyr_amt = temp_ow - line.total
                            if line.code == 'CPFEE_SPR_SIN_AW_EMP':
                                aw_emp_amt = line.total
                                aw_empyr_amt = temp_aw - line.total
                        cpf_data.update({payslip_dt.month: [ow_wages,
                                                            ow_empyr_amt,
                                                            ow_emp_amt,
                                                            aw_wages,
                                                            aw_empyr_amt,
                                                            aw_emp_amt]})
                        if payslip_dt.month in months:
                            months.remove(payslip_dt.month)
                    for rest_mnth in months:
                        cpf_data.update({rest_mnth: [0.0, 0.0,
                                                     0.0, 0.0,
                                                     0.0, 0.0]})
                    res['cpf_data'] = cpf_data
                    res['emp_name'] = contract.employee_id.name
                    res['identification_id'] = \
                        contract.employee_id.identification_id
                    res['work_phone'] = contract.employee_id.work_phone
                    res['birthday'] = birthday
                    res['cessation_date'] = cessation_date
                    res['eyer_contibution'] = formatLang(
                        self.env, income_tax_rec.eyer_contibution)
                    res['eyee_contibution'] = formatLang(
                        self.env, income_tax_rec.eyee_contibution)
                    res['additional_wage'] = formatLang(
                        self.env, income_tax_rec.additional_wage)
                    if income_tax_rec.add_wage_pay_date:
                        res['add_wage_pay_date'] = income_tax_rec.add_wage_pay_date.strftime(
                            get_lang(self.env).date_format)
                    res['refund_eyers_contribution'] = formatLang(
                        self.env, income_tax_rec.refund_eyers_contribution)
                    res['refund_eyees_contribution'] = formatLang(
                        self.env, income_tax_rec.refund_eyees_contribution)
                    if income_tax_rec.refund_eyers_date:
                        res['refund_eyers_date'] = income_tax_rec.refund_eyers_date.strftime(
                            get_lang(self.env).date_format)
                    if income_tax_rec.refund_eyees_date:
                        res['refund_eyees_date'] = income_tax_rec.refund_eyees_date.strftime(
                            get_lang(self.env).date_format)
                    res['refund_eyers_interest_contribution'] = formatLang(
                        self.env,
                        income_tax_rec.refund_eyers_interest_contribution)
                    res['refund_eyees_interest_contribution'] = formatLang(
                        self.env,
                        income_tax_rec.refund_eyees_interest_contribution)
                    res['date_today'] = date.today().strftime(get_lang(self.env).date_format) or ''
                    res['previous_year'] = previous_year
                    res['year'] = year
                vals.append(res)
        return vals

    @api.model
    def _get_report_values(self, docids, data):
        model = self.env.context.get('active_model')
        docs = self.env[model].browse(self.env.context.get('active_id'))
        datas = docs.read([])[0]
        report_lines = self.get_data(datas)
        return {'doc_ids': self.ids,
                'doc_model': model,
                'data': datas,
                'docs': docs,
                'time': time,
                'get_data': report_lines}
