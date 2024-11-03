import logging
import math
import re
import time
import traceback
from lxml import etree
from json import dumps


from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError
from datetime import date, timedelta
import json

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    current_rate = fields.Float(string="Current Rate", default=lambda self: self.env.company.currency_id.rate, digits=(12, 12), readonly=True)
    is_company_curr = fields.Boolean(default=False)
    current_inverse_rate = fields.Float(string='Current Inverse Rate', default=lambda self: self.env.company.currency_id.conversion, readonly=True)
    inverse_rate_visible = fields.Boolean(default=False)
    # amount_residual = fields.Monetary(string='Amount Due', compute='_compute_amount_residual', store=True, currency_field='company_currency_id')
    tax_rate = fields.Float(string='Tax Rate', digits=(12, 12), readonly=True)
    taxes_base_price = fields.Float(string='Taxes Base Price', digits=(12, 12), readonly=True, related='amount_untaxed')
    sales_times_tax_rate = fields.Float('Taxes', store=True, readonly=True, digits=(12, 12), compute='_compute_amount_sales_times_tax_rate')
    tax_applies_on = fields.Char(compute='_compute_tax_applies_on', string="Tax Applies to")
    exchange_ids = fields.Many2one('account.move', check_company=True, string='Journal Exchange')
    invoice_payment_ids = fields.Many2many('account.payment', 'account_move_payment_rel', 'account_move_id', 'payment_id', string='Payments', copy=False)

    
    def action_post(self):    
        result = super(AccountMove, self).action_post()
        for rec in self:
            if rec.purchase_order_ids:
                for purchase_order_id in rec.purchase_order_ids:
                    picking_ids = self.env['stock.picking'].search([('origin','ilike',purchase_order_id.name)])
                    for picking_id in picking_ids:
                        picking_id.check_data_move(picking_id)
        return result


    def _compute_tax_applies_on(self):
        for rec in self:
            tax_information = False
            res_config = self.company_id.tax_discount_policy or False
        
            if res_config:
                if res_config == 'untax':
                    tax_information = 'After Discount'
                else:
                    tax_information = 'Before Discount'
            rec.tax_applies_on = tax_information



    def _recompute_tax_lines(self, recompute_tax_base_amount=False):
        self.ensure_one()
        # company_id = self.env.context.get("company_id") or self.env.company.id
        # company_obj = self.env['res.company'].browse(company_id)
        
        if self.apply_manual_currency_exchange and self.manual_currency_exchange_inverse_rate <= 0.0:
            raise UserError(_('Inverse rate must be greater than 0'))

        
        # if not company_obj.is_taxes_rate:
        #     super(AccountMove, self)._recompute_tax_lines(recompute_tax_base_amount)
        # else:
        in_draft_mode = self != self._origin

        def _serialize_tax_grouping_key(grouping_dict):
            return '-'.join(str(v) for v in grouping_dict.values())

        def _compute_base_line_taxes(base_line):
            move = base_line.move_id
            sign = -1 if move.is_inbound() else 1
            res_config = self.company_id.tax_discount_policy or False
            disc = 0
            if res_config == 'untax':
                if base_line.discount_method and base_line.discount_amount:
                    if base_line.discount_method == 'per':
                        disc =  sign * (base_line.price_unit) * (base_line.discount_amount/100)
                    else:
                        disc =  sign * (base_line.discount_amount / base_line.quantity)
            elif res_config == 'tax':
                disc = 0

            if move.is_invoice(include_receipts=True):
                handle_price_include = True
                quantity = base_line.quantity
                is_refund = move.move_type in ('out_refund', 'in_refund')
                price_unit_wo_discount = ((sign * base_line.price_unit) - disc)
            else:
                handle_price_include = False
                quantity = 1.0
                tax_type = base_line.tax_ids[0].type_tax_use if base_line.tax_ids else None
                is_refund = (tax_type == 'sale' and base_line.debit) or (tax_type == 'purchase' and base_line.credit)
                price_unit_wo_discount = ((base_line.balance - disc) * base_line.quantity)

            balance_taxes_res = base_line.tax_ids._origin.compute_all(price_unit_wo_discount,
                                                                      currency=base_line.currency_id,
                                                                      quantity=quantity,
                                                                      product=base_line.product_id,
                                                                      partner=base_line.partner_id,
                                                                      is_refund=is_refund,
                                                                      handle_price_include=handle_price_include,
                                                                      )
            price_taxes_include = 0
            all_taxes = 0
            for x in balance_taxes_res['taxes']:
                all_taxes = all_taxes + x['amount']
                if x['price_include']:
                    price_taxes_include = price_taxes_include + x['amount']
            if move.move_type == 'entry':
                repartition_field = is_refund and 'refund_repartition_line_ids' or 'invoice_repartition_line_ids'
                repartition_tags = base_line.tax_ids.mapped(repartition_field).filtered(lambda x: x.repartition_type == 'base').tag_ids
                tags_need_inversion = (tax_type == 'sale' and not is_refund) or (tax_type == 'purchase' and is_refund)
                if tags_need_inversion:
                    balance_taxes_res['base_tags'] = base_line._revert_signed_tags(repartition_tags).ids
                    for tax_res in balance_taxes_res['taxes']:
                        tax_res['tag_ids'] = base_line._revert_signed_tags(
                            self.env['account.account.tag'].browse(tax_res['tag_ids'])).ids
            return balance_taxes_res

        taxes_map = {}
        to_remove = self.env['account.move.line']
        for line in self.line_ids.filtered('tax_repartition_line_id'):
            grouping_dict = self._get_tax_grouping_key_from_tax_line(line)
            grouping_key = _serialize_tax_grouping_key(grouping_dict)
            if grouping_key in taxes_map:
                to_remove += line
            else:
                taxes_map[grouping_key] = {
                                            'tax_line': line,
                                            'amount': 0.0,
                                            'tax_base_amount': 0.0,
                                            'grouping_dict': False,
                                          }
        self.line_ids -= to_remove
        # ==== Mount base lines ====
        for line in self.line_ids.filtered(lambda line: not line.tax_repartition_line_id):
            # Don't call compute_all if there is no tax.
            if not line.tax_ids:
                line.tax_tag_ids = [(5, 0, 0)]
                continue
            compute_all_vals = _compute_base_line_taxes(line)
            # Assign tags on base line
            line.tax_tag_ids = compute_all_vals['base_tags']
            tax_exigible = True
            for tax_vals in compute_all_vals['taxes']:
                grouping_dict = self._get_tax_grouping_key_from_base_line(line, tax_vals)
                grouping_key = _serialize_tax_grouping_key(grouping_dict)
                tax_repartition_line = self.env['account.tax.repartition.line'].browse(tax_vals['tax_repartition_line_id'])
                tax = tax_repartition_line.invoice_tax_id or tax_repartition_line.refund_tax_id
                if tax.tax_exigibility == 'on_payment':
                    tax_exigible = False
                taxes_map_entry = taxes_map.setdefault(grouping_key, {
                                                                        'tax_line': None,
                                                                        'amount': 0.0,
                                                                        'tax_base_amount': 0.0,
                                                                        'grouping_dict': False,
                                                                      })
                if self.discount_type == 'global':
                    if line.quantity:
                        taxes_map_entry['amount'] += tax_vals['amount'] / line.quantity * line.quantity
                else:
                    taxes_map_entry['amount'] += tax_vals['amount']
                taxes_map_entry['tax_base_amount'] += tax_vals['base']
                taxes_map_entry['grouping_dict'] = grouping_dict
                line.tax_exigible = tax_exigible
        
        date = self.date
        if self.ref:
            if self.move_type in ('out_refund', 'in_refund'):
                name_inv = re.sub('Reversal|of|:|\s*', '', self.ref)
                inv_id = self.env['account.move'].search([('name', '=', name_inv)])
                if inv_id:
                    date = inv_id.invoice_date

        for taxes_map_entry in taxes_map.values():
            # The tax line is no longer used in any base lines, drop it.
            if taxes_map_entry['tax_line'] and not taxes_map_entry['grouping_dict']:
                self.line_ids -= taxes_map_entry['tax_line']
                continue
            currency = self.env['res.currency'].browse(taxes_map_entry['grouping_dict']['currency_id'])
            # Don't create tax lines with zero balance.
            if currency.is_zero(taxes_map_entry['amount']):
                if taxes_map_entry['tax_line']:
                    self.line_ids -= taxes_map_entry['tax_line']
                continue
            tax_base_amount = (-1 if self.is_inbound() else 1) * taxes_map_entry['tax_base_amount']
            # tax_base_amount field is expressed using the company currency.

            if self.apply_manual_currency_exchange:
                tax_base_amount = tax_base_amount / self.manual_currency_exchange_rate
            else:
                tax_base_amount = currency._convert(tax_base_amount, self.company_currency_id, self.company_id, date or fields.Date.context_today(self),is_tax=True)

            # Recompute only the tax_base_amount.
            if taxes_map_entry['tax_line'] and recompute_tax_base_amount:
                taxes_map_entry['tax_line'].tax_base_amount = tax_base_amount
                continue

            if self.apply_manual_currency_exchange:
                balance = taxes_map_entry['amount'] / self.manual_currency_exchange_rate
            else:
                balance = currency._convert(taxes_map_entry['amount'],
                                            self.journal_id.company_id.currency_id,
                                            self.journal_id.company_id,
                                            date or fields.Date.context_today(self),
                                            is_tax=True
                                            )

            to_write_on_line = { 'amount_currency': taxes_map_entry['amount'],
                                 'currency_id': taxes_map_entry['grouping_dict']['currency_id'],
                                 'debit': balance > 0.0 and balance or 0.0,
                                 'credit': balance < 0.0 and -balance or 0.0,
                                 'tax_base_amount': tax_base_amount,
                               }
            if taxes_map_entry['tax_line']:
                # Update an existing tax line.
                taxes_map_entry['tax_line'].update(to_write_on_line)
            else:
                create_method = in_draft_mode and self.env['account.move.line'].new or self.env['account.move.line'].create
                tax_repartition_line_id = taxes_map_entry['grouping_dict']['tax_repartition_line_id']
                tax_repartition_line = self.env['account.tax.repartition.line'].browse(tax_repartition_line_id)
                tax = tax_repartition_line.invoice_tax_id or tax_repartition_line.refund_tax_id
                cek = {
                            **to_write_on_line,
                            'name': tax.name,
                            'move_id': self.id,
                            'partner_id': line.partner_id.id,
                            'company_id': line.company_id.id,
                            'company_currency_id': line.company_currency_id.id,
                            'tax_base_amount': tax_base_amount,
                            'exclude_from_invoice_tab': True,
                            'tax_exigible': tax.tax_exigibility == 'on_invoice',
                            **taxes_map_entry['grouping_dict'],
                        }

                # is_taxline_exist = False
                # for line2 in self.line_ids:
                #     if line2.name == tax.name:
                #         is_taxline_exist = True
                #         break

                # if not is_taxline_exist:
                taxes_map_entry['tax_line'] = create_method({
                                                                **to_write_on_line,
                                                                'name': tax.name,
                                                                'move_id': self.id,
                                                                'partner_id': line.partner_id.id,
                                                                'company_id': line.company_id.id,
                                                                'company_currency_id': line.company_currency_id.id,
                                                                'tax_base_amount': tax_base_amount,
                                                                'exclude_from_invoice_tab': True,
                                                                'tax_exigible': tax.tax_exigibility == 'on_invoice',
                                                                **taxes_map_entry['grouping_dict'],
                                                                'analytic_tag_ids': [(6, 0, self.analytic_group_ids._origin.ids)],
                                                            })
            if in_draft_mode and taxes_map_entry['tax_line']:
                taxes_map_entry['tax_line'].update(taxes_map_entry['tax_line']._get_fields_onchange_balance(force_computation=True))  

    
    
    @api.onchange('invoice_date', 'currency_id')
    def _compute_current_rate(self):
        self.current_rate = self.env.company.currency_id.rate
        if self.invoice_date:
            self.date = self.invoice_date
            curr = self.env['res.currency.rate'].search(['&',('name', '<=', self.invoice_date),('currency_id', '=', self.currency_id.id)], limit=1)
            if curr:
                self.current_rate = curr[0].rate
            self._onchange_currency()
            self._recompute_dynamic_lines(recompute_all_taxes=True)

    @api.onchange('currency_id')
    def _hide_current_rate(self):
        if self.currency_id == self.env.company.currency_id:
            self.is_company_curr = True
            self.inverse_rate_visible = False
        else:
            self.is_company_curr = False
            if self.env.company.is_inverse_rate == True:
                self.inverse_rate_visible = True
            else:
                self.inverse_rate_visible = False

    @api.onchange('invoice_date', 'currency_id')
    def _inverse_rate(self):
        if self.current_rate:
            curr = self.env['res.currency.rate'].search(['&',('name', '<=', self.invoice_date),('currency_id', '=', self.currency_id.id)], limit=1)
            if curr:
                self.current_inverse_rate = curr[0].conversion
            # self.current_inverse_rate = 1 / self.current_rate

    #================ Currency Revaluation ===============
    def button_revaluation(self):
        action = self.env['ir.actions.act_window']._for_xml_id('equip3_accounting_multicurrency.currency_invoice_revaluation_wizard_action')
        return action

    def button_view_revaluation(self):      
        return {
                'name':  _('Currency Revaluation'),
                'type': 'ir.actions.act_window',
                'view_mode': 'tree,kanban,form',
                'res_model': 'account.move',
                'views_id': self.env.ref('account.view_move_tree').id,
                'domain': [('currency_revaluation_ref_id' ,'=', self.id)],
                'context' : {'default_move_type': 'entry'}
            }

    def button_view_exchange_journal(self):      
        return {
                'name':  _('Journal Exchange'),
                'type': 'ir.actions.act_window',
                'view_mode': 'tree,kanban,form',
                'res_model': 'account.move',
                'views_id': self.env.ref('account.view_move_tree').id,
                'domain': [('id' ,'=', self.exchange_ids.id)],
                'context' : {'default_move_type': 'entry', 'move_type': 'entry'}
            }

    

    @api.depends(
        'line_ids.matched_debit_ids.debit_move_id.move_id.payment_id.is_matched',
        'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual',
        'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual_currency',
        'line_ids.matched_credit_ids.credit_move_id.move_id.payment_id.is_matched',
        'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual',
        'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual_currency',
        'line_ids.debit',
        'line_ids.credit',
        'line_ids.currency_id',
        'line_ids.amount_currency',
        'line_ids.amount_residual',
        'line_ids.amount_residual_currency',
        'line_ids.payment_id.state',
        'line_ids.full_reconcile_id')
    def _compute_amount_sales_times_tax_rate(self):
        # res = super(AccountMove, self)._compute_amount()
        for rec in self:
            if rec.amount_untaxed:
                # rec.taxes_base_price = rec.amount_untaxed
                if rec.tax_rate > 0:
                    rec.sales_times_tax_rate = rec.amount_untaxed / rec.tax_rate
                else:
                    rec.sales_times_tax_rate = 0

    @api.onchange('invoice_date', 'currency_id')
    def _tax_rate(self):
        for rec in self:
            rec.tax_rate = rec.currency_id.tax_rate

    def reverse_moves(self):
        self.ensure_one()
        # moves = self.filtered(lambda move: move.currency_revaluation_ref_id == move.id)

        # Create default values.
        # default_values_list = []
        # for move in moves:
        #     default_values_list.append(move._prepare_default_reversal(move))

        # Create reversals.
        # reversals = self.env['account.move.reversal'].with_context(default_reversal_default_values_list=default_values_list).create({})

        reversals = self.env['account.move.reversal'].create({'move_ids': self.ids})
        reversals.reverse_moves()
        return True

    def action_invoice_paid(self):
        res = super(AccountMove, self).action_invoice_paid()
        return res

    def _compute_payments_widget_to_reconcile_info(self):
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
                    # Same foreign currency.
                    amount = abs(line.amount_residual_currency)
                else:
                    # Different foreign currencies.
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

            if not payments_widget_vals['content']:
                continue

            move.invoice_outstanding_credits_debits_widget = json.dumps(payments_widget_vals)
            move.invoice_has_outstanding = True

        res = super(AccountMove, self)._compute_payments_widget_to_reconcile_info()
        return res




class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.model
    def _get_fields_onchange_subtotal_model(self, price_subtotal, move_type, currency, company, date):
        if self.ref:
            if self.move_id.move_type in ('out_refund', 'in_refund'):
                name_inv = re.sub('Reversal|of|:|\s*', '', self.ref)
                inv_id = self.env['account.move'].search([('name', '=', name_inv)])
                if inv_id:
                    date = inv_id.invoice_date
        res = super(AccountMoveLine, self)._get_fields_onchange_subtotal_model(price_subtotal = price_subtotal, move_type = move_type, currency = currency, company = company, date = date)
        res_config = self.company_id.tax_discount_policy or False
        if res_config:
            if move_type in self.move_id.get_outbound_types():
                sign = 1
            elif move_type in self.move_id.get_inbound_types():
                sign = -1
            else:
                sign = 1
            post_discount_account = self.company_id.post_discount_account
            if post_discount_account:
                if res_config == 'untax':
                    price_subtotal = price_subtotal + self.discount_amt

                amount_currency = price_subtotal * sign
                if self.move_id.apply_manual_currency_exchange and self.move_id.manual_currency_exchange_inverse_rate == 0.0:
                    raise UserError(_('Inverse rate must be greater than 0'))
                if self.move_id.apply_manual_currency_exchange:
                    balance = amount_currency / self.move_id.manual_currency_exchange_rate
                else:
                    balance = currency._convert(amount_currency, company.currency_id, company, date or fields.Date.context_today(self))
                discount_amt_currency = self.discount_amt

                res['price_unit'] = self.price_unit
                res['amount_currency'] = amount_currency
                res['discount_amt'] = self.discount_amt
                res['currency_id'] = currency.id
                res['debit'] = balance > 0.0 and balance or 0.0
                res['credit'] = balance < 0.0 and -balance or 0.0
            else:                
                amount_currency = price_subtotal * sign
                if self.move_id.apply_manual_currency_exchange and self.move_id.manual_currency_exchange_inverse_rate == 0.0:
                    raise UserError(_('Inverse rate must be greater than 0'))
                if self.move_id.apply_manual_currency_exchange:
                    balance = amount_currency / self.move_id.manual_currency_exchange_rate
                else:
                    balance = currency._convert(amount_currency, company.currency_id, company, date or fields.Date.context_today(self))

                res['amount_currency'] = amount_currency
                res['discount_amt'] = self.discount_amt
                res['currency_id'] = currency.id
                res['debit'] = balance > 0.0 and balance or 0.0
                res['credit'] = balance < 0.0 and -balance or 0.0
        return res


    def reconcile(self):
        ''' Reconcile the current move lines all together.
        :return: A dictionary representing a summary of what has been done during the reconciliation:
                * partials:             A recorset of all account.partial.reconcile created during the reconciliation.
                * full_reconcile:       An account.full.reconcile record created when there is nothing left to reconcile
                                        in the involved lines.
                * tax_cash_basis_moves: An account.move recordset representing the tax cash basis journal entries.
        '''
        def _add_lines_to_exchange_difference_vals_partial_payment(lines, exchange_diff_move_vals, tmp_amount_currency):
            journal = self.env['account.journal'].browse(exchange_diff_move_vals['journal_id'])
            to_reconcile = []
            tmp_date = max(exchange_diff_move_vals['date'], lines[1].date)

            for line in lines[0]:
                exchange_diff_move_vals['date'] = max(exchange_diff_move_vals['date'], line.date)
                tmp_ref = " "
                dif_balance = 0

                if not line.company_currency_id.is_zero(line.amount_residual):
                    # amount_residual_currency == 0 and amount_residual has to be fixed.

                    if line.amount_residual > 0.0:
                        exchange_line_account = journal.company_id.expense_currency_exchange_account_id
                    else:
                        exchange_line_account = journal.company_id.income_currency_exchange_account_id

                elif line.currency_id and not line.currency_id.is_zero(line.amount_residual_currency):
                    # amount_residual == 0 and amount_residual_currency has to be fixed.

                    if line.amount_residual_currency > 0.0:
                        exchange_line_account = journal.company_id.expense_currency_exchange_account_id
                    else:
                        exchange_line_account = journal.company_id.income_currency_exchange_account_id
                else:
                    continue

                amount_residual =  line.amount_residual
                amount_residual_currency = line.amount_residual_currency
                
                # if not move_entry_type:
                if line.move_id.move_type != 'entry':
                    sign = 1
                    if line.move_id.move_type in ["out_invoice", "out_refund", "out_receipt","in_invoice", "in_refund", "in_receipt"]:
                        sign = -1
                    
                    # if lines[0].move_id.move_type == 'entry':
                    #     account_id = lines[0].move_id.journal_id.default_account_id
                    # elif lines[1].move_id.move_type == 'entry':
                    #     account_id = lines[1].move_id.journal_id.default_account_id

                    revaluataion_amount_residual = 0
                    revaluataion_amount_residual_currency = 0
                    
                    if line.move_id.currency_revaluation_id:                        
                        for currency_revaluation_id in line.move_id.currency_revaluation_id.filtered(lambda x: x.state == 'posted'):
                            line_ids = currency_revaluation_id.line_ids.filtered(lambda x: x.account_id == line.account_id)
                            revaluataion_amount_residual += (sum(line_ids.mapped('amount_residual')))
                            revaluataion_amount_residual_currency += (sum(line_ids.mapped('amount_residual_currency')))                        
                        
                    amount_residual += revaluataion_amount_residual
                    amount_residual_currency += revaluataion_amount_residual_currency
                    tmp_ref += line.move_id.name

                    # amount_residual *= sign
                
                if line.move_id.move_type == 'entry':
                    if lines[0].move_id.move_type == 'entry':
                        # account_id = lines[0].move_id.journal_id.default_account_id
                        move_type = lines[1].move_id.move_type
                        inv_name = lines[1].move_id.name
                    elif lines[1].move_id.move_type == 'entry':
                        # account_id = lines[1].move_id.journal_id.default_account_id
                        move_type = lines[0].move_id.move_type
                        inv_name = lines[0].move_id.name
                    
                    account_move = line.move_id.payment_id.reconciled_invoice_ids
                    if move_type in ["out_invoice", "out_refund", "out_receipt"]:
                        account_move = line.move_id.payment_id.reconciled_invoice_ids
                    if move_type in ["in_invoice", "in_refund", "in_receipt"]:
                        account_move = line.move_id.payment_id.reconciled_bill_ids
                    
                    if len(account_move) > 0:
                        inv_payment = account_move.filtered(lambda x: x.name == inv_name)
                        revaluataion_amount_residual = 0
                        revaluataion_amount_residual_currency = 0
                        sign = 1
                        for inv in inv_payment:
                            if inv.move_type in ["out_invoice", "out_refund", "out_receipt","in_invoice", "in_refund", "in_receipt"]:
                                sign = -1
                            for currency_revaluation_id in inv.currency_revaluation_id.filtered(lambda x: x.state == 'posted'):
                                line_ids = currency_revaluation_id.line_ids.filtered(lambda x: x.account_id == line.account_id)
                                revaluataion_amount_residual += (sum(line_ids.mapped('amount_residual')))
                                revaluataion_amount_residual_currency += (sum(line_ids.mapped('amount_residual_currency')))
                                                        
                        revaluataion_amount_residual *= sign

                        amount_residual += revaluataion_amount_residual
                        amount_residual_currency += revaluataion_amount_residual_currency
                        tmp_ref += line.move_id.ref
                        
                        # amount_residual *= sign


                if amount_residual > 0.0:
                    exchange_line_account = journal.company_id.expense_currency_exchange_account_id
                else:
                    exchange_line_account = journal.company_id.income_currency_exchange_account_id

                sequence = len(exchange_diff_move_vals['line_ids'])
                exchange_diff_move_vals['line_ids'] += [
                    (0, 0, {
                        'name': _('Currency exchange rate difference ('+ tmp_ref +')'),
                        'debit': -amount_residual if amount_residual < 0.0 else 0.0,
                        'credit': amount_residual if amount_residual > 0.0 else 0.0,
                        # 'amount_currency': -line.amount_residual_currency,
                        'account_id': line.account_id.id,
                        'currency_id': line.currency_id.id,
                        'partner_id': line.partner_id.id,
                        'sequence': sequence,
                    }),
                    (0, 0, {
                        'name': _('Currency exchange rate difference ('+ tmp_ref +')'),
                        'debit': amount_residual if amount_residual > 0.0 else 0.0,
                        'credit': -amount_residual if amount_residual < 0.0 else 0.0,
                        # 'amount_currency': line.amount_residual_currency,
                        'account_id': exchange_line_account.id,
                        'currency_id': line.currency_id.id,
                        'partner_id': line.partner_id.id,
                        'sequence': sequence + 1,
                    }),
                ]

                to_reconcile.append((line, sequence))
            # raise UserError("asdasdasdasdas 1")
            return to_reconcile

        results = {}

        if not self:
            return results

        # List unpaid invoices
        not_paid_invoices = self.move_id.filtered(
            lambda move: move.is_invoice(include_receipts=True) and move.payment_state not in ('paid', 'in_payment')
        )

        # ==== Check the lines can be reconciled together ====
        company = None
        account = None
        for line in self:
            if line.reconciled:
                raise UserError(_("You are trying to reconcile some entries that are already reconciled."))
            if not line.account_id.reconcile and line.account_id.internal_type != 'liquidity':
                raise UserError(_("Account %s does not allow reconciliation. First change the configuration of this account to allow it.")
                                % line.account_id.display_name)
            if line.move_id.state != 'posted':
                raise UserError(_('You can only reconcile posted entries.'))
            if company is None:
                company = line.company_id
            elif line.company_id != company:
                raise UserError(_("Entries doesn't belong to the same company: %s != %s")
                                % (company.display_name, line.company_id.display_name))
            if account is None:
                account = line.account_id
            elif line.account_id != account:
                raise UserError(_("Entries are not from the same account: %s != %s")
                                % (account.display_name, line.account_id.display_name))

        sorted_lines = self.sorted(key=lambda line: (line.date_maturity or line.date, line.currency_id))

        # ==== Collect all involved lines through the existing reconciliation ====
        involved_lines = sorted_lines
        involved_partials = self.env['account.partial.reconcile']
        current_lines = involved_lines
        current_partials = involved_partials
        while current_lines:
            current_partials = (current_lines.matched_debit_ids + current_lines.matched_credit_ids) - current_partials
            involved_partials += current_partials
            current_lines = (current_partials.debit_move_id + current_partials.credit_move_id) - current_lines
            involved_lines += current_lines

        # ==== Create partials ====
        partials = self.env['account.partial.reconcile'].create(sorted_lines._prepare_reconciliation_partials())

        # Track newly created partials.
        results['partials'] = partials
        involved_partials += partials

        # ==== Create entries for cash basis taxes ====
        is_cash_basis_needed = account.user_type_id.type in ('receivable', 'payable')
        if is_cash_basis_needed and not self._context.get('move_reverse_cancel'):
            tax_cash_basis_moves = partials._create_tax_cash_basis_moves()
            results['tax_cash_basis_moves'] = tax_cash_basis_moves

        # ==== Check if a full reconcile is needed ====
        if involved_lines[0].currency_id and all(line.currency_id == involved_lines[0].currency_id for line in involved_lines):
            is_full_needed = all(line.currency_id.is_zero(line.amount_residual_currency) for line in involved_lines)
        else:
            is_full_needed = all(line.company_currency_id.is_zero(line.amount_residual) for line in involved_lines)

        if is_full_needed:
            # ==== Create the exchange difference move ====
            if self._context.get('no_exchange_difference'):
                exchange_move = None
            else:
                exchange_move = involved_lines._create_exchange_difference_move()
                if exchange_move:
                    exchange_move_lines = exchange_move.line_ids.filtered(lambda line: line.account_id == account)

                    # Track newly created lines.
                    involved_lines += exchange_move_lines

                    # Track newly created partials.
                    exchange_diff_partials = exchange_move_lines.matched_debit_ids \
                                             + exchange_move_lines.matched_credit_ids
                    involved_partials += exchange_diff_partials
                    results['partials'] += exchange_diff_partials

                    exchange_move._post(soft=False)

            # ==== Create the full reconcile ====
            results['full_reconcile'] = self.env['account.full.reconcile'].create({
                'exchange_move_id': exchange_move and exchange_move.id,
                'partial_reconcile_ids': [(6, 0, involved_partials.ids)],
                'reconciled_line_ids': [(6, 0, involved_lines.ids)],
            })

        else:
            # if self[1].currency_id.id != self[1].company_id.currency_id.id:
            if len(self) > 1 and self[1].currency_id.id != self[1].company_id.currency_id.id:
                exchange_move = False
                journal = company.currency_exchange_journal_id
                exchange_diff_move_vals = {
                    'move_type': 'entry',
                    'date': self[0].date,
                    'journal_id': journal.id,
                    'line_ids': [],
                }
                
                tmp_amount_currency = -abs(self[0].amount_currency)
                to_reconcile = _add_lines_to_exchange_difference_vals_partial_payment(self, exchange_diff_move_vals, tmp_amount_currency)
                if exchange_diff_move_vals['line_ids']:
                    # Check the configuration of the exchange difference journal.
                    if not journal:
                        raise UserError(_("You should configure the 'Exchange Gain or Loss Journal' in your company settings, to manage automatically the booking of accounting entries related to differences between exchange rates."))
                    if not journal.company_id.expense_currency_exchange_account_id:
                        raise UserError(_("You should configure the 'Loss Exchange Rate Account' in your company settings, to manage automatically the booking of accounting entries related to differences between exchange rates."))
                    if not journal.company_id.income_currency_exchange_account_id.id:
                        raise UserError(_("You should configure the 'Gain Exchange Rate Account' in your company settings, to manage automatically the booking of accounting entries related to differences between exchange rates."))

                    exchange_diff_move_vals['date'] = max(exchange_diff_move_vals['date'], company._get_user_fiscal_lock_date())
                    exchange_move = self.env['account.move'].create(exchange_diff_move_vals)
                    self[0].move_id.write({'exchange_ids' : exchange_move.id})
                    # raise UserError("asdasdasdasdas 1")

                partials_vals_list = []
                for source_line, sequence in to_reconcile:
                    exchange_diff_line = exchange_move.line_ids[sequence]

                    if source_line.company_currency_id.is_zero(source_line.amount_residual):
                        exchange_field = 'amount_residual_currency'
                    else:
                        exchange_field = 'amount_residual'

                    if exchange_diff_line[exchange_field] > 0.0:
                        debit_line = exchange_diff_line
                        credit_line = source_line
                    else:
                        debit_line = source_line
                        credit_line = exchange_diff_line

                    partials_vals_list.append({
                        'amount': abs(source_line.amount_residual),
                        'debit_amount_currency': abs(debit_line.amount_residual_currency),
                        'credit_amount_currency': abs(credit_line.amount_residual_currency),
                        'debit_move_id': debit_line.id,
                        'credit_move_id': credit_line.id,
                    })

                self.env['account.partial.reconcile'].create(partials_vals_list)

                if exchange_move:
                    exchange_move._post(soft=False)

        # Trigger action for paid invoices
        not_paid_invoices\
            .filtered(lambda move: move.payment_state in ('paid', 'in_payment'))\
            .action_invoice_paid()

        ''' Reconcile the journal items given as ids in the context.
        :param writeoff_acc_id: account to post the writeoff on.
        :param writeoff_journal_id: journal to post the writeoff on.
        :return: True
        '''
        # paid_invoices = self.env['account.move'].search([('id', 'in', self.mapped('move_id').ids), ('payment_state', '=', 'paid')])
        # if paid_invoices:
        #     revaluation = self.env['account.move'].search([('currency_revaluation_ref_id', 'in', paid_invoices.ids)])
        #     for reval in revaluation:
        #         reval.reverse_moves()
        #         raise UserError("Masuk ke sini reval.reverse_moves()")

        for line in self:
            if line.move_id.payment_state:
                line.move_id._compute_amount()

        return results


    def _create_exchange_difference_move(self):
        ''' Create the exchange difference journal entry on the current journal items.
        :return: An account.move record.
        '''

        def _add_lines_to_exchange_difference_vals(lines, exchange_diff_move_vals):
            ''' Generate the exchange difference values used to create the journal items
            in order to fix the residual amounts and add them into 'exchange_diff_move_vals'.

            1) When reconciled on the same foreign currency, the journal items are
            fully reconciled regarding this currency but it could be not the case
            of the balance that is expressed using the company's currency. In that
            case, we need to create exchange difference journal items to ensure this
            residual amount reaches zero.

            2) When reconciled on the company currency but having different foreign
            currencies, the journal items are fully reconciled regarding the company
            currency but it's not always the case for the foreign currencies. In that
            case, the exchange difference journal items are created to ensure this
            residual amount in foreign currency reaches zero.

            :param lines:                   The account.move.lines to which fix the residual amounts.
            :param exchange_diff_move_vals: The current vals of the exchange difference journal entry.
            :return:                        A list of pair <line, sequence> to perform the reconciliation
                                            at the creation of the exchange difference move where 'line'
                                            is the account.move.line to which the 'sequence'-th exchange
                                            difference line will be reconciled with.
            '''
            journal = self.env['account.journal'].browse(exchange_diff_move_vals['journal_id'])
            to_reconcile = []
            if lines and len(lines) >= 2:
                tmp_date = max(exchange_diff_move_vals['date'], lines[1].date)
                tmp_amount_currency = lines[1].amount_currency
            
            for line in lines:
                exchange_diff_move_vals['date'] = max(exchange_diff_move_vals['date'], line.date)
                tmp_ref = " "

                amount_residual =  line.amount_residual
                amount_residual_currency = line.amount_residual_currency

                dif_balance = 0

                if not line.company_currency_id.is_zero(amount_residual):
                    # amount_residual_currency == 0 and amount_residual has to be fixed.
                    if amount_residual > 0.0:
                        exchange_line_account = journal.company_id.expense_currency_exchange_account_id
                    else:
                        exchange_line_account = journal.company_id.income_currency_exchange_account_id

                elif line.currency_id and not line.currency_id.is_zero(amount_residual_currency):
                    # amount_residual == 0 and amount_residual_currency has to be fixed.
                    if amount_residual_currency > 0.0:
                        exchange_line_account = journal.company_id.expense_currency_exchange_account_id
                    else:
                        exchange_line_account = journal.company_id.income_currency_exchange_account_id
                else:
                    continue

                # if not move_entry_type:
                if line.move_id.move_type != 'entry':
                    sign = 1
                    if line.move_id.move_type in ["out_invoice", "out_refund", "out_receipt","in_invoice", "in_refund", "in_receipt"]:
                        sign = -1
                    
                    # if lines[0].move_id.move_type == 'entry':
                    #     account_id = lines[0].move_id.journal_id.default_account_id
                    # elif lines[1].move_id.move_type == 'entry':
                    #     account_id = lines[1].move_id.journal_id.default_account_id

                    revaluataion_amount_residual = 0
                    revaluataion_amount_residual_currency = 0
                    
                    if line.move_id.currency_revaluation_id:                        
                        for currency_revaluation_id in line.move_id.currency_revaluation_id.filtered(lambda x: x.state == 'posted'):
                            line_ids = currency_revaluation_id.line_ids.filtered(lambda x: x.account_id == line.account_id)
                            revaluataion_amount_residual += (sum(line_ids.mapped('amount_residual')))
                            revaluataion_amount_residual_currency += (sum(line_ids.mapped('amount_residual_currency')))                        
                        
                    amount_residual += revaluataion_amount_residual
                    amount_residual_currency += revaluataion_amount_residual_currency
                    tmp_ref += line.move_id.name

                    # amount_residual *= sign
                
                if line.move_id.move_type == 'entry':
                    if lines[0].move_id.move_type == 'entry':
                        account_id = lines[0].move_id.journal_id.default_account_id
                        move_type = lines[1].move_id.move_type
                        inv_name = lines[1].move_id.name
                    elif lines[1].move_id.move_type == 'entry':
                        account_id = lines[1].move_id.journal_id.default_account_id
                        move_type = lines[0].move_id.move_type
                        inv_name = lines[0].move_id.name
                    
                    account_move = line.move_id.payment_id.reconciled_invoice_ids
                    if move_type in ["out_invoice", "out_refund", "out_receipt"]:
                        account_move = line.move_id.payment_id.reconciled_invoice_ids
                    if move_type in ["in_invoice", "in_refund", "in_receipt"]:
                        account_move = line.move_id.payment_id.reconciled_bill_ids
                    
                    if len(account_move) > 0:
                        inv_payment = account_move.filtered(lambda x: x.name == inv_name)
                        revaluataion_amount_residual = 0
                        revaluataion_amount_residual_currency = 0
                        sign = 1
                        for inv in inv_payment:
                            if inv.move_type in ["out_invoice", "out_refund", "out_receipt","in_invoice", "in_refund", "in_receipt"]:
                                sign = -1
                            for currency_revaluation_id in inv.currency_revaluation_id.filtered(lambda x: x.state == 'posted'):
                                line_ids = currency_revaluation_id.line_ids.filtered(lambda x: x.account_id == line.account_id)
                                revaluataion_amount_residual += (sum(line_ids.mapped('amount_residual')))
                                revaluataion_amount_residual_currency += (sum(line_ids.mapped('amount_residual_currency')))
                                                        
                        revaluataion_amount_residual *= sign

                        amount_residual += revaluataion_amount_residual
                        amount_residual_currency += revaluataion_amount_residual_currency
                        tmp_ref += line.move_id.ref
                        
                        # amount_residual *= sign


                if amount_residual > 0.0:
                    exchange_line_account = journal.company_id.expense_currency_exchange_account_id
                else:
                    exchange_line_account = journal.company_id.income_currency_exchange_account_id

                
                # tmp_amount_residual = line.amount_residual
                sequence = len(exchange_diff_move_vals['line_ids'])
                exchange_diff_move_vals['line_ids'] += [
                    (0, 0, {
                        'name': _('Currency exchange rate difference '+tmp_ref),
                        'debit': -amount_residual if amount_residual < 0.0 else 0.0,
                        'credit': amount_residual if amount_residual > 0.0 else 0.0,
                        # 'amount_currency': -amount_residual_currency,
                        'account_id': line.account_id.id,
                        'currency_id': line.currency_id.id,
                        'partner_id': line.partner_id.id,
                        'sequence': sequence,
                    }),
                    (0, 0, {
                        'name': _('Currency exchange rate difference '+tmp_ref),
                        'debit': amount_residual if amount_residual > 0.0 else 0.0,
                        'credit': -amount_residual if amount_residual < 0.0 else 0.0,
                        # 'amount_currency': amount_residual_currency,
                        'account_id': exchange_line_account.id,
                        'currency_id': line.currency_id.id,
                        'partner_id': line.partner_id.id,
                        'sequence': sequence + 1,
                    }),
                ]
                to_reconcile.append((line, sequence))
            # raise UserError("asdasdasdasdas 2")
            return to_reconcile

        def _add_cash_basis_lines_to_exchange_difference_vals(lines, exchange_diff_move_vals):
            ''' Generate the exchange difference values used to create the journal items
            in order to fix the cash basis lines using the transfer account in a multi-currencies
            environment when this account is not a reconcile one.

            When the tax cash basis journal entries are generated and all involved
            transfer account set on taxes are all reconcilable, the account balance
            will be reset to zero by the exchange difference journal items generated
            above. However, this mechanism will not work if there is any transfer
            accounts that are not reconcile and we are generating the cash basis
            journal items in a foreign currency. In that specific case, we need to
            generate extra journal items at the generation of the exchange difference
            journal entry to ensure this balance is reset to zero and then, will not
            appear on the tax report leading to erroneous tax base amount / tax amount.

            :param lines:                   The account.move.lines to which fix the residual amounts.
            :param exchange_diff_move_vals: The current vals of the exchange difference journal entry.
            '''
            for move in lines.move_id:
                account_vals_to_fix = {}

                move_values = move._collect_tax_cash_basis_values()

                # The cash basis doesn't need to be handle for this move because there is another payment term
                # line that is not yet fully paid.
                if not move_values or not move_values['is_fully_paid']:
                    continue

                # ==========================================================================
                # Add the balance of all tax lines of the current move in order in order
                # to compute the residual amount for each of them.
                # ==========================================================================

                for line in move_values['to_process_lines']:

                    vals = {
                        'currency_id': line.currency_id.id,
                        'partner_id': line.partner_id.id,
                        'tax_ids': [(6, 0, line.tax_ids.ids)],
                        'tax_tag_ids': [(6, 0, line._convert_tags_for_cash_basis(line.tax_tag_ids).ids)],
                        'debit': line.debit,
                        'credit': line.credit,
                    }

                    if line.tax_repartition_line_id:
                        # Tax line.
                        grouping_key = self.env['account.partial.reconcile']._get_cash_basis_tax_line_grouping_key_from_record(line)
                        if grouping_key in account_vals_to_fix:
                            debit = account_vals_to_fix[grouping_key]['debit'] + vals['debit']
                            credit = account_vals_to_fix[grouping_key]['credit'] + vals['credit']
                            balance = debit - credit

                            account_vals_to_fix[grouping_key].update({
                                'debit': balance if balance > 0 else 0,
                                'credit': -balance if balance < 0 else 0,
                                'tax_base_amount': account_vals_to_fix[grouping_key]['tax_base_amount'] + line.tax_base_amount,
                            })
                        else:
                            account_vals_to_fix[grouping_key] = {
                                **vals,
                                'account_id': line.account_id.id,
                                'tax_base_amount': line.tax_base_amount,
                                'tax_repartition_line_id': line.tax_repartition_line_id.id,
                            }
                    elif line.tax_ids:
                        # Base line.
                        account_to_fix = line.company_id.account_cash_basis_base_account_id
                        if not account_to_fix:
                            continue

                        grouping_key = self.env['account.partial.reconcile']._get_cash_basis_base_line_grouping_key_from_record(line, account=account_to_fix)

                        if grouping_key not in account_vals_to_fix:
                            account_vals_to_fix[grouping_key] = {
                                **vals,
                                'account_id': account_to_fix.id,
                            }
                        else:
                            # Multiple base lines could share the same key, if the same
                            # cash basis tax is used alone on several lines of the invoices
                            account_vals_to_fix[grouping_key]['debit'] += vals['debit']
                            account_vals_to_fix[grouping_key]['credit'] += vals['credit']

                # ==========================================================================
                # Subtract the balance of all previously generated cash basis journal entries
                # in order to retrieve the residual balance of each involved transfer account.
                # ==========================================================================

                cash_basis_moves = self.env['account.move'].search([('tax_cash_basis_move_id', '=', move.id)])
                for line in cash_basis_moves.line_ids:
                    grouping_key = None
                    if line.tax_repartition_line_id:
                        # Tax line.
                        grouping_key = self.env['account.partial.reconcile']._get_cash_basis_tax_line_grouping_key_from_record(
                            line,
                            account=line.tax_line_id.cash_basis_transition_account_id,
                        )
                    elif line.tax_ids:
                        # Base line.
                        grouping_key = self.env['account.partial.reconcile']._get_cash_basis_base_line_grouping_key_from_record(
                            line,
                            account=line.company_id.account_cash_basis_base_account_id,
                        )

                    if grouping_key not in account_vals_to_fix:
                        continue

                    account_vals_to_fix[grouping_key]['debit'] -= line.debit
                    account_vals_to_fix[grouping_key]['credit'] -= line.credit

                # ==========================================================================
                # Generate the exchange difference journal items:
                # - to reset the balance of all transfer account to zero.
                # - fix rounding issues on the tax account/base tax account.
                # ==========================================================================

                for values in account_vals_to_fix.values():
                    balance = values['debit'] - values['credit']

                    if move.company_currency_id.is_zero(balance):
                        continue

                    if values.get('tax_repartition_line_id'):
                        # Tax line.
                        tax_repartition_line = self.env['account.tax.repartition.line'].browse(values['tax_repartition_line_id'])
                        account = tax_repartition_line.account_id or self.env['account.account'].browse(values['account_id'])

                        sequence = len(exchange_diff_move_vals['line_ids'])
                        exchange_diff_move_vals['line_ids'] += [
                            (0, 0, {
                                **values,
                                'name': _('Currency exchange rate difference (cash basis)'),
                                'debit': balance if balance > 0.0 else 0.0,
                                'credit': -balance if balance < 0.0 else 0.0,
                                'account_id': account.id,
                                'sequence': sequence,
                            }),
                            (0, 0, {
                                **values,
                                'name': _('Currency exchange rate difference (cash basis)'),
                                'debit': -balance if balance < 0.0 else 0.0,
                                'credit': balance if balance > 0.0 else 0.0,
                                'account_id': values['account_id'],
                                'tax_ids': [],
                                'tax_tag_ids': [],
                                'tax_repartition_line_id': False,
                                'sequence': sequence + 1,
                            }),
                        ]
                    else:
                        # Base line.
                        sequence = len(exchange_diff_move_vals['line_ids'])
                        exchange_diff_move_vals['line_ids'] += [
                            (0, 0, {
                                **values,
                                'name': _('Currency exchange rate difference (cash basis)'),
                                'debit': balance if balance > 0.0 else 0.0,
                                'credit': -balance if balance < 0.0 else 0.0,
                                'sequence': sequence,
                            }),
                            (0, 0, {
                                **values,
                                'name': _('Currency exchange rate difference (cash basis)'),
                                'debit': -balance if balance < 0.0 else 0.0,
                                'credit': balance if balance > 0.0 else 0.0,
                                'tax_ids': [],
                                'tax_tag_ids': [],
                                'sequence': sequence + 1,
                            }),
                        ]

        if not self:
            return self.env['account.move']

        company = self[0].company_id
        journal = company.currency_exchange_journal_id
        exchange_diff_move_vals = {
            'move_type': 'entry',
            'date': date.min,
            'journal_id': journal.id,
            'line_ids': [],
        }

        # Fix residual amounts.
        to_reconcile = _add_lines_to_exchange_difference_vals(self, exchange_diff_move_vals)

        # Fix cash basis entries.
        is_cash_basis_needed = self[0].account_internal_type in ('receivable', 'payable')
        if is_cash_basis_needed:
            _add_cash_basis_lines_to_exchange_difference_vals(self, exchange_diff_move_vals)

        # ==========================================================================
        # Create move and reconcile.
        # ==========================================================================

        if exchange_diff_move_vals['line_ids']:
            # Check the configuration of the exchange difference journal.
            if not journal:
                raise UserError(_("You should configure the 'Exchange Gain or Loss Journal' in your company settings, to manage automatically the booking of accounting entries related to differences between exchange rates."))
            if not journal.company_id.expense_currency_exchange_account_id:
                raise UserError(_("You should configure the 'Loss Exchange Rate Account' in your company settings, to manage automatically the booking of accounting entries related to differences between exchange rates."))
            if not journal.company_id.income_currency_exchange_account_id.id:
                raise UserError(_("You should configure the 'Gain Exchange Rate Account' in your company settings, to manage automatically the booking of accounting entries related to differences between exchange rates."))

            exchange_diff_move_vals['date'] = max(exchange_diff_move_vals['date'], company._get_user_fiscal_lock_date())

            exchange_move = self.env['account.move'].create(exchange_diff_move_vals)
            self[0].move_id.write({'exchange_ids' : exchange_move.id})
            # raise UserError("asdasdasdasdas 2")
        else:
            return None

        # Reconcile lines to the newly created exchange difference journal entry by creating more partials.
        partials_vals_list = []
        for source_line, sequence in to_reconcile:
            exchange_diff_line = exchange_move.line_ids[sequence]

            if source_line.company_currency_id.is_zero(source_line.amount_residual):
                exchange_field = 'amount_residual_currency'
            else:
                exchange_field = 'amount_residual'

            if exchange_diff_line[exchange_field] > 0.0:
                debit_line = exchange_diff_line
                credit_line = source_line
            else:
                debit_line = source_line
                credit_line = exchange_diff_line

            partials_vals_list.append({
                'amount': abs(source_line.amount_residual),
                'debit_amount_currency': abs(debit_line.amount_residual_currency),
                'credit_amount_currency': abs(credit_line.amount_residual_currency),
                'debit_move_id': debit_line.id,
                'credit_move_id': credit_line.id,
            })

        self.env['account.partial.reconcile'].create(partials_vals_list)

        return exchange_move
    

    