# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.exceptions import Warning

class AccountCashboxWizard(models.Model):
    _name = "account.cashbox.wizard"

    pos_session_id = fields.Many2one('pos.session', string="POS Session")
    line_ids = fields.One2many('account.cashbox.wizard.line', 'account_cashbox_wizard_id', string='Cashbox Wizard')
    amount_total = fields.Float(string='Amount Total', compute='_compute_amount_total')
    is_closing_wizard = fields.Boolean("Closing balance wizard lines")
    is_validate = fields.Boolean('Is Validate?')
    is_return = fields.Boolean('Is Return?')

    @api.depends('line_ids.coin_value', 'line_ids.number', 'line_ids.subtotal')
    def _compute_amount_total(self):
        for rec in self:
            rec.amount_total = sum([l.subtotal for l in rec.line_ids])

    def action_close_wizard(self):
        active_id = self._context.get("active_id")
        session = self.env['pos.session'].browse(active_id)
        if session:
            history = self.env['pos.cashbox.history'].save_balance_history(session)

            # Opening
            if not self.is_closing_wizard:
                for line in session.pos_session_cashbox_wizard_ids:
                    if not line.is_closing_line:
                        line.unlink()
                session.pos_session_cashbox_wizard_ids += self.line_ids

                history.write({ 'start_date': fields.Datetime.now() })

            # Closing
            if self.is_closing_wizard:
                for line in session.pos_session_cashbox_wizard_ids:
                    if line.is_closing_line:
                        line.unlink()
                session.pos_session_cashbox_wizard_ids += self.line_ids

                history.write({ 'closing_date': fields.Datetime.now() })

            for statement in session.statement_ids:
                statement._compute_starting_balance()
                statement._compute_ending_balance()


    def action_close_and_return(self):
        History = self.env['pos.cashbox.history']
        context = dict(self._context)
        session = self.pos_session_id
        amount_total = self.amount_total


        # Opening
        if not self.is_closing_wizard:
            if session.config_id.cashbox_line_amount and not self.is_validate:
                if session.config_id.cashbox_line_amount != self.amount_total:
                    return {
                        'name': 'Manager PIN required',
                        'type': 'ir.actions.act_window',
                        'view_type': 'form',
                        'view_mode': 'form',
                        'res_model': 'account.cashbox.wizard.validate',
                        'target': 'new',
                        'context': { 'default_account_cashbox_wizard_id': self.id }
                    }
                
            for line in session.pos_session_cashbox_wizard_ids:
                if not line.is_closing_line:
                    line.unlink()
            session.pos_session_cashbox_wizard_ids += self.line_ids

            history = History.save_balance_history(session)
            history.write({ 'start_date': fields.Datetime.now() })

            for statement in session.statement_ids:
                statement._compute_starting_balance()

            session.config_id.write({ 'write_date': fields.Datetime.now() })

            message_log = f'<div class="pos_cash_control _op"><div><b>Opening Cash Control</b></div><div>Amount Total: {amount_total}</div></div>'
            session.message_post(body=message_log, message_type='notification')

            return session.with_context(balance='start').open_cashbox_pos()

        # Closing
        if self.is_closing_wizard:
            for line in session.pos_session_cashbox_wizard_ids:
                if line.is_closing_line:
                    line.unlink()
            session.pos_session_cashbox_wizard_ids += self.line_ids

            history = History.save_balance_history(session)
            history.write({ 'closing_date': fields.Datetime.now() })
            for statement in session.statement_ids:
                statement._compute_ending_balance()
                
            session.config_id.write({ 'write_date': fields.Datetime.now() })

            message_log = f'<div class="pos_cash_control _cp"><div><b>Closing Cash Control</b></div><div>Amount Total: {amount_total}</div></div>'
            session.message_post(body=message_log, message_type='notification')
            
            return session.action_pos_session_closing_control()

    def action_closing_cash_control(self):
        return self.action_close_and_return()

    def continue_process(self):
        return self.action_close_and_return()


class AccountCashboxWizardLines(models.Model):
    _name = "account.cashbox.wizard.line"

    account_cashbox_wizard_id = fields.Many2one('account.cashbox.wizard', string="Cashbox Wizard")
    coin_value = fields.Float(string='Coin/Bill Value', digits=0)
    number = fields.Integer(string='#Coins/Bills', help='Opening Unit Numbers')
    subtotal = fields.Float(compute='_sub_total', string='Subtotal', digits=0, readonly=True)
    cashbox_id = fields.Many2one('account.bank.statement.cashbox', string="Cashbox")
    currency_id = fields.Many2one('res.currency', related='cashbox_id.currency_id')
    pos_config_id = fields.Many2one('pos.config', string="POS Config")
    pos_session_id = fields.Many2one('pos.session', string="POS Session")
    is_closing_line = fields.Boolean('Closing line', related="account_cashbox_wizard_id.is_closing_wizard")

    @api.depends('coin_value', 'number')
    def _sub_total(self):
        """ Calculates Sub total"""
        for cashbox_line in self:
            cashbox_line.subtotal = cashbox_line.coin_value * cashbox_line.number


class AccountCashboxWizard(models.TransientModel):
    _name = 'account.cashbox.wizard.validate'
    _rec_name = 'pin'

    pin = fields.Integer('PIN')
    account_cashbox_wizard_id = fields.Many2one('account.cashbox.wizard', string="Cashbox Wizard")

    def save(self):
        wizard = self.account_cashbox_wizard_id
        wizard.write({ 'is_validate': True })

        manager_pins = []
        for manager in wizard.pos_session_id.config_id.manager_ids:
            manager_pins += [manager.pos_security_pin]

        if not self.pin in manager_pins or not self.pin:
            raise Warning(f'PIN is incorrect')

        return self.account_cashbox_wizard_id.continue_process()