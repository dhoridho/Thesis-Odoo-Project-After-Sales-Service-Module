import time

from odoo import api, models


class PayslipReport(models.AbstractModel):
    _name = 'report.sg_hr_report.report_payslip_sample'
    _description = "Payslip Sample Report"

    @api.model
    def get_category(self, curr_id, code):
        """Get Category."""
        res = {}
        tot_a = 0.0
        payslip_line_obj = self.env['hr.payslip.line']
        basic_pay = overtime_pay = 0.0
        pay_slip_line_ids = payslip_line_obj.search([('slip_id', '=',
                                                      curr_id.id)])
        for rec in pay_slip_line_ids:
            if rec.code == 'SC100':
                basic_pay = rec.total
            if rec.code == 'BASIC':
                basic_pay = rec.total
            if rec.code == 'SC102':
                overtime_pay = rec.total
        res.update({'basic_pay': basic_pay,
                    'overtime_hour': curr_id.overtime_hours,
                    'overtime_pay': overtime_pay, })
        tot_a = basic_pay
        return res

    @api.model
    def category_total_employr(self, curr_ids, CAT_CPF_EMPLOYER,
                               CATCPFAGENCYSERVICESER):
        """Category total employee."""
        total = 0.0
        if CAT_CPF_EMPLOYER:
            total += self.category_line(curr_ids, CAT_CPF_EMPLOYER, None,
                                        'Total')
        if CATCPFAGENCYSERVICESER:
            total += self.category_line(curr_ids, CATCPFAGENCYSERVICESER, None,
                                        'Total')
        return total

    @api.model
    def category_total(self, curr_ids, DED, CAT_CPF_EMPLOYEE,
                       CATCPFAGENCYSERVICESEE, DED_INCL_CPF):
        """Category Total."""
        total = 0.0
        if DED:
            total += self.category_line(curr_ids, DED, None, 'Total')
        if CAT_CPF_EMPLOYEE:
            total += self.category_line(curr_ids, CAT_CPF_EMPLOYEE, None,
                                        'Total')
        if CATCPFAGENCYSERVICESEE:
            total += self.category_line(curr_ids, CATCPFAGENCYSERVICESEE, None,
                                        'Total')
        if DED_INCL_CPF:
            total += self.category_line(curr_ids, DED_INCL_CPF, None, 'Total')
        return total

    @api.model
    def category_line(self, curr_ids, code, overtime_code, code_tittle):
        """Category line."""
        res = []
        line_dict = {}
        total_allowances = 0.0
        rule_categ_obj = self.env['hr.salary.rule.category']
        rule_obj = self.env['hr.salary.rule']
        payslip_line_obj = self.env['hr.payslip.line']
        hr_sal_rule_categ_ids = rule_categ_obj.search(
            [('code', '=', code)])
        hr_sal_rule_ids = rule_obj.search([
            ('category_id', 'in', hr_sal_rule_categ_ids.ids)])
        if hr_sal_rule_ids:
            sal_rule_code = [sal_rule_rec.code for sal_rule_rec in
                             hr_sal_rule_ids
                             if sal_rule_rec.code != overtime_code and
                             sal_rule_rec.code]
            sal_rule_code_list = [code_rec.encode('UTF8') for code_rec in
                                  sal_rule_code]
            if sal_rule_code_list:
                payslip_line_rec = payslip_line_obj.search([
                    ('slip_id', '=', curr_ids.id),
                    ('code', 'in', sal_rule_code_list)])
                for line_rec in payslip_line_rec:
                    line_dict = ({'name': line_rec.name,
                                  'total': line_rec.total,
                                  'code': line_rec.code})
                    res.append(line_dict)
                    total_allowances += line_rec.total
        if code_tittle == 'Total':
            rec = self.total_allowances(total_allowances)
            return rec
        return res

    @api.model
    def total_allowances(self, total_amount):
        """Get total allowances."""
        return total_amount

    @api.model
    def blank_line(self, line_key):
        """Blank line."""
        line_list = []
        if line_key == 'deduction_line':
            for line in range(1, 3):
                line_list.append(line)
        return line_list

    @api.model
    def blank_fix_line(self, len_fetch_line):
        """Black fix line."""
        fix_line_list = []
        remain_line = 4 - len_fetch_line
        for line_rec in range(1, remain_line + 1):
            fix_line_list.append(line_rec)
        return fix_line_list

    @api.model
    def additional_blank_fix_line(self, add_line, len_fetch_line):
        """Additional blank line."""
        fix_line_list = []
        remain_line = len_fetch_line - 2 - add_line - 3
        for line_rec in range(1, remain_line):
            fix_line_list.append(line_rec)
        return fix_line_list

    def get_worked_hour(self, data):
        """Get worked hour."""
        amt = 0.0
        if data.input_line_ids:
            for line in data.input_line_ids:
                if line.code == "SC100I":
                    amt = line.amount
        return amt

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['hr.payslip'].browse(docids)
        return {
            'doc_ids': self.ids,
            'doc_model': 'hr.payslip',
            'docs': docs,
            'time': time,
            'get_category': self.get_category,
            'category_line': self.category_line,
            'category_total': self.category_total,
            'category_total_employr': self.category_total_employr,
            'total_allowances': self.total_allowances,
            'blank_line': self.blank_line,
            'blank_fix_line': self.blank_fix_line,
            'get_worked_hour': self.get_worked_hour,
            'additional_blank_fix_line': self.additional_blank_fix_line}
