from odoo import fields, models, api


class HrExpenseSheetWizard(models.TransientModel):
    _name = 'hr.expense.sheet.wizard'

    feedback = fields.Text()

    def submit(self):
        """ Prepare the Cash Expense feedback and trigger Approve. """
        self.ensure_one()
        hr_expense = self.env['hr.expense.sheet'].browse(self._context.get('active_ids', []))
        hr_expense.feedback_parent = self.feedback
        hr_expense.approve_expense_sheets()
