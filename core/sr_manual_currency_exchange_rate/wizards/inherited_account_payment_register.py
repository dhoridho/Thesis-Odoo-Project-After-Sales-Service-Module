# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) Sitaram Solutions (<https://sitaramsolutions.in/>).
#
#    For Module Support : info@sitaramsolutions.in  or Skype : contact.hiren1188
#
##############################################################################
 
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class srAccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    apply_manual_currency_exchange = fields.Boolean(string='Apply Manual Currency Exchange')
    manual_currency_exchange_rate = fields.Float(string='Manual Currency Exchange Rate')
    active_manual_currency_rate = fields.Boolean('active Manual Currency', default=False)

    @api.onchange('currency_id')
    def onchange_currency_id(self):
        if self.currency_id:
            if self.company_id.currency_id != self.currency_id:
                self.active_manual_currency_rate = True
            else:
                self.active_manual_currency_rate = False
        else:
            self.active_manual_currency_rate = False
            
    @api.model
    def default_get(self, fields):
        result = super(srAccountPaymentRegister, self).default_get(fields)
        move_id = self.env['account.move'].browse(self._context.get('active_ids')).filtered(lambda move: move.is_invoice(include_receipts=True))
            # raise UserError("The following invoices can not be paid in the same payment. Please check the rate of the invoices and try again." + notif_field)
        for move in move_id:
            if 'apply_manual_currency_exchange' in move:
                result.update({
                    'apply_manual_currency_exchange': move.apply_manual_currency_exchange,
                    'manual_currency_exchange_rate': move.manual_currency_exchange_rate,
                })
            else:
                result.write({
                    'apply_manual_currency_exchange': False,
                    'manual_currency_exchange_rate': 0,
                })
            break
        return result

    @api.depends('source_amount', 'source_amount_currency', 'source_currency_id', 'company_id', 'currency_id', 'payment_date','apply_manual_currency_exchange','manual_currency_exchange_rate')
    def _compute_amount(self):
        for wizard in self:
            if wizard.source_currency_id == wizard.currency_id:
                # Same currency.
                wizard.amount = wizard.source_amount_currency
            elif wizard.currency_id == wizard.company_id.currency_id:
                # Payment expressed on the company's currency.
                wizard.amount = wizard.source_amount
            else:
                # Foreign currency on payment different than the one set on the journal entries.
                if wizard.apply_manual_currency_exchange:
                    amount_payment_currency = wizard.source_amount * wizard.manual_currency_exchange_rate
                else:
                    amount_payment_currency = wizard.company_id.currency_id._convert(wizard.source_amount, wizard.currency_id, wizard.company_id, wizard.payment_date)
                wizard.amount = amount_payment_currency

    @api.depends('amount')
    def _compute_payment_difference(self):
        for wizard in self:
            if wizard.source_currency_id == wizard.currency_id:
                # Same currency.
                wizard.payment_difference = wizard.source_amount_currency - wizard.amount
            elif wizard.currency_id == wizard.company_id.currency_id:
                # Payment expressed on the company's currency.
                wizard.payment_difference = wizard.source_amount - wizard.amount
            else:
                # Foreign currency on payment different than the one set on the journal entries.
                amount_payment_currency = wizard.company_id.currency_id.with_context(
                    manual_rate=self.manual_currency_exchange_rate,
                    active_manutal_currency = self.apply_manual_currency_exchange,
                )._convert(wizard.source_amount, wizard.currency_id, wizard.company_id, wizard.payment_date)
                wizard.payment_difference = amount_payment_currency - wizard.amount

    def _create_payment_vals_from_wizard(self):
        payment_vals = {
            'date': self.payment_date,
            'amount': self.amount,
            'payment_type': self.payment_type,
            'partner_type': self.partner_type,
            'ref': self.communication,
            'journal_id': self.journal_id.id,
            'currency_id': self.currency_id.id,
            'partner_id': self.partner_id.id,
            'partner_bank_id': self.partner_bank_id.id,
            'payment_method_id': self.payment_method_id.id,
            'destination_account_id': self.line_ids[0].account_id.id,
            'apply_manual_currency_exchange':self.apply_manual_currency_exchange,
            'manual_currency_exchange_rate':self.manual_currency_exchange_rate,
            'active_manual_currency_rate':self.active_manual_currency_rate
        }

        if not self.currency_id.is_zero(self.payment_difference) and self.payment_difference_handling == 'reconcile':
            payment_vals['write_off_line_vals'] = {
                'name': self.writeoff_label,
                'amount': self.payment_difference,
                'account_id': self.writeoff_account_id.id,
            }
        return payment_vals

    def _create_payments(self):
        self.ensure_one()
        batches = self._get_batches()
        edit_mode = self.can_edit_wizard and (len(batches[0]['lines']) == 1 or self.group_payment)
        to_reconcile = []
        if edit_mode:
            payment_vals = self._create_payment_vals_from_wizard()
            line_ids = []

            # Add the bank account move line
            line_ids.append((0, 0, {
                'name': 'Customer Payment ' + self.currency_id.name + ' - ' + str(self.amount) + ' - ' + self.partner_id.name + ' - ' + str(self.payment_date),
                'account_id': self.journal_id.default_account_id.id,
                'debit': self.amount,
                'credit': 0.0,
            }))

            # Add the difference account move line
            for line in self.difference_ids:
                line_ids.append((0, 0, {
                    'name': 'Difference Account ' + ' -  ' + line.account_id.name,
                    'account_id': line.account_id.id,
                    'debit': 0.0,
                    'credit': line.payment_amount,
                }))

            # Add the invoice account move line
            for line in self.line_ids:
                line_ids.append((0, 0, {
                    'name': 'Invoice Payment ' + self.currency_id.name + ' - ' + str(line.amount_currency) + ' - ' + line.partner_id.name + ' - ' + str(self.payment_date),
                    'account_id': line.account_id.id,
                    'debit': 0.0,
                    'credit': line.amount_currency,
                }))

            # Create the journal entry for the payment
            journal_entry_vals = {
                'date': self.payment_date,
                'ref': self.communication,
                'journal_id': self.journal_id.id,
                'line_ids': line_ids,
            }
            move_id_obj = self.env['account.move'].create(journal_entry_vals)
            if self.difference_ids:
                payment_vals.update({'move_id': move_id_obj.id})
                
            payment_vals_list = [payment_vals]
            to_reconcile.append(batches[0]['lines'])
        else:
            # Don't group payments: Create one batch per move.
            if not self.group_payment:
                new_batches = []
                for batch_result in batches:
                    for line in batch_result['lines']:
                        new_batches.append({
                            **batch_result,
                            'lines': line,
                        })
                batches = new_batches

            payment_vals_list = []
            for batch_result in batches:
                payment_vals_list.append(self._create_payment_vals_from_batch(batch_result))
                to_reconcile.append(batch_result['lines'])


        payments = self.env['account.payment'].create(payment_vals_list)

        # If payments are made using a currency different than the source one, ensure the balance match exactly in
        # order to fully paid the source journal items.
        # For example, suppose a new currency B having a rate 100:1 regarding the company currency A.
        # If you try to pay 12.15A using 0.12B, the computed balance will be 12.00A for the payment instead of 12.15A.
        if edit_mode:
            for payment, lines in zip(payments, to_reconcile):
                # Batches are made using the same currency so making 'lines.currency_id' is ok.
                if payment.currency_id != lines.currency_id:
                    liquidity_lines, counterpart_lines, writeoff_lines = payment._seek_for_lines()
                    source_balance = abs(sum(lines.mapped('amount_residual')))
                    payment_rate = liquidity_lines[0].amount_currency / liquidity_lines[0].balance
                    source_balance_converted = abs(source_balance) * payment_rate
                    # Translate the balance into the payment currency is order to be able to compare them.
                    # In case in both have the same value (12.15 * 0.01 ~= 0.12 in our example), it means the user
                    # attempt to fully paid the source lines and then, we need to manually fix them to get a perfect
                    # match.
                    payment_balance = abs(sum(counterpart_lines.mapped('balance')))
                    payment_amount_currency = abs(sum(counterpart_lines.mapped('amount_currency')))
                    if not payment.currency_id.is_zero(source_balance_converted - payment_amount_currency):
                        continue

                    delta_balance = source_balance - payment_balance

                    # Balance are already the same.
                    if self.company_currency_id.is_zero(delta_balance):
                        continue

                    # Fix the balance but make sure to peek the liquidity and counterpart lines first.
                    debit_lines = (liquidity_lines + counterpart_lines).filtered('debit')
                    credit_lines = (liquidity_lines + counterpart_lines).filtered('credit')

                    payment.move_id.write({'line_ids': [
                        (1, debit_lines[0].id, {'debit': debit_lines[0].debit + delta_balance}),
                        (1, credit_lines[0].id, {'credit': credit_lines[0].credit + delta_balance}),
                    ]})

        if self.difference_ids:
            for line in payments.move_id.line_ids:
                if line.account_id == self.line_ids.account_id:
                    line.write({'debit': 0.0, 'credit': self.source_amount})
                for diff_line in self.difference_ids:
                    if line.account_id == diff_line.account_id:
                        line.write({'debit': 0.0, 'credit': diff_line.payment_amount})
                    

        payments.action_post()

        domain = [('account_internal_type', 'in', ('receivable', 'payable')), ('reconciled', '=', False)]
        for payment, lines in zip(payments, to_reconcile):

            # When using the payment tokens, the payment could not be posted at this point (e.g. the transaction failed)
            # and then, we can't perform the reconciliation.
            if payment.state != 'posted':
                continue

            payment_lines = payment.line_ids.filtered_domain(domain)
            for account in payment_lines.account_id:
                (payment_lines + lines)\
                    .filtered_domain([('account_id', '=', account.id), ('reconciled', '=', False)])\
                    .reconcile()

        return payments