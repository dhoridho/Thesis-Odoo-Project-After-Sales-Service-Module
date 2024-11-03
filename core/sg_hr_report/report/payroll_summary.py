import time

from odoo import api, models


class PayrollSummaryReport(models.AbstractModel):
    _name = 'report.sg_hr_report.hr_payroll_summary_report_tmp'
    _description = "Payroll Summary Report"

    @api.model
    def get_name(self, data):
        date_from = data.get('date_from' or False)
        date_to = data.get('date_to' or False)
        final_group_total = []

        result = {}
        total = {}
        emp_obj = self.env['hr.employee']
        payslip_obj = self.env['hr.payslip']
        employee_ids = emp_obj.search([('id', 'in', data.get('employee_ids'))])
        for employee in employee_ids:
            payslip_ids = payslip_obj.search(
                [('employee_id', '=', employee.id),
                 ('date_from', '>=', date_from),
                 ('date_from', '<=', date_to),
                 ('state', 'in', ['draft', 'done', 'verify'])])
            commission = incentive = net = lvd = exa = exd = gross =\
                twage = 0.0
            cpf = pf = overtime = backpay = bonus = donation = cpftotal = 0.0
            sdl = fwl = 0.0
            for payslip in payslip_ids:
                twage += payslip.contract_id.wage_to_pay
                for rule in payslip.details_by_salary_rule_category:
                    if rule.code == 'SC102':
                        overtime += rule.total
                    if rule.code == 'SC104':
                        commission += rule.total
                    if rule.code == 'SC105':
                        incentive += rule.total
                    if rule.code == 'NET':
                        net += rule.total
                    if rule.code == 'SC196':
                        lvd += rule.total
                    if rule.code == 'SC122':
                        exa += rule.total
                    if rule.code == 'SC299':
                        exd += rule.total
                    if rule.code == 'GROSS':
                        gross += rule.total
                    if rule.category_id.code == 'CAT_CPF_EMPLOYEE':
                        cpf += rule.total
                    if rule.category_id.code == 'CAT_CPF_EMPLOYER':
                        pf += rule.total
                    if rule.category_id.code == 'CAT_CPF_TOTAL':
                        cpftotal += rule.total
                    if rule.code == 'SC48':
                        backpay += rule.total
                    if rule.code == 'SC121':
                        bonus += rule.total
                    if rule.register_id.name in ['CPF - ECF', 'CPF - MBMF',
                                                 'CPF - SINDA', 'CPF - CDAC']:
                        donation += rule.total
                    if rule.code == 'CPFSDL':
                        sdl += rule.total
                    if rule.code == 'FWL':
                        fwl += rule.total
                payslip_result = {'ename': payslip.employee_id.name or '',
                                  'eid': payslip.employee_id and
                                  payslip.employee_id.user_id and
                                  payslip.employee_id.user_id.login or '',
                                  'payslip_name': payslip.name,
                                  'twage': twage,
                                  'net': net or 0.0,
                                  'lvd': lvd or 0.0,
                                  'exa': exa or 0.0,
                                  'exd': exd or 0.0,
                                  'gross': gross or 0.0,
                                  'cpf': cpf or 0.0,
                                  'pf': pf or 0.0,
                                  'bonus': bonus or 0.0,
                                  'overtime': overtime or 0.0,
                                  'donation': donation or 0.0,
                                  'cpftotal': cpftotal or 0.0,
                                  'sdl': sdl or 0.0,
                                  'fwl': fwl or 0.0,
                                  'incentive': incentive or 0.0,
                                  'commission': commission or 0.0}
                if payslip.employee_id.department_id:
                    department_id = payslip.employee_id.department_id.id
                    if department_id in result:
                        result.get(department_id).append(payslip_result)
                    else:
                        result.update({department_id: [payslip_result]})
                else:
                    if 'Undefined' in result:
                        result.get('Undefined').append(payslip_result)
                    else:
                        result.update({'Undefined': [payslip_result]})
        finalcommission = finalincentive = finaltwage = finalnet = finallvd = 0
        finalexa = finalexd = finalgross = finalcpf = finalpf = 0
        finalovertime = finalbackpay = finalbonus = finaldonation = 0
        finalcpftotal = finalsdl = finalfwl = 0
        final_result = {}
        for key, val in result.items():
            if key == 'Undefined':
                category_name = 'Undefined'
            else:
                category_name = self.env['hr.department'].browse(key).name
            total = {'name': category_name, 'commission': 0.0,
                     'incentive': 0.0, 'twage': 0.0, 'net': 0.0,
                     'lvd': 0.0, 'exa': 0.0,
                     'exd': 0.0, 'gross': 0.0, 'cpf': 0.0, 'pf': 0.0,
                     'overtime': 0.0, 'backpay': 0.0, 'bonus': 0.0,
                     'donation': 0.0, 'cpftotal': 0.0, 'sdl': 0.0,
                     'fwl': 0.0}
            for line in val:
                for field in line:
                    if field in total:
                        total.update({field: total.get(field) +
                                      line.get(field)})
            final_result[key] = {'lines': val, 'total': total}
            finaltwage += total['twage']
            finalnet += total['net']
            finallvd += total['lvd']
            finalexa += total['exa']
            finalexd += total['exd']
            finalgross += total['gross']
            finalcpf += total['cpf']
            finalpf += total['pf']
            finalovertime += total['overtime']
            finalbackpay += total['backpay']
            finalbonus += total['bonus']
            finaldonation += total['donation']
            finalcpftotal += total['cpftotal']
            finalsdl += total['sdl']
            finalfwl += total['fwl']
            finalcommission += total['commission']
            finalincentive += total['incentive']

        final_total = {'twage': finaltwage or 0.0,
                       'net': finalnet or 0.0,
                       'lvd': finallvd or 0.0,
                       'exa': finalexa or 0.0,
                       'exd': finalexd or 0.0,
                       'gross': finalgross or 0.0,
                       'cpf': finalcpf or 0.0,
                       'pf': finalpf or 0.0,
                       'overtime': finalovertime or 0.0,
                       'backpay': finalbackpay or 0.0,
                       'bonus': finalbonus or 0.0,
                       'donation': finaldonation or 0.0,
                       'cpftotal': finalcpftotal or 0.0,
                       'sdl': finalsdl or 0.0,
                       'fwl': finalfwl or 0.0,
                       'commission': finalcommission or 0.0,
                       'incentive': finalincentive or 0.0}
        final_group_total.append(final_total)
        return final_result.values(), final_group_total

#     @api.model
#     def finalgrouptotal(self):
#         return self.final_group_total

    def _get_report_values(self, docids, data=None):
        ctx = self.env.context
        model = ctx.get('active_model', 'payroll.summary.wizard')
        docs = self.env[model].browse(ctx.get('active_id', docids))
        get_name, finalgrouptotal = self.get_name(data)
        return {'doc_ids': self.ids,
                'doc_model': model,
                'data': data,
                'docs': docs,
                'time': time,
                'get_name': get_name,
                'finalgrouptotal': finalgrouptotal or []}
