# -*- coding: utf-8 -*-

from datetime import datetime

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.addons import decimal_precision as dp
from odoo.tools.translate import _


class AccountPettycashFundReconcile(models.TransientModel):
    _name = 'account.pettycash.fund.reconcile'
    _desc = 'Petty Cash Fund Reconciliation Wizard'

    @api.model
    def _get_fund(self):
        fund_id = self.env.context.get('active_id', False)
        return fund_id

    @api.model
    def _get_vouchers(self):
        fund_id = self._get_fund()
        if not fund_id:
            return []
        f = self.env['account.pettycash'].browse(fund_id)
        vouchers = [(6, 0, [v.id for v in f.voucher_id if v.state == 'approved'])]   
        return vouchers

    fund = fields.Many2one('account.pettycash', required=True,
                           default=_get_fund, string="Fund")
    date = fields.Date(string="Bill Date", required=True, default=datetime.today().date())
    payable_account = fields.Many2one(
        'account.account', required=False, domain=[('user_type_id.name', '=', 'Payable')],
        help="The account used to record the payable amount to the custodian.")
    reconciled_amount = fields.Float(
        digits=dp.get_precision('Product Price'), readonly=True)
    move = fields.Many2one('account.move', readonly=True)
    #remove add a line button
    vouchers = fields.Many2many('account.pettycash.voucher.wizard', 'account_pettycash_voucher_rel', 'voucher_id', 'wizard_id', default=_get_vouchers, readonly=True)
    is_pettycash_voucher_approved = fields.Boolean('Petty Cash Voucher Approved')

    def reconcile_vouchers(self):
        PettyCash = self.env['account.pettycash']
        for wiz in self:
            total = 0.0
            total_amount = [voucher.total for voucher in wiz.vouchers]

            if sum(total_amount) > self.fund.balance:
                raise ValidationError(
                    _("Insufficient Funds! \nTotal amount want to recocile %s, but available balance is %s. " % (
                    sum(total_amount), self.fund.balance)))

            for voucher in wiz.vouchers:
                # Do not process if voucher does not belong to this fund.
                if not voucher.fund \
                        or voucher.fund.id != wiz.fund.id:
                    raise ValidationError(
                        _("Voucher (%s) does not belong to this petty cash "
                          "fund." % (voucher.name)))

                voucher.proforma_voucher()
                total += voucher.total
                voucher.move_id.write({'pettycash_id': wiz.fund.id, 'is_petty_cash_voucher': True, 'amount_total_signed': -(voucher.move_id.amount_total_signed), 'date' : wiz.date, 'invoice_date' : wiz.date})                
            wiz.reconciled_amount = total

            for voucher in wiz.fund.voucher_id:
                if voucher.state in ['rejected','cancelled']:
                    voucher.is_reconcile = True
        return
