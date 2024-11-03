from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountLoanLine(models.Model):
    _inherit = "account.loan.line"
    
    pv_of_lease_recal = fields.Monetary(currency_field="currency_id")
    lease_liabilities_ending = fields.Monetary(currency_field="currency_id")
    rou_beginning = fields.Monetary(currency_field="currency_id", compute="_compute_amounts")
    depreciation = fields.Monetary(currency_field="currency_id", compute="_compute_amounts")
    rou_ending = fields.Monetary(currency_field="currency_id", compute="_compute_amounts")

    @api.depends("payment_amount", "interests_amount", "pending_principal_amount", "pv_of_lease_recal", "lease_liabilities_ending")
    def _compute_amounts(self):
        for rec in self:
            if rec.loan_type == 'pvip':
                rec.depreciation = rec.payment_amount - (rec.loan_id.implicit_interest_exp / rec.loan_id.periods)
                rec.rou_beginning = rec.depreciation * (rec.loan_id.periods - rec.sequence + 1)
                rec.rou_ending = rec.rou_beginning - rec.depreciation
                # rec.principal_amount = rec.payment_amount - rec.interests_amount
                # rec.final_pending_principal_amount = (rec.pending_principal_amount - rec.payment_amount + rec.interests_amount)
                super(AccountLoanLine, self)._compute_amounts()
            else:
                rec.depreciation = 0
                rec.rou_beginning = 0
                rec.rou_ending = 0
                super(AccountLoanLine, self)._compute_amounts()        

    def compute_amount(self):
        if self.loan_type == 'pvip':
            return (self.loan_id.loan_amount / self.loan_id.periods)
        else:
            return super(AccountLoanLine, self).compute_amount()

    def compute_pv_of_lease_recal(self):
        return (self.loan_id.loan_amount / self.loan_id.periods) / (1 + ((self.rate/100) / 12)) ** self.sequence

    def check_amount(self):        
        if self.loan_type == 'pvip':
            self.interests_amount = self.compute_interest()
            self.payment_amount = self.compute_amount()
            self.pv_of_lease_recal = self.compute_pv_of_lease_recal()
        else:
            return super(AccountLoanLine, self).check_amount()

    def compute_interest(self):
        if self.loan_type == 'pvip':
            return (self.loan_id.loan_amount / self.loan_id.periods) - ((self.loan_id.loan_amount / self.loan_id.periods) / (1 + ((self.rate/100) / 12)) ** (self.loan_id.periods - self.sequence + 1))
        else:
            return super(AccountLoanLine, self).compute_interest()