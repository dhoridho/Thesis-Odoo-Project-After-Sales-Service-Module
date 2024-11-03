# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError


class AccountMove(models.Model):
    _inherit = "account.move"

    # name = fields.Char(string='Number', required=True, readonly=False, copy=False, default='/')

    def _get_sequence(self):
        self.ensure_one()
        journal = self.journal_id
        if self.move_type in ('entry', 'out_invoice', 'in_invoice', 'out_receipt', 'in_receipt') or not journal.refund_sequence:
            return journal.sequence_id
        if not journal.refund_sequence_id:
            return
        return journal.refund_sequence_id

    def _post(self, soft=True):
        for move in self:
            if move.name:
                if move.name == '/':
                    sequence = move._get_sequence()
                    print(sequence)
                    if not sequence:
                        raise UserError(_('Please define a sequence on your journal.'))
                    move.name = sequence.with_context(ir_sequence_date=move.date).next_by_id()
        res = super(AccountMove, self)._post(soft=True)
        return res

    @api.onchange('journal_id')
    def onchange_journal_id(self):
        self.name = '/'

    def _constrains_date_sequence(self):
        return
