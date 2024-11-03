from odoo import api, fields, models
from datetime import datetime
from dateutil.relativedelta import relativedelta


class AccountLoan(models.Model):
    _inherit = "account.loan"

    @api.model
    def _default_short_term_loan_account(self):
        payable_type_id = self.env.ref('account.data_account_type_payable')
        short_term = self.env["account.account"].sudo().search([('code','=','22110001'),('user_type_id', '=', payable_type_id.id)],limit=1)
        if short_term:
            return short_term.id
        else:
            return False

    @api.model
    def _default_long_term_loan_account(self):
        payable_type_id = self.env.ref('account.data_account_type_payable')
        long_term = self.env["account.account"].sudo().search([('code','=','22110002'),('user_type_id', '=', payable_type_id.id)],limit=1)
        if long_term:
            return long_term.id
        else:
            return False
    
    @api.model
    def _default_interest_expenses_account(self):
        expenses_type_id = self.env.ref('account.data_account_type_expenses')
        interest_expenses = self.env["account.account"].sudo().search([('code','=','91100010'),('user_type_id', '=', expenses_type_id.id)],limit=1)
        if interest_expenses:
            return interest_expenses.id
        else:
            return False

    short_term_loan_account_id = fields.Many2one(default=lambda r: r._default_short_term_loan_account())
    long_term_loan_account_id = fields.Many2one(default=lambda r: r._default_long_term_loan_account())
    interest_expenses_account_id = fields.Many2one(default=lambda r: r._default_interest_expenses_account())
    loan_type = fields.Selection(
        [
            ('pvip', 'PVIF'),
            ("fixed-annuity", "Fixed Annuity"),
            ("fixed-annuity-begin", "Fixed Annuity Begin"),
            ("fixed-principal", "Fixed Principal"),
            ("interest", "Only interest"),
        ],
        required=True,
        help="Method of computation of the period annuity",
        readonly=True,
        states={"draft": [("readonly", False)]},
        default="pvip",
    )
    total_lease_recal = fields.Monetary(currency_field="currency_id", compute='compute_total_lease_recal')
    implicit_interest_exp = fields.Monetary(currency_field="currency_id", compute='compute_implicit_interest_exp')
    line_ids_pvif = fields.One2many("account.loan.line", readonly=True, inverse_name="loan_id", copy=False, relate='line_ids')

    # inherit from account_loan
    @api.onchange("company_id")
    def _onchange_company(self):
        self._onchange_is_leasing()
        ## start comment this for fill default account
        # self.interest_expenses_account_id = (
        #     self.short_term_loan_account_id
        # ) = self.long_term_loan_account_id = False
        ## end comment

    def loan_rate(self):
        if self.loan_type == 'pvip':
            return self.compute_rate(self.rate, 'real', self.method_period)
        else:
            return super(AccountLoan, self).loan_rate()

    def compute_draft_lines(self):
        self.ensure_one()
        if self.loan_type == 'pvip':
            self.fixed_periods = self.periods
            self.fixed_loan_amount = self.loan_amount
            self.line_ids.unlink()
            amount = self.loan_amount
            if self.start_date:
                date = self.start_date
            else:
                date = datetime.today().date()
            delta = relativedelta(months=self.method_period)
            if not self.payment_on_first_period:
                date += delta
            for i in range(1, self.periods + 1):
                line = self.env["account.loan.line"].create(
                    self.new_line_vals(i, date, amount)
                )
                line.check_amount()
                date += delta
                amount -= line.principal_amount
            amount = self.total_lease_recal
            for line_id in self.line_ids:
                line_id.write({'pending_principal_amount': amount,
                            'lease_liabilities_ending': amount - line_id.principal_amount
                            })
                line_id.check_amount()
                amount -= line_id.principal_amount
            if self.long_term_loan_account_id:
                self.check_long_term_principal_amount()
        else:
            super(AccountLoan, self).compute_draft_lines()

    @api.depends('line_ids')
    def compute_total_lease_recal(self):
        for rec in self:
            if rec.line_ids:
                rec.total_lease_recal = sum(rec.line_ids.mapped('pv_of_lease_recal'))
            else:
                rec.total_lease_recal = 0

    @api.depends('total_lease_recal')
    def compute_implicit_interest_exp(self):
        for rec in self:
            rec.implicit_interest_exp = rec.loan_amount - rec.total_lease_recal

    def check_long_term_principal_amount(self):
        if self.loan_type == 'pvip':
            lines = self.line_ids.filtered(lambda r: not r.move_ids)
            amount = 0
            if not lines:
                return
            final_sequence = min(lines.mapped("sequence"))
            for line in lines.sorted("sequence", reverse=True):
                date = line.date + relativedelta(months=12)
                if self.state == "draft" or line.sequence != final_sequence:
                    line.long_term_pending_principal_amount = line.lease_liabilities_ending

                line.long_term_principal_amount = line.principal_amount
        else:
            return super(AccountLoan, self).check_long_term_principal_amount()
