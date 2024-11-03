from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api


class HrSalaryRuleExt(models.Model):
    _inherit = 'hr.salary.rule'
    _description = 'Inherited to categorized Ordinary and Additional Wages \
                    at salary rule level.'

    is_cpf = fields.Selection([('no_cpf', 'No CPF'),
                               ('ow', 'OW'),
                               ('aw', 'AW')], 'Is CPF')


class HrPayslipExt(models.Model):
    _inherit = 'hr.payslip'
    _description = 'Inherited for Ordinary and Additional Wages Integration \
                    with Pay slip Computation.'

    def _get_ow_aw(self):
        """
            This method compute current payslip ow and aw
            and previous payslip total aw and ow
        """
        for rec in self:
            rec.current_ow = 0
            rec.current_aw = 0
            rec.current_aw_ow = current_aw_ow = 0
            rec.all_aw_ow = all_aw_ow = 0
            rec.all_aw_ow_limit = False
            today = datetime.today().date()
            current_year = today.year
            current_year_start_date = str(current_year) + '-01-01' or ''
            date_from = rec.date_from
            previous_month_last_date = date_from - relativedelta(days=1)
            payslip_ids = rec.search([
                ('employee_id', '=', rec.employee_id.id),
                ('contract_id', '=', rec.contract_id.id),
                ('date_from', '>=', current_year_start_date),
                ('date_to', '<=', previous_month_last_date)])
            ow_ids = rec.line_ids.filtered(
                lambda x: x.salary_rule_id.is_cpf == 'ow')
            aw_ids = rec.line_ids.filtered(
                lambda x: x.salary_rule_id.is_cpf == 'aw')
            for owline in ow_ids:
                rec.current_ow += owline.amount
            for awline in aw_ids:
                rec.current_aw += awline.amount
            if rec.current_ow > 6000:
                rec.current_ow = 6000
            current_aw_ow = rec.current_ow + rec.current_aw
            rec.current_aw_ow = current_aw_ow
            for payslip in payslip_ids:
                all_aw_ow += payslip.current_aw_ow
                rec.all_aw_ow = all_aw_ow
            if rec.all_aw_ow > 102000:
                rec.all_aw_ow_limit = True

    current_ow = fields.Float(string="Current Payslip OW", compute='_get_ow_aw')
    current_aw = fields.Float(string="Current Payslip AW", compute='_get_ow_aw')
    current_aw_ow = fields.Float("Current AW OW", compute='_get_ow_aw')
    all_aw_ow = fields.Float("All AW OW", compute='_get_ow_aw')
    all_aw_ow_limit = fields.Boolean('All Aw Ow Limit', compute='_get_ow_aw')

    @api.model
    def _get_payslip_lines(self, contract_ids, payslip_id):
        def _sum_salary_rule_category(localdict, category, amount):
            if category.parent_id:
                localdict = _sum_salary_rule_category(localdict, category.parent_id, amount)
            localdict['categories'].dict[category.code] = category.code in localdict['categories'].dict and localdict['categories'].dict[category.code] + amount or amount
            return localdict

        class BrowsableObject(object):
            def __init__(self, employee_id, dict, env):
                self.employee_id = employee_id
                self.dict = dict
                self.env = env

            def __getattr__(self, attr):
                return attr in self.dict and self.dict.__getitem__(attr) or 0.0

        class InputLine(BrowsableObject):
            """a class that will be used into the python code, mainly for usability purposes"""
            def sum(self, code, from_date, to_date=None):
                if to_date is None:
                    to_date = fields.Date.today()
                self.env.cr.execute("""
                    SELECT sum(amount) as sum
                    FROM hr_payslip as hp, hr_payslip_input as pi
                    WHERE hp.employee_id = %s AND hp.state = 'done'
                    AND hp.date_from >= %s AND hp.date_to <= %s AND hp.id = pi.payslip_id AND pi.code = %s""",
                    (self.employee_id, from_date, to_date, code))
                return self.env.cr.fetchone()[0] or 0.0

        class WorkedDays(BrowsableObject):
            """a class that will be used into the python code, mainly for usability purposes"""
            def _sum(self, code, from_date, to_date=None):
                if to_date is None:
                    to_date = fields.Date.today()
                self.env.cr.execute("""
                    SELECT sum(number_of_days) as number_of_days, sum(number_of_hours) as number_of_hours
                    FROM hr_payslip as hp, hr_payslip_worked_days as pi
                    WHERE hp.employee_id = %s AND hp.state = 'done'
                    AND hp.date_from >= %s AND hp.date_to <= %s AND hp.id = pi.payslip_id AND pi.code = %s""",
                    (self.employee_id, from_date, to_date, code))
                return self.env.cr.fetchone()

            def sum(self, code, from_date, to_date=None):
                res = self._sum(code, from_date, to_date)
                return res and res[0] or 0.0

            def sum_hours(self, code, from_date, to_date=None):
                res = self._sum(code, from_date, to_date)
                return res and res[1] or 0.0

        class Payslips(BrowsableObject):
            """a class that will be used into the python code, mainly for usability purposes"""

            def sum(self, code, from_date, to_date=None):
                if to_date is None:
                    to_date = fields.Date.today()
                self.env.cr.execute("""SELECT sum(case when hp.credit_note = False then (pl.total) else (-pl.total) end)
                            FROM hr_payslip as hp, hr_payslip_line as pl
                            WHERE hp.employee_id = %s AND hp.state = 'done'
                            AND hp.date_from >= %s AND hp.date_to <= %s AND hp.id = pl.slip_id AND pl.code = %s""",
                            (self.employee_id, from_date, to_date, code))
                res = self.env.cr.fetchone()
                return res and res[0] or 0.0

        #we keep a dict with the result because a value can be overwritten by another rule with the same code
        result_dict = {}
        rules_dict = {}
        worked_days_dict = {}
        inputs_dict = {}
        blacklist = []
        payslip = self.env['hr.payslip'].browse(payslip_id)
        obj_rule = self.env['hr.salary.rule']
        for worked_days_line in payslip.worked_days_line_ids:
            worked_days_dict[worked_days_line.code] = worked_days_line
        for input_line in payslip.input_line_ids:
            inputs_dict[input_line.code] = input_line

        categories = BrowsableObject(payslip.employee_id.id, {}, self.env)
        inputs = InputLine(payslip.employee_id.id, inputs_dict, self.env)
        worked_days = WorkedDays(payslip.employee_id.id,
                                 worked_days_dict, self.env)
        payslips = Payslips(payslip.employee_id.id, payslip, self.env)
        rules = BrowsableObject(payslip.employee_id.id, rules_dict, self.env)

        ow_brw = obj_rule.search([('is_cpf', '=', 'ow')])
        aw_brw = obj_rule.search([('is_cpf', '=', 'aw')])
        ow_ids = ow_brw.ids
        aw_ids = aw_brw.ids
        ow_total = aw_total = 0.0

        baselocaldict = {'categories': categories, 'rules': rules,
                         'payslip': payslips, 'worked_days': worked_days,
                         'inputs': inputs}
        # get the ids of the structures on the contracts and
        # their parent id as well
        contracts = self.env['hr.contract'].browse(contract_ids)
        if len(contracts) == 1 and payslip.struct_id:
            structure_ids = list(set(
                payslip.struct_id._get_parent_structure().ids))
        else:
            structure_ids = contracts.get_all_structures()
        # get the rules of the structure and thier children
        rule_ids = self.env['hr.payroll.structure'
                            ].browse(structure_ids).get_all_rules()
        # run the rules by sequence
        sorted_rule_ids = [id for id, sequence in sorted(
            rule_ids, key=lambda x:x[1])]
        sorted_rules = self.env['hr.salary.rule'].browse(sorted_rule_ids)

        for contract in contracts:
            employee = contract.employee_id
            localdict = dict(baselocaldict, employee=employee,
                             contract=contract)
            for rule in sorted_rules:
                key = rule.code + '-' + str(contract.id)
                localdict['result'] = None
                localdict['result_qty'] = 1.0
                localdict['result_rate'] = 100
                localdict['ow_total'] = ow_total
                localdict['aw_total'] = aw_total
                # check if the rule can be applied
                if rule._satisfy_condition(localdict) and rule.id not in blacklist:
                    # compute the amount of the rule
                    amount, qty, rate = rule._compute_rule(localdict)
                    if rule.id in ow_ids:
                        ow_total += float(qty) * amount * rate / 100
                        ow_ids.remove(rule.id)
                    elif rule.id in aw_ids:
                        aw_total += float(qty) * amount * rate / 100
                        aw_ids.remove(rule.id)

                    # check if there is already a rule computed with that code
                    previous_amount = rule.code in localdict and localdict[rule.code] or 0.0
                    # set/overwrite the amount computed for this rule in the localdict
                    tot_rule = amount * qty * rate / 100.0
                    localdict[rule.code] = tot_rule
                    rules_dict[rule.code] = rule
                    # sum the amount for its salary category
                    localdict = _sum_salary_rule_category(localdict, rule.category_id, tot_rule - previous_amount)
                    # create/overwrite the rule in the temporary results
                    result_dict[key] = {
                        'salary_rule_id': rule.id,
                        'contract_id': contract.id,
                        'name': rule.name,
                        'code': rule.code,
                        'category_id': rule.category_id.id,
                        'sequence': rule.sequence,
                        'appears_on_payslip': rule.appears_on_payslip,
                        'condition_select': rule.condition_select,
                        'condition_python': rule.condition_python,
                        'condition_range': rule.condition_range,
                        'condition_range_min': rule.condition_range_min,
                        'condition_range_max': rule.condition_range_max,
                        'amount_select': rule.amount_select,
                        'amount_fix': rule.amount_fix,
                        'amount_python_compute': rule.amount_python_compute,
                        'amount_percentage': rule.amount_percentage,
                        'amount_percentage_base': rule.amount_percentage_base,
                        'register_id': rule.register_id.id,
                        'amount': amount,
                        'employee_id': contract.employee_id.id,
                        'quantity': qty,
                        'rate': rate,
                    }
                else:
                    # blacklist this rule and its children
                    blacklist += [id for id, seq in rule._recursive_search_of_rules()]
        return list(result_dict.values())


#     @api.model
#     def _get_payslip_lines(self, contract_ids, payslip_id):
#         def _sum_salary_rule_category(localdict, category, amount):
#             if category.parent_id:
#                 localdict = _sum_salary_rule_category(localdict,
#                                                       category.parent_id,
#                                                       amount)
#             localdict['categories'].dict[category.code] = category.code in \
#                 localdict['categories'].dict and \
#                 localdict['categories'].dict[category.code] + amount or amount
#             return localdict
# 
#         class BrowsableObject(object):
#             def __init__(self, employee_id, dict):
#                 self.employee_id = employee_id
#                 self.dict = dict
# 
#             def __getattr__(self, attr):
#                 return attr in self.dict and self.dict.__getitem__(attr) or 0.0
# 
#         class InputLine(BrowsableObject):
#             """a class that will be used into the python code, mainly for \
#             usability purposes"""
#             def sum(self, code, from_date, to_date=None):
#                 if to_date is None:
#                     to_date = fields.Date.today()
#                 self.env.cr.execute("""
#                     SELECT sum(amount) as sum
#                     FROM hr_payslip as hp, hr_payslip_input as pi
#                     WHERE hp.employee_id = %s AND hp.state = 'done'
#                     AND hp.date_from >= %s AND hp.date_to <= %s AND hp.id = \
#                     pi.payslip_id AND pi.code = %s""", (self.employee_id,
#                                                         from_date, to_date,
#                                                         code))
#                 return self.env.cr.fetchone()[0] or 0.0
# 
#         class WorkedDays(BrowsableObject):
#             """a class that will be used into the python code, mainly for \
#             usability purposes"""
#             def _sum(self, code, from_date, to_date=None):
#                 if to_date is None:
#                     to_date = fields.Date.today()
#                 self.env.cr.execute("""
#                     SELECT sum(number_of_days) as number_of_days, \
#                     sum(number_of_hours) as number_of_hours
#                     FROM hr_payslip as hp, hr_payslip_worked_days as pi
#                     WHERE hp.employee_id = %s AND hp.state = 'done'
#                     AND hp.date_from >= %s AND hp.date_to <= %s AND hp.id = \
#                     pi.payslip_id AND pi.code = %s""", (self.employee_id,
#                                                         from_date, to_date,
#                                                         code))
#                 return self.env.cr.fetchone()
# 
#             def sum(self, code, from_date, to_date=None):
#                 res = self._sum(code, from_date, to_date)
#                 return res and res[0] or 0.0
# 
#             def sum_hours(self, code, from_date, to_date=None):
#                 res = self._sum(code, from_date, to_date)
#                 return res and res[1] or 0.0
# 
#         class Payslips(BrowsableObject):
#             """a class that will be used into the python code, mainly for \
#             usability purposes"""
# 
#             def sum(self, code, from_date, to_date=None):
#                 if to_date is None:
#                     to_date = fields.Date.today()
#                 self.env.cr.execute("""SELECT sum(case when hp.credit_note = \
#                             False then (pl.total) else (-pl.total) end)
#                             FROM hr_payslip as hp, hr_payslip_line as pl
#                             WHERE hp.employee_id = %s AND hp.state = 'done'
#                             AND hp.date_from >= %s AND hp.date_to <= %s AND \
#                             hp.id = pl.slip_id AND pl.code = %s""", (
#                                 self.employee_id, from_date, to_date, code))
#                 res = self.env.cr.fetchone()
#                 return res and res[0] or 0.0
# 
#         # we keep a dict with the result because a value can be overwritten by
#         # another rule with the same code
#         result_dict = {}
#         rules = {}
#         categories_dict = {}
#         blacklist = []
#         payslip_obj = self.env['hr.payslip']
#         obj_rule = self.env['hr.salary.rule']
#         payslip = payslip_obj.browse(payslip_id)
#         worked_days = {}
#         for worked_days_line in payslip.worked_days_line_ids:
#             worked_days[worked_days_line.code] = worked_days_line
#         inputs = {}
#         for input_line in payslip.input_line_ids:
#             inputs[input_line.code] = input_line
# 
#         categories_obj = BrowsableObject(payslip.employee_id.id,
#                                          categories_dict)
#         input_obj = InputLine(payslip.employee_id.id, inputs)
#         worked_days_obj = WorkedDays(payslip.employee_id.id, worked_days)
#         payslip_obj = Payslips(payslip.employee_id.id, payslip)
#         rules_obj = BrowsableObject(payslip.employee_id.id, rules)
#         # get ordinary wages and additional wages rules
#         ow_brw = obj_rule.search([('is_cpf', '=', 'ow')])
#         aw_brw = obj_rule.search([('is_cpf', '=', 'aw')])
#         ow_ids = ow_brw.ids
#         aw_ids = aw_brw.ids
#         ow_total = aw_total = 0.0
#         baselocaldict = {'payslip_brw': payslip, 'categories': categories_obj,
#                          'rules': rules_obj, 'payslip': payslip_obj,
#                          'worked_days': worked_days_obj, 'inputs': input_obj}
#         # get the ids of the structures on the contracts and their parent id
#         # as well
#         contracts = self.env['hr.contract'].browse(contract_ids)
#         structure_ids = contracts.get_all_structures()
#         # get the rules of the structure and thier children
#         rule_ids = self.env['hr.payroll.structure'].browse(
#                                                 structure_ids).get_all_rules()
#         # run the rules by sequence
#         sorted_rule_ids = [id for id, sequence in sorted(rule_ids,
#                                                          key=lambda x:x[1])]
#         for contract in contracts:
#             employee = contract.employee_id
#             localdict = dict(baselocaldict, employee=employee,
#                              contract=contract)
#             for rule in self.env['hr.salary.rule'].browse(sorted_rule_ids):
#                 key = rule.code + '-' + str(contract.id)
#                 localdict['result'] = None
#                 localdict['result_qty'] = 1.0
#                 localdict['result_rate'] = 100
#                 localdict['ow_total'] = ow_total
#                 localdict['aw_total'] = aw_total
#                 # check if the rule can be applied
#                 if rule._satisfy_condition(localdict) and rule.id not \
#                         in blacklist:
#                     # compute the amount of the rule
#                     amount, qty, rate = rule._compute_rule(localdict)
#                     if rule.id in ow_ids:
#                         ow_total += float(qty) * amount * rate / 100
#                         ow_ids.remove(rule.id)
#                     elif rule.id in aw_ids:
#                         aw_total += float(qty) * amount * rate / 100
#                         aw_ids.remove(rule.id)
#                     # check if there is already a rule computed with that code
#                     previous_amount = rule.code in localdict and \
#                         localdict[rule.code] or 0.0
#                     # set/overwrite the amount computed for this rule in
#                     # the localdict
#                     tot_rule = amount * qty * rate / 100.0
#                     localdict[rule.code] = tot_rule
#                     rules[rule.code] = rule
#                     # sum the amount for its salary category
#                     localdict = _sum_salary_rule_category(localdict,
#                                                           rule.category_id,
#                                                           (tot_rule -
#                                                            previous_amount))
#                     # create/overwrite the rule in the temporary results
#                     result_dict[key] = {
#                         'salary_rule_id': rule.id,
#                         'contract_id': contract.id,
#                         'name': rule.name,
#                         'code': rule.code,
#                         'category_id': rule.category_id.id,
#                         'sequence': rule.sequence,
#                         'appears_on_payslip': rule.appears_on_payslip,
#                         'condition_select': rule.condition_select,
#                         'condition_python': rule.condition_python,
#                         'condition_range': rule.condition_range,
#                         'condition_range_min': rule.condition_range_min,
#                         'condition_range_max': rule.condition_range_max,
#                         'amount_select': rule.amount_select,
#                         'amount_fix': rule.amount_fix,
#                         'amount_python_compute': rule.amount_python_compute,
#                         'amount_percentage': rule.amount_percentage,
#                         'amount_percentage_base': rule.amount_percentage_base,
#                         'register_id': rule.register_id.id,
#                         'amount': amount,
#                         'employee_id': contract.employee_id.id,
#                         'quantity': qty,
#                         'rate': rate,
#                     }
#                 else:
#                     blacklist += [id for id, seq in
#                                   rule._recursive_search_of_rules()]
# 
#         result = [value for code, value in result_dict.items()]
#         return result