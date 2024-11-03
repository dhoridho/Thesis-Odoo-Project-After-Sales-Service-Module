# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.addons import decimal_precision as dp
from odoo.tools import float_compare, float_is_zero
from odoo.tools.translate import _
from odoo.exceptions import ValidationError


class AccountPettycashFundChange(models.TransientModel):
    _name = 'account.pettycash.fund.change'
    _description = 'Petty Cash Fund Change Wizard'

    @api.model
    def _get_fund(self):
        fund_id = self.env.context.get('active_id', False)
        return fund_id

    @api.model
    def _get_fund_name(self):
        name = False
        fnd = self.env['account.pettycash'].browse(self._get_fund())
        if fnd:
            name = fnd.name
        return name

    @api.model
    def _get_fund_amount(self):
        amount = False
        fnd = self.env['account.pettycash'].browse(self._get_fund())
        if fnd:
            amount = fnd.amount
        return amount

    @api.model
    def _get_custodian(self):
        _id = False
        fnd = self.env['account.pettycash'].browse(self._get_fund())
        if fnd:
            _id = fnd.custodian.id
        return _id

    fund = fields.Many2one('account.pettycash', default=_get_fund, required=True)
    fund_name = fields.Char(default=_get_fund_name)
    custodian = fields.Many2one('res.users', default=_get_custodian)
    fund_amount = fields.Monetary(string='Fund Amount', related='fund.amount', readonly=True, digits=dp.get_precision('Product Price'))
    new_amount = fields.Monetary(digits=dp.get_precision('Product Price'), default=_get_fund_amount)
    payable_account = fields.Many2one('account.account', domain=[('user_type_id.name', 'in', ['Payable', 'Receivable', 'Bank and Cash', 'Current Assets', 'Current Liabilities'])], string='Modify Account')
    receivable_account = fields.Many2one('account.account', domain=[('user_type_id.name', '=', 'Receivable')])
    effective_date = fields.Date(string='Accounting Date', required=True)
    do_receivable = fields.Boolean()
    move = fields.Many2one('account.move', string="Journal Entry")
    is_add_balance = fields.Boolean('Add Balance')
    currency_id = fields.Many2one('res.currency', string='Currency', related='fund.currency_id', required=True)

    @api.onchange('new_amount')
    def onchange_new_amount(self):
        for wiz in self:
            res = False
            if float_compare(wiz.new_amount, wiz.fund_amount,
                             precision_digits=2) == -1:
                res = True
            wiz.do_receivable = res

    def change_fund(self):
        for wizard in self:
            fnd = wizard.fund
            modify_balance = wizard.new_amount - wizard.fund_amount

            final_balance = wizard.fund.balance + modify_balance
            if final_balance < 0:
                raise ValidationError(_("Operation Failed !!! \nNew changed voucher amount is lower than existing balance."))
            if wizard.new_amount < wizard.fund.balance:
                raise ValidationError(_("Please check your entry! New Fund amount cannot be lesser than current Petty Cash Balance."))
            # Make necessary changes to fund
            #
            update_vals = {}
            if fnd.name and fnd.name != wizard.fund_name:
                update_vals.update({'name': wizard.fund_name})
            if wizard.custodian and fnd.custodian.id != wizard.custodian.id:
                update_vals.update({'custodian': wizard.custodian.id})
            fnd.write(update_vals)

            # Is there is a change in fund amount create journal entries
            #
            if not float_is_zero(wizard.new_amount, precision_digits=2) \
                and float_compare(
                    fnd.amount, wizard.new_amount, precision_digits=2) != 0:

                action = 'Increase'
                if float_compare(wizard.new_amount, fnd.amount,
                                    precision_digits=2) == -1:
                    action = 'Decrease'
                desc = _("%s Petty Cash Fund (%s)"
                            % (action, wizard.fund.name))

                # If it is an increase create a payable account entry. If
                # we are decreasing the fund amount it should be a receivable
                # from the custodian.
                #
                if action == 'Increase':
                    modify_amount = wizard.new_amount - wizard.fund_amount
                else:
                    modify_amount = wizard.fund_amount - wizard.new_amount

                modify_amount = fnd._convert(modify_amount, wizard.effective_date)
                # raise ValidationError(_("askdjalskdjklsa"))
                if wizard.is_add_balance:
                    move = fnd.create_payable_journal_entry(fnd, wizard.payable_account.id, wizard.effective_date, modify_amount, desc)
                    wizard.move = move
                    move.write({'pettycash_id': wizard.fund.id})
                # wizard.fund.final_balance = final_balance
                # wizard.fund.balance = final_balance
                # wizard.fund.balance = final_balance
                # Change the amount on the fund record
                fnd.change_fund_amount(wizard.new_amount)

