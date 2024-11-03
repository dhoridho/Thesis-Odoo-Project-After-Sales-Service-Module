from datetime import date
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError

from odoo import api, models, fields, _


class HrContract(models.Model):
    _inherit = 'hr.contract'

    hr_contract_income_tax_ids = fields.One2many('hr.contract.income.tax',
                                                 'contract_id', 'Income Tax')


class HrContractIncomeTax(models.Model):
    _name = 'hr.contract.income.tax'
    _rec_name = 'contract_id'
    _description = "Hr Contract IncomeTax"

    @api.depends('start_date', 'end_date', 'contract_id.employee_id')
    def _get_payroll_computational_data(self):
        payslip_obj = self.env['hr.payslip']
        for data in self:
            mbf = donation = CPF_designated_pension_provident_fund = \
                payslip_net_amount = bonus_amount = gross_commission = \
                transport_allowance = gross_amt = 0.00
            start_date = data.start_date - relativedelta(years=1)
            end_date = data.end_date - relativedelta(years=1)

            payslip_ids = payslip_obj.search([
                ('date_from', '>=', start_date),
                ('date_from', '<=', end_date),
                ('employee_id', '=', data.contract_id.employee_id.id),
                ('state', 'in', ['draft', 'done', 'verify'])])
            for payslip in payslip_ids:
                for line in payslip.line_ids:
                    if line.code == 'CPFMBMF':
                        mbf += line.total
                    if line.code in ['CPFSINDA', 'CPFCDAC', 'CPFECF']:
                        donation += line.total
                    if line.category_id.code == 'CAT_CPF_EMPLOYEE':
                        CPF_designated_pension_provident_fund += line.total
                    if line.code == 'GROSS':
                        payslip_net_amount += line.total
                    if line.code == 'SC121':
                        bonus_amount += line.total
                    if line.category_id.code == 'GROSS':
                        gross_amt += line.total
                    if line.code in ['SC102', 'SC103']:
                        gross_amt += line.total
                    if line.code in ['SC104', 'SC105']:
                        gross_commission += line.total
                    if line.code == 'TA':
                        transport_allowance += line.total
            data.mbf = mbf or 0.0
            data.donation = donation or 0.0
            data.CPF_designated_pension_provident_fund = \
                CPF_designated_pension_provident_fund or 0.0
            data.payslip_net_amount = \
                payslip_net_amount or 0.0
            data.bonus_amount = bonus_amount or 0.0
            data.gross_commission = gross_commission or 0.0
            data.transport = transport_allowance or 0.0

    contract_id = fields.Many2one('hr.contract', 'Contract')
    start_date = fields.Date('Assessment Start Date',
                             default=date(date.today().year, 1, 1))
    end_date = fields.Date('Assessment End Date',
                           default=date(date.today().year, 12, 31))
    cessation_date = fields.Date('Cessation Date')
    director_fee = fields.Float('18. Directors fee')
    gain_profit = fields.Float('19(a). Gains & Profit from Share Options \
                               For S10 (1) (g)')
    exempt_income = fields.Float('20. Exempt Income/ Income subject to Tax \
                                 Remission')
    employment_income = fields.Float('21. Amount of employment income for \
                                     which tax is borne by employer')
    benefits_kind = fields.Selection([('Y', "Benefits-in-kind rec'd"),
                                      ('N', "Benefits-in-kind not rec'd")],
                                     string='23. Benefits-in-kind')
    section_applicable = fields.Selection([
        ('Y', 'S45 applicable'),
        ('N', 'S45 not applicable')], string='24. Section 45 applicable')
    employee_income_tax = fields.Selection([
        ('F', 'Tax fully borne by employer on employment income only'),
        ('P', 'Tax partially borne by employer on certain employment income items'),
        ('H', 'A fixed amount of income tax liability borne by employee. \
        Not applicable if income tax is fully paid by employee'),
        ('N', 'Not Applicable')],
        string='25. Employees Income Tax borne by employer')
    gratuity_payment = fields.Selection([
        ('Y', 'Gratuity/ payment in lieu of notice/ex-gratia paid'),
        ('N', 'No Gratuity/ payment in lieu of notice/ex-gratia paid')],
        string='26. Gratuity/ Notice Pay/ Ex-gratia payment/ Others')
    compensation = fields.Selection([
        ('Y', ' Compensation / Retrenchment benefits paid'),
        ('N', 'No Compensation / Retrenchment benefits paid')],
        string='27. Compensation for loss of office')
    approve_obtain_iras = fields.Selection([
        ('Y', 'Approval obtained from IRAS'),
        ('N', 'No approval obtained from IRAS ')],
        string='27(a). Approval obtained from IRAS')
    approval_date = fields.Date('27(b). Date of approval')
    from_ir8s = fields.Selection([
        ('Y', 'IR8S is applicable'), ('N', 'IR8S is not applicable')],
        string='29. Form IR8S')
    exempt_remission = fields.Selection([
        ('1', 'Tax Remission on Overseas Cost of Living Allowance (OCLA)'),
        ('3', 'Seaman'), ('4', 'Exemption'),
        ('5', 'Overseas Pension Fund with Tax Concession'),
        ('6', 'Income from Overseas Employment'),
        ('7', 'Income from Overseas Employment and Overseas Pension Fund \
        with Tax Concession')], string='30. Exempt/ Remission income Indicator')
    gross_commission = fields.Float(
        compute='_get_payroll_computational_data',
        string='31. Gross Commission')
    fromdate = fields.Date('32(a). From Date')
    todate = fields.Date('32(b). To Date')
    gross_commission_indicator = fields.Selection([
        ('M', ' Monthly'), ('O', 'Other than monthly'), ('B', 'Both')],
        string='33. Gross Commission Indicator')
    pension = fields.Float('34. Pension')
    entertainment_allowance = fields.Float('36. Entertainment Allowance')
    other_allowance = fields.Float('37. Other Allowance')
    gratuity_payment_amt = fields.Float('38(b)(1). Gratuity')
    compensation_loss_office = fields.Float(
        '38(a). Compensation for loss of office')
    retirement_benifit_up = fields.Float(
        '39. Retirement benefits accrued up to 31.12.92')
    retirement_benifit_from = fields.Float(
        '40. Retirement benefits accrued from 1993')
    contribution_employer = fields.Float(
        '41. Contributions made by employer to any pension / provident fund \
        constituted outside Singapore')
    excess_voluntary_contribution_cpf_employer = fields.Float(
        '42. Excess / voluntary contribution to CPF by employer')
    gains_profit_share_option = fields.Float(
        '43. Gains and profits from share options for S10 (1) (b)')
    benifits_in_kinds = fields.Float('44. Value of benefits-in- kinds')
    emp_voluntary_contribution_cpf = fields.Float(
        "45. E'yees voluntary contribution to CPF obligatory by contract \
        of employment (overseas posting)")
    bonus_declaration_date = fields.Date('49. Date of declaration of bonus')
    director_fee_approval_date = fields.Date(
        '50. Date of approval of directors fees')
    fund_name = fields.Char('51. Name of fund for Retirement benefits')
    deginated_pension = fields.Char(
        "52. Name of Designated Pension or Provident Fund for which e'yee \
        made compulsory contribution")
    mbf = fields.Float(
        compute='_get_payroll_computational_data', string='12. MBF')
    donation = fields.Float(
        compute='_get_payroll_computational_data', string='13. Donation')
    CPF_designated_pension_provident_fund = fields.Float(
        compute='_get_payroll_computational_data', string='14. CPF/Designated \
        Pension or Provident Fund')
    indicator_for_CPF_contributions = fields.Selection([
        ('Y', 'Obligatory'),
        ('N', 'Not obligatory')],
        string='84. Indicator for CPF contributions in respect of overseas \
        posting which is obligatory by contract of employment')
    CPF_capping_indicator = fields.Selection([
        ('Y', 'Capping has been applied'),
        ('N', 'Capping has been not applied')],
        string='85. CPF capping indicator')
    singapore_permanent_resident_status = fields.Selection(
        [('Y', 'Singapore Permanent Resident Status is approved'),
         ('N', 'Singapore Permanent Resident Status is not approved')],
        string='86. Singapore Permanent Resident Status is approved')
    approval_has_been_obtained_CPF_board = fields.Selection(
        [('Y', ' Approval has been obtained from CPF Board to make full \
            contribution'),
         ('N', ' Approval has NOT been obtained from CPF Board to make \
            full contribution')], string='87. Approval has been \
            obtained from CPF Board to make full contribution')
    eyer_contibution = fields.Float('88. Eyers Contribution')
    eyee_contibution = fields.Float('89. Eyees Contribution')
    additional_wage = fields.Float('99. Additional wages')
    add_wage_pay_date = fields.Date(
        '101. Date of payment for additional wages')
    refund_eyers_contribution = fields.Float(
        '102. Amount of refund applicable to Eyers contribution')
    refund_eyees_contribution = fields.Float(
        '105. Amount of refund applicable to Eyees contribution')
    refund_eyers_date = fields.Date('104. Date of refund given to employer')
    refund_eyees_date = fields.Date('107. Date of refund given to employee')
    refund_eyers_interest_contribution = fields.Float(
        '103. Amount of refund applicable to Eyers Interest on contribution')
    refund_eyees_interest_contribution = fields.Float(
        '106. Amount of refund applicable to Eyees Interest on contribution')
    insurance = fields.Float('Insurance')
    payslip_net_amount = fields.Float(
        compute='_get_payroll_computational_data',
        string='16. Gross Salary, Fees, Leave Pay, Wages and Overtime Pay')
    bonus_amount = fields.Float(
        compute='_get_payroll_computational_data', string='17. Bonus')

    transport = fields.Float(compute='_get_payroll_computational_data',
                             string='35. Transport Allowance')
    notice_pay = fields.Float('38(b)(2). Notice Pay')
    ex_gratia = fields.Float('38(b)(3). Ex-Gratia')
    others = fields.Float('38(b)(4). Others')
    reason = fields.Char('38(b)(4)(a). Reason')
    employee_income = fields.Float(
        "22. Fixed Amount of income tax liability for which tax borne by \
        employee")
    contribution_mandetory = fields.Selection(
        [('Yes', 'Yes'), ('No', 'No')], "Are Contribution Mandetory?")
    contribution_amount = fields.Float("Full Amount of the contributions")
    contribution_charged = fields.Selection(
        [('Yes', 'Yes'), ('No', 'No')], "Were contribution charged / \
        deductions claimed by a Singapore permanent establishment?")
    gorss_comm_period_from = fields.Date("31(a). Gross Commission From")
    gorss_comm_period_to = fields.Date("31(b). Gross Commission To")
    gross_comm_indicator = fields.Selection(
        [('M', 'Monthly'), ('O', 'Other than monthly'), ('B', 'Both')],
        "Gross Commission Indicator")

    @api.onchange('end_date')
    def onchange_end_date(self):
        if self.start_date >= self.end_date:
            raise ValidationError(
            _("You must enter start date less than end date."))
