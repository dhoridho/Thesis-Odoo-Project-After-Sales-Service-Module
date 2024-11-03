from odoo import fields, models, api


class VendorDepositHrCashAdvanceWizard(models.TransientModel):
    _name = 'vendor.deposit.wizard'

    feedback = fields.Text()
    is_reject = fields.Boolean(default=False)
    

    def submit(self):
        """ Prepare the Cash Advance feedback and trigger Approve. """
        self.ensure_one()
        cash_advance = self.env['vendor.deposit'].browse(self._context.get('active_ids', []))
        cash_advance.feedback_parent = self.feedback
        if self.env.context.get('is_approve'):
            cash_advance.action_approve()
        else:
             cash_advance.action_reject()
