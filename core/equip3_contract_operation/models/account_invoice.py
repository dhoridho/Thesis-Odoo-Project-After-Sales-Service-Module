from odoo import models, fields, api, _


class AccountMove(models.Model):
    _inherit = 'account.move'
    
    agreement_id = fields.Many2one('agreement')
    expense_plan_id = fields.Many2one('agreement.expense.plan', string="Expense Plan")
    
    
    def action_cancel(self):
        for move in self:
            # We remove all the analytics entries for this journal
            move.mapped('line_ids.analytic_line_ids').unlink()

        self.mapped('line_ids').remove_move_reconcile()
        self.write({'state': 'cancel'})
        return True
