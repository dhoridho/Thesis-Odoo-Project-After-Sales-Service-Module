from odoo import fields, models, api


class HrLoanWizard(models.TransientModel):
    _name = 'hr.loan.wizard'

    feedback = fields.Text()
    is_reject = fields.Boolean(default=False)

    def submit(self):
        """ Prepare the Loan feedback and trigger Approve. """
        self.ensure_one()
        hr_loan = self.env['employee.loan.details'].browse(self._context.get('active_ids', []))
        hr_loan.feedback_parent = self.feedback
        if self.env.context.get('is_approve'):
            hr_loan.action_approved()
        else:
             hr_loan.action_rejected()


class HrLoanCancelWizard(models.TransientModel):
    _name = 'hr.loan.cancel.wizard'

    feedback = fields.Text()
    is_reject = fields.Boolean(default=False)

    def submit(self):
        """ Prepare the Loan feedback and trigger Approve. """
        self.ensure_one()
        hr_loan = self.env['employee.loan.cancelation'].browse(self._context.get('active_ids', []))
        hr_loan.feedback_parent = self.feedback
        if self.env.context.get('is_approve'):
            hr_loan.action_approved()
        else:
             hr_loan.action_reject()



class HrFullLoanWizard(models.TransientModel):
    _name = 'hr.full.loan.wizard'

    feedback = fields.Text()

    def submit(self):
        """ Prepare the Loan feedback and trigger Approve. """
        self.ensure_one()
        hr_full_loan = self.env['hr.full.loan.payment'].browse(self._context.get('active_ids', []))
        hr_full_loan.feedback_parent = self.feedback
        hr_full_loan.action_approved()
        for line in hr_full_loan.installment_lines:
            line.state = 'approve'

class LoanInstallmentWizard(models.TransientModel):
    _name = 'hr.loan.installment.wizard'

    feedback = fields.Text()

    def submit(self):
        """ Prepare the Loan Installment feedback and trigger Approve. """
        self.ensure_one()
        loan_installment = self.env['loan.installment.details'].browse(self._context.get('active_ids', []))
        loan_installment.feedback_parent = self.feedback
        loan_installment.action_approved()