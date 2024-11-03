from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountPayments(models.Model):
    _inherit = 'account.payment'

    def _prepare_move_line_default_vals(self, write_off_line_vals=None):
        self.ensure_one()
        if self.active_manual_currency_rate:
            if self.apply_manual_currency_exchange:
                write_off_line_vals = write_off_line_vals or {}

                if not self.journal_id.payment_debit_account_id or not self.journal_id.payment_credit_account_id:
                    raise UserError(_(
                        "You can't create a new payment without an outstanding payments/receipts account set on the %s journal.",
                        self.journal_id.display_name))

                # Compute amounts.
                write_off_amount = write_off_line_vals.get('amount', 0.0)
                if self.payment_type == 'inbound':
                    # Receive money.
                    counterpart_amount = -self.amount
                    write_off_amount *= -1
                elif self.payment_type == 'outbound':
                    # Send money.
                    counterpart_amount = self.amount
                else:
                    counterpart_amount = 0.0
                    write_off_amount = 0.0

                origin_inv = self.env['account.move'].search([('name','=',self.ref)], limit=1)
                
                if self.active_manual_currency_rate:
                    if self.apply_manual_currency_exchange:
                        balance = counterpart_amount / self.manual_currency_exchange_rate
                        write_off_balance = write_off_amount / self.manual_currency_exchange_rate
                    else:
                        balance = self.currency_id._convert(counterpart_amount, self.company_id.currency_id, self.company_id, self.date or origin_inv.date)
                        write_off_balance = self.currency_id._convert(write_off_amount, self.company_id.currency_id, self.company_id, self.date or origin_inv.date)
                else:
                    balance = self.currency_id._convert(counterpart_amount, self.company_id.currency_id, self.company_id, self.date or origin_inv.date)
                    write_off_balance = self.currency_id._convert(write_off_amount, self.company_id.currency_id, self.company_id, self.date or origin_inv.date)

                counterpart_amount_currency = counterpart_amount
                write_off_amount_currency = write_off_amount
                currency_id = self.currency_id.id

                if self.is_internal_transfer:
                    if self.payment_type == 'inbound':
                        liquidity_line_name = _('Transfer to %s', self.journal_id.name)
                    else: # payment.payment_type == 'outbound':
                        liquidity_line_name = _('Transfer from %s', self.journal_id.name)
                else:
                    liquidity_line_name = self.payment_reference

                # Compute a default label to set on the journal items.

                payment_display_name = {
                    'outbound-customer': _("Customer Reimbursement"),
                    'inbound-customer': _("Customer Payment"),
                    'outbound-supplier': _("Vendor Payment"),
                    'inbound-supplier': _("Vendor Reimbursement"),
                }

                default_line_name = self.env['account.move.line']._get_default_line_name(
                    _("Internal Transfer") if self.is_internal_transfer else payment_display_name['%s-%s' % (self.payment_type, self.partner_type)],
                    self.amount,
                    self.currency_id,
                    self.date,
                    partner=self.partner_id,
                )

                line_vals_list = [
                    # Liquidity line.
                    {
                        'name': liquidity_line_name or default_line_name,
                        'date_maturity': self.date,
                        'amount_currency': -counterpart_amount_currency,
                        'currency_id': currency_id,
                        'debit': balance < 0.0 and -balance or 0.0,
                        'credit': balance > 0.0 and balance or 0.0,
                        'partner_id': self.partner_id.id,
                        'account_id': self.journal_id.payment_debit_account_id.id if balance < 0.0 else self.journal_id.payment_credit_account_id.id,
                    },
                    # Receivable / Payable.
                    {
                        'name': self.payment_reference or default_line_name,
                        'date_maturity': self.date,
                        'amount_currency': counterpart_amount_currency + write_off_amount_currency if currency_id else 0.0,
                        'currency_id': currency_id,
                        'debit': balance + write_off_balance > 0.0 and balance + write_off_balance or 0.0,
                        'credit': balance + write_off_balance < 0.0 and -balance - write_off_balance or 0.0,
                        'partner_id': self.partner_id.id,
                        'account_id': self.destination_account_id.id,
                    },
                ]
                if write_off_balance:
                    # Write-off line.
                    line_vals_list.append({
                        'name': write_off_line_vals.get('name') or default_line_name,
                        'amount_currency': -write_off_amount_currency,
                        'currency_id': currency_id,
                        'debit': write_off_balance < 0.0 and -write_off_balance or 0.0,
                        'credit': write_off_balance > 0.0 and write_off_balance or 0.0,
                        'partner_id': self.partner_id.id,
                        'account_id': write_off_line_vals.get('account_id'),
                    })
                return line_vals_list        
        res = super(AccountPayments, self)._prepare_move_line_default_vals(write_off_line_vals)
        return res

    def action_post(self):
        for rec in self:
            if rec.move_id.period_id.id == False:
                raise UserError("Please define the Fiscal Year and Period first before post any Journal Entry")
            elif rec.move_id.period_id.id != False and rec.move_id.period_id.state == 'done':
                raise UserError("You can not post any journal entry already on Closed Period")
        super(AccountPayments, self).action_post()
        active_ids = self._context.get('active_ids')
        if active_ids:
            for invoice in self.env['account.move'].browse(active_ids):
                if invoice.state == 'posted' :
                    existing_payment_ids = invoice.invoice_payment_ids.ids
                    new_payment_ids = self.ids
                    all_payment_ids = list(set(existing_payment_ids + new_payment_ids))
                    invoice.write({'invoice_payment_ids': [(6, 0, all_payment_ids)]})
                    # print('invoice_payment_ids', invoice.invoice_payment_ids.ids)

            for payments in self:
                if payments.move_id.state == 'posted' and payments.state != 'posted':
                    payments.write({'state': payments.move_id.state})
                    if active_ids:
                        for active_id in active_ids:
                            payments.write({'invoice_origin_ids': [(4, active_id)]})

        for payments in self:
            if payments.move_id.state == 'posted' and payments.state != 'posted':
                payments.write({'state' : payments.move_id.state})

        
                



    def action_cancel(self):
        super(AccountPayments, self).action_cancel()
        for payments in self:
            if payments.move_id.state == 'cancel' and payments.state != 'cancel':
                payments.write({'state' : payments.move_id.state})

    def action_draft(self):
        super(AccountPayments, self).action_draft()
        for payments in self:
            if payments.move_id.state == 'draft' and payments.state != 'draft':
                payments.write({'state' : payments.move_id.state})