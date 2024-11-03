# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class AccountBankStatementCashBox(models.Model):
    """
    Account Bank Statement popup that allows entering cash details.
    """
    _inherit = 'account.bank.statement.cashbox'
    _description = 'Account Bank Statement Cashbox Details'

    description = fields.Char("Description")
    bnk_cash_control = fields.Boolean("Cash Control")
    is_closing_line = fields.Boolean("Is Closing Balance?")
    pos_session_id = fields.Many2one("pos.session", "POS Session")

    def set_default_cashbox(self):
        self.ensure_one()
        current_session = self.env['pos.session'].browse(self.env.context['default_pos_session_id'])
        lines = current_session.config_id.pos_cashbox_lines_ids
        context = dict(self._context)
        self.cashbox_lines_ids.unlink()
        self.cashbox_lines_ids = [[0, 0, {'coin_value': line.coin_value, 'number': line.number, 'subtotal': line.subtotal}] for line in lines]
        current_session.cash_opening_balance = self.total

        return {
            'name': _('Cash Control'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.bank.statement.cashbox',
            'view_id': self.env.ref('point_of_sale.view_account_bnk_stmt_cashbox_footer').id,
            'type': 'ir.actions.act_window',
            'context': context,
            'target': 'new',
            'res_id': self.id,
        }

    # def set_default_cashbox(self):
    #     total_amt = self.total
    #     vals = self.env.context.copy()
    #     vals.update({'pos_session_id':vals.get('default_pos_session_id')})
    #     self.env.context = vals
    #     res = super(AccountBankStmtCashWizard,self).set_default_cashbox()
    #     current_session = self.env['pos.session'].browse(self.env.context['pos_session_id'])
    #     current_session.cash_opening_balance = total_amt
    #     return res

    def validate_from_ui(self, session_id, balance, values):
        """
        Create , Edit , Delete of Closing Balance Grid
        param session_id: POS Open Session id .
        param values: Array records to save
        return: Array of cashbox line.
        """
        session = self.env['pos.session'].browse(int(session_id))
        bnk_stmt = session.cash_register_id
        if (balance == 'start'):
            self = session.cash_register_id.cashbox_start_id
        else:
            self = session.cash_register_id.cashbox_end_id
        if not self:
            self = self.create({'description': "Created from POS"})
            if self and (balance == 'end'):
                account_bank_statement = session.cash_register_id
                account_bank_statement.write({'cashbox_end_id': self.id})
        for val in values:
            id = val.get('id', None)
            number = val.get('number', 0)
            coin_value = val.get('coin_value', 0)
            cashbox_line = self.env['account.cashbox.line']
            if id and number and coin_value:  # Add new Row
                cashbox_line = cashbox_line.browse(id)
                cashbox_line.write({'number': number,
                                    'coin_value': coin_value
                                    })
            elif not id and number and coin_value:  # Add new Row
                cashbox_line.create({'number': number,
                                     'coin_value': coin_value,
                                     'cashbox_id': self.id
                                     })
            elif id and not (number and coin_value):  # Delete Exist Row
                cashbox_line = cashbox_line.browse(id)
                cashbox_line.unlink()

        total = 0.0
        for lines in self.cashbox_lines_ids:
            total += lines.subtotal
        if (balance == 'start'):  # starting balance
            bnk_stmt.write({
                'balance_start': total,
                'cashbox_start_id': self.id
            })
        else:  # closing balance
            bnk_stmt.write({
                'balance_end_real': total,
                'cashbox_end_id': self.id
            })
        if (balance == 'end'):
            if bnk_stmt.difference < 0:
                if self.env.user.id == SUPERUSER_ID:
                    return (_('you have to send more %s %s') %
                            (bnk_stmt.currency_id.symbol,
                             abs(bnk_stmt.difference)))
                else:
                    return (_('you have to send more amount'))
            elif bnk_stmt.difference > 0:
                if self.env.user.id == SUPERUSER_ID:
                    return (_('you may be missed some bills equal to %s %s')
                            % (bnk_stmt.currency_id.symbol,
                               abs(bnk_stmt.difference)))
                else:
                    return (_('you may be missed some bills'))
            else:
                return (_('you done a Great Job'))
        else:
            return

    def validate(self):
        """
        TODO: Raise popup for set closing balance in session POS
        """
        res = super(AccountBankStmtCashWizard, self).validate()
        bnk_stmt_id = (self.env.context.get('bank_statement_id', False) or
                       self.env.context.get('active_id', False))
        bnk_stmt = self.env['account.bank.statement'].browse(bnk_stmt_id)
        if bnk_stmt.pos_session_id.state == 'closing_control':
            if bnk_stmt.difference < 0:
                raise UserError(_('you have to send more %s %s') % (
                    bnk_stmt.currency_id.symbol,
                    abs(bnk_stmt.difference)))
            elif bnk_stmt.difference > 0:
                raise UserError(_('you may be missed some '
                                  'bills equal to %s %s') % (
                                    bnk_stmt.currency_id.symbol,
                                    abs(bnk_stmt.difference)))
            else:
                return res
        else:
            return res
