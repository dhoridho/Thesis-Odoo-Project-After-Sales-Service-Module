# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.safe_eval import safe_eval

class HrSalaryRuleCategory(models.Model):
    _inherit = 'hr.salary.rule.category'

    @api.constrains('code')
    def check_code(self):
        for record in self:
            if record.code:
                check_code = self.search([('code', '=', record.code), ('id', '!=', record.id)])
                if check_code:
                    raise ValidationError("Salary Rule Category Code must be unique!")

class HrSalaryRule(models.Model):
    _inherit = 'hr.salary.rule'

    tax_calculation_method = fields.Selection([('gross', 'Gross'), ('gross_up', 'Gross Up'),
                                                ('nett', 'Nett')],
                                                string='Tax Calculation Method', default='')
    payslip_type = fields.Many2many('hr.payslip.type', string='Payslip Type')
    category_on_payslip = fields.Selection([('income', 'Income'), ('deduction', 'Deduction'),
                                            ('take_home_Pay', 'Take Home Pay')],
                                           string='Category on Payslip', default='')
    tax_category = fields.Selection([('income_reguler', 'Income Reguler'), ('income_irreguler', 'Income Irreguler'),
                                            ('deduction', 'Deduction')],
                                           string='Tax Category', default='')
    bpjs_kesehatan_report = fields.Selection([('gapok_pensiunan', 'Gapok / Pensiunan'),
                                              ('tunjangan_tetap', 'Tunjangan Tetap'),
                                              ('iuran_perusahaan', 'Iuran Perusahaan'),
                                              ('iuran_pegawai', 'Iuran Pegawai')],
                                             string='BPJS Kesehatan Report', default='')
    bpjs_ketenagakerjaan_report = fields.Selection([('upah', 'Upah'),
                                              ('rapel', 'Rapel'),
                                              ('iuran_jkk', 'Iuran JKK'),
                                              ('iuran_jkm', 'Iuran JKM'),
                                              ('iuran_jht_pemberi_kerja', 'Iuran JHT Pemberi Kerja'),
                                              ('iuran_jht_pekerja', 'Iuran JHT PeKerja'),
                                              ('iuran_jp_pemberi_kerja', 'Iuran JP Pemberi Kerja'),
                                              ('iuran_jp_pekerja', 'Iuran JP PeKerja'),],
                                             string='BPJS Ketenagakerjaan Report', default='')
    apply_to_overtime_calculation = fields.Boolean('Apply to Overtime Calculation', default=False)
    amount_python_compute = fields.Text(string='Python Code',
                                        default='''
                        # Available variables:
                        #----------------------
                        # payslip: object containing the payslips
                        # employee: hr.employee object
                        # contract: hr.contract object
                        # rules: object containing the rules code (previously computed)
                        # categories: object containing the computed salary rule categories (sum of amount of all rules belonging to that category).
                        # worked_days: object containing the computed worked days.
                        # inputs: object containing the computed inputs.
                        # inputs.OVT.amount: get Overtime fee amount
                        # inputs.OVT_MEAL.amount: get Overtime Meal amount

                        # Note: returned value have to be set in the variable 'result'

                        result = contract.wage * 0.10''')

    def _get_worked_days_notes(self):
        result = """
        <table class="table table-striped">
        <tbody>
        <tr><td><b>Description</b></td><td><b>Code</b></td><td style="text-align: left;"><b>Number of Days</b></td><td style="text-align: left;"><b>Number of Hours</b></td></tr>
        <tr><td>Normal Working Days paid at 100%<br></td><td>WORK100<br></td><td style="text-align: left;">0.00</td><td style="text-align: left;">0.00</td></tr>
        <tr><td>Total Calendar Days in Current Month<br></td><td>CALDAYS<br></td><td style="text-align: left;"><span style="text-align: right;">0.00</span><br></td><td style="text-align: left;"><span style="text-align: right;">0.00</span><br></td></tr>
        <tr><td>Total Public Holidays in Current Month<br></td><td>GLOBAL<br></td><td><span style="text-align: right;">0.00</span><br></td><td><span style="text-align: right;">0.00</span><br></td></tr>
        <tr><td>Total Present in Current Month<br></td><td>COUNT_PRESENT<br></td><td><span style="text-align: right;">0.00</span><br></td><td><span style="text-align: right;">0.00</span><br></td></tr>
        <tr><td>Total Fully Present in Current Month<br></td><td>COUNT_FULLY_PRESENT<br></td><td><span style="text-align: right;">0.00</span><br></td><td><span style="text-align: right;">0.00</span><br></td></tr>
        <tr><td>Total Absent in Current Month<br></td><td>COUNT_ABSENT<br></td><td><span style="text-align: right;">0.00</span><br></td><td><span style="text-align: right;">0.00</span><br></td></tr>
        <tr><td>Total Leave in Current Month<br></td><td>COUNT_LEAVE<br></td><td><span style="text-align: right;">0.00</span><br></td><td><span style="text-align: right;">0.00</span><br></td></tr>
        <tr><td>Early Check in<br></td><td>EARLY_CHECKIN<br></td><td><span style="text-align: right;">0.00</span><br></td><td><span style="text-align: right;">0.00</span><br></td></tr>
        <tr><td>Ontime Check in<br></td><td>ONTIME_CHECKIN<br></td><td><span style="text-align: right;">0.00</span><br></td><td><span style="text-align: right;">0.00</span><br></td></tr
        ><tr><td><p>Late Check in<br></p></td><td>LATE_CHECKIN<br></td><td><span style="text-align: right;">0.00</span><br></td><td><span style="text-align: right;">0.00</span><br></td></tr>
        <tr><td>No Check in<br></td><td>NO_CHECKIN<br></td><td><span style="text-align: right;">0.00</span><br></td><td><span style="text-align: right;">0.00</span><br></td></tr>
        <tr><td>Early Check out<br></td><td>EARLY_CHECKOUT<br></td><td><span style="text-align: right;">0.00</span><br></td><td><span style="text-align: right;">0.00</span><br></td></tr>
        <tr><td>Ontime Check out<br></td><td>ONTIME_CHECKOUT<br></td><td><span style="text-align: right;">0.00</span><br></td><td><span style="text-align: right;">0.00</span><br></td></tr>
        <tr><td>Late Check out&nbsp;<br></td><td>LATE_CHECKOUT<br></td><td><span style="text-align: right;">0.00</span><br></td><td><span style="text-align: right;">0.00</span><br></td></tr>
        <tr><td>No Check out<br></td><td>NO_CHECKOUT<br></td><td><span style="text-align: right;">0.00</span><br></td><td><span style="text-align: right;">0.00</span><br></td></tr>
        <tr><td>Total Saturdays in Current Month<br></td><td>SATURDAYS<br></td><td><span style="text-align: right;">0.00</span><br></td><td><span style="text-align: right;">0.00</span><br></td></tr>
        <tr><td>Total Sundays in Current Month<br></td><td>SUNDAYS<br></td><td><span style="text-align: right;">0.00</span><br></td><td><span style="text-align: right;">0.00</span><br></td></tr>
        <tr><td>Total Overtime<br></td><td>OVERTIME<br></td><td><span style="text-align: right;">0.00</span><br></td><td><span style="text-align: right;">0.00</span><br></td></tr>
        </tbody>
        </table>"""
        return result

    worked_days_notes = fields.Html('Worked Days', default=_get_worked_days_notes)
    spt_category_ids = fields.Many2many('hr.spt.category')
    appears_on_report = fields.Boolean('Appears on Report', default=True,
        help="Used to display the salary rule on report.")
    category_on_natura_tax = fields.Many2one('hr.natura.category', string="Category on Natura Tax")

    @api.model
    def create(self, vals):
        if vals.get('slip_id'):
            if self.search([('code', '=', vals.get('code')), ('slip_id', '=', vals.get('slip_id'))]):
                raise ValidationError(_('Duplicate code for salary rule %s (%s)!') % (
                    vals.get('name'), vals.get('code')))
        else:
            if self.search([('code', '=', vals.get('code')), ('id', '!=', vals.get('id'))]):
                raise ValidationError(_('Salary Rule Code must be unique!'))
        return super(HrSalaryRule, self).create(vals)

    def write(self, vals):
        if vals.get('slip_id', False):
            if self.search([('code', '=', vals.get('code')), ('slip_id', '=', vals.get('slip_id'))]):
                raise ValidationError(_('Duplicate code for salary rule %s (%s)!') % (
                        vals.get('name'), vals.get('code')))
        else:
            if self.search([('code', '=', vals.get('code')), ('id', '!=', vals.get('id'))]):
                raise ValidationError(_('Salary Rule Code must be unique!'))
        return super(HrSalaryRule, self).write(vals)

    @api.onchange('category_id')
    def onchange_category(self):
        if self.category_id:
            self.worked_days_notes = False
            self.worked_days_notes = self._get_worked_days_notes()
    
    # @api.onchange('tax_calculation_method')
    # def onchange_tax_calculation_method(self):
    #     if not self.tax_calculation_method:
    #         self.category_on_natura_tax = False

    def _compute_rule(self, localdict):
        self.ensure_one()
        if self.amount_select == 'fix':
            # amount = 0.0
            # for contract in localdict['contract']:
            #     contract_line = contract.mapped('contract_line_ids')
            #     for rec in contract_line.filtered(lambda r: r.amount_select == 'fix'):
            #         code = rec.salary_rule_id.code
            #         if self.code == code:
            #             amount = rec.amount
            try:
                return self.amount_fix, float(safe_eval(self.quantity, localdict)), 100.0
                # return amount, float(safe_eval(self.quantity, localdict)), 100.0
            except:
                raise UserError(_('Wrong quantity defined for salary rule %s (%s).') % (self.name, self.code))
        elif self.amount_select == 'percentage':
            try:
                return (float(safe_eval(self.amount_percentage_base, localdict)),
                        float(safe_eval(self.quantity, localdict)),
                        self.amount_percentage)
            except:
                raise UserError(_('Wrong percentage base or quantity defined for salary rule %s (%s).') % (self.name, self.code))
        else:
            try:
                safe_eval(self.amount_python_compute, localdict, mode='exec', nocopy=True)
                return float(localdict['result']), 'result_qty' in localdict and localdict['result_qty'] or 1.0, 'result_rate' in localdict and localdict['result_rate'] or 100.0
            except:
                raise UserError(_('Wrong python code defined for salary rule %s (%s).') % (self.name, self.code))

class HrSalaryRuleWorkedDays(models.Model):
    _name = 'hr.salary.rule.worked_days'
    _order = 'salary_rule_id, sequence'

    name = fields.Char(string='Description', required=True)
    salary_rule_id = fields.Many2one('hr.salary.rule', string='Salary Rule', required=True, ondelete='cascade', index=True)
    sequence = fields.Integer(required=True, index=True, default=10)
    code = fields.Char(string='Code', required=True)
    number_of_days = fields.Float(string='Number of Days')
    number_of_hours = fields.Float(string='Number of Hours')

class HrPayslipType(models.Model):
    _name = 'hr.payslip.type'
    _description = 'Payslip Type'

    name = fields.Char('Name')

