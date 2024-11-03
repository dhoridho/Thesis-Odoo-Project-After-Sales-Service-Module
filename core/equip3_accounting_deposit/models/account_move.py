
from odoo import tools, api, fields, models, _
from json import dumps
import json
from datetime import date


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _compute_payments_widget_to_reconcile_info(self):
        res = super(AccountMove, self)._compute_payments_widget_to_reconcile_info()
        
        # for move in self:
        #     if move.state != 'posted' \
        #             or move.payment_state not in ('not_paid', 'partial') \
        #             or not move.is_invoice(include_receipts=True):
        #         continue

        #     pay_term_lines = move.line_ids\
        #         .filtered(lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))

        #     domain = [
        #         ('state', '=', 'post'),
        #         ('remaining_amount', '>', 0),
        #         ('partner_id', '=', move.commercial_partner_id.id),
        #     ]
 
        #     payments_widget_vals = json.loads(move.invoice_outstanding_credits_debits_widget)
        #     if not payments_widget_vals:
        #         move.invoice_outstanding_credits_debits_widget = json.dumps(False)
        #         move.invoice_has_outstanding = False
        #         payments_widget_vals = {'outstanding': True, 'content': [], 'move_id': move.id}
        #     if move.is_inbound():
        #         deposit_ids = self.env['customer.deposit'].search(domain)
        #     else:
        #         deposit_ids = self.env['vendor.deposit'].search(domain)
        #     for deposit_move_id in deposit_ids:
        #         for line in deposit_move_id.deposit_move_id.line_ids if move.is_inbound() else deposit_move_id.move_id.line_ids:
        #             if line.account_id == deposit_move_id.deposit_account_id:
        #                 if line.currency_id == move.currency_id:
        #                     # Same foreign currency.
        #                     amount = abs(deposit_move_id.remaining_amount)
        #                 else:
        #                     # Different foreign currencies.
        #                     amount = move.company_currency_id._convert(
        #                         abs(deposit_move_id.remaining_amount),
        #                         move.currency_id,
        #                         move.company_id,
        #                         line.date,
        #                     )
        #                 if move.currency_id.is_zero(amount):
        #                     continue

        #                 payments_widget_vals['content'].append({
        #                     'journal_name': line.ref or line.move_id.name,
        #                     'amount': amount,
        #                     'currency': move.currency_id.symbol,
        #                     'id': line.id,
        #                     'move_id': line.move_id.id,
        #                     'position': move.currency_id.position,
        #                     'digits': [69, move.currency_id.decimal_places],
        #                     'payment_date': fields.Date.to_string(line.date),
        #                 })               
        #     if not payments_widget_vals['content']:
        #         continue
        #     move.invoice_outstanding_credits_debits_widget = json.dumps(payments_widget_vals)
        #     move.invoice_has_outstanding = True


        for move in self:
            move.invoice_outstanding_credits_debits_widget = json.dumps(False)
            move.invoice_has_outstanding = False

            if move.state != 'posted' \
                    or move.payment_state not in ('not_paid', 'partial') \
                    or not move.is_invoice(include_receipts=True):
                continue

            pay_term_lines = move.line_ids\
                .filtered(lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))

            domain = [
                ('account_id', 'in', pay_term_lines.account_id.ids),
                ('parent_state', '=', 'posted'),
                ('partner_id', '=', move.commercial_partner_id.id),
                ('reconciled', '=', False),
                '|', ('amount_residual', '!=', 0.0), ('amount_residual_currency', '!=', 0.0),
            ]

            payments_widget_vals = {'outstanding': True, 'content': [], 'move_id': move.id}

            if move.is_inbound():
                domain.append(('balance', '<', 0.0))
                payments_widget_vals['title'] = _('Outstanding credits')
            else:
                domain.append(('balance', '>', 0.0))
                payments_widget_vals['title'] = _('Outstanding debits')

            for line in self.env['account.move.line'].search(domain):
        
                if line.currency_id == move.currency_id:
                    amount = abs(line.amount_residual_currency)
                else:
                    amount = move.company_currency_id._convert(
                        abs(line.amount_residual),
                        move.currency_id,
                        move.company_id,
                        line.date,
                    )

                if move.currency_id.is_zero(amount):
                    continue

                payments_widget_vals['content'].append({
                    'journal_name': line.ref or line.move_id.name,
                    'amount': amount,
                    'currency': move.currency_id.symbol,
                    'id': line.id,
                    'move_id': line.move_id.id,
                    'position': move.currency_id.position,
                    'digits': [69, move.currency_id.decimal_places],
                    'payment_date': fields.Date.to_string(line.date),
                })

            deposit_domain = [
                ('partner_id', '=', move.partner_id.id),
                ('company_id', '=', move.company_id.id),
                ('branch_id', '=', move.branch_id.id),
                ('state', '=', 'post'),
                ('remaining_amount', '>', 0),
                ('currency_id', '=', move.currency_id.id),
            ]
            if move.move_type == "out_invoice":
                customer_deposit_ids = self.env['customer.deposit'].search(deposit_domain)
                for deposit in customer_deposit_ids:
                    move_line = deposit.deposit_move_id.line_ids.filtered(lambda r: r.debit > 0)
                    if deposit.deposit_move_id.id :
                        payments_widget_vals['content'].append({
                            'journal_name': deposit.deposit_move_id.ref or deposit.deposit_move_id.name,
                            'amount': deposit.remaining_amount,
                            'currency': deposit.currency_id.symbol,
                            'id': move_line.id,
                            'move_id': deposit.deposit_move_id.id,
                            'position': deposit.deposit_move_id.currency_id.position,
                            'digits': [69, deposit.deposit_move_id.currency_id.decimal_places],
                            'payment_date': fields.Date.to_string(move_line.date),
                        })
            elif move.move_type == "in_invoice":
                vendor_deposit_ids = self.env['vendor.deposit'].search(deposit_domain)
                for deposit in vendor_deposit_ids:
                    move_line = deposit.move_id.line_ids.filtered(lambda r: r.credit > 0)
                    if deposit.move_id.id :
                        payments_widget_vals['content'].append({
                            'journal_name': deposit.move_id.ref or deposit.move_id.name,
                            'amount': deposit.remaining_amount,
                            'currency': deposit.currency_id.symbol,
                            'id': move_line.id,
                            'move_id': deposit.move_id.id,
                            'position': deposit.move_id.currency_id.position,
                            'digits': [69, deposit.move_id.currency_id.decimal_places],
                            'payment_date': fields.Date.to_string(move_line.date),
                        })


            if not payments_widget_vals['content']:
                continue

            move.invoice_outstanding_credits_debits_widget = json.dumps(payments_widget_vals)
            move.invoice_has_outstanding = True
        return res

    def js_assign_outstanding_line(self, line_id):
        self.ensure_one()
        lines = self.env['account.move.line'].browse(line_id)
        if lines.customer_deposit_id:
            if self.amount_residual > lines.customer_deposit_id.remaining_amount:
                allocation_amount = lines.customer_deposit_id.remaining_amount
            else:
                allocation_amount = self.amount_residual
            reconcile_deposit_id = self.env['account.deposit.reconcile'].create({
                                    'date': date.today(),
                                    'allocation_line_ids': [(0, 0, {
                                        'invoice_id': self.id,
                                        'allocation_amount': allocation_amount
                                    })]
                                })
            reconcile_deposit_id.with_context({'active_id': lines.customer_deposit_id.id}).reconcile_deposit()
        elif lines.vendor_deposit_id:
            if self.amount_residual > lines.vendor_deposit_id.remaining_amount:
                allocation_amount = lines.vendor_deposit_id.remaining_amount
            else:
                allocation_amount = self.amount_residual
            reconcile_deposit_id = self.env['account.vendor.deposit.reconcile'].create({
                                    'date': date.today(),
                                    'allocation_line_ids': [(0, 0, {
                                        'invoice_id': self.id,
                                        'allocation_amount': allocation_amount
                                    })]
                                })
            reconcile_deposit_id.with_context({'active_id': lines.vendor_deposit_id.id}).reconcile_deposit()            

        return super(AccountMove, self).js_assign_outstanding_line(line_id)

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    customer_deposit_id = fields.Many2one('customer.deposit', string="Customer Deposit")
    vendor_deposit_id = fields.Many2one('vendor.deposit', string="Vendor Deposit")
