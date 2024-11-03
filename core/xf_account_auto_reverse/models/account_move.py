# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = 'account.move'

    # Fields    
    auto_reverse = fields.Boolean(
        string='Reverse Automatically',
        default=False,
        copy=False,
        help='If this checkbox is ticked, this entry will be automatically reversed at specified date.',
    )
    auto_reverse_date = fields.Date(
        string='Auto-Reversal Date',
        index=True,
        copy=False,
        help="This required field is used to schedule auto-reversing."
    )
    auto_reverse_journal_id = fields.Many2one(
        string='Auto-Reversal Journal',
        comodel_name='account.journal',
        copy=False,
        help='If empty, uses the journal of the journal entry to be reversed.',
        check_company=True,
    )
    auto_reverse_date_mode = fields.Selection(
        string='Reversal Entry Date',
        selection=[
            ('custom', 'Specific'),
            ('entry', 'Journal Entry Date')
        ],
        required=True,
        copy=False,
        default='custom',
    )
    auto_reversal_entry_date = fields.Date(
        string='Reversal Entry Date',
        copy=False,
        help='Accounting date of reversal journal entry.'
    )
    auto_reversed = fields.Boolean(
        string='Reversed Automatically',
        readonly=True,
        index=True,
        copy=False,
    )

    # Compute and search fields, in the same order of fields declaration

    # Constraints and onchanges

    @api.constrains('auto_reverse', 'auto_reverse_date')
    def _check_auto_reverse_date(self):
        for move in self:
            if move.auto_reverse and not move.auto_reverse_date:
                raise ValidationError(_('Please set Auto-Reversal Date'))

    @api.constrains('auto_reverse', 'move_type')
    def _check_auto_reverse_type(self):
        for move in self:
            if move.auto_reverse and move.move_type in ('out_refund', 'in_refund'):
                raise ValidationError(_('Credit Notes and Refunds cannot be reversed automatically!'))

    @api.onchange('auto_reverse_date_mode')
    def _onchange_auto_reverse_date_mode(self):
        for move in self:
            if move.auto_reverse_date_mode == 'custom' and not move.auto_reversal_entry_date:
                move.auto_reversal_entry_date = move.auto_reverse_date
            elif move.auto_reverse_date_mode == 'entry':
                move.auto_reversal_entry_date = None

    @api.onchange('auto_reverse_date')
    def _onchange_auto_reverse_date(self):
        for move in self:
            if move.auto_reverse_date_mode == 'custom':
                move.auto_reversal_entry_date = move.auto_reverse_date

    # Built-in methods overrides
    # Action methods

    def button_draft(self):
        super(AccountMove, self).button_draft()
        self._reset_auto_reverse_checkboxes()

    def button_cancel(self):
        super(AccountMove, self).button_cancel()
        self._reset_auto_reverse_checkboxes()

    # Business methods

    def _reset_auto_reverse_checkboxes(self):
        self.write({'auto_reverse': False, 'auto_reversed': False})

    def run_auto_reverse(self):
        domain = [
            ('state', '=', 'posted'),
            ('auto_reverse', '=', True),
            ('auto_reversed', '!=', True),
            ('auto_reverse_date', '<=', fields.Date.today()),
        ]
        moves_to_reverse = self.search(domain)
        for move in moves_to_reverse:
            journal = move.auto_reverse_journal_id

            self.env['account.move.reversal'].create({
                'move_ids': [(6, 0, move.ids)],
                'date_mode': move.auto_reverse_date_mode,
                'date': move.auto_reversal_entry_date,
                'reason': 'Scheduled Auto-Reversing',
                'refund_method': 'cancel',
                'journal_id': journal and journal.id,
                'company_id': move.company_id.id,
            }).reverse_moves()
            if move.reversal_move_id:
                move.auto_reversed = True
