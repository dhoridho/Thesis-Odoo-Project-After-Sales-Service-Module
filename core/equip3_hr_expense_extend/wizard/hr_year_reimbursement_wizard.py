# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.
from odoo import _, api, fields, models


class Message(models.TransientModel):
    _name = 'hr.expense.reimbursement'

    reimbursement_date_after = fields.Integer("Reimbursement Date after")

    def prepare_reimbursement(self):
        """ Prepare the reimbursement date. """
        self.ensure_one()
        expense_cycle = self.env['hr.expense.cycle'].browse(self._context.get('active_ids', []))
        expense_cycle.reimbursement_date_after = self.reimbursement_date_after
        expense_cycle.expense_confirm()
