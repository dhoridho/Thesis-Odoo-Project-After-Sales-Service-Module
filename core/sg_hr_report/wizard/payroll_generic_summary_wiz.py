
import base64
import io
import time
#  from cStringIO import StringIO
from datetime import datetime
from odoo.tools.misc import formatLang, format_date, get_lang

from dateutil.relativedelta import relativedelta as rv

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

import xlwt


class PayrollExcelExportSummary(models.TransientModel):
    _name = "payroll.excel.export.summary"
    _description = "Payroll Excel Export Summary"

    file = fields.Binary(
        "Click On Download Link To Download Xls File", readonly=True)
    name = fields.Char("Name", default='generic summary.xls')


class PayrollGenericSummaryWizard(models.TransientModel):
    _name = 'payroll.generic.summary.wizard'
    _description = "Payroll Generic Summary"

    date_from = fields.Date(
        'Date From',
        default=lambda *a: time.strftime('%Y-%m-01'))
    date_to = fields.Date(
        'Date To',
        default=lambda *a: str(datetime.now() + rv(
            months=+1, day=1, days=-1))[:10])
    employee_ids = fields.Many2many(
        'hr.employee',
        'hr_employee_payroll_rel4',
        'emp_id4', 'employee_id', 'Employee Name')
    salary_rule_ids = fields.Many2many(
        'hr.salary.rule', 'hr_employe_salary_rule_rel', 'salary_rule_id',
        'employee_id', 'Employee payslip')

    @api.model
    def intcomma(self, n, thousands_sep):
        sign = '-' if n < 0 else ''
        n = str(abs(n)).split('.')
        dec = '' if len(n) == 1 else '.' + n[1]
        n = n[0]
        m = len(n)
        res = sign + (str(thousands_sep[1]).join(
            [n[0:m % 3]] + [n[i:i + 3] for i in range(
                m % 3, m, 3)])).lstrip(str(thousands_sep[1])) + dec
        return res

    def print_order(self):
        """Print order.

        The method used to context updated and another wizard of action call
        @self: Record set
        @return: Return action of wizard in dictionary
        -------------------------------------------------------------------------
        """
        context = dict(self.env.context) if self.env.context else {}
        start_date = self.date_from
        end_date = self.date_to
        emp_ids = self.employee_ids
        if not emp_ids.ids:
            raise ValidationError(_("Please select employee"))
        salary_rule_ids = self.salary_rule_ids
        if not salary_rule_ids.ids:
            raise ValidationError(_("Please select salary rule"))
        if start_date >= end_date:
            raise ValidationError(
                _("You must be enter start date less than end date !"))
        context.update({'employee_ids': emp_ids,
                        'salary_rules_id': salary_rule_ids,
                        'date_from': start_date,
                        'date_to': end_date})
        workbook = xlwt.Workbook()
        worksheet = workbook.add_sheet('Sheet 1')
        font = xlwt.Font()
        font.bold = True
        header = xlwt.easyxf('font: bold 1, height 280')
        res_user = self.env["res.users"].browse(context.get('uid'))
        salary_rule = [rule.name for rule in salary_rule_ids]
        start_date_formate = start_date.strftime('%d/%m/%Y')
        end_date_formate = end_date.strftime('%d/%m/%Y')
        date_period = start_date_formate + ' To ' + end_date_formate
        alignment = xlwt.Alignment()  # Create Alignment
        alignment.horz = xlwt.Alignment.HORZ_RIGHT
        style = xlwt.easyxf('align: wrap yes')
        style.num_format_str = '0.00'
        worksheet.col(0).width = 5000
        worksheet.col(1).width = 5000
        worksheet.col(4).width = 4000
        worksheet.row(0).height = 500
        worksheet.row(1).height = 500
        worksheet.row(2).height = 500
        borders = xlwt.Borders()
        borders.bottom = xlwt.Borders.MEDIUM
        border_style = xlwt.XFStyle()  # Create Style
        border_style.borders = borders
        border_style = xlwt.easyxf('font: bold 1; align: wrap on;')

        worksheet.write(0, 0, "Company Name :- " +
                        res_user.company_id.name, header)
        worksheet.write(1, 0, "Payroll Generic Summary Report :", header)
        worksheet.write(1, 2, "", header)
        worksheet.write(2, 0, "Period :", header)
        worksheet.write(2, 1, date_period, header)

        row = 4
        col = 5
        worksheet.write(4, 0, "Employee No", border_style)
        worksheet.write(4, 1, "Employee Name", border_style)
        worksheet.write(4, 2, "Wage", border_style)
        worksheet.write(4, 3, "Wage To Pay", border_style)
        worksheet.write(4, 4, "Rate Per Hour", border_style)
        for rule in salary_rule:
            worksheet.write(row, col, rule, border_style)
            col += 1
        row += 2
        result = {}
        total = {}
        employee_ids = emp_ids
        res_lang_id = self.env['res.lang'].search(
            [('code', '=', res_user.lang)], limit=1)
        thousands_sep = ","
        if res_lang_id:
            thousands_sep = res_lang_id._data_get()
        else:
            raise ValidationError(
                _('You must be select the language for login user!'))

        tot_categ_cont_wage = tot_categ_cont_wage_to_pay = \
            tot_categ_cont_rate_per_hour = 0.0
        payslip_ids = self.env['hr.payslip'].search_count([
            ('employee_id', 'in', emp_ids.ids),
            ('date_from', '>=', start_date),
            ('date_from', '<=', end_date),
            ('state', 'in', ['draft', 'done', 'verify'])])
        if not payslip_ids:
            raise ValidationError(_(
                'There is no payslip details between '
                'selected date %s and %s') % (
                start_date.strftime(get_lang(self.env).date_format),
                end_date.strftime(get_lang(self.env).date_format)))
        for employee in employee_ids:
            payslip_ids = self.env['hr.payslip'].search([
                ('employee_id', '=', employee.id),
                ('date_from', '>=', start_date),
                ('date_from', '<=', end_date),
                ('state', 'in',
                 ['draft', 'done',
                  'verify'])])
            if not payslip_ids:
                continue
            contract_wage = 0.0
            contract_wage_to_pay = 0.0
            contract_rate_per_hour = 0.0
            new_payslip_result = {}
            for rule in salary_rule:
                new_payslip_result.update({rule: 0.00})
            for payslip in payslip_ids:
                contract_rate_per_hour += payslip and payslip.contract_id \
                    and payslip.contract_id.rate_per_hour or 0.0
                for rule in payslip.details_by_salary_rule_category:
                    if rule.code == 'BASIC':
                        contract_wage += payslip and payslip.contract_id and \
                            payslip.contract_id.wage or 0.0
                        contract_wage_to_pay += payslip and \
                            payslip.contract_id and \
                            payslip.contract_id.wage_to_pay or 0.0
                    for set_rule in salary_rule:
                        rule_total = 0.00
                        if rule.name == set_rule:
                            rule_total += rule.total
                        res = {set_rule: new_payslip_result.get(
                            set_rule, 0) + float(rule_total), 'conn': 100}
                        new_payslip_result.update(res)
            payslip_result = {'department': employee.department_id.id or
                              "Undefined",
                              'ename': employee.name,
                              'eid': employee.user_id.login,
                              'wage': contract_wage,
                              'wage_to_pay': contract_wage_to_pay,
                              'rate_per_hour': contract_rate_per_hour}
            value_found = True
            for key, val in new_payslip_result.items():
                if val:
                    value_found = False
            if value_found:
                continue
            payslip_result.update(new_payslip_result)
            if payslip.employee_id.department_id:
                if payslip.employee_id.department_id.id in result:
                    result.get(payslip.employee_id.department_id.id).append(
                        payslip_result)
                else:
                    result.update(
                        {payslip.employee_id.department_id.id:
                         [payslip_result]})
            else:
                if 'Undefined' in result:
                    result.get('Undefined').append(payslip_result)
                else:
                    result.update({'Undefined': [payslip_result]})
        final_total = {'name': "Grand Total"}
        for rule in salary_rule:
            final_total.update({rule: 0.0})
        for key, val in result.items():
            categ_cont_wage = categ_cont_wage_to_pay = \
                categ_cont_rate_per_hour = 0.0
            style = xlwt.easyxf('font: bold 0')
            if key == 'Undefined':
                category_name = 'Undefined'
                category_id = 0
            else:
                hr_depart_brw = self.env['hr.department'].browse(key)
                category_name = hr_depart_brw.name
                category_id = hr_depart_brw.id
            total = {'categ_id': category_id, 'name': category_name}
            for rule in salary_rule:
                total.update({rule: 0.0})
            for line in val:
                for field in line:
                    if field in total:
                        total.update(
                            {field: total.get(field) + line.get(field)})
            style1 = xlwt.easyxf()
            style1.num_format_str = '0.00'
            if total.get("name") == "Undefined":
                for payslip_result in result[total.get("name")]:
                    categ_cont_wage += payslip_result.get("wage")
                    tot_categ_cont_wage += payslip_result.get("wage")
                    categ_cont_wage_to_pay += payslip_result.get("wage_to_pay")
                    tot_categ_cont_wage_to_pay += payslip_result.get(
                        "wage_to_pay")
                    categ_cont_rate_per_hour += payslip_result.get(
                        "rate_per_hour")
                    tot_categ_cont_rate_per_hour += payslip_result.get(
                        "rate_per_hour")
                    contract_wage = str(abs(payslip_result.get("wage")))
                    contract_wage = self.intcomma(
                        float(contract_wage), thousands_sep)
                    contract_wage = contract_wage.ljust(
                        len(contract_wage.split('.')[0]) + 3, '0')
                    contract_wage_to_pay = str(
                        abs(payslip_result.get("wage_to_pay")))
                    contract_wage_to_pay = self.intcomma(
                        float(contract_wage_to_pay), thousands_sep)
                    contract_wage_to_pay = contract_wage_to_pay.ljust(
                        len(contract_wage_to_pay.split('.')[0]) + 3, '0')
                    contract_rate_per_hour = str(
                        abs(payslip_result.get("rate_per_hour")))
                    contract_rate_per_hour = self.intcomma(
                        float(contract_rate_per_hour), thousands_sep)
                    contract_rate_per_hour = contract_rate_per_hour.ljust(
                        len(contract_rate_per_hour.split('.')[0]) + 3, '0')
                    worksheet.write(row, 0, payslip_result.get("eid"))
                    worksheet.write(row, 1, payslip_result.get("ename"))
                    style.alignment = alignment
                    worksheet.write(row, 2, contract_wage, style)
                    worksheet.write(row, 3, contract_wage_to_pay, style)
                    worksheet.write(row, 4, contract_rate_per_hour, style)
                    col = 5
                    for rule in salary_rule:
                        split_total_rule = str(abs(payslip_result.get(rule)))
                        split_total_rule = self.intcomma(
                            float(split_total_rule), thousands_sep)
                        split_total_rule = split_total_rule.ljust(
                            len(split_total_rule.split('.')[0]) + 3, '0')
                        style.alignment = alignment
                        worksheet.write(row, col, split_total_rule, style)
                        col += 1
                    row += 1
            else:
                for payslip_result in result[total.get("categ_id")]:
                    categ_cont_wage += payslip_result.get("wage")
                    tot_categ_cont_wage += payslip_result.get("wage")
                    categ_cont_wage_to_pay += payslip_result.get("wage_to_pay")
                    tot_categ_cont_wage_to_pay += payslip_result.get(
                        "wage_to_pay")
                    categ_cont_rate_per_hour += payslip_result.get(
                        "rate_per_hour")
                    tot_categ_cont_rate_per_hour += payslip_result.get(
                        "rate_per_hour")
                    contract_wage = str(abs(payslip_result.get("wage")))
                    contract_wage = self.intcomma(
                        float(contract_wage), thousands_sep)
                    contract_wage = contract_wage.ljust(
                        len(contract_wage.split('.')[0]) + 3, '0')
                    contract_wage_to_pay = str(
                        abs(payslip_result.get("wage_to_pay")))
                    contract_wage_to_pay = self.intcomma(
                        float(contract_wage_to_pay), thousands_sep)
                    contract_wage_to_pay = contract_wage_to_pay.ljust(
                        len(contract_wage_to_pay.split('.')[0]) + 3, '0')
                    contract_rate_per_hour = str(
                        abs(payslip_result.get("rate_per_hour")))
                    contract_rate_per_hour = self.intcomma(
                        float(contract_rate_per_hour), thousands_sep)
                    contract_rate_per_hour = contract_rate_per_hour.ljust(
                        len(contract_rate_per_hour.split('.')[0]) + 3, '0')
                    worksheet.write(row, 0, payslip_result.get("eid"))
                    worksheet.write(row, 1, payslip_result.get("ename"))
                    style.alignment = alignment
                    worksheet.write(row, 2, contract_wage, style)
                    worksheet.write(row, 3, contract_wage_to_pay, style)
                    worksheet.write(row, 4, contract_rate_per_hour, style)
                    col = 5
                    for rule in salary_rule:
                        split_total_rule = str(abs(payslip_result.get(rule)))
                        split_total_rule = self.intcomma(
                            float(split_total_rule), thousands_sep)
                        split_total_rule = split_total_rule.ljust(
                            len(split_total_rule.split('.')[0]) + 3, '0')
                        style.alignment = alignment
                        worksheet.write(row, col, split_total_rule, style)
                        col += 1
                    row += 1

            borders = xlwt.Borders()
            borders.top = xlwt.Borders.MEDIUM
            borders.bottom = xlwt.Borders.MEDIUM
            border_top = xlwt.XFStyle()  # Create Style
            border_top.borders = borders
            style = xlwt.easyxf('font: bold 1')
            style.num_format_str = '0.00'
            worksheet.write(row, 0, str("Total " + total["name"]), style)
            worksheet.write(row, 1, "", style)
            col = 5
            categ_cont_wage = str(abs(categ_cont_wage))
            categ_cont_wage = self.intcomma(
                float(categ_cont_wage), thousands_sep)
            categ_cont_wage = categ_cont_wage.ljust(
                len(categ_cont_wage.split('.')[0]) + 3, '0')
            categ_cont_wage_to_pay = str(abs(categ_cont_wage_to_pay))
            categ_cont_wage_to_pay = self.intcomma(
                float(categ_cont_wage_to_pay), thousands_sep)
            categ_cont_wage_to_pay = categ_cont_wage_to_pay.ljust(
                len(categ_cont_wage_to_pay.split('.')[0]) + 3, '0')
            categ_cont_rate_per_hour = str(abs(categ_cont_rate_per_hour))
            categ_cont_rate_per_hour = self.intcomma(
                float(categ_cont_rate_per_hour), thousands_sep)
            categ_cont_rate_per_hour = categ_cont_rate_per_hour.ljust(
                len(categ_cont_rate_per_hour.split('.')[0]) + 3, '0')
            style.alignment = alignment
            worksheet.write(row, 2, categ_cont_wage, style)
            worksheet.write(row, 3, categ_cont_wage_to_pay, style)
            worksheet.write(row, 4, categ_cont_rate_per_hour, style)
            for rule in salary_rule:
                rule_total = 0.0
                split_total_rule = str(abs(total[rule]))
                split_total_rule = self.intcomma(
                    float(split_total_rule), thousands_sep)
                split_total_rule = split_total_rule.ljust(
                    len(split_total_rule.split('.')[0]) + 3, '0')
                style.alignment = alignment
                worksheet.write(row, col, split_total_rule, style)
                rule_total = final_total[rule] + total[rule]
                final_total.update({rule: rule_total})
                col += 1
            row += 2
        borders = xlwt.Borders()
        borders.top = xlwt.Borders.MEDIUM
        border_total = xlwt.XFStyle()  # Create Style
        border_total.borders = borders
        row += 1
        worksheet.write(row, 0, final_total["name"], style)
        worksheet.write(row, 1, "", border_total)
        col = 5
        tot_categ_cont_wage = str(abs(tot_categ_cont_wage))
        tot_categ_cont_wage = self.intcomma(
            float(tot_categ_cont_wage), thousands_sep)
        tot_categ_cont_wage = tot_categ_cont_wage.ljust(
            len(tot_categ_cont_wage.split('.')[0]) + 3, '0')
        tot_categ_cont_wage_to_pay = str(abs(tot_categ_cont_wage_to_pay))
        tot_categ_cont_wage_to_pay = self.intcomma(
            float(tot_categ_cont_wage_to_pay), thousands_sep)
        tot_categ_cont_wage_to_pay = tot_categ_cont_wage_to_pay.ljust(
            len(tot_categ_cont_wage_to_pay.split('.')[0]) + 3, '0')
        tot_categ_cont_rate_per_hour = str(abs(tot_categ_cont_rate_per_hour))
        tot_categ_cont_rate_per_hour = self.intcomma(
            float(tot_categ_cont_rate_per_hour), thousands_sep)
        tot_categ_cont_rate_per_hour = tot_categ_cont_rate_per_hour.ljust(
            len(tot_categ_cont_rate_per_hour.split('.')[0]) + 3, '0')
        style.alignment = alignment
        worksheet.write(row, 2, tot_categ_cont_wage, style)
        worksheet.write(row, 3, tot_categ_cont_wage_to_pay, style)
        worksheet.write(row, 4, tot_categ_cont_rate_per_hour, style)
        for rule in salary_rule:
            split_total_rule = str(abs(final_total[rule]))
            split_total_rule = self.intcomma(
                float(split_total_rule), thousands_sep)
            split_total_rule = split_total_rule.ljust(
                len(split_total_rule.split('.')[0]) + 3, '0')
            style.alignment = alignment
            worksheet.write(row, col, split_total_rule, style)
            col += 1
        row += 1

        fp = io.BytesIO()
        workbook.save(fp)
        fp.seek(0)
        data = fp.read()
        fp.close()
        res = base64.b64encode(data)
        module_rec = self.env['payroll.excel.export.summary'].create(
            {'name': 'Generic Summary.xls', 'file': res})
        return {
            'name': _('Generic Summary Report'),
            'res_id': module_rec.id,
            "view_mode": 'form',
            'res_model': 'payroll.excel.export.summary',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': context,
        }
