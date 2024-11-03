from odoo import models, fields, api
from odoo.tools.translate import _
from odoo.exceptions import UserError

class AccountMoveReversal(models.TransientModel):
    _inherit = 'account.move.reversal'


    def reverse_moves(self):
        self.ensure_one()
        # active_id = self._context.get('active_id')
        move_id = self.env['account.move'].browse(self._context.get('active_ids'))
        company_id = move_id.company_id
        branch_id = move_id.branch_id
        check_periods = self.env['sh.account.period'].search([('company_id', '=', company_id.id), ('branch_id', '=', branch_id.id), ('date_start', '<=', self.date), ('date_end', '>=', self.date), ('state', '=', 'done')])
        if check_periods:
            raise UserError(_('You can not post any journal entry already on Closed Period'))
        moves = self.move_ids
 
        # Create default values.
        default_values_list = []
        for move in moves:
            default_values_list.append(self._prepare_default_reversal(move))

        batches = [
            [self.env['account.move'], [], True],   # Moves to be cancelled by the reverses.
            [self.env['account.move'], [], False],  # Others.
        ]

        # Group moves by their journal and reversal date.
        for move, default_vals in zip(moves, default_values_list):
            is_auto_post = bool(default_vals.get('auto_post'))
            is_cancel_needed = not is_auto_post and self.refund_method in ('cancel', 'modify')
            batch_index = 0 if is_cancel_needed else 1
            batches[batch_index][0] |= move
            batches[batch_index][1].append(default_vals)

       # Handle reverse method.
        moves_to_redirect = self.env['account.move']
        for moves, default_values_list, is_cancel_needed in batches:
            new_moves = moves._reverse_moves(default_values_list, cancel=is_cancel_needed)

            if self.refund_method == 'modify':
                moves_vals_list = []
                for move in moves.with_context(include_business_fields=True):
                    moves_vals_list.append(move.copy_data({'date': self.date if self.date_mode == 'custom' else move.date})[0])
                new_moves = self.env['account.move'].create(moves_vals_list)


            moves_to_redirect |= new_moves

        self.new_move_ids = moves_to_redirect

        # Create action.
        action = {
            'name': _('Reverse Moves'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
        }
        moves = {}
        if len(moves_to_redirect) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': moves_to_redirect.id,
                'context': {'default_move_type':  moves_to_redirect.move_type},
            })
            moves.update({
                'move_type': moves_to_redirect.move_type,
                # 'state': 'posted',
            })
            moves_to_redirect.write(moves)
        else:
            action.update({
                'view_mode': 'tree,form',
                'domain': [('id', 'in', moves_to_redirect.ids)],
            })
            if len(set(moves_to_redirect.mapped('move_type'))) == 1:
                action['context'] = {'default_move_type':  moves_to_redirect.mapped('move_type').pop()}
        return action
    
    def _prepare_default_reversal(self, move):
        move_vals = super(AccountMoveReversal, self)._prepare_default_reversal(move)
        reverse_date = self.date if self.date_mode == 'custom' else move.date
        reval_id = []
        if move.currency_revaluation_ref_id:
            reval_id = move.currency_revaluation_ref_id.id
        else :
            reval_id = move.id

        move_vals.update({'name': _('R%s', move.name),
                          'currency_revaluation_ref_id': reval_id,
                         })
        return move_vals
        # reverse_date = self.date if self.date_mode == 'custom' else move.date
        # reval_id = []
        # if move.currency_revaluation_ref_id:
        #     reval_id = move.currency_revaluation_ref_id.id
        # else :
        #     reval_id = move.id
        # return {
        #     'name': _('R%s', move.name),
        #     'ref': _('Reversal of: %(move_name)s, %(reason)s', move_name=move.name, reason=self.reason) 
        #            if self.reason
        #            else _('Reversal of: %s', move.name),
        #     'date': reverse_date,
        #     'invoice_date': move.is_invoice(include_receipts=True) and (self.date or move.date) or False,
        #     'journal_id': self.journal_id and self.journal_id.id or move.journal_id.id,
        #     # 'state': 'posted',
        #     # 'move_type': move.move_type in ('in_invoice', 'in_refund') and 'in_refund' or 'entry',
        #     'invoice_payment_term_id': None,
        #     'invoice_user_id': move.invoice_user_id.id,
        #     'auto_post': True if reverse_date > fields.Date.context_today(self) else False,
        #     'currency_revaluation_ref_id': reval_id,
        # }
        
    def _reverse_moves_post_hook(self, moves):
        """ Execute post hooks after the moves are reversed.
        """
        self.ensure_one()
        if self.refund_method == 'modify':
            moves.write({'date': self.date})
        return