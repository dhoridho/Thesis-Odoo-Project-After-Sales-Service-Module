# -*- coding: utf-8 -*-
#################################################################################
#
#   Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#   See LICENSE file for full copyright and licensing details.
#   License URL : <https://store.webkul.com/license.html/>
#
#################################################################################

from odoo import api, fields, models, tools, _
from odoo.tools import float_is_zero
from collections import defaultdict
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)


class InheritPosSession(models.Model):
    _inherit = "pos.session"

    def _accumulate_amounts(self, data):
        # Accumulate the amounts for each accounting lines group
        # Each dict maps `key` -> `amounts`, where `key` is the group key.
        # E.g. `combine_receivables` is derived from pos.payment records
        # in the self.order_ids with group key of the `payment_method_id`
        # field of the pos.payment record.
        def amounts(): return {'amount': 0.0, 'amount_converted': 0.0}
        def tax_amounts(): return {'amount': 0.0, 'amount_converted': 0.0,
                                   'base_amount': 0.0, 'base_amount_converted': 0.0}
        split_receivables = defaultdict(amounts)
        split_receivables_cash = defaultdict(amounts)
        combine_receivables = defaultdict(amounts)
        combine_receivables_cash = defaultdict(amounts)
        invoice_receivables = defaultdict(amounts)
        wk_invoice_receivables = defaultdict(amounts)
        wk_invoice_payment_data = []
        sales = defaultdict(amounts)
        taxes = defaultdict(tax_amounts)
        stock_expense = defaultdict(amounts)
        stock_return = defaultdict(amounts)
        stock_output = defaultdict(amounts)
        rounding_difference = {'amount': 0.0, 'amount_converted': 0.0}
        # Track the receivable lines of the invoiced orders' account moves for reconciliation
        # These receivable lines are reconciled to the corresponding invoice receivable lines
        # of this session's move_id.
        order_account_move_receivable_lines = defaultdict(
            lambda: self.env['account.move.line'])
        rounded_globally = self.company_id.tax_calculation_rounding_method == 'round_globally'
        for order in self.order_ids:
            wko_amount = 0
            # Combine pos receivable lines
            # Separate cash payments for cash reconciliation later.
            _logger.info(
                "***********split_receivables_cash*****1111***:%r", split_receivables_cash)
            for payment in order.payment_ids:
                _logger.info("*********order******:%r", payment.amount)
                wko_amount += payment.amount
                amount, date = payment.amount, payment.payment_date
                if payment.payment_method_id.split_transactions:
                    if payment.payment_method_id.is_cash_count:
                        split_receivables_cash[payment] = self._update_amounts(
                            split_receivables_cash[payment], {'amount': amount}, date)
                    else:
                        split_receivables[payment] = self._update_amounts(
                            split_receivables[payment], {'amount': amount}, date)
                else:
                    key = payment.payment_method_id
                    if payment.payment_method_id.is_cash_count:
                        combine_receivables_cash[key] = self._update_amounts(
                            combine_receivables_cash[key], {'amount': amount}, date)
                    else:
                        combine_receivables[key] = self._update_amounts(
                            combine_receivables[key], {'amount': amount}, date)
            if order.is_invoiced:
                # Combine invoice receivable lines
                f_amount = wko_amount
                key = order.partner_id.property_account_receivable_id.id
                credit_amounts = self._update_amounts({'amount': 0.0, 'amount_converted': 0.0}, {
                                                      'amount': f_amount}, order.date_order)
                wk_invoice_payment_data.append(credit_amounts)
                wk_invoice_receivables[key] = wk_invoice_payment_data
                _logger.info(
                    "*******************wk_invoice_receivables[key]*******:%r", wk_invoice_receivables[key])
                # if self.config_id.cash_rounding:
                #     invoice_receivables[key] = self._update_amounts(invoice_receivables[key], {'amount': order.amount_paid}, order.date_order)
                # else:
                #     invoice_receivables[key] = self._update_amounts(invoice_receivables[key], {'amount': order.amount_total}, order.date_order)
                # side loop to gather receivable lines by account for reconciliation
                for move_line in order.account_move.line_ids.filtered(lambda aml: aml.account_id.internal_type == 'receivable' and not aml.reconciled):
                    order_account_move_receivable_lines[move_line.account_id.id] |= move_line
            else:
                order_taxes = defaultdict(tax_amounts)
                for order_line in order.lines:
                    line = self._prepare_line(order_line)
                    # Combine sales/refund lines
                    sale_key = (
                        # account
                        line['income_account_id'],
                        # sign
                        -1 if line['amount'] < 0 else 1,
                        # for taxes
                        tuple((tax['id'], tax['account_id'], tax['tax_repartition_line_id'])
                              for tax in line['taxes']),
                        line['base_tags'],
                    )
                    sales[sale_key] = self._update_amounts(
                        sales[sale_key], {'amount': line['amount']}, line['date_order'])
                    # Combine tax lines
                    for tax in line['taxes']:
                        tax_key = (tax['account_id'], tax['tax_repartition_line_id'], tax['id'], tuple(
                            tax['tag_ids']))
                        order_taxes[tax_key] = self._update_amounts(
                            order_taxes[tax_key],
                            {'amount': tax['amount'],
                                'base_amount': tax['base']},
                            tax['date_order'],
                            round=not rounded_globally
                        )
                for tax_key, amounts in order_taxes.items():
                    if rounded_globally:
                        amounts = self._round_amounts(amounts)
                    for amount_key, amount in amounts.items():
                        taxes[tax_key][amount_key] += amount

                if self.company_id.anglo_saxon_accounting and order.picking_ids.ids:
                    # Combine stock lines
                    stock_moves = self.env['stock.move'].sudo().search([
                        ('picking_id', 'in', order.picking_ids.ids),
                        ('company_id.anglo_saxon_accounting', '=', True),
                        ('product_id.categ_id.property_valuation', '=', 'real_time')
                    ])
                    for move in stock_moves:
                        exp_key = move.product_id._get_product_accounts()[
                            'expense']
                        out_key = move.product_id.categ_id.property_stock_account_output_categ_id
                        amount = - \
                            sum(move.sudo().stock_valuation_layer_ids.mapped('value'))
                        stock_expense[exp_key] = self._update_amounts(stock_expense[exp_key], {
                                                                      'amount': amount}, move.picking_id.date, force_company_currency=True)
                        if move.location_id.usage == 'customer':
                            stock_return[out_key] = self._update_amounts(stock_return[out_key], {
                                                                         'amount': amount}, move.picking_id.date, force_company_currency=True)
                        else:
                            stock_output[out_key] = self._update_amounts(stock_output[out_key], {
                                                                         'amount': amount}, move.picking_id.date, force_company_currency=True)

                if self.config_id.cash_rounding:
                    diff = order.amount_paid - order.amount_total
                    rounding_difference = self._update_amounts(
                        rounding_difference, {'amount': diff}, order.date_order)

                # Increasing current partner's customer_rank
                order.partner_id._increase_rank('customer_rank')

        _logger.info("******combine_receivables******:%r", combine_receivables)
        _logger.info("******combine_receivable_cashs******:%r",
                     combine_receivables_cash)
        _logger.info("******split_receivables******:%r", split_receivables)
        _logger.info("******split_receivables***cash***:%r",
                     split_receivables_cash)
        # ewr
        if self.company_id.anglo_saxon_accounting:
            global_session_pickings = self.picking_ids.filtered(
                lambda p: not p.pos_order_id)
            if global_session_pickings:
                stock_moves = self.env['stock.move'].search([
                    ('picking_id', 'in', global_session_pickings.ids),
                    ('company_id.anglo_saxon_accounting', '=', True),
                    ('product_id.categ_id.property_valuation', '=', 'real_time'),
                ])
                for move in stock_moves:
                    exp_key = move.product_id._get_product_accounts()[
                        'expense']
                    out_key = move.product_id.categ_id.property_stock_account_output_categ_id
                    amount = - \
                        sum(move.stock_valuation_layer_ids.mapped('value'))
                    stock_expense[exp_key] = self._update_amounts(
                        stock_expense[exp_key], {'amount': amount}, move.picking_id.date)
                    if move.location_id.usage == 'customer':
                        stock_return[out_key] = self._update_amounts(
                            stock_return[out_key], {'amount': amount}, move.picking_id.date)
                    else:
                        stock_output[out_key] = self._update_amounts(
                            stock_output[out_key], {'amount': amount}, move.picking_id.date)
        MoveLine = self.env['account.move.line'].with_context(
            check_move_validity=False)

        data.update({
            'taxes':                               taxes,
            'sales':                               sales,
            'stock_expense':                       stock_expense,
            'split_receivables':                   split_receivables,
            'combine_receivables':                 combine_receivables,
            'split_receivables_cash':              split_receivables_cash,
            'combine_receivables_cash':            combine_receivables_cash,
            'invoice_receivables':                 invoice_receivables,
            'wk_invoice_receivables':              wk_invoice_receivables,
            'stock_return':                        stock_return,
            'stock_output':                        stock_output,
            'order_account_move_receivable_lines': order_account_move_receivable_lines,
            'rounding_difference':                 rounding_difference,
            'MoveLine':                            MoveLine
        })
        return data

    def _create_invoice_receivable_lines(self, data):
        # Create invoice receivable lines for this session's move_id.
        # Keep reference of the invoice receivable lines because
        # they are reconciled with the lines in order_account_move_receivable_lines
        MoveLine = data.get('MoveLine')
        invoice_receivables = data.get('invoice_receivables')
        receivable_account_id = False
        invoice_receivable_vals = defaultdict(list)
        invoice_receivable_lines = {}
        for receivable_account_id, amounts in data.get('wk_invoice_receivables').items():
            for item in amounts:
                invoice_receivable_vals[receivable_account_id].append(self._get_invoice_receivable_vals(
                    receivable_account_id, item['amount'], item['amount_converted']))
        # for receivable_account_id, amounts in invoice_receivables.items():
        #     test = self._get_invoice_receivable_vals(receivable_account_id, amounts['amount'], amounts['amount_converted'])
        #     invoice_receivable_vals[receivable_account_id].append(test)
        for receivable_account_id, vals in invoice_receivable_vals.items():
            invoice_receivable_lines[receivable_account_id] = MoveLine.create(
                vals)

        data.update({'invoice_receivable_lines': invoice_receivable_lines})
        return data

    def _reconcile_account_move_lines(self, data):
        # reconcile cash receivable lines
        split_cash_statement_lines = data.get('split_cash_statement_lines')
        combine_cash_statement_lines = data.get('combine_cash_statement_lines')
        split_cash_receivable_lines = data.get('split_cash_receivable_lines')
        combine_cash_receivable_lines = data.get(
            'combine_cash_receivable_lines')
        order_account_move_receivable_lines = data.get(
            'order_account_move_receivable_lines')
        invoice_receivable_lines = data.get('invoice_receivable_lines')
        stock_output_lines = data.get('stock_output_lines')

        for statement in self.statement_ids:
            if not self.config_id.cash_control:
                statement.write({'balance_end_real': statement.balance_end})
            statement.button_post()
            all_lines = (
                split_cash_statement_lines[statement].mapped('move_id.line_ids').filtered(
                    lambda aml: aml.account_id.internal_type == 'receivable')
                | combine_cash_statement_lines[statement].mapped('move_id.line_ids').filtered(lambda aml: aml.account_id.internal_type == 'receivable')
                | split_cash_receivable_lines[statement]
                | combine_cash_receivable_lines[statement]
            )
            _logger.info("***info of lines*%r****%r*****%r****%r", split_cash_statement_lines[statement].mapped('move_id.line_ids').filtered(lambda aml: aml.account_id.internal_type == 'receivable'), combine_cash_statement_lines[statement].mapped(
                'move_id.line_ids').filtered(lambda aml: aml.account_id.internal_type == 'receivable'), split_cash_receivable_lines[statement], combine_cash_receivable_lines[statement])
            accounts = all_lines.mapped('account_id')
            lines_by_account = [all_lines.filtered(
                lambda l: l.account_id == account) for account in accounts]
            for lines in lines_by_account:
                _logger.info("****Before reconcile 1*****:%r", lines)
                lines.write({'reconciled': False})
                lines.reconcile()
            # We try to validate the statement after the reconciliation is done
            # because validating the statement requires each statement line to be
            # reconciled.
            # Furthermore, if the validation failed, which is caused by unreconciled
            # cash difference statement line, we just ignore that. Leaving the statement
            # not yet validated. Manual reconciliation and validation should be made
            # by the user in the accounting app.
            try:
                statement.button_validate()
            except UserError:
                pass

        # reconcile invoice receivable lines
        for account_id in order_account_move_receivable_lines:
            _logger.info("*************111111111***********:%r", (order_account_move_receivable_lines[account_id]
                                                                  | invoice_receivable_lines.get(account_id, self.env['account.move.line'])
                                                                  ).with_context(coming_from_pos=True).read(['reconciled']))
            (order_account_move_receivable_lines[account_id]
             | invoice_receivable_lines.get(account_id, self.env['account.move.line'])
             ).write({'reconciled': False})
            _logger.info("*****Reconciling linesssS*******:%r", (order_account_move_receivable_lines[account_id]
                                                                 | invoice_receivable_lines.get(account_id, self.env['account.move.line'])
                                                                 ).with_context(coming_from_pos=True))
            _logger.info("****Before reconcile 22*****")
            (order_account_move_receivable_lines[account_id]
             | invoice_receivable_lines.get(account_id, self.env['account.move.line'])
             ).with_context(coming_from_pos=True).reconcile()

        # reconcile stock output lines
        pickings = self.picking_ids.filtered(lambda p: not p.pos_order_id)
        pickings |= self.order_ids.filtered(
            lambda o: not o.is_invoiced).mapped('picking_ids')
        stock_moves = self.env['stock.move'].search(
            [('picking_id', 'in', pickings.ids)])
        stock_account_move_lines = self.env['account.move'].search(
            [('stock_move_id', 'in', stock_moves.ids)]).mapped('line_ids')
        for account_id in stock_output_lines:
            _logger.info("*********222222222@@***********:%r", (stock_output_lines[account_id].filtered(lambda aml: not aml.reconciled)
                                                                | stock_account_move_lines.filtered(lambda aml: aml.account_id == account_id)
                                                                ).read(['reconciled']))
            _logger.info("****Before reconcile 3*****")
            (stock_output_lines[account_id].filtered(lambda aml: not aml.reconciled)
             | stock_account_move_lines.filtered(lambda aml: aml.account_id == account_id)
             ).reconcile()
        return data
