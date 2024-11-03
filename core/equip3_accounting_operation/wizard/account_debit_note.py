from odoo import api, fields, models, _
from odoo.exceptions import UserError

class AccountDebitNote(models.TransientModel):
    _inherit = 'account.debit.note'

    def _prepare_default_values(self, move):
        res = super(AccountDebitNote, self)._prepare_default_values(move)
        if move.move_type == 'in_invoice':
            res['move_type'] = 'in_refund'

        return res
    

    def create_debit(self):
        res = super(AccountDebitNote, self).create_debit()
        move_id = self.env['account.move'].browse(self._context.get('active_ids'))
        company_id = move_id.company_id
        branch_id = move_id.branch_id
        check_periods = self.env['sh.account.period'].search([('company_id', '=', company_id.id), ('branch_id', '=', branch_id.id), ('date_start', '<=', self.date), ('date_end', '>=', self.date), ('state', '=', 'done')])
        # check_periods = self.env['sh.account.period'].search([('company_id', '=', self.company_id.id), ('branch_id', '=', self.branch_id.id), ('state', '=', 'done'),('date_start', '<=', self.voucher_date), ('date_end', '>=', self.voucher_date)])
        if check_periods:
            raise UserError(_('You can not post any journal entry already on Closed Period'))

        return res