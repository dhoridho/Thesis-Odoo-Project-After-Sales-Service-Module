# -*- coding: utf-8 -*-


from odoo import api, fields, models, _
from odoo.exceptions import Warning

class PosSession(models.Model):
    _inherit = 'pos.session'
 
    pos_session_cashbox_wizard_ids = fields.One2many('account.cashbox.wizard.line', 'pos_session_id', string='Cashbox Lines')
    cash_management_ids = fields.One2many('pos.cash.in.out', 'pos_session_id', string='Cash Management')
    cash_history_ids = fields.One2many('pos.cashbox.history', 'pos_session_id', string='Cashbox History')
    gain_loss_move_id = fields.Many2one('account.move', string="Gain/Loss Journal Entry")


    def action_open_cash_control_before_opening(self):
        if self.cash_control and self.state == 'opening_control':
            return self.pos_session_opening_control(is_return=True)

    def action_end_session_opened_open_cash_control(self):
        return self.pos_session_closing_control(is_return=True)


    def _get_cash_real_expected(self):
        session = self
        cash_payment_method = session.payment_method_ids.filtered('is_cash_count')[:1]
        if cash_payment_method:
            total_cash_payment = sum(session.order_ids.mapped('payment_ids').filtered(
                lambda payment: payment.payment_method_id == cash_payment_method).mapped('amount'))

            total_entry_encoding = session.cash_register_id.total_entry_encoding

            cash_register_total_entry_encoding = total_entry_encoding + (
                0.0 if session.state == 'closed' else total_cash_payment
            )

            money_in = sum(session.cash_management_ids.filtered(lambda c: c.action == 'in').mapped('amount'))
            money_out = sum(session.cash_management_ids.filtered(lambda c: c.action == 'out').mapped('amount'))
            money_in_out = (money_in - money_out)
            cash_register_total_entry_encoding += money_in_out

            # Expected (cash_real_expected)
            return session.cash_opening_balance + cash_register_total_entry_encoding

        return 0

    # OVERRIDE
    def action_pos_session_close(self):
        # IF "Expected" value different with "Actual in Cash" (Closing Difference is not Null)
        # Then show warning balance closing
        if not self.cash_register_id:
            return self._validate_session()

        cash_real_expected = self._get_cash_real_expected()

        if self.cash_control and cash_real_expected != self.cash_register_balance_end_real:
            # Only pos manager can close statements with cash_real_expected not equal cash_register_balance_end_real.
            if not self.user_has_groups("equip3_pos_masterdata.group_pos_supervisor") and not self.user_has_groups("equip3_pos_masterdata.group_pos_manager"):
                raise Warning(_(
                    "Expected value is different with Actual in Cash (real), "
                    "You can contact your manager to force it."
                    "\n\nExpected: (%.2f)"
                    "\nActual in Cash: (%.2f)"
                ) % (cash_real_expected, self.cash_register_balance_end_real))
            else:
                return self._warning_balance_closing()
        else:
            return self._validate_session()

    # OVERRIDE
    def _warning_balance_closing(self):
        self.ensure_one()

        context = dict(self._context)
        context['session_id'] = self.id
        context['default_cash_closing_balance_char'] = self._format_currency_amount(self.cash_closing_balance)
        context['default_cash_register_difference_char'] = self._format_currency_amount(self.cash_register_difference)

        return {
            'name': _('Balance control'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'closing.balance.confirm.wizard',
            'views': [(False, 'form')],
            'type': 'ir.actions.act_window',
            'context': context,
            'target': 'new'
        }
        
    def _format_currency_amount(self, amount):
        pre = post = u''
        currency_id = self.cash_journal_id.company_id.currency_id
        if currency_id.position == 'before':
            pre = u'{symbol}\N{NO-BREAK SPACE}'.format(symbol=currency_id.symbol or '')
        else:
            post = u'\N{NO-BREAK SPACE}{symbol}'.format(symbol=currency_id.symbol or '')

        amount = '{:,.0f}'.format(amount)
        format_amount = '{pre}{amount}{post}'.format(amount=amount, pre=pre, post=post)
        format_amount = str(format_amount)
        format_amount = ' '.join(format_amount.split())
        return format_amount

    @api.depends('pos_session_cashbox_wizard_ids')
    def _compute_opening_control_balance(self):
        super(PosSession, self)._compute_opening_control_balance()
        for rec in self:
            o_balance = 0
            for line in rec.pos_session_cashbox_wizard_ids:
                if not line.is_closing_line:
                    o_balance += line.subtotal
            rec.cash_opening_balance = o_balance

    @api.depends('pos_session_cashbox_wizard_ids')
    def _compute_closing_control_balance(self):
        super(PosSession, self)._compute_closing_control_balance()
        for rec in self:
            o_balance = 0
            for line in rec.pos_session_cashbox_wizard_ids:
                if line.is_closing_line:
                    o_balance += line.subtotal
            rec.cash_closing_balance = o_balance

    def action_save_cashbox(self, vals):
        cashbox_values = {
            'action': vals['action'],
            'product_id': vals['product_id'],
            'amount': vals['amount'],
            'reason': vals['reason'],
            'pos_session_id': self.id,
        }
        self.env['pos.cash.in.out'].create(cashbox_values)
        return { 'status': 'success' }

    def pos_session_opening_control(self, is_return=False):
        values = {
            'is_return': is_return,
            'pos_session_id': self.id,
            'line_ids': [
                (0, 0, {'coin_value': line.coin_value, 'number': line.number, 'subtotal': line.subtotal}) 
                for line in self.pos_config_cashbox_lines_ids
            ],
        }
        wizard = self.env['account.cashbox.wizard'].create(values)
        return {
            'name': "Cash Control",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.cashbox.wizard',
            'views': [(self.env.ref('equip3_pos_cashbox.account_cashbox_wizard_form').id, 'form')],
            'target': 'new',
            'res_id': wizard.id,
        }

    def pos_session_closing_control(self, is_return=False):
        values = {
            'is_return': is_return,
            'pos_session_id': self.id,
            'line_ids': [
                (0, 0, {'coin_value': line.coin_value, 'number': 0, 'subtotal': line.subtotal}) 
                for line in self.pos_config_cashbox_lines_ids
            ],
            'is_closing_wizard': True,
        }
        wizard = self.env['account.cashbox.wizard'].create(values)
        return {
            'name': "Cash Control",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.cashbox.wizard',
            'views': [(self.env.ref('equip3_pos_cashbox.account_cashbox_wizard_form').id, 'form')],
            'target': 'new',
            'res_id': wizard.id,
        }


    @api.depends('payment_method_ids', 'order_ids', 'cash_register_balance_start', 'cash_register_id','cash_opening_balance')
    def _compute_cash_balance(self):
        for session in self:
            cash_payment_method = session.payment_method_ids.filtered('is_cash_count')[:1]
            if cash_payment_method:
                total_cash_payment = sum(session.order_ids.mapped('payment_ids').filtered(
                    lambda payment: payment.payment_method_id == cash_payment_method).mapped('amount'))

                total_entry_encoding = session.cash_register_id.total_entry_encoding

                cash_register_total_entry_encoding = total_entry_encoding + (
                    0.0 if session.state == 'closed' else total_cash_payment
                )

                money_in = sum(session.cash_management_ids.filtered(lambda c: c.action == 'in').mapped('amount'))
                money_out = sum(session.cash_management_ids.filtered(lambda c: c.action == 'out').mapped('amount'))
                money_in_out = (money_in - money_out)
                cash_register_total_entry_encoding += money_in_out

                # Transactions (cash_real_transaction)
                session.cash_register_total_entry_encoding = cash_register_total_entry_encoding

                # Expected (cash_real_expected)
                session.cash_register_balance_end = session.cash_opening_balance + session.cash_register_total_entry_encoding

                # Closing Difference = Actual in Cash (cash_register_balance_end_real) - Expected  (cash_real_expected)
                # Old: session.cash_register_difference = session.cash_register_balance_end_real - session.cash_register_balance_end
                session.cash_register_difference = session.cash_register_balance_end_real - (
                            session.cash_opening_balance + total_cash_payment + money_in_out
                        )

            else:
                session.cash_register_total_entry_encoding = 0.0
                session.cash_register_balance_end = 0.0
                session.cash_register_difference = 0.0


    def _validate_session(self):
        self.ensure_one()
        res = super(PosSession, self)._validate_session()

        for cash in self.cash_management_ids:
            values = cash._prepare_journal_for_cash_management()
            move = self.env['account.move'].sudo().create(values)
            cash.write({ 'account_move_id': move.id })
            move.action_post()

        return res

    def _get_statement_line_vals(self, statement, receivable_account, amount, date=False, partner=False):
        session = self
        res = super(PosSession, self)._get_statement_line_vals(statement=statement, 
            receivable_account=receivable_account, amount=amount, date=date, partner=partner)

        # Amount = Actual in Cash - Opening Balance - CLosing Difference
        if session.config_id.company_id.is_post_closing_cashbox_value_in_session: 
            res['amount'] = session.cash_register_balance_end_real - session.cash_opening_balance - session.cash_register_difference

        # Amount = Actual in Cash - Opening Balance
        if not session.config_id.company_id.is_post_closing_cashbox_value_in_session:
            res['amount'] = session.cash_register_balance_end_real - session.cash_opening_balance

        return res
 
    def _create_cash_statement_lines_and_cash_move_lines(self, data):
        session = self 

        skip_transactions_creation = False
        transaction = session.cash_register_balance_end_real - session.cash_opening_balance
        for statement in session.statement_ids:
            statement.write({ 'transaction': transaction })
        if session.config_id.company_id.is_post_closing_cashbox_value_in_session: 
            if transaction <= 0:
                skip_transactions_creation = True
        else:
            if session.cash_register_balance_end_real <= 0:
                skip_transactions_creation = True

        #TODO: Create bank statement without journal item (status new/processing)
        if skip_transactions_creation:
            for statement in session.statement_ids:
                statement.write({ 'journal_entries_status': 'Cannot create Journal Entries' })

            data.update({'skip_transactions_creation': True})
            return data

        for statement in session.statement_ids:
            if statement.line_ids:
                statement.write({ 'journal_entries_status': 'Journal Entries Posted' })

        return super(PosSession, self)._create_cash_statement_lines_and_cash_move_lines(data=data)


    def _create_account_move(self):
        res = super(PosSession, self)._create_account_move()
        session = self
        session._create_journal_for_cash_difference()

        # TODO: update Ending Balance value
        for statement in session.statement_ids:
            statement._compute_ending_balance()



    def _create_journal_for_cash_difference(self):
        """
        a. If cash_register_balance_end_real - cash_opening_session > 0
            i. Journal Items account:
                1. debit → cashbox payment method intermediary account
                2. credit → → cashbox payment method > cash journal profit account
        b. If cash_register_balance_end_real - cash_opening_session < 0
            i. Journal Items account:
                1. debit → → cashbox payment method > cash journal loss account
                2. credit → cashbox payment method intermediary account
        c. If cash_register_balance_end_real - cash_opening_session == 0
            i. Don’t create journal
        """

        self.ensure_one()
        session = self

        # Closing Difference = Actual in Cash (cash_register_balance_end_real) - Expected  (cash_real_expected)
        amount = session.cash_register_balance_end_real - session.cash_real_expected

        if not self.cash_control or not amount or amount == 0:
            return False

        line_ids, first_vals, second_vals = [], [], []
        payment_method = session.config_id.cashbox_payment_method_id

        if not payment_method:
            raise Warning(_('Please setup Cashbox Payment Method in the config'))
        journal_id = payment_method.cash_journal_id

        if not journal_id.profit_account_id:
            raise Warning(_('Please configure Profit Account in Payment Method "%s" > Cash Journal' % payment_method.name ))
        if not journal_id.loss_account_id:
            raise Warning(_('Please configure Loss Account in Payment Method "%s" > Cash Journal' % payment_method.name ))

        intermediary_account_id = payment_method.receivable_account_id
        profit_account_id = journal_id.profit_account_id
        loss_account_id = journal_id.loss_account_id
        ref = 'Cash Difference %s - ' % str(session.name)

        if amount > 0:
            first_vals = {
                'debit' : abs(amount), 
                'credit' : 0, 
                'name' : 'Cashbox', 
                'account_id' : intermediary_account_id.id,
                'currency_id' : session.currency_id.id,
                'company_id' : session.company_id.id,
            }
            second_vals = {
                'debit' : 0, 
                'credit' : abs(amount), 
                'name' : 'Gain Acc', 
                'account_id' : profit_account_id.id,
                'currency_id' : session.currency_id.id,
                'company_id' : session.company_id.id,
            }

        if amount < 0:
            first_vals = {
                'debit' : abs(amount), 
                'credit' : 0, 
                'name' : 'Loss Acc', 
                'account_id' : loss_account_id.id,
                'currency_id' : session.currency_id.id,
                'company_id' : session.company_id.id,
            }
            second_vals = {
                'debit' : 0, 
                'credit' : abs(amount), 
                'name' : 'Cashbox', 
                'account_id' : intermediary_account_id.id,
                'currency_id' : session.currency_id.id,
                'company_id' : session.company_id.id,
            }

        today = fields.Datetime.now().date()
        period = self.env['sh.account.period'].sudo().search([('date_start','<=',today),('date_end','>=',today)], limit=1)
        
        values = {
            'is_from_pos_cash_difference': True,
            'move_type': 'entry',
            'ref': ref,
            'origin': 'Cash Difference ' + session.name,
            'pos_session_id': session.id,
            'journal_id': journal_id.id,
            'line_ids': [(0, 0, first_vals), (0, 0, second_vals)],
            'period_id': period.id or None,
            'fiscal_year': period.fiscal_year_id.id or None,
            'branch_id': session.pos_branch_id.id,
            'pos_branch_id': session.pos_branch_id.id,
        }
        move_id = self.env['account.move'].sudo().create(values)

        session.write({
            'gain_loss_move_id': move_id.id
        })

        move_id.action_post()

        return move_id



class ClosingBalanceConfirm(models.TransientModel):
    _inherit = 'closing.balance.confirm.wizard'

    cash_closing_balance_char = fields.Char('Cash Closing Balance (Char)')
    cash_register_difference_char = fields.Char('Closing Difference (Char)')

    # OVERRIDE
    def confirm_closing_balance(self):
        current_session =  self.env['pos.session'].browse(self._context['session_id'])
        current_session._validate_session()

        current_session.config_id.write({ 'write_date': fields.Datetime.now() })

        report_action = self.env.ref('equip3_pos_general.report_pos_sales_pdf').report_action(current_session)      
        report_action['close_on_report_download']=True
        return report_action