# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class CloseFundWizard(models.TransientModel):
    _name = 'account.pettycash.fund.close'
    _description = 'Petty Cash Fund Closing Wizard'

    @api.model
    def _get_fund(self):
        fund_id = self.env.context.get('active_id', False)
        return fund_id

    @api.model
    def _domain_receivable_account(self):
        return [('user_type_id.name', 'in', ['Expenses', 'Bank and Cash']), ('company_id','=', self.env.company.id)]

    fund = fields.Many2one('account.pettycash', default=_get_fund, required=True)
    receivable_account = fields.Many2one('account.account', domain=_domain_receivable_account)
    effective_date = fields.Date(string='Accounting Date', required=True, default=fields.Date.context_today)
    close_balance = fields.Monetary(related='fund.balance', string='Close Balance', store=True)
    currency_id = fields.Many2one('res.currency', string='Currency', related='fund.currency_id', required=True)
    company_id = fields.Many2one('res.company', related='fund.company_id')
    apply_manual_currency_exchange = fields.Boolean(string="Apply Manual Currency Exchange")
    manual_currency_exchange_rate = fields.Float(string="Manual Currency Exchange Rate", digits=(12,12))
    manual_currency_exchange_inverse_rate = fields.Float(string="Inverse Rate", digits=(12,12))
    active_manual_currency_rate = fields.Boolean('active Manual Currency', default=False)

    @api.onchange('currency_id')
    def onchange_currency_id(self):
        if self.currency_id:
            if self.company_id.currency_id != self.currency_id:
                if not self.effective_date:
                    raise UserError(_('Please set Accounting Date first'))
                self.active_manual_currency_rate = True                
            else:
                self.active_manual_currency_rate = False
        else:
            self.active_manual_currency_rate = False

    @api.onchange('manual_currency_exchange_inverse_rate')
    def _oncange_rate_conversion(self):
        if self.manual_currency_exchange_inverse_rate:
            self.manual_currency_exchange_rate = 1 / self.manual_currency_exchange_inverse_rate

    @api.onchange('manual_currency_exchange_rate')
    def _oncange_rate(self):
        if self.manual_currency_exchange_rate:
            self.manual_currency_exchange_inverse_rate = 1 / self.manual_currency_exchange_rate

    def close_fund(self):
        for wizard in self:
            if wizard.apply_manual_currency_exchange:
                wizard.fund.close_fund(wizard.effective_date, wizard.receivable_account, wizard.manual_currency_exchange_inverse_rate)
            else:
                wizard.fund.close_fund(wizard.effective_date, wizard.receivable_account)
