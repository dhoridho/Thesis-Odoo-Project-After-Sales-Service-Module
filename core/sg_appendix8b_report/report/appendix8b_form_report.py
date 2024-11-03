import time
from datetime import datetime

from odoo import api, models, tools, _
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DSDF


class PpdAppendix8bForm(models.AbstractModel):
    _name = "report.sg_appendix8b_report.report_appendix8b"
    _description = "Appendix 8b report"

    def get_employee(self, data):
        result = []
        hr_contract_income_tax = self.env['hr.contract.income.tax']
        contract_ids = self.env['hr.contract'].search([
            ('employee_id', 'in', data.get('employee_ids', []))])
        if len(contract_ids.ids) == 0:
            raise UserError(_('No Contract found for selected dates'))
        employer_name = emp_add = authorized_person = batchdate = ''
        cmp_reg_no = autho_person_desg = autho_person_tel = last_year = ''
        from_date = to_date = start_date = end_date = False
        if data.get('start_date', False) and data.get('end_date', False):
            from_date = data.get('start_date', False)
            to_date = data.get('end_date', False)
            fiscal_start = from_date.year - 1
            fiscal_end = to_date.year - 1
            start_date = '%s-01-01' % tools.ustr(int(fiscal_start))
            end_date = '%s-12-31' % tools.ustr(int(fiscal_end))
            start_date = datetime.strptime(start_date, DSDF)
            end_date = datetime.strptime(end_date, DSDF)
        if data.get('payroll_user'):
            payroll_use_id = int(data['payroll_user'])
            authorized_person = self.env['res.users'
                                         ].browse(payroll_use_id).name
            payroll_emp = self.env['hr.employee'].search([
                ('user_id', '=', payroll_use_id)])
            if len(payroll_emp.ids) != 0:
                premp_brw = payroll_emp[0]
                autho_person_desg = premp_brw.job_id and \
                    premp_brw.job_id.id and premp_brw.job_id.name or ''
                autho_person_tel = premp_brw.work_phone or ''
        if data.get('batch_date'):
            batchdate = data['batch_date'].strftime('%d/%m/%Y')
        for contract in contract_ids:
            employee_id = contract.employee_id
            contract_income_tax_id = hr_contract_income_tax.search([
                                            ('contract_id', '=', contract.id),
                                            ('start_date', '>=', from_date),
                                            ('end_date', '<=', to_date)],
                                            limit=1)
            if contract_income_tax_id:
                vals = []
                gross_amt_qulfy_secA_s10_b = 0.0
                gorss_amt_gain_secA_s10_b = 0.0
                gross_amt_qulfy_secA_s10_g = 0.0
                gorss_amt_gain_secA_s10_g = 0.0

                gross_amt_qulfy_secB_s10_b = 0.0
                gross_amt_qulfy_secB_s10_g = 0.0
                gorss_amt_gain_secB_s10_b = 0.0
                gorss_amt_gain_secB_g = 0.0
                eris_smes_secB_s10_b = 0.0
                eris_smes_secB_s10_g = 0.0

                gross_amt_qulfy_secC_s10_b = 0.0
                gorss_amt_gain_secC_b = 0.0
                eris_all_corporation_secC_s10_b = 0.0
                gross_amt_qulfy_secC_s10_g = 0.0
                gorss_amt_gain_secC_g = 0.0
                eris_all_corporation_secC_s10_g = 0.0

                eris_start_ups_secD_s10_b = 0.0
                eris_start_ups_secD_s10_g = 0.0
                gross_amt_qulfy_secD_s10_b = 0.0
                gorss_amt_gain_secD_s10_b = 0.0
                gross_amt_qulfy_secD_s10_g = 0.0
                gorss_amt_gain_secD_s10_g = 0.0

                grand_total_secE_gross_amt_qulfy_s10_b = 0.0
                grand_total_secE_gross_amt_qulfy_s10_g = 0.0
                grand_total_secE_gorss_amt_gain_s10_b = 0.0
                grand_total_secE_gorss_amt_gain_s10_g = 0.0

                for res in contract_income_tax_id.app_8b_income_tax:
                    cmp_reg_no = employee_id.company_id and \
                        employee_id.company_id.company_registry
                    employer_name = employee_id.address_id and \
                        employee_id.address_id.name or ''
                    if employee_id.address_id and \
                            employee_id.address_id.id:
                        emp_add = str(employee_id.address_id.street or ''
                                      ) + ',' + \
                                  str(employee_id.address_id.street2 or '')
                    if from_date:
                        last_year = fiscal_start or ''
                    tax_plan = ''
                    exercise_date = ''
                    exercise_price = open_market_val = 0.0
                    open_market_val1 = 0.0
                    if res.tax_plan == 'esop':
                        tax_plan = 'ESOP'
                        exercise_price += res.ex_price_esop
                        open_market_val1 += res.open_val_esop
                        if res.is_moratorium is True:
                            exercise_date = res.moratorium_date
                            open_market_val += res.moratorium_price
                        else:
                            exercise_date = res.esop_date
                            open_market_val += res.open_val_esop
                        grant_date = res.tax_plan_grant_date.strftime(
                            '%Y/%m/%d')
                        esop_appvl_date = '2003-01-01'
                        if res.section == 'sectionA':
                            if grant_date > esop_appvl_date:
                                gross_amt_qulfy_secA_s10_b += \
                                                res.secA_grss_amt_qulfy_tx
                                gorss_amt_gain_secA_s10_b += \
                                    res.secA_grss_amt_qulfy_tx
                            elif grant_date < esop_appvl_date:
                                gross_amt_qulfy_secA_s10_g += \
                                            res.secA_grss_amt_qulfy_tx
                                gorss_amt_gain_secA_s10_g += \
                                    res.secA_grss_amt_qulfy_tx
                        elif res.section == 'sectionB':
                            if grant_date > esop_appvl_date:
                                gross_amt_qulfy_secB_s10_b += \
                                                res.secB_grss_amt_qulfy_tx
                                gorss_amt_gain_secB_s10_b += \
                                    res.eris_smes + \
                                    res.secB_grss_amt_qulfy_tx
                                eris_smes_secB_s10_b += res.eris_smes
                            elif grant_date < esop_appvl_date:
                                gross_amt_qulfy_secB_s10_g += \
                                            res.secB_grss_amt_qulfy_tx
                                gorss_amt_gain_secB_g += res.eris_smes + \
                                    res.secB_grss_amt_qulfy_tx
                                eris_smes_secB_s10_g += res.eris_smes
                        elif res.section == 'sectionC':
                            if grant_date > esop_appvl_date:
                                gross_amt_qulfy_secC_s10_b += \
                                            res.secC_grss_amt_qulfy_tx
                                gorss_amt_gain_secC_b += res.eris_smes + \
                                    res.secC_grss_amt_qulfy_tx
                                eris_all_corporation_secC_s10_b += \
                                    res.eris_smes
                            elif grant_date < esop_appvl_date:
                                gross_amt_qulfy_secC_s10_g += \
                                                res.secC_grss_amt_qulfy_tx
                                gorss_amt_gain_secC_g += res.eris_smes + \
                                    res.secC_grss_amt_qulfy_tx
                                eris_all_corporation_secC_s10_g += \
                                    res.eris_smes
                        elif res.section == 'sectionD':
                            if grant_date > esop_appvl_date:
                                gross_amt_qulfy_secD_s10_b += \
                                                res.secD_grss_amt_qulfy_tx
                                gorss_amt_gain_secD_s10_b += \
                                    res.eris_start_ups + \
                                    res.secD_grss_amt_qulfy_tx
                                eris_start_ups_secD_s10_b += \
                                    res.eris_start_ups
                            elif grant_date < esop_appvl_date:
                                gross_amt_qulfy_secD_s10_g += \
                                            res.secD_grss_amt_qulfy_tx
                                gorss_amt_gain_secD_s10_g += \
                                    res.eris_smes + \
                                    res.secC_grss_amt_qulfy_tx
                                eris_start_ups_secD_s10_g += \
                                    res.eris_start_ups
                    if res.tax_plan == 'esow':
                        tax_plan = 'ESOW'
                        exercise_price += res.pay_under_esow
                        open_market_val1 += res.esow_plan
                        if res.is_moratorium is True:
                            exercise_date = res.moratorium_date
                            open_market_val += res.moratorium_price
                        else:
                            exercise_date = res.esow_date
                            open_market_val += res.esow_plan
                        if res.section == 'sectionA':
                            gross_amt_qulfy_secA_s10_b += \
                                res.secA_grss_amt_qulfy_tx
                            gorss_amt_gain_secA_s10_b += \
                                res.secA_grss_amt_qulfy_tx
                        elif res.section == 'sectionB':
                            gross_amt_qulfy_secB_s10_b += \
                                res.secB_grss_amt_qulfy_tx
                            gorss_amt_gain_secB_s10_b += res.eris_smes + \
                                res.secB_grss_amt_qulfy_tx
                            eris_smes_secB_s10_b += res.eris_smes
                        elif res.section == 'sectionC':
                            gross_amt_qulfy_secC_s10_b += \
                                res.secC_grss_amt_qulfy_tx
                            gorss_amt_gain_secC_b += res.eris_smes + \
                                res.secC_grss_amt_qulfy_tx
                            eris_all_corporation_secC_s10_b += \
                                res.eris_smes
                        elif res.section == 'sectionD':
                            gross_amt_qulfy_secD_s10_b += \
                                                res.secD_grss_amt_qulfy_tx
                            gorss_amt_gain_secD_s10_b += \
                                res.eris_start_ups + \
                                res.secD_grss_amt_qulfy_tx
                            eris_start_ups_secD_s10_b += res.eris_start_ups
                    vals.append({
                        'indicator': tax_plan,
                        'section': res.section,
                        'grant_date': res.tax_plan_grant_date,
                        'exercise_date': exercise_date,
                        'exercise_price': exercise_price,
                        'open_market_val': open_market_val,
                        'no_of_share': res.no_of_share,
                        'gross_amt_secA': res.secA_grss_amt_qulfy_tx,
                        'open_market_val1': open_market_val1,
                        'eris_smes': res.eris_smes or 0.0,
                        'gross_amt_secB': res.secB_grss_amt_qulfy_tx,
                        'gross_amt_secB_1': (res.eris_smes +
                                             res.secB_grss_amt_qulfy_tx),
                        'eris_all_corporation': res.eris_all_corporation,
                        'gross_amt_secC': res.secC_grss_amt_qulfy_tx,
                        'gross_amt_secC_1': (res.eris_all_corporation +
                                             res.secC_grss_amt_qulfy_tx),
                        'eris_start_ups': res.eris_start_ups,
                        'gross_amt_secD': res.secD_grss_amt_qulfy_tx,
                        'gross_amt_secD_1': (res.eris_start_ups +
                                             res.secD_grss_amt_qulfy_tx),
                    })
                grand_total_secE_gross_amt_qulfy_s10_b = \
                gross_amt_qulfy_secA_s10_b + gross_amt_qulfy_secB_s10_b + \
                gross_amt_qulfy_secC_s10_b + gross_amt_qulfy_secD_s10_b

                grand_total_secE_gross_amt_qulfy_s10_g = \
                gross_amt_qulfy_secA_s10_g + gross_amt_qulfy_secB_s10_g + \
                gross_amt_qulfy_secC_s10_g + gross_amt_qulfy_secD_s10_g

                grand_total_secE_gorss_amt_gain_s10_b = \
                gorss_amt_gain_secA_s10_b + gorss_amt_gain_secB_s10_b + \
                gorss_amt_gain_secC_b + gorss_amt_gain_secD_s10_b

                grand_total_secE_gorss_amt_gain_s10_g = \
                gorss_amt_gain_secA_s10_g + gorss_amt_gain_secB_g + \
                gorss_amt_gain_secC_g + gorss_amt_gain_secD_s10_g

                result.append({
                   'year_id': from_date.year or '',
                   'last_year': last_year,
                   'employee_name': employee_id.name,
                   'employer_name': employer_name,
                   'employer_address': emp_add,
                   'authorized_person': authorized_person,
                   'autho_person_desg': autho_person_desg,
                   'autho_person_tel': autho_person_tel,
                   'cmp_reg_no': cmp_reg_no,
                   'emp_id_no': employee_id.identification_id or '',
                   'batchdate': batchdate or '',
                   'vals': vals,
                   'gross_amt_qulfy_secA_s10_b': gross_amt_qulfy_secA_s10_b,
                   'gorss_amt_gain_secA_s10_b': gorss_amt_gain_secA_s10_b,
                   'gross_amt_qulfy_secA_s10_g': gross_amt_qulfy_secA_s10_g,
                   'gorss_amt_gain_secA_s10_g': gorss_amt_gain_secA_s10_g,
                   'gross_amt_qulfy_secB_s10_b': gross_amt_qulfy_secB_s10_b,
                   'gross_amt_qulfy_secB_s10_g': gross_amt_qulfy_secB_s10_g,
                   'gorss_amt_gain_secB_s10_b': gorss_amt_gain_secB_s10_b,
                   'gorss_amt_gain_secB_s10_g': gorss_amt_gain_secB_g,
                   'eris_smes_secB_s10_b': eris_smes_secB_s10_b,
                   'eris_smes_secB_s10_g': eris_smes_secB_s10_g,
                   'gross_amt_qulfy_secC_s10_b': gross_amt_qulfy_secC_s10_b,
                   'gorss_amt_gain_secC_s10_b': gorss_amt_gain_secC_b,
                   'eris_all_corporation_secC_s10_b':
                   eris_all_corporation_secC_s10_b,
                   'gross_amt_qulfy_secC_s10_g': gross_amt_qulfy_secC_s10_g,
                   'gorss_amt_gain_secC_s10_g': gorss_amt_gain_secC_g,
                   'eris_all_corporation_secC_s10_g':
                   eris_all_corporation_secC_s10_g,
                   'eris_start_ups_secD_s10_b': eris_start_ups_secD_s10_b,
                   'eris_start_ups_secD_s10_g': eris_start_ups_secD_s10_g,
                   'gross_amt_qulfy_secD_s10_b': gross_amt_qulfy_secD_s10_b,
                   'gorss_amt_gain_secD_s10_b': gorss_amt_gain_secD_s10_b,
                   'gross_amt_qulfy_secD_s10_g': gross_amt_qulfy_secD_s10_g,
                   'gorss_amt_gain_secD_s10_g': gorss_amt_gain_secD_s10_g,
                   'grand_total_secE_gross_amt_qulfy_s10_b':
                   grand_total_secE_gross_amt_qulfy_s10_b,
                   'grand_total_secE_gross_amt_qulfy_s10_g':
                   grand_total_secE_gross_amt_qulfy_s10_g,
                   'grand_total_secE_gorss_amt_gain_s10_b':
                   grand_total_secE_gorss_amt_gain_s10_b,
                   'grand_total_secE_gorss_amt_gain_s10_g':
                   grand_total_secE_gorss_amt_gain_s10_g,
                })
        return result

    @api.model
    def _get_report_values(self, docids, data=None):
        model = self.env.context.get('active_model')
        docs = self.env[model].browse(self.env.context.get('active_id'))
        data = docs.read([])[0]
        report_lines = self.get_employee(data)
        return {
            'doc_ids': self.ids,
            'doc_model': model,
            'data': data,
            'docs': docs,
            'time': time,
            'get_employee': report_lines
        }
