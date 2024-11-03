# -*- coding: utf-8 -*-

import logging
from collections import defaultdict
from datetime import datetime, date, timedelta
from passlib.context import CryptContext

import pytz
from pytz import timezone

from odoo import api, fields, models, tools, SUPERUSER_ID, _
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools import float_is_zero, float_compare
from lxml import etree

crypt_context = CryptContext(schemes=['pbkdf2_sha512', 'plaintext'], deprecated=['plaintext'])
_logger = logging.getLogger(__name__)

# TODO: workflow of pos session and account bank statement odoo 13
#       - pos session create, session will reading all payment_method_ids (payment methods) (1)
#       - from (1) they create statement_ids (account bank statement) and add it to pos session (2)
#       - from (2) when close session , they push to account brank statement with relation 1 to 1 (one-to-one). 1 account bank statement - 1 account bank statement line
#       - summary: 1 payment method - 1 account journal - 1 account bank statement - 1 account bank statement line

class PosSessionLogCashier(models.Model):
    _name = 'pos.session.log.cashier'
    _description = 'POS Session Log Cashier'

    name = fields.Char('Device ID', required=1) # Device ID is random generated string set for each browser if login in the pos screen and not real device ID
    user_id = fields.Many2one('res.users', 'Cashier')
    login_date = fields.Datetime('Login Date')
    logout_date = fields.Datetime('Logout Date', help='Logout Date / Close POS Screen Date')
    session_id = fields.Many2one('pos.session', 'POS Session')

class PosSession(models.Model):
    _inherit = "pos.session"

    required_reinstall_cache = fields.Boolean(
        'Reinstall Datas',
        default=0,
        help='If checked, when session start, all pos caches will remove and reinstall')
    backup_session = fields.Boolean('Backup Session')
    pos_branch_id = fields.Many2one('res.branch', string='Branch', readonly=1, default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, domain=lambda self: [('id', 'in', self.env.branches.ids)])
    employee_id = fields.Many2one('hr.employee', string='Assigned Employee')
    lock_state = fields.Selection([
        ('unlock', 'Un lock'),
        ('locked', 'Locked')
    ], default='unlock',
        string='Lock state',
        help='Unlock: when pos session start, pos not lock screen\n'
             'locked: when pos session start, pos auto lock screen')

    order_log_ids = fields.One2many(
        'pos.order.log',
        'session_id',
        string='Log Actions of Orders'
    )
    opened_at = fields.Datetime('Opened At', readonly=1)
    opened_uid = fields.Many2one('res.users', 'Opened by', readonly=1)
    last_login_time = fields.Datetime('Last Login Date', tracking=3, readonly=1)
    login_number = fields.Integer(tracking=3, readonly=1)
    state = fields.Selection(selection_add=[('opening_control', 'Opening Control')],tracking=3)
    cash_opening_balance = fields.Monetary(string='Opening Balance', compute="_compute_opening_control_balance", currency_field='currency_id')
    cash_closing_balance = fields.Monetary(string='Closing Balance', compute="_compute_closing_control_balance", currency_field='currency_id')
    
    is_closing_wizard = fields.Boolean('Closing Wizard')
    pos_config_cashbox_lines_ids = fields.One2many('account.cashbox.line', 'pos_session_id', string='Cashbox Wizard')
    pos_config_cashbox_clsosing_line_ids = fields.One2many('account.cashbox.line', 'pos_session_id', string='Cashbox Closing Lines')
    cash_register_balance_end_real = fields.Monetary(
        currency_field='currency_id',
        related='cash_closing_balance',
        help="Total of closing cash control lines.")

    cashier_id = fields.Many2one('res.users', string="Assigned Cashier")
    total_invoice_count = fields.Integer("Invoice Count", compute='_compute_invoice_count')
    total_faktur_count = fields.Integer("Faktur Count", compute='_compute_total_faktur_count')

    log_cashier_ids = fields.One2many('pos.session.log.cashier','session_id', string='Log Cashier in POS Screen')
    is_multi_session = fields.Boolean('Multi Session', compute='_compute_is_multi_session')

    order_with_receivable_invoice_ids = fields.One2many('pos.order', 
        compute='_compute_order_with_receivable_invoice_ids', 
        string='Order with Receivable Invoices')
    pos_config_uuid = fields.Char('POS Config uuid', compute='_compute_pos_config_uuid')

    @api.model
    def fields_view_get(self, view_id=None, view_type=None, toolbar=False, submenu=False):
        res = super(PosSession, self).fields_view_get(view_id=view_id, view_type=view_type,toolbar=toolbar,submenu=submenu)

        user_pos_not_create_edit =  self.env.user.has_group('equip3_pos_masterdata.group_pos_cashier') or self.env.user.has_group('equip3_pos_masterdata.group_pos_waiter') or self.env.user.has_group('equip3_pos_masterdata.group_pos_cooker')
        user_pos_have_create_edit =  self.env.user.has_group('equip3_pos_masterdata.group_pos_staff') or self.env.user.has_group('equip3_pos_masterdata.group_pos_supervisor') or self.env.user.has_group('equip3_pos_masterdata.group_pos_manager')
        if user_pos_not_create_edit and not user_pos_have_create_edit:
            root = etree.fromstring(res['arch'])
            root.set('edit', 'false')
            res['arch'] = etree.tostring(root)
            
        return res


    def _get_report_z_x_filename(self):
        self.ensure_one()
        name = ' Report ('+(self.name or '/')+')'
        if self.state == 'opened':
            name = 'X '+name
        else:
            name = 'Z '+name
        return name

    def _compute_opening_control_balance(self):
        for rec in self:
            o_balance = 0
            for line in rec.pos_session_cashbox_wizard_ids:
                if not line.is_closing_line:
                    o_balance += line.subtotal
            rec.cash_opening_balance = o_balance

    def _compute_closing_control_balance(self):
        for rec in self:
            o_balance = 0
            for line in rec.pos_session_cashbox_wizard_ids:
                if line.is_closing_line:
                    o_balance += line.subtotal
            rec.cash_closing_balance = o_balance

    def pos_session_opening_control(self):
        pos_session_control_view = self.env.ref('equip3_pos_general.view_pos_session_cash_control_form')
        return {
            'name': "Cash Control",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'pos.session',
            'views': [(pos_session_control_view.id, 'form')],
            'target': 'new',
            'res_id': self.id,
            'domain': [('id','=',self.id)],
            'context': {'default_pos_config_cashbox_lines_ids':self.pos_config_cashbox_lines_ids.ids},
        }

    def pos_session_closing_control(self):
        pos_session_closing_control_view = self.env.ref('equip3_pos_general.view_pos_session_cash_closing_control_form')
        return {
            'name': "Cash Control",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'pos.session',
            'views': [(pos_session_closing_control_view.id, 'form')],
            'target': 'new',
            # 'res_id': self.id,
            'domain': [('pos_config_cashbox_clsosing_line_ids','in',[1,2])],
            'context': {'default_is_closing_wizard':True},
        }

    def _compute_is_multi_session(self):
        for rec in self:
            is_multi_session = False
            if rec.config_id:
                is_multi_session = rec.config_id.multi_session
            rec.is_multi_session = is_multi_session

    def _compute_pos_config_uuid(self):
        for rec in self:
            uuid = 'False'
            if rec.config_id:
                uuid = rec.config_id.uuid
            rec.pos_config_uuid = uuid

    def _prepare_line(self, order_line):
        """ Derive from order_line the order date, income account, amount and taxes information.

        These information will be used in accumulating the amounts for sales and tax lines.
        """
        def get_income_account(order_line):
            product = order_line.product_id
            income_account = product.with_company(order_line.company_id)._get_product_accounts()['income']
            if not income_account:
                raise UserError(_('Please define income account for this product: "%s" (id:%d).')
                                % (product.name, product.id))
            return order_line.order_id.fiscal_position_id.map_account(income_account)

        company = order_line.order_id.company_id
        property_account_expense_categ_id = company.pos_product_discount1_id.categ_id.property_account_expense_categ_id

        tax_ids = order_line.tax_ids_after_fiscal_position\
                    .filtered(lambda t: t.company_id.id == order_line.order_id.company_id.id)
        sign = -1 if order_line.qty >= 0 else 1
        if company.tax_discount_policy=='untax':
            price = sign * order_line.price_unit * (1 - (order_line.discount or 0.0) / 100.0)
        else:
            price = sign * order_line.price_unit 
        # The 'is_refund' parameter is used to compute the tax tags. Ultimately, the tags are part
        # of the key used for summing taxes. Since the POS UI doesn't support the tags, inconsistencies
        # may arise in 'Round Globally'.
        check_refund = lambda x: x.qty * x.price_unit < 0
        if self.company_id.tax_calculation_rounding_method == 'round_globally':
            is_refund = all(check_refund(line) for line in order_line.order_id.lines)
        else:
            is_refund = check_refund(order_line)

        # TODO: Don't count Exchange Order as refund
        if order_line.order_id.is_exchange_order:
            is_refund = False

        tax_data = tax_ids.compute_all(price_unit=price, quantity=abs(order_line.qty), currency=self.currency_id, is_refund=is_refund)
        taxes = tax_data['taxes']
        # For Cash based taxes, use the account from the repartition line immediately as it has been paid already
        for tax in taxes:
            tax_rep = self.env['account.tax.repartition.line'].browse(tax['tax_repartition_line_id'])
            tax['account_id'] = tax_rep.account_id.id
        date_order = order_line.order_id.date_order
        taxes = [{'date_order': date_order, **tax} for tax in taxes]
        res = {
            'date_order': order_line.order_id.date_order,
            'income_account_id': get_income_account(order_line).id,
            'amount': order_line.price_subtotal,
            'taxes': taxes,
            'base_tags': tuple(tax_data['base_tags']),
        }

        #TODO: Force positive subtotal when exchange order but not product exchanged
        if order_line.order_id.is_exchange_order and not order_line.is_product_exchange:
            res['amount'] = abs(order_line.price_subtotal)

        if property_account_expense_categ_id and order_line.discount_amount_percent:
            res['amount']+= order_line.discount_amount_percent
        if self.config_id.enable_gift_card and (order_line.product_id.id == self.config_id.gift_card_product_id.id):
            res.update({
                'income_account_id': self.config_id.gift_card_account_id.id,
            })
        return res

    def _create_cash_statement_lines_and_cash_move_lines(self, data):
        # Create the split and combine cash statement lines and account move lines.
        # Keep the reference by statement for reconciliation.
        # `split_cash_statement_lines` maps `statement` -> split cash statement lines
        # `combine_cash_statement_lines` maps `statement` -> combine cash statement lines
        # `split_cash_receivable_lines` maps `statement` -> split cash receivable lines
        # `combine_cash_receivable_lines` maps `statement` -> combine cash receivable lines
        MoveLine = data.get('MoveLine')
        split_receivables_cash = data.get('split_receivables_cash')
        combine_receivables_cash = data.get('combine_receivables_cash')

        statements_by_journal_id = {statement.journal_id.id: statement for statement in self.statement_ids}
        # handle split cash payments
        split_cash_statement_line_vals = defaultdict(list)
        split_cash_receivable_vals = defaultdict(list)
        for data_arr, amounts in split_receivables_cash.items():
            pos_payment = data_arr[0]
            statement = statements_by_journal_id[pos_payment.payment_method_id.cash_journal_id.id]
            split_cash_statement_line_vals[statement].append(self._get_statement_line_vals(statement, pos_payment.payment_method_id.receivable_account_id, amounts['amount'], date=pos_payment.payment_date, partner=pos_payment.pos_order_id.partner_id))
            split_cash_receivable_vals[statement].append(self._get_split_receivable_vals(data_arr, amounts['amount'], amounts['amount_converted']))

        # handle combine cash payments
        combine_cash_statement_line_vals = defaultdict(list)
        combine_cash_receivable_vals = defaultdict(list)
        for data_arr, amounts in combine_receivables_cash.items():
            payment_method = data_arr[0]
            if not float_is_zero(amounts['amount'] , precision_rounding=self.currency_id.rounding):
                statement = statements_by_journal_id[payment_method.cash_journal_id.id]
                combine_cash_statement_line_vals[statement].append(self._get_statement_line_vals(statement, payment_method.receivable_account_id, amounts['amount']))
                combine_cash_receivable_vals[statement].append(self._get_combine_receivable_vals(data_arr, amounts['amount'], amounts['amount_converted']))
        # create the statement lines and account move lines
        BankStatementLine = self.env['account.bank.statement.line']
        split_cash_statement_lines = {}
        combine_cash_statement_lines = {}
        split_cash_receivable_lines = {}
        combine_cash_receivable_lines = {}
        for statement in self.statement_ids:
            split_cash_statement_lines[statement] = BankStatementLine.create(split_cash_statement_line_vals[statement])
            combine_cash_statement_lines[statement] = BankStatementLine.create(combine_cash_statement_line_vals[statement])
            split_cash_receivable_lines[statement] = MoveLine.create(split_cash_receivable_vals[statement])
            combine_cash_receivable_lines[statement] = MoveLine.create(combine_cash_receivable_vals[statement])

        data.update(
            {'split_cash_statement_lines':    split_cash_statement_lines,
             'combine_cash_statement_lines':  combine_cash_statement_lines,
             'split_cash_receivable_lines':   split_cash_receivable_lines,
             'combine_cash_receivable_lines': combine_cash_receivable_lines
             })
        return data

    def _accumulate_amounts(self, data):
        # Accumulate the amounts for each accounting lines group
        # Each dict maps `key` -> `amounts`, where `key` is the group key.
        # E.g. `combine_receivables` is derived from pos.payment records
        # in the self.order_ids with group key of the `payment_method_id`
        # field of the pos.payment record.
        amounts = lambda: {'amount': 0.0, 'amount_converted': 0.0}
        tax_amounts = lambda: {'amount': 0.0, 'amount_converted': 0.0, 'base_amount': 0.0, 'base_amount_converted': 0.0}
        split_receivables = defaultdict(amounts)
        split_receivables_cash = defaultdict(amounts)
        combine_receivables = defaultdict(amounts)
        combine_receivables_cash = defaultdict(amounts)
        invoice_receivables = defaultdict(amounts)
        sales = defaultdict(amounts)
        sales_discounts = defaultdict(amounts)
        taxes = defaultdict(tax_amounts)
        stock_expense = defaultdict(amounts)
        stock_return = defaultdict(amounts)
        stock_output = defaultdict(amounts)
        mdr_company = defaultdict(amounts)
        mdr_customer = defaultdict(amounts)
        rounding_difference = defaultdict(amounts)
        total_discount_amount_percent = 0
        # Track the receivable lines of the invoiced orders' account moves for reconciliation
        # These receivable lines are reconciled to the corresponding invoice receivable lines
        # of this session's move_id.
        order_account_move_receivable_lines = defaultdict(lambda: self.env['account.move.line'])
        rounded_globally = self.company_id.tax_calculation_rounding_method == 'round_globally' 
        for order in self.order_ids.filtered(lambda x: x.state not in ('draft','cancel','quotation')):
            company_order = order.company_id
            if not company_order.pos_product_discount1_id:
                raise UserError("Please settle discount product on POS General Settings")
            if not company_order.pos_product_discount1_id.categ_id.property_account_expense_categ_id:
                raise UserError( "Define product category “(the Discount Service’s product category)” expense account for ("+company_order.name+").")
            pos_discount_account_id = company_order.pos_product_discount1_id.categ_id.property_account_expense_categ_id.id
            # Combine pos receivable lines
            # Separate cash payments for cash reconciliation later.
            for payment in order.payment_ids:
                amount, date = payment.amount, payment.payment_date
                if payment.mdr_paid_by == 'Customer':
                    amount -= round(payment.mdr_amount,payment.currency_id.decimal_places)
                    mdr_customer_key = (payment.payment_method_id,-1 if payment.mdr_amount < 0 else 1,payment.currency_id)
                    mdr_customer[mdr_customer_key] = self._update_amounts(mdr_customer[mdr_customer_key], {'amount': round(payment.mdr_amount,payment.currency_id.decimal_places)}, date)
                if payment.mdr_paid_by == 'Company':
                    amount -= round(payment.mdr_amount,payment.currency_id.decimal_places)
                    mdr_company_key = (payment.payment_method_id,-1 if payment.mdr_amount < 0 else 1,payment.currency_id)
                    mdr_company[mdr_company_key] = self._update_amounts(mdr_company[mdr_company_key], {'amount': round(payment.mdr_amount,payment.currency_id.decimal_places)}, date)
 
                    
                if payment.payment_method_id.split_transactions:
                    key = (payment,payment.currency_id)
                    if payment.payment_method_id.is_cash_count:
                        split_receivables_cash[key] = self._update_amounts(split_receivables_cash[key], {'amount': amount}, date)
                    else:
                        split_receivables[key] = self._update_amounts(split_receivables[key], {'amount': amount}, date)
                else:
                    key = (payment.payment_method_id,payment.currency_id)
                    if payment.payment_method_id.is_cash_count:
                        combine_receivables_cash[key] = self._update_amounts(combine_receivables_cash[key], {'amount': amount}, date)
                    else:
                        combine_receivables[key] = self._update_amounts(combine_receivables[key], {'amount': amount}, date)

            if order.is_invoiced:
                # Combine invoice receivable lines
                key = order.partner_id
                # if self.config_id.cash_rounding:
                #     invoice_receivables[key] = self._update_amounts(invoice_receivables[key], {'amount': order.amount_paid - order.total_mdr_amount_customer}, order.date_order)
                # else:
                invoice_receivables[key] = self._update_amounts(invoice_receivables[key], {'amount': order.amount_total - order.total_mdr_amount_customer}, order.date_order)
                # side loop to gather receivable lines by account for reconciliation
                for move_line in order.account_move.line_ids.filtered(lambda aml: aml.account_id.internal_type == 'receivable' and not aml.reconciled):
                    order_account_move_receivable_lines[move_line.account_id.id] |= move_line
            else:
                order_taxes = defaultdict(tax_amounts)
                for order_line in order.lines:
                    line = self._prepare_line(order_line)
                    # Combine sales/refund lines
                    sign = -1 if line['amount'] < 0 else 1
                    if order_line.order_id.is_exchange_order:
                        sign = 1
                    sale_key = (
                        # account
                        line['income_account_id'],
                        sign,
                        # for taxes
                        tuple((tax['id'], tax['account_id'], tax['tax_repartition_line_id']) for tax in line['taxes']),
                        line['base_tags'],
                        order.currency_id
                    )
                    sales[sale_key] = self._update_amounts(sales[sale_key], {'amount': line['amount']}, line['date_order'])
                    # Combine tax lines
                    for tax in line['taxes']:
                        tax_key = (tax['account_id'], tax['tax_repartition_line_id'], tax['id'], tuple(tax['tag_ids']),order.currency_id)
                        order_taxes[tax_key] = self._update_amounts(
                            order_taxes[tax_key],
                            {'amount': tax['amount'], 'base_amount': tax['base']},
                            tax['date_order'],
                            round=not rounded_globally
                        )
                    # Promotion Stack
                    total_discount_amount_percent += order_line.discount_amount_percent
                    for promotion_stack in order_line.promotion_stack_ids:
                        discount_account_id = pos_discount_account_id
                        promotion_id = promotion_stack.promotion_id
                        if promotion_id.promotion_product_discount_id:
                            product_categ_id = promotion_id.promotion_product_discount_id.categ_id
                            if not product_categ_id.property_account_income_categ_id:
                                raise UserError(_('Please set Income Account for Product Category "%s"' % product_categ_id.name))
                            discount_account_id = product_categ_id.property_account_income_categ_id.id

                        if discount_account_id and promotion_stack.amount:
                            pos_discount_key = (
                                discount_account_id,
                                -1 if promotion_stack.amount < 0 else 1,
                                order.currency_id, 
                                promotion_id
                            )
                            sales_discounts[pos_discount_key] = self._update_amounts(
                                sales_discounts[pos_discount_key], 
                                {'amount': promotion_stack.amount}, 
                                line['date_order']
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
                        exp_key = move.product_id._get_product_accounts()['expense']
                        out_key = move.product_id.categ_id.property_stock_account_output_categ_id
                        amount = -sum(move.sudo().stock_valuation_layer_ids.mapped('value'))
                        stock_expense[exp_key] = self._update_amounts(stock_expense[exp_key], {'amount': amount}, move.picking_id.date, force_company_currency=True)
                        if move.location_id.usage == 'customer':
                            stock_return[out_key] = self._update_amounts(stock_return[out_key], {'amount': amount}, move.picking_id.date, force_company_currency=True)
                        else:
                            stock_output[out_key] = self._update_amounts(stock_output[out_key], {'amount': amount}, move.picking_id.date, force_company_currency=True)

                if self.config_id.company_id.is_order_rounding and self.config_id.company_id.apply_rounding_type  and self.config_id.company_id.rounding_method_id:
                    rounding_diff_key = (order.currency_id)
                    if order.rounding_payment:
                        rounding_difference[rounding_diff_key] = self._update_amounts(rounding_difference[rounding_diff_key], {'amount': order.rounding_payment}, order.date_order)

                # Increasing current partner's customer_rank
                partners = (order.partner_id | order.partner_id.commercial_partner_id)
                partners._increase_rank('customer_rank')

        if self.company_id.anglo_saxon_accounting:
            global_session_pickings = self.picking_ids.filtered(lambda p: not p.pos_order_id)
            if global_session_pickings:
                stock_moves = self.env['stock.move'].sudo().search([
                    ('picking_id', 'in', global_session_pickings.ids),
                    ('company_id.anglo_saxon_accounting', '=', True),
                    ('product_id.categ_id.property_valuation', '=', 'real_time'),
                ])
                for move in stock_moves:
                    exp_key = move.product_id._get_product_accounts()['expense']
                    out_key = move.product_id.categ_id.property_stock_account_output_categ_id
                    amount = -sum(move.stock_valuation_layer_ids.mapped('value'))
                    stock_expense[exp_key] = self._update_amounts(stock_expense[exp_key], {'amount': amount}, move.picking_id.date)
                    if move.location_id.usage == 'customer':
                        stock_return[out_key] = self._update_amounts(stock_return[out_key], {'amount': amount}, move.picking_id.date)
                    else:
                        stock_output[out_key] = self._update_amounts(stock_output[out_key], {'amount': amount}, move.picking_id.date)
        MoveLine = self.env['account.move.line'].with_context(check_move_validity=False)

        data.update({
            'mdr_company':mdr_company,
            'mdr_customer':mdr_customer,
            'taxes':                               taxes,
            'sales':                               sales,
            'sales_discounts':                      sales_discounts,
            'total_discount_amount_percent':        total_discount_amount_percent,
            'stock_expense':                       stock_expense,
            'split_receivables':                   split_receivables,
            'combine_receivables':                 combine_receivables,
            'split_receivables_cash':              split_receivables_cash,
            'combine_receivables_cash':            combine_receivables_cash,
            'invoice_receivables':                 invoice_receivables,
            'stock_return':                        stock_return,
            'stock_output':                        stock_output,
            'order_account_move_receivable_lines': order_account_move_receivable_lines,
            'rounding_difference':                 rounding_difference,
            'MoveLine':                            MoveLine
        })
        return data

    # OVERRIDE
    def _create_non_reconciliable_move_lines(self, data):
        # Create account.move.line records for
        #   - sales
        #   - taxes
        #   - stock expense
        #   - non-cash split receivables (not for automatic reconciliation)
        #   - non-cash combine receivables (not for automatic reconciliation)
        taxes = data.get('taxes')
        sales = data.get('sales')
        total_discount_amount_percent = data.get('total_discount_amount_percent')
        sales_discounts = data.get('sales_discounts')
        mdr_company = data.get('mdr_company')
        mdr_customer = data.get('mdr_customer')
        stock_expense = data.get('stock_expense')
        split_receivables = data.get('split_receivables')
        combine_receivables = data.get('combine_receivables')
        rounding_difference = data.get('rounding_difference')
        MoveLine = data.get('MoveLine')

        tax_vals = [self._get_tax_vals(key, amounts['amount'], amounts['amount_converted'], amounts['base_amount_converted']) for key, amounts in taxes.items() if amounts['amount']]
        # Check if all taxes lines have account_id assigned. If not, there are repartition lines of the tax that have no account_id.
        tax_names_no_account = [line['name'] for line in tax_vals if line['account_id'] == False]
        if len(tax_names_no_account) > 0:
            error_message = _(
                'Unable to close and validate the session.\n'
                'Please set corresponding tax account in each repartition line of the following taxes: \n%s'
            ) % ', '.join(tax_names_no_account)
            raise UserError(error_message)
        rounding_vals = []

        rounding_vals = [self._get_rounding_difference_vals(key, amounts['amount'], amounts['amount_converted']) for key, amounts in rounding_difference.items()]
        mdr_customer_deatil_aml = [self._get_mdr_customer_vals(key, amounts['amount'], amounts['amount_converted']) for key, amounts in mdr_customer.items()]
        if mdr_customer_deatil_aml:
            mdr_customer_deatil_aml = mdr_customer_deatil_aml[0]
        mdr_company_detail_aml = [self._get_mdr_company_vals(key, amounts['amount'], amounts['amount_converted']) for key, amounts in mdr_company.items()]
        dict_move_line = (tax_vals
            + [self._get_sale_discount_vals(key, amounts['amount'], amounts['amount_converted']) for key, amounts in sales_discounts.items() if amounts['amount']]
            + [self._get_sale_vals(key, amounts['amount'], amounts['amount_converted']) for key, amounts in sales.items()]
            + mdr_customer_deatil_aml
            + mdr_company_detail_aml
            # + [self._get_stock_expense_vals(key, amounts['amount'], amounts['amount_converted']) for key, amounts in stock_expense.items()]
            + [self._get_split_receivable_vals(key, amounts['amount'], amounts['amount_converted']) for key, amounts in split_receivables.items()]
            + [self._get_combine_receivable_vals(key, amounts['amount'], amounts['amount_converted']) for key, amounts in combine_receivables.items()]
            + rounding_vals)

        dict_move_line = [ x for x in dict_move_line if x] # Check if there is None value

        MoveLine.create(
            dict_move_line
        )
        return data

    def _create_stock_output_lines(self, data):
        # # Keep reference to the stock output lines because
        # # they are reconciled with output lines in the stock.move's account.move.line
        # MoveLine = data.get('MoveLine')
        # stock_output = data.get('stock_output')
        # stock_return = data.get('stock_return')

        # stock_output_vals = defaultdict(list)
        # stock_output_lines = {}
        # for stock_moves in [stock_output, stock_return]:
        #     for account, amounts in stock_moves.items():
        #         stock_output_vals[account].append(self._get_stock_output_vals(account, amounts['amount'], amounts['amount_converted']))

        # for output_account, vals in stock_output_vals.items():
        #     stock_output_lines[output_account] = MoveLine.create(vals)

        # data.update({'stock_output_lines': stock_output_lines})
        return data

    def _credit_amounts(self, partial_move_line_vals, amount, amount_converted, force_company_currency=False):
        """ `partial_move_line_vals` is completed by `credit`ing the given amounts.

        NOTE Amounts in PoS are in the currency of journal_id in the session.config_id.
        This means that amount fields in any pos record are actually equivalent to amount_currency
        in account module. Understanding this basic is important in correctly assigning values for
        'amount' and 'amount_currency' in the account.move.line record.

        :param partial_move_line_vals dict:
            initial values in creating account.move.line
        :param amount float:
            amount derived from pos.payment, pos.order, or pos.order.line records
        :param amount_converted float:
            converted value of `amount` from the given `session_currency` to company currency

        :return dict: complete values for creating 'amount.move.line' record
        """
        if self.is_in_company_currency or force_company_currency:
            additional_field = {}
        else:
            additional_field = {
                'amount_currency': -amount,
                'currency_id': self.currency_id.id,
            }
        data = {
            'debit': -amount_converted if amount_converted < 0.0 else 0.0,
            'credit': amount_converted if amount_converted > 0.0 else 0.0,
            **partial_move_line_vals,
            **additional_field,
        }
        if partial_move_line_vals.get('currency_id') and partial_move_line_vals.get('currency_id') != self.company_id.currency_id.id:
            currency = self.env['res.currency'].browse(partial_move_line_vals['currency_id'])
            data['debit'] = currency._convert(data['debit'], self.company_id.currency_id, self.company_id,fields.Datetime.now())
            data['credit'] = currency._convert(data['credit'], self.company_id.currency_id, self.company_id,fields.Datetime.now())
            data['amount_currency'] = -amount
        return data


    def _debit_amounts(self, partial_move_line_vals, amount, amount_converted, force_company_currency=False):
        """ `partial_move_line_vals` is completed by `debit`ing the given amounts.

        See _credit_amounts docs for more details.
        """
        if self.is_in_company_currency or force_company_currency:
            additional_field = {}
        else:
            additional_field = {
                'amount_currency': amount,
                'currency_id': self.currency_id.id,
            }
        data = {
            'debit': amount_converted if amount_converted > 0.0 else 0.0,
            'credit': -amount_converted if amount_converted < 0.0 else 0.0,
            **partial_move_line_vals,
            **additional_field,
        }
        if partial_move_line_vals.get('currency_id') and partial_move_line_vals.get('currency_id') != self.company_id.currency_id.id:
            currency = self.env['res.currency'].browse(partial_move_line_vals['currency_id'])
            data['debit'] = currency._convert(data['debit'], self.company_id.currency_id, self.company_id,fields.Datetime.now())
            data['credit'] = currency._convert(data['credit'], self.company_id.currency_id, self.company_id,fields.Datetime.now())
            data['amount_currency'] = amount
        return data

    def _get_split_receivable_vals(self, data_arr, amount, amount_converted):
        payment = data_arr[0]
        partial_vals = {
            'account_id': payment.payment_method_id.receivable_account_id.id,
            'move_id': self.move_id.id,
            'currency_id':payment.currency_id.id,
            'partner_id': self.env["res.partner"]._find_accounting_partner(payment.partner_id).id,
            'name': '%s - %s' % (self.name, payment.payment_method_id.name),
        }
        if payment.payment_method_id.jr_use_for:
            partial_vals.update({
                'account_id': self.config_id.gift_card_account_id.id,
            })
        return self._debit_amounts(partial_vals, amount, amount_converted)
    
    def _get_combine_receivable_vals(self, data_arr, amount, amount_converted):
        payment_method = data_arr[0]
        currency = data_arr[1]
        partial_vals = {
            'account_id': payment_method.receivable_account_id.id,
            'move_id': self.move_id.id,
            'currency_id':currency.id,
            'name': '%s - %s' % (self.name, payment_method.name)
        }
        if payment_method.jr_use_for and self.config_id.enable_gift_card:
            if not self.config_id.gift_card_account_id:
                raise Warning(_("Please set gift card account in pos config first."))
            partial_vals.update({
                'account_id': self.config_id.gift_card_account_id.id,
            })
        return self._debit_amounts(partial_vals, amount, amount_converted)

    def _get_sale_vals(self, key, amount, amount_converted):
        account_id, sign, tax_keys, base_tag_ids,currency = key
        tax_ids = set(tax[0] for tax in tax_keys)
        applied_taxes = self.env['account.tax'].browse(tax_ids)
        title = 'Sales' if sign == 1 else 'Refund'
        name = '%s untaxed' % title
        if applied_taxes:
            name = '%s with %s' % (title, ', '.join([tax.name for tax in applied_taxes]))

        partial_vals = {
            'name': name,
            'account_id': account_id,
            'currency_id':currency.id,
            'move_id': self.move_id.id,
            'tax_ids': [(6, 0, tax_ids)],
            'tax_tag_ids': [(6, 0, base_tag_ids)],
        }

        return self._credit_amounts(partial_vals, amount, amount_converted)

    def _get_tax_vals(self, key, amount, amount_converted, base_amount_converted):
        account_id, repartition_line_id, tax_id, tag_ids,currency = key
        tax = self.env['account.tax'].browse(tax_id)
        partial_args = {
            'name': tax.name,
            'account_id': account_id,
            'move_id': self.move_id.id,
            'currency_id':currency.id,
            'tax_base_amount': abs(base_amount_converted),
            'tax_repartition_line_id': repartition_line_id,
            'tax_tag_ids': [(6, 0, tag_ids)],
        }
        return self._debit_amounts(partial_args, amount, amount_converted)

    def _get_sale_discount_vals(self, key, amount, amount_converted):
        account_id, sign,currency, promotion = key
        name = 'Discount'
        if promotion and promotion.promotion_product_discount_id:
            name = 'Discount'
        if sign < 0:
            name="Discount Return / Price increase from pricelist"
        partial_args = {
            'name': name,
            'account_id': account_id,
            'currency_id':currency.id,
            'move_id': self.move_id.id,
        }
        if sign > 0:
            return self._debit_amounts(partial_args, amount, amount_converted)
        else:
            return self._debit_amounts(partial_args, amount, amount_converted)

    def _get_rounding_difference_vals(self,key, amount, amount_converted):
        currency = key[0]
        if self.config_id.company_id.is_order_rounding and self.config_id.company_id.apply_rounding_type  and self.config_id.company_id.rounding_method_id:
            partial_args = {
                'name': 'Rounding line',
                'move_id': self.move_id.id,
                'currency_id':currency.id,
            }
            if float_compare(0.0, amount, precision_rounding=self.currency_id.rounding) < 0:    # loss
                partial_args['name'] =  'Rounding line (Loss)'
                partial_args['account_id'] = self.config_id.company_id.rounding_method_id.loss_account_id.id
                return self._debit_amounts(partial_args, -amount, -amount_converted)

            if float_compare(0.0, amount, precision_rounding=self.currency_id.rounding) > 0:   # profit
                partial_args['name'] =  'Rounding line (Profit)'
                partial_args['account_id'] = self.config_id.company_id.rounding_method_id.profit_account_id.id
                return self._credit_amounts(partial_args, amount, amount_converted)

    def _get_mdr_customer_vals(self, key, amount, amount_converted):
        payment_method, sign,currency = key
        name = 'MDR (Customer)'
        if not payment_method.mdr_intermediary_account_id:
            raise ValidationError(_('Please set the MDR Intermediary Account for payment method '+payment_method.name+'.'))
        if sign > 0:
            partial_args = {
                'name': name,
                'account_id': payment_method.receivable_account_id.id,
                'currency_id':currency.id,
                'move_id': self.move_id.id,
            }
            debit = self._debit_amounts(partial_args, amount, amount_converted)
            partial_args = {
                'name': name,
                'account_id': payment_method.mdr_intermediary_account_id.id,
                'move_id': self.move_id.id,
                'currency_id':currency.id,
            }
            credit = self._credit_amounts(partial_args, amount, amount_converted)
            return [debit,credit]
        else:
            partial_args = {
                'name': name,
                'account_id': payment_method.receivable_account_id.id,
                'move_id': self.move_id.id,
                'currency_id':currency.id,
            }
            credit = self._credit_amounts(partial_args, amount, amount_converted)
            partial_args = {
                'name': name,
                'account_id': payment_method.mdr_intermediary_account_id.id,
                'move_id': self.move_id.id,
                'currency_id':currency.id,
            }
            debit = self._debit_amounts(partial_args, amount, amount_converted)
            return [debit,credit]


    def _get_mdr_company_vals(self, key, amount, amount_converted):
        payment_method, sign,currency = key
        name = 'MDR (Company)'
        if not payment_method.mdr_intermediary_account_id:
            raise ValidationError(_('Please set the MDR Intermediary Account for payment method '+payment_method.name+'.'))
        if sign > 0:
            partial_args = {
                'name': name,
                'account_id': payment_method.mdr_intermediary_account_id.id,
                'move_id': self.move_id.id,
                'currency_id':currency.id,
            }
            debit = self._debit_amounts(partial_args, amount, amount_converted)
            return debit
        else:
            partial_args = {
                'name': name,
                'account_id': payment_method.mdr_intermediary_account_id.id,
                'move_id': self.move_id.id,
                'currency_id':currency.id,
            }
            credit = self._credit_amounts(partial_args, amount, amount_converted)
            return credit

    def _reconcile_account_move_lines(self, data):
        # reconcile cash receivable lines
        split_cash_statement_lines = data.get('split_cash_statement_lines')
        combine_cash_statement_lines = data.get('combine_cash_statement_lines')
        split_cash_receivable_lines = data.get('split_cash_receivable_lines')
        combine_cash_receivable_lines = data.get('combine_cash_receivable_lines')
        order_account_move_receivable_lines = data.get('order_account_move_receivable_lines')
        invoice_receivable_lines = data.get('invoice_receivable_lines')
        stock_output_lines = data.get('stock_output_lines')

        
        for statement in self.statement_ids:
            if not 'skip_transactions_creation' in data:
                if not self.config_id.cash_control:
                    statement.write({'balance_end_real': statement.balance_end})

                statement.button_post()
                all_lines = (
                      split_cash_statement_lines[statement].mapped('move_id.line_ids').filtered(lambda aml: aml.account_id.internal_type == 'receivable' and not aml.reconciled)
                    | combine_cash_statement_lines[statement].mapped('move_id.line_ids').filtered(lambda aml: aml.account_id.internal_type == 'receivable'  and not aml.reconciled)
                    | split_cash_receivable_lines[statement]
                    | combine_cash_receivable_lines[statement]
                )
                accounts = all_lines.mapped('account_id')
                lines_by_account = [all_lines.filtered(lambda l: l.account_id == account and not l.reconciled) for account in accounts]
                for lines in lines_by_account:
                    lines.reconcile()
                # We try to validate the statement after the reconciliation is done because validating the statement requires each statement line to be
                # reconciled. Furthermore, if the validation failed, which is caused by unreconciled cash difference statement line, we just ignore that. 
                # Leaving the statement not yet validated. Manual reconciliation and validation should be made by the user in the accounting app.
                
                try:
                    statement.button_validate()
                except UserError:
                    pass

        # reconcile invoice receivable lines
        for account_id in order_account_move_receivable_lines:
            ( order_account_move_receivable_lines[account_id]
            | invoice_receivable_lines.get(account_id, self.env['account.move.line'])
            ).reconcile()

        # reconcile stock output lines
        pickings = self.picking_ids.filtered(lambda p: not p.pos_order_id)
        pickings |= self.order_ids.filtered(lambda o: not o.is_invoiced).mapped('picking_ids')
        stock_moves = self.env['stock.move'].search([('picking_id', 'in', pickings.ids)])
        stock_account_move_lines = self.env['account.move'].search([('stock_move_id', 'in', stock_moves.ids)]).mapped('line_ids')
        # for account_id in stock_output_lines:
        #     ( stock_output_lines[account_id]
        #     | stock_account_move_lines.filtered(lambda aml: aml.account_id == account_id)
        #     ).filtered(lambda aml: not aml.reconciled).reconcile()
        return data



    @api.depends('config_id', 'statement_ids', 'payment_method_ids')
    def _compute_cash_all(self):
        res = super(PosSession, self)._compute_cash_all()
        for ss in self:
            ss.cash_control = ss.config_id.bnk_cash_control
        return res

    def open_cashbox_pos(self):
        res = super(PosSession, self).open_cashbox_pos()
        res['context']['default_cashbox_lines_ids'] = self.pos_config_cashbox_lines_ids.ids
        o_balance = 0
        # self.cash_opening_balance = o_balance
        if not len(self.pos_config_cashbox_lines_ids.ids) > 0 and self.cash_opening_balance==0:
            raise ValidationError(_('Please set the opening balance first!'))
        else:
            for line in self.pos_config_cashbox_lines_ids:
                o_balance += line.subtotal
            self.cash_opening_balance = o_balance
            if self.config_id:
                self.state = 'opened'
                return self.config_id.open_ui()

    def close_cashbox_pos(self):
        self.ensure_one()
        action = self.with_context({
            'balance': 'close',
            'default_is_closing_line': True,
            'default_cashbox_lines_ids': False,
            'default_pos_session_id': self.id,
            'default_pos_id': self.config_id.id,
        }).cash_register_id.open_cashbox_id()
        action['view_id'] = self.env.ref('point_of_sale.view_account_bnk_stmt_cashbox_footer').id
        return action

    @api.model
    def create(self, vals):
        print('---------- Session Created ---------', vals)
        if self._context.get('active_id'):
            self = self.env['pos.session'].browse(int(self._context.get('active_id')))
        if self._context.get('default_is_closing_wizard'):
            for i in vals.get('pos_config_cashbox_clsosing_line_ids'):
                aa = self.search([
                ('state', '!=', 'closed'),
                ('config_id', '=', self.config_id.id),
                ('rescue', '=', False)])
                print('---------- vals ---------', i[2].get('coin_value')*i[2].get('number'),self.config_id,self.rescue,self.state)
                i[2].update({
                    # 'pos_config_id': self.config_id.id,
                    'is_closing_line': True,
                    'pos_session_id': self.id
                })
            if self.config_id:
                vals.update({'config_id': self.config_id.id})

        print('---------- vals-22222 ---------',vals)

        config = self.env['pos.config'].browse(vals.get('config_id'))
        if config.pos_branch_id:
            vals.update({'pos_branch_id': config.pos_branch_id.id})
        else:
            vals.update({'pos_branch_id': self.env['res.branch'].sudo().get_default_branch()})

        user_branch_ids = []
        if self.env.user.branch_ids:
            user_branch_ids = self.env.user.branch_ids.ids

        if config.pos_branch_id.id not in user_branch_ids:
            raise UserError('This POS assigned to Branch "%s" \n'
                            'But your account not set Branch, \n'
                            'Please go to Settings / Users & Companies / User and config your User \n'
                            'Have the same Branch with this POS Setting' % config.pos_branch_id.name)

        cash_bal_data = []
        for line in  config.pos_cashbox_lines_ids:
            temp_vals = {}
            temp_vals['coin_value'] = line.coin_value
            temp_vals['number'] = line.number
            cash_bal_data.append([0,0,temp_vals])

        vals.update({'pos_config_cashbox_lines_ids':cash_bal_data})
        vals.update({'pos_config_cashbox_lines_ids': cash_bal_data})
        print("\n\n\n All Data ",vals)

        session = super(PosSession, self).create(vals)

        session.update_stock_at_closing = config.point_of_sale_update_stock_quantities == "closing"
        if session.state == 'opening_control' and session.config_id.cash_control and session.config_id.default_set_cash_open:
            session.set_cashbox_pos(session.config_id.default_set_cash_amount,
                                    session.config_id.default_set_cash_notes or 'Automatic')
        return session

    def set_cashbox_pos(self, cashbox_value, notes):
        res = super(PosSession, self).set_cashbox_pos(cashbox_value, notes)
        _logger.info('[set_cashbox_pos] with cashbox_value %s and notes %s' % (cashbox_value, notes))
        return res

    @api.constrains('config_id')
    def _check_pos_config(self):  # todo: we need open multi session base on 1 POS CONFIG
        config = self.config_id
        if config.multi_session:
            return True
        else:
            return super(PosSession, self)._check_pos_config()

    def get_session_by_employee_id(self, employee_id, pos_config_id):
        _logger.info(
            '[Begin] get_session_by_employee_id for employee_id %s and pos_config_id %s' % (employee_id, pos_config_id))
        employee = self.env['hr.employee'].browse(employee_id)
        session_opened = self.search([
            ('employee_id', '=', None),
            ('config_id', '=', pos_config_id),
            ('state', '=', 'opened'),
        ], limit=1)
        if session_opened:
            session_opened.write({'employee_id': employee_id})
            return {
                'session': session_opened.search_read([('id', '=', session_opened.id)], [])[0],
                'login_number': session_opened.login(),
                'state': 'blank',
            }
        session = self.search([
            ('employee_id', '=', employee_id),
            ('config_id', '=', pos_config_id),
            ('state', '!=', 'closed'),
        ], limit=1)
        if session:
            return {
                'session': session.search_read([('id', '=', session.id)], [])[0],
                'login_number': session.login(),
                'state': 'opened',
            }
        else:
            session = self.env['pos.session'].sudo().create({
                'user_id': self.env.user.id,
                'config_id': pos_config_id,
                'employee_id': employee_id,
            })
            session.write({'name': session.name + '( %s )' % employee.name})
            return {
                'session': session.search_read([('id', '=', session.id)], [])[0],
                'login_number': session.login(),
                'state': 'new',
            }
        
    def register_license(self, license):
        if license:
            isValid = crypt_context.verify_and_update(self.env.cr.dbname, license)[0]
            if isValid:
                self.env['ir.config_parameter'].sudo().set_param('license', license)
        else:
            return False
        return isValid

    def force_action_pos_session_close(self):
        for session in self:
            session.with_context(force_close=1)._validate_session()
            _logger.info('[force_action_pos_session_close] closed session: %s' % session.name)
        return True

    def action_pos_session_closing_control(self):
        for session in self:
            if not session.config_id.allow_closing_session and not self.env.user.has_group(
                    'point_of_sale.group_pos_manager'):
                raise UserError(_('You have not permission closing session \n'
                                  'Please request Manager or admin \n'
                                  '1. Go to POS Setting / Security tab and check to field Allow Closing Session \n'
                                  '2. Or you are become Point of Sale Admin'))
            orders = self.env['pos.order'].search([
                ('state', '=', 'draft'),
                ('session_id', '=', session.id),
            ])
            _logger.info('orders not full fill payment: %s' % orders)
            for order in orders:
                if order._is_pos_order_paid():
                    order.action_pos_order_paid()
                    self.env.cr.commit()
                else:
                    order.write({'state': 'quotation'})
            self.env['pos.backup.orders'].search([
                ('config_id', '=', session.config_id.id)
            ]).unlink()
        res = super(PosSession, self).action_pos_session_closing_control()
        self.create_invoice_from_sessions()


        """
        If member selected and payment method is receivable = True:
            - Every order has own invoice
            - If 5 orders then create 5 invoices too
        """
        for session in self:
            values = []
            values += self._prepare_invoice_for_receivable(session)
            for value in values:
                move = self.env['account.move'].sudo().create(value)
                if move.line_ids:
                    move.action_post() # set status to POSTED
                    self.register_payment_for_receivable(move)

        for session in self:
            session.config_id.write({ 'write_date': fields.Datetime.now() })

        # return self.env.ref('equip3_pos_general.report_pos_sales_pdf').report_action(self)
        return True


    def _prepare_invoice_for_receivable(self, session):
        self.ensure_one()
        values = []
        query = '''
            SELECT po.partner_id, array_agg(po.id)
            FROM pos_order AS po
            INNER JOIN res_partner AS rp ON rp.id = po.partner_id
            LEFT JOIN pos_payment AS pp ON pp.pos_order_id = po.id
            LEFT JOIN pos_payment_method AS ppm ON ppm.id = pp.payment_method_id
            WHERE po.return_order_id IS NULL 
                AND po.session_id = {session_id}
                AND ppm.is_receivables = 't'
            GROUP BY po.partner_id
        '''.format(session_id=session.id)
        self._cr.execute(query)
        results = dict(self._cr.fetchall())
        if not results:
            return []

        for partner_id in results:
            partner = self.env['res.partner'].browse(int(partner_id))
            order_ids = results[partner_id]
            orders = self.env['pos.order'].search([('id','in',order_ids)])

            for pos_order in orders:
                line_ids, first_vals, second_vals = [], [], []
                first_account_id = partner.property_account_receivable_id
                second_account_id = False

                payment_method_name = ''
                amount = 0
                for payment in pos_order.payment_ids:
                    payment_method = payment.payment_method_id
                    if payment_method.is_receivables:
                        amount += payment.amount
                        payment_method_name += payment_method_name and f', {payment_method.name}' or payment_method.name
                        second_account_id = payment_method.receivable_account_id

                if not first_account_id:
                    raise ValidationError(_(f'Please configure Account Receivable in member "{partner.name}"'))
                if not second_account_id:
                    raise ValidationError(_(f'Please configure Intermediary Account in Payment methods: "{payment_method_name}"'))

                analytic_group_id = self.env['account.analytic.tag'].search([], limit=1)

                journal_id = session.config_id.journal_id # From pos.config -> Sales Journal
                first_vals = {
                    'debit' : amount, 
                    'credit' : 0,
                    'name' : '%s' % first_account_id.name, 
                    'account_id' : first_account_id.id,
                    'currency_id' : session.currency_id.id,
                    'company_id' : session.company_id.id,
                }
                second_vals = {
                    'debit' : 0, 
                    'credit' : amount, 
                    'name' : '%s' % second_account_id.name, 
                    'account_id' : second_account_id.id,
                    'currency_id' : session.currency_id.id,
                    'company_id' : session.company_id.id,
                }

                invoice_line_ids = []
                invoice_line_ids.append(( 0, 0, {
                    'product_id' : False,
                    'name' : '%s' % second_account_id.name, 
                    'account_id' : second_account_id.id,
                    'quantity' : 1,
                    'product_uom_id' : False,
                    'analytic_tag_ids': [[6, False, [analytic_group_id.id]]], 
                    'tax_ids': [],
                    'price_unit' : amount,
                    'discount_amount' : 0,
                }))

                values += [{
                    'partner_id': partner.id,
                    'date': fields.Date.context_today(self),
                    'invoice_date': fields.Date.context_today(self),
                    'move_type': 'out_invoice',
                    'ref': 'POS Payment Credit - ' + str(pos_order.name),
                    'origin': 'POS - ' + session.name,
                    'pos_session_id': session.id,
                    'pos_order_id': pos_order.id,
                    'journal_id': journal_id.id,
                    'invoice_line_ids': invoice_line_ids,
                    'line_ids': [(0, 0, first_vals), (0, 0, second_vals)],
                    'branch_id': session.pos_branch_id.id,
                    'pos_branch_id': session.pos_branch_id.id,
                    'is_from_pos_receivable': True,
                }]

        return values

    def register_payment_for_receivable(self, move):
        RegisterPayment = self.env['account.payment.register']
        
        payment_list = move.pos_order_id.payment_ids.filtered(lambda p: p.payment_method_id.is_receivables == False)
        pay_amount_residual = 0
        for payment in payment_list:
            if not move.amount_residual:
                break
            amount = payment.amount + pay_amount_residual
            if amount > move.amount_residual:
                amount = move.amount_residual
                pay_amount_residual = amount - move.amount_residual
            else:
                pay_amount_residual = 0
            journal_id = payment.payment_method_id.account_journal_id
            if not journal_id:
                raise UserError(_('Please set Journal for payment method "%s"' % payment.payment_method_id.name))

            context = self._context and self._context.copy() or {}
            context.update({
                'active_model': 'account.move', 
                'active_ids': [move.id],
                'active_id': move.id,
                'dont_redirect_to_payments': True,
            })
            fields_list = [
                'payment_date', 'payment_difference_handling', 
                'start_date', 'recurring_interval', 
                'recurring_interval_unit', 'stop_recurring_interval', 'move_type', 'active_manual_currency_rate',
                'administration_fee', 'current_rate_id', 'current_inverse_rate_id', 'line_ids']
            default_values = RegisterPayment.with_context(context).default_get(fields_list)
            default_values.update({
                'can_edit_wizard': True, 
                'payment_type': 'inbound', 
                'partner_type': 'customer', 
                'amount': payment.amount, 
                'currency_id': move.currency_id.id, 
                'company_id': move.company_id.id, 
                'branch_id': move.branch_id.id, 
                'partner_id': move.partner_id and move.partner_id.id or False, 
                'communication': move.name, 
                'journal_id': journal_id.id, 
            })
            register = RegisterPayment.with_context(context).create(default_values)
            register.action_create_payments()

        return True

    def create_invoice_from_sessions(self):
        for pos_session in self:
            payment_method_data = {}
            order_ids = self.env['pos.order'].search([('session_id', '=', pos_session.id)])
            for order in order_ids:
                for payment in order.payment_ids:
                    payment_method = payment.payment_method_id
                    if payment.amount > 0.0 and payment.payment_method_id.generate_invoice:
                        if not payment.payment_method_id.invoice_partner_id:
                            raise UserError('Invoice partner is missing in POS payment method : %s' % payment.payment_method_id.name)
                        if not payment.payment_method_id.receivable_account_id:
                            raise UserError('Receivable account is missing in POS payment method : %s' % payment.payment_method_id.name)
                        
                        amount = payment.amount - payment.mdr_amount
                        vals = {
                            'amount': amount,
                            'payment': payment,
                            'order': order,
                            'mdr_customer': 0,
                            'mdr_intermediary_account_id': False,
                        }

                        if payment.mdr_paid_by == 'Customer':
                            vals['mdr_customer'] = payment.mdr_amount
                            if payment_method.mdr_intermediary_account_id:
                                vals['mdr_intermediary_account_id'] = payment_method.mdr_intermediary_account_id.id
                            else:
                                raise UserError('MDR Intermediary Account is missing in POS payment method : %s' % payment.payment_method_id.name)

                        if payment_method in payment_method_data:
                            payment_method_data[payment_method] = payment_method_data[payment_method]  + [vals]
                        else:
                            payment_method_data[payment_method] = [vals]
            for payment in payment_method_data:
                datas = payment_method_data.get(payment)
                vals = self._prepare_invoice_vals_from_payment(datas, payment, pos_session)
                move = self.env['account.move'].sudo().create(vals)
                for line in move.invoice_line_ids:
                    line._onchange_product_id()

        return True

    def _prepare_invoice_vals_from_payment(self, datas, payment_method, pos_session):
        default_journal_id = self.env['account.journal'].search([
            ('type', '=', 'sale'),
            ('company_id', '=', self.env.company.id),
        ], limit=1)

        invoice_line_ids = []
        count = 1
        for line in datas:
            price = line.get('amount', 0)
            if line.get('mdr_customer'):
                price += line.get('mdr_customer', 0)

            order = line.get('order')
            payment = line.get('payment')
            name = order.name
            line_vals = {
                'name': name,
                'approval_code': payment.approval_code,
                'account_id': payment.payment_method_id.receivable_account_id.id,
                'price_unit': price,
                'price_unit': price,
                'price_subtotal': price,
                'price_total': price,
                'tax_ids':False,
                'quantity': 1,
            }
            invoice_line_ids.append((0, 0, line_vals))

            if line.get('mdr_customer'):
                price = -1 * line.get('mdr_customer', 0)
                invoice_line_ids.append((0, 0, {
                    'name': 'MDR Customer',
                    'account_id': line['mdr_intermediary_account_id'],
                    'price_unit': price,
                    'price_subtotal': price,
                    'tax_ids': False,
                    'price_total': price,
                    'quantity': 1,
                }))

        return {
            'date': fields.Date.context_today(self),
            'invoice_date': fields.Date.context_today(self),
            'ref': pos_session.name,
            'origin': pos_session.name,
            'move_type': 'out_invoice',
            'pos_session_id': pos_session.id,
            'currency_id': self.env.user.company_id.currency_id.id,
            'company_id': self.env.user.company_id.id,
            'partner_id': payment_method.invoice_partner_id.id,
            'journal_id': default_journal_id and default_journal_id.id,
            'invoice_line_ids': invoice_line_ids
        }

    def _get_backup_session(self, order):
        # todo 1: we create new pos session or get pos session rescue, and add pos_session_id of draft order to this session
        # todo 2: for current session can close and rescue session use next session
        closed_session = order.session_id
        rescue_session = self.search([
            ('state', 'not in', ('closed', 'closing_control')),
            ('rescue', '=', True),
            ('config_id', '=', closed_session.config_id.id),
        ], limit=1)
        if rescue_session:
            return rescue_session.id
        new_session = self.create({
            'config_id': closed_session.config_id.id,
            'name': _('(SESSION BACKUP FOR %s, save Orders not full full payments)' %  closed_session.name ),
            'rescue': True,
            'backup_session': True,
        })
        new_session.action_pos_session_open()
        return new_session.id

    def getExpiredDays(self):
        license_started_date = self.env['ir.config_parameter'].sudo().get_param('license_started_date')
        license = self.env['ir.config_parameter'].sudo().get_param('license')
        isValid = False
        if not license_started_date:
            return {
                'Code': 403,
                'usedDays': 0,
                'isValid': isValid
            }
        else:
            started_date = datetime.strptime(license_started_date, DEFAULT_SERVER_DATE_FORMAT)
            today = datetime.today()
            usedDays = (today - started_date).days
            if license:
                isValid = crypt_context.verify_and_update(self.env.cr.dbname, license)[0]
            if started_date > today:
                return {
                    'Code': 200,
                    'isValid': False,
                    'usedDays': 31
                }
            else:
                return {
                    'Code': 200,
                    'isValid': isValid,
                    'usedDays': usedDays
                }

    def _check_if_no_draft_orders(self):
        orders_not_done = self.order_ids.filtered(
            lambda order: order.state not in ['cancel', 'paid', 'done', 'invoiced'] and order.is_payment_method_with_receivable == False)
        if len(orders_not_done) >= 1:
            for session in self:
                if session.rescue:
                    raise UserError(_('It not possible close session backup if have orders not full fill payment, \n '
                                      'Please register payment or cancel orders with reference in list:  %s ' % [
                                          order.pos_reference for order in orders_not_done]))
            _logger.warning('Total orders_not_done is %s' % len(orders_not_done))
            # TODO: normally when pos closing session, if have any orders draft, Odoo Original not allow closing Session
            # So, system can not drop orders draft. and need keep orders existing system like a Quotation Order
            # So, we create new session like Rescue Session and save all Orders draft/quotation state to it
            for order in orders_not_done:
                rescue_session_id = self._get_backup_session(order)
                order.write({'session_id': rescue_session_id})
                self.env.cr.commit()
        return super(PosSession, self)._check_if_no_draft_orders()

    def action_pos_session_validate(self):
        for session in self:
            orders = self.env['pos.order'].search([
                ('state', '=', 'draft'),
                ('session_id', '=', session.id),
                ('picking_ids', '=', None)
            ])
            for order in orders:
                if order._is_pos_order_paid():
                    order.action_pos_order_paid()
                    self.env.cr.commit()

        result = super(PosSession, self).action_pos_session_validate()
        if type(result) == dict and result.get('tag', '') == 'reload':
            
            for session in self:
                session.config_id.write({ 'write_date': fields.Datetime.now() })

            return self.env.ref('equip3_pos_general.report_pos_sales_pdf').report_action(self)
        else:
            return result

    def lock_session(self, vals):
        return self.sudo().write(vals)

    def login(self):
        res = super(PosSession, self).login()
        self.write({'last_login_time': fields.Datetime.now()})
        return res

    def action_open_move(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('account.action_move_out_invoice_type')
        action['context'] = {
            'default_move_type': 'out_invoice', 
            'is_ppn_invisible': True, 
            'def_invisible': False,
        }

        domain = []
        if self.move_id:
            domain += [('id', '=', self.move_id.id)]
        else:
            domain += [('id', '=', None)]
        action['domain'] = domain

        return action

    def action_open_faktur(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('account.action_move_out_invoice_type')
        action['context'] = {
            'default_move_type': 'out_invoice', 
            'is_ppn_invisible': True, 
            'def_invisible': False,
        }
        action['domain'] = [('pos_session_id', '=', self.id),('origin','=',self.name)]
        return action

    def write(self, vals):
        if vals.get('login_number', None):
            vals.update({
                'opened_at': fields.Datetime.now(),
                'opened_uid': self.env.user.id,
            })
        return super(PosSession, self).write(vals)

    def update_required_reinstall_cache(self):
        return self.write({'required_reinstall_cache': False})

    def get_pos_session(self, session_id):
        if session_id:
            session = self.browse(int(session_id))
        if session:
            if session.user_id.has_group('point_of_sale.group_pos_manager'):
                admin = 1
            else:
                admin = 0
            pos_session = {
                "id": session.id,
                "name": session.name,
                "user_id": [session.user_id.id,
                            session.user_id.name],
                "cash_control": session.cash_control,
                "state": session.state,
                "stop_at": session.stop_at,
                "config_id": [session.config_id.id,
                              session.config_id.display_name],
                "start_at": session.start_at,
                "currency_id": [session.currency_id.id,
                                session.currency_id.name],
                "cash_register_balance_end_real": (
                    session.cash_register_balance_end_real),
                "cash_register_total_entry_encoding": (
                    session.cash_register_total_entry_encoding),
                "cash_register_difference": (
                    session.cash_register_difference),
                "cash_register_balance_start": (
                    session.cash_register_balance_start),
                "cash_register_balance_end": (
                    session.cash_register_balance_end),
                "is_admin": (admin)
            }
            return pos_session
        else:
            return

    def get_cashbox(self, session_id, balance):
        session = self.browse(int(session_id))
        session.ensure_one()
        context = dict(session._context)
        balance_type = balance or 'end'
        context['bank_statement_id'] = session.cash_register_id.id
        context['balance'] = balance_type
        context['default_pos_id'] = session.config_id.id
        cashbox_id = None
        if balance_type == 'start':
            cashbox_id = session.cash_register_id.cashbox_start_id.id
        else:
            cashbox_id = session.cash_register_id.cashbox_end_id.id
        cashbox_line = []
        total = 0
        if cashbox_id:
            accountCashboxLine = self.env['account.cashbox.line'].sudo()
            cashbox = accountCashboxLine.search([
                ('cashbox_id', '=', cashbox_id)
            ])
            if cashbox:
                for line in cashbox:
                    subtotal = line.number * line.coin_value
                    total += subtotal
                    cashbox_line.append({
                        "id": line.id,
                        "number": line.number,
                        "coin_value": line.coin_value,
                    })
        return cashbox_line

    def _validate_session(self):
        self.ensure_one()
        if self.state != 'closing_control' and not self._context.get('force_close'):
            if self.state == 'closed':
                raise UserError("Current session already closed.")
            elif self.state == 'opening_control':
                raise UserError("Current session status is Opening Control, can't closed.")
            elif self.state == 'opened':
                raise UserError("Current session status is In Progress, can't closed.")
            else:
                raise UserError("Can't closed session.")

        if self.order_ids or self.statement_ids.line_ids:
            self.cash_real_transaction = self.cash_register_total_entry_encoding
            self.cash_real_expected = self.cash_register_balance_end
            self.cash_real_difference = self.cash_register_difference
            if self.state == 'closed':
                raise UserError(_('This session is already closed.'))
            self._check_if_no_draft_orders()
            if self.update_stock_at_closing:
                self._create_picking_at_end_of_session()
            # Users without any accounting rights won't be able to create the journal entry. If this
            # case, switch to sudo for creation and posting.
            try:
                self.with_company(self.company_id)._create_account_move()
            except AccessError as e:
                if self.user_has_groups('point_of_sale.group_pos_user'):
                    self.sudo().with_company(self.company_id)._create_account_move()
                else:
                    raise e
            if self.move_id.line_ids:
                # Set the uninvoiced orders' state to 'done'
                self.env['pos.order'].search([('session_id', '=', self.id), ('state', '=', 'paid')]).write(
                    {'state': 'done'})
            else:
                self.move_id.unlink()
        elif not self.cash_register_id.difference:
            cash_register = self.cash_register_id
            cash_register.pos_session_id = False
            cash_register.unlink()
        self.write({'state': 'closed'})


        context = self._context.copy()
        context.update({'pos_session_id': self.id})
        # res = super(PosSession, self.with_context(context))._validate_session()
        if self.move_id and self.pos_branch_id:
            self.env.cr.execute("UPDATE account_move SET pos_branch_id=%s WHERE id=%s" % (
                self.pos_branch_id.id, self.move_id.id))
            self.env.cr.execute("UPDATE account_move_line SET pos_branch_id=%s WHERE move_id=%s" % (
                self.pos_branch_id.id, self.move_id.id))
        vals = {}
        if not self.start_at:
            vals['start_at'] = fields.Datetime.now()
        if not self.stop_at:
            vals['stop_at'] = fields.Datetime.now()
        if vals:
            self.write(vals)
        # if type(res) == dict and res.get('tag', '') == 'reload':
        return self.env.ref('equip3_pos_general.report_pos_sales_pdf').report_action(self)
        # else:
        #     return res

    def get_session_online(self):
        sessions_opened = self.sudo().search([('state', '=', 'opened')])
        return len(sessions_opened)

    def check_expired_license(self):
        license_started_date = self.env['ir.config_parameter'].sudo().get_param('license_started_date')
        if not license_started_date:
            return 366
        else:
            started_date = datetime.strptime(license_started_date, DEFAULT_SERVER_DATE_FORMAT)
            today = datetime.today()
            delta = (today - started_date).days
            return delta

    def _compute_invoice_count(self):
        for record in self:
            # invoices = self.env['account.move'].sudo().search([('pos_session_id', '=', record.id),('origin','=',record.name)])
            domain = [('pos_session_id', '=', record.id),('origin','=',record.name)]
            if record.move_id:
                domain = [('id','=',record.move_id.id)]
            else:
                domain = [('id','=',None)]
            invoice_count = self.env['account.move'].sudo().search_count(domain)
            record.total_invoice_count = invoice_count

    def _compute_total_faktur_count(self):
        for record in self:
            domain = [('pos_session_id', '=', record.id),('origin','=',record.name)]
            total_faktur_count = self.env['account.move'].sudo().search_count(domain)
            record.total_faktur_count = total_faktur_count
        

    def _compute_order_with_receivable_invoice_ids(self):
        order_by_session_id = {}
        if self.ids:
            query = """
                SELECT po.session_id, array_agg(po.id)
                FROM pos_order AS po
                INNER JOIN res_partner AS rp ON rp.id = po.partner_id
                LEFT JOIN pos_payment AS pp ON pp.pos_order_id = po.id
                LEFT JOIN pos_payment_method AS ppm ON ppm.id = pp.payment_method_id
                WHERE po.return_order_id IS NULL 
                    AND po.session_id IN (%s)
                    AND ppm.is_receivables = 't'
                GROUP BY po.session_id
            """ % (str(self.ids)[1:-1])
            self._cr.execute(query)
            order_by_session_id = dict(self._cr.fetchall())

        for record in self:
            order_ids = order_by_session_id.get(record.id, [])
            record.order_with_receivable_invoice_ids = self.env['pos.order'].sudo().search([('id','in',order_ids)])

    def log_cashier_pos(self, action, vals={}):
        self.ensure_one()
        device_id = vals.get('device_id')
        if not device_id:
            return False

        domain = [('session_id','=', self.id), ('name','=', device_id)]
        logs = self.env['pos.session.log.cashier'].sudo().search(domain, limit=10) # find id in log_cashier_ids

        if action == 'login':
            if not logs:
                values = {
                    'session_id': self.id,
                    'name': device_id,
                    'user_id': self.cashier_id and self.cashier_id.id or False,
                    'login_date': fields.Datetime.now(),
                }
                self.env['pos.session.log.cashier'].sudo().create(values)

        if action == 'logout':
            for log in logs:
                log.write({ 'logout_date': fields.Datetime.now() })

        return True

    def get_session_by_cashier_id(self, cashier_id, pos_config_id):
        _logger.info(
            '[Begin] get_session_by_cashier_id for cashier_id %s and pos_config_id %s' % (cashier_id, pos_config_id))
        cashier = self.env['res.users'].browse(cashier_id)
        session_opened = self.search([('cashier_id','=',None),('config_id','=',pos_config_id),('state','=','opened')
        ], limit=1)
        if session_opened:
            session_opened.write({'cashier_id': cashier_id})
            return {
                'session': session_opened.search_read([('id', '=', session_opened.id)], [])[0],
                'login_number': session_opened.login(),
                'state': 'blank',
            }

        session = self.search([('cashier_id','=',cashier_id),('config_id','=',pos_config_id),('state','!=','closed')], limit=1)
        if session:
            return {
                'session': session.search_read([('id', '=', session.id)], [])[0],
                'login_number': session.login(),
                'state': 'opened',
            }
        else:
            session = self.env['pos.session'].sudo().create({
                'user_id': self.env.user.id,
                'config_id': pos_config_id,
                'cashier_id': cashier_id,
            })
            session.write({'name': session.name + '( %s )' % cashier.name})
            return {
                'session': session.search_read([('id', '=', session.id)], [])[0],
                'login_number': session.login(),
                'state': 'new',
            }



    def _get_complement_expense_vals(self, exp_account, amount, amount_converted, move_id):
        partial_args = {'account_id': exp_account.id, 'move_id': move_id.id}
        return self._debit_amounts(partial_args, amount, amount_converted, force_company_currency=True)

    def _get_complement_output_vals(self, exp_account, amount, amount_converted, move_id):
        partial_args = {'account_id': exp_account.id, 'move_id': move_id.id}
        return self._credit_amounts(partial_args, amount, amount_converted, force_company_currency=True)

    def _create_complementary_journal(
            self, stock_complement, stock_output_complement):
        complementary_journal_id = self.config_id.complementary_journal_id
        if not complementary_journal_id:
            raise UserError(_(
                'Complement Journal not available on PoS Configuration'))
        Move = self.env['account.move'].with_context(
            default_journal_id=complementary_journal_id.id).create({
                'journal_id': complementary_journal_id.id,
                'date': fields.Date.context_today(self),
                'ref': self.name,
        })
        MoveLine = self.env['account.move.line'].with_context(check_move_validity=False)
        MoveLine.create([self._get_complement_expense_vals(
            key, amounts['amount'], amounts['amount_converted'], Move) \
            for key, amounts in stock_complement.items()]
            + [self._get_complement_output_vals(
            key, amounts['amount'], amounts['amount_converted'], Move) \
            for key, amounts in stock_output_complement.items()])
        if Move.line_ids:
            Move._post()
        return Move

    # OVERRIDE
    def _create_account_move(self):
        """ Create account.move and account.move.line records for this session.

        Side-effects include:
            - setting self.move_id to the created account.move record
            - creating and validating account.bank.statement for cash payments
            - reconciling cash receivable lines, invoice receivable lines and stock output lines
        """
        journal = self.config_id.journal_id
        # Passing default_journal_id for the calculation of default currency of account move
        # See _get_default_currency in the account/account_move.py.
        account_move = self.env['account.move'].with_context(default_journal_id=journal.id).create({
            'journal_id': journal.id,
            'date': fields.Date.context_today(self),
            'ref': self.name,
            'branch_id': self.pos_branch_id.id, #  add default branch from pos.session
            'pos_branch_id': self.pos_branch_id.id, # add  default branch from pos.session
            'pos_session_id': self.id,
        })
        self.write({'move_id': account_move.id})

        data = {}
        data = self._accumulate_amounts(data)
        data = self._create_non_reconciliable_move_lines(data)
        data = self._create_cash_statement_lines_and_cash_move_lines(data)
        data = self._create_invoice_receivable_lines(data)
        data = self._create_stock_output_lines(data)
        data = self._create_balancing_line(data)

        if account_move.line_ids:
            account_move._post()

        data = self._reconcile_account_move_lines(data)

        amounts = lambda: {'amount': 0.0, 'amount_converted': 0.0}
        stock_complement = defaultdict(amounts)
        stock_output_complement = defaultdict(amounts)
        lines = self.order_ids.mapped('lines').filtered(lambda line: line.is_complementary)
        for order_line in lines:
            product_id = order_line.product_id
            date_order = order_line.order_id.date_order
            exp_key = product_id._get_product_accounts()['expense']
            amount = order_line.qty * product_id.standard_price
            out_key = product_id.categ_id.property_stock_account_output_categ_id
            stock_complement[exp_key] = self._update_amounts(
                stock_complement[exp_key], {'amount': amount},
                date_order, force_company_currency=True)
            stock_output_complement[out_key] = self._update_amounts(
                stock_output_complement[out_key], {'amount': amount},
                date_order, force_company_currency=True)

        if lines:
            self._create_complementary_journal(stock_complement, stock_output_complement)

        return False

    def get_pos_name(self):
        if self and self.config_id:
            return self.config_id.name

    def get_report_timezone(self):
        if self.env.user and self.env.user.tz:
            tz = timezone(self.env.user.tz)
        else:
            tz = pytz.utc
        return tz

    def get_session_date(self, date_time):
        if date_time:
            if self.env.user and self.env.user.tz:
                tz = timezone(self.env.user.tz)
            else:
                tz = pytz.utc
            c_time = datetime.now(tz)
            hour_tz = int(str(c_time)[-5:][:2])
            min_tz = int(str(c_time)[-5:][3:])
            sign = str(c_time)[-6][:1]
            if sign == '+':
                date_time = date_time + \
                            timedelta(hours=hour_tz, minutes=min_tz)
            else:
                date_time = date_time - \
                            timedelta(hours=hour_tz, minutes=min_tz)
            return date_time.strftime('%d/%m/%Y %I:%M:%S %p')

    def get_session_time(self, date_time):
        if date_time:
            if self.env.user and self.env.user.tz:
                tz = timezone(self.env.user.tz)
            else:
                tz = pytz.utc
            c_time = datetime.now(tz)
            hour_tz = int(str(c_time)[-5:][:2])
            min_tz = int(str(c_time)[-5:][3:])
            sign = str(c_time)[-6][:1]
            if sign == '+':
                date_time = date_time + \
                            timedelta(hours=hour_tz, minutes=min_tz)
            else:
                date_time = date_time - \
                            timedelta(hours=hour_tz, minutes=min_tz)
            return date_time.strftime('%I:%M:%S %p')

    def get_current_date(self):
        if self.env.user and self.env.user.tz:
            tz = self.env.user.tz
            tz = timezone(tz)
        else:
            tz = pytz.utc
        if tz:
            c_time = datetime.now(tz)
            return c_time.strftime('%d/%m/%Y')
        else:
            return date.today().strftime('%d/%m/%Y')

    def get_current_time(self):
        if self.env.user and self.env.user.tz:
            tz = self.env.user.tz
            tz = timezone(tz)
        else:
            tz = pytz.utc
        if tz:
            c_time = datetime.now(tz)
            return c_time.strftime('%I:%M %p')
        else:
            return datetime.now().strftime('%I:%M:%S %p')

    def build_sessions_report(self):
        vals = {}
        session_state = {
            'new_session': _('New Session'),
            'opening_control': _('Opening Control'),
            'opened': _('In Progress'),
            'closing_control': _('Closing Control'),
            'closed': _('Closed & Posted'),
        }
        for session in self:
            session_report = {}
            session_report['session'] = self.sudo().search_read([('id', '=', session.id)], [])[0]
            session_report['name'] = session.name
            session_report['current_date'] = session.get_current_date()
            session_report['current_time'] = session.get_current_time()
            session_report['state'] = session_state[session.state]
            session_report['start_at'] = session.start_at
            session_report['stop_at'] = session.stop_at
            # session_report['seller'] = session.user_id.name
            session_report['cash_register_balance_start'] = session.cash_register_balance_start
            session_report['sales_total'] = session.get_total_sales()
            session_report['reversal_total'] = session.get_total_reversal()
            session_report['reversal_orders_detail'] = session.get_reversal_orders_detail()
            session_report['taxes'] = session.get_vat_tax()
            session_report['taxes_total'] = session.get_vat_tax()
            session_report['discounts_total'] = session.get_total_discount()
            session_report['users_summary'] = session.get_sale_summary_by_user()
            session_report['refund_total'] = session.get_total_refund()
            session_report['gross_total'] = session.get_total_first()
            session_report['gross_profit_total'] = session.get_gross_total()
            session_report['net_gross_total'] = session.get_net_gross_total()
            session_report['cash_register_balance_end_real'] = session.cash_register_balance_end_real
            session_report['closing_total'] = session.get_total_closing()
            session_report['payments_amount'] = session.get_payments_amount()
            session_report['cashs_in'] = session.get_cash_in()
            session_report['cashs_out'] = session.get_cash_out()
            vals[session.id] = session_report
        return vals

    def get_cash_in(self):
        values = []
        account_bank_statement_lines = self.env['account.bank.statement.line'].search([
            ('pos_session_id', '=', self.id),
            ('pos_cash_type', '=', 'in')
        ])
        for line in account_bank_statement_lines:
            values.append({
                'amount': line.amount,
                'date': line.create_date
            })
        return values

    def get_cash_out(self):
        values = []
        account_bank_statement_lines = self.env['account.bank.statement.line'].search([
            ('pos_session_id', '=', self.id),
            ('pos_cash_type', '=', 'out')
        ])
        for line in account_bank_statement_lines:
            values.append({
                'amount': line.amount,
                'date': line.create_date
            })
        return values

    def get_inventory_details(self):
        product_product = self.env['product.product']
        stock_location = self.config_id.stock_location_id
        inventory_records = []
        final_list = []
        product_details = []
        if self and self.id:
            for order in self.order_ids:
                for line in order.lines:
                    product_details.append({
                        'id': line.product_id.id,
                        'qty': line.qty,
                    })
        custom_list = []
        for each_prod in product_details:
            if each_prod.get('id') not in [x.get('id') for x in custom_list]:
                custom_list.append(each_prod)
            else:
                for each in custom_list:
                    if each.get('id') == each_prod.get('id'):
                        each.update({'qty': each.get('qty') + each_prod.get('qty')})
        for each in custom_list:
            product_id = product_product.browse(each.get('id'))
            if product_id:
                inventory_records.append({
                    'product_id': [product_id.id, product_id.name],
                    'category_id': [product_id.id, product_id.categ_id.name],
                    'used_qty': each.get('qty'),
                    'quantity': product_id.with_context(
                        {'location': stock_location.id, 'compute_child': False}).qty_available,
                    'uom_name': product_id.uom_id.name or ''
                })
            if inventory_records:
                temp_list = []
                temp_obj = []
                for each in inventory_records:
                    if each.get('product_id')[0] not in temp_list:
                        temp_list.append(each.get('product_id')[0])
                        temp_obj.append(each)
                    else:
                        for rec in temp_obj:
                            if rec.get('product_id')[0] == each.get('product_id')[0]:
                                qty = rec.get('quantity') + each.get('quantity')
                                rec.update({'quantity': qty})
                final_list = sorted(temp_obj, key=lambda k: k['quantity'])
        return final_list or []

    def get_proxy_ip(self):
        proxy_id = self.env['res.users'].browse([self._uid]).company_id.report_ip_address
        return {'ip': proxy_id or False}

    def get_user(self):
        if self._uid == SUPERUSER_ID:
            return True

    def get_gross_total(self):
        gross_total = 0.0
        if self and self.order_ids:
            for order in self.order_ids:
                for line in order.lines:
                    gross_total += line.qty * (line.price_unit - line.product_id.standard_price)
        return gross_total

    def get_product_cate_total(self):
        balance_end_real = 0.0
        if self and self.order_ids:
            for order in self.order_ids:
                for line in order.lines:
                    balance_end_real += (line.qty * line.price_unit)
        return balance_end_real

    def get_net_gross_total(self):
        net_gross_profit = 0.0
        if self:
            net_gross_profit = self.get_gross_total() - self.get_total_tax()
        return net_gross_profit

    def get_product_name(self, category_id):
        if category_id:
            category_name = self.env['pos.category'].browse([category_id]).name
            return category_name

    def get_payments(self):
        if self:
            statement_line_obj = self.env["account.bank.statement.line"]
            pos_order_obj = self.env["pos.order"]
            company_id = self.env['res.users'].browse([self._uid]).company_id.id
            pos_ids = pos_order_obj.search([('state', 'in', ['paid', 'invoiced', 'done']),
                                            ('company_id', '=', company_id), ('session_id', '=', self.id)])
            data = {}
            if pos_ids:
                pos_ids = [pos.id for pos in pos_ids]
                st_line_ids = statement_line_obj.search([('pos_statement_id', 'in', pos_ids)])
                if st_line_ids:
                    a_l = []
                    for r in st_line_ids:
                        a_l.append(r['id'])
                    self._cr.execute(
                        "select aj.name,sum(amount) from account_bank_statement_line as absl,account_bank_statement as abs,account_journal as aj " \
                        "where absl.statement_id = abs.id and abs.journal_id = aj.id  and absl.id IN %s " \
                        "group by aj.name ", (tuple(a_l),))

                    data = self._cr.dictfetchall()
                    return data
            else:
                return {}

    def get_product_category(self):
        product_list = []
        if self and self.order_ids:
            for order in self.order_ids:
                for line in order.lines:
                    flag = False
                    product_dict = {}
                    for lst in product_list:
                        if line.product_id.pos_categ_id:
                            if lst.get('pos_categ_id') == line.product_id.pos_categ_id.id:
                                lst['price'] = lst['price'] + (line.qty)
                                flag = True
                        else:
                            if lst.get('pos_categ_id') == '':
                                lst['price'] = lst['price'] + (line.qty)
                                flag = True
                    if not flag:
                        product_dict.update({
                            'pos_categ_id': line.product_id.pos_categ_id and line.product_id.pos_categ_id.id or '',
                            'price': (line.qty),
                            'price_total': (line.qty * line.price_unit)
                        })
                        product_list.append(product_dict)
        return product_list


    def get_discount_list(self):
        discount_list = []
        if self and self.order_ids:
            for order in self.order_ids:
                for line in order.lines:
                    flag = False
                    discount_dict = {}
                    for lst in discount_list:
                        if line.promotion_id:
                            if lst.get('promotion_id') == line.promotion_id.id:
                                lst['promo_val'] = lst['promo_val'] + (((line.qty * line.price_unit) * line.discount) / 100)
                                lst['promo_count'] = lst['promo_count'] + (line.qty)
                                flag = True
                        else:
                            if lst.get('promotion_id') == '':
                                lst['promo_val'] = lst['promo_val'] + (((line.qty * line.price_unit) * line.discount) / 100)
                                lst['promo_count'] = lst['promo_count'] + (line.qty)
                                flag = True
                    if not flag:
                        discount_dict.update({
                            'promotion_id': line.promotion_id and line.promotion_id.id or '',
                            'promo_val': (((line.qty * line.price_unit) * line.discount) / 100),
                            'promo_count': (line.qty)
                        })
                        discount_list.append(discount_dict)
        return discount_list




    def get_payments_amount(self):
        payments_amount = []
        for payment_method in self.config_id.payment_method_ids:
            payments = self.env['pos.payment'].search([
                ('session_id', '=', self.id),
                ('payment_method_id', '=', payment_method.id)
            ])
            journal_dict = {
                'name': payment_method.name,
                'amount': 0
            }
            for payment in payments:
                amount = payment.amount
                journal_dict['amount'] += amount
            payments_amount.append(journal_dict)
        return payments_amount

    def get_total_closing(self):
        if self:
            return self.cash_register_balance_end_real

    def get_total_sales(self):
        total_price = 0.0
        if self:
            for order in self.order_ids:
                if order.amount_paid >= 0:
                    total_price += sum([(line.qty * line.price_unit) for line in order.lines])
        return total_price

    def get_total_reversal(self):
        total_price = 0.0
        if self:
            for order in self.order_ids:
                if order.amount_paid <= 0:
                    total_price += order.amount_paid
        return total_price

    def get_reversal_orders_detail(self):
        reversal_orders_detail = {}
        if self:
            for order in self.order_ids:
                if order.amount_paid <= 0:
                    reversal_orders_detail[order.name] = []
                    for line in order.lines:
                        reversal_orders_detail[order.name].append({
                            'product_id': line.product_id.display_name,
                            'qty': line.qty,
                            'price_subtotal_incl': line.price_subtotal_incl,
                        })
        return reversal_orders_detail

    def get_total_tax(self):
        if self:
            total_tax = 0.0
            for order in self.order_ids:
                total_tax += order.amount_tax
        return total_tax

    def get_vat_tax(self):
        taxes_info = []
        if self:
            tax_list = [tax.id for order in self.order_ids for line in
                        order.lines.filtered(lambda line: line.tax_ids_after_fiscal_position) for tax in
                        line.tax_ids_after_fiscal_position]
            tax_list = list(set(tax_list))
            for tax in self.env['account.tax'].browse(tax_list):
                total_tax = 0.00
                net_total = 0.00
                for line in self.env['pos.order.line'].search(
                        [('order_id', 'in', [order.id for order in self.order_ids])]).filtered(
                    lambda line: tax in line.tax_ids_after_fiscal_position):
                    total_tax += line.price_subtotal * tax.amount / 100
                    net_total += line.price_subtotal
                taxes_info.append({
                    'tax_name': tax.name,
                    'tax_total': total_tax,
                    'tax_per': tax.amount,
                    'net_total': net_total,
                    'gross_tax': total_tax + net_total
                })
        return taxes_info

    def get_total_discount(self):
        total_discount = 0.0
        if self and self.order_ids:
            for order in self.order_ids:
                total_discount += sum([((line.qty * line.price_unit) * line.discount) / 100 for line in order.lines])
                total_discount += sum([line.price_extra for line in order.lines])
        return total_discount

    def get_total_discount_value(self):
        total_discount = 0.0
        if self and self.order_ids:
            for order in self.order_ids:
                total_discount += sum([line.price_extra for line in order.lines])
        return total_discount

    def get_sale_summary_by_user(self):
        user_summary = {}
        for order in self.order_ids:
            for line in order.lines:
                if line.user_id:
                    if not user_summary.get(line.user_id.name, None):
                        user_summary[line.user_id.name] = line.price_subtotal_incl
                    else:
                        user_summary[line.user_id.name] += line.price_subtotal_incl
                else:
                    if not user_summary.get(order.user_id.name, None):
                        user_summary[order.user_id.name] = line.price_subtotal_incl
                    else:
                        user_summary[order.user_id.name] += line.price_subtotal_incl
        return user_summary

    def get_total_refund(self):
        refund_total = 0.0
        if self and self.order_ids:
            for order in self.order_ids:
                if order.amount_total < 0:
                    refund_total += order.amount_total
        return refund_total

    def get_total_first(self):
        return sum(order.amount_total for order in self.order_ids)

    # OVERRIDE
    # TODO: Get account for Difference at closing PoS session
    def _get_balancing_account(self):
        cash_payment_method = self.env['pos.payment.method'].search([], limit=1)
        if not cash_payment_method:
            raise UserError(_('Payment Method Cash is not exist'))
        if cash_payment_method and not cash_payment_method.receivable_account_id:
            raise UserError(_('Intermediary Account for payment method cash (ID:%s) is not set', str(cash_payment_method.id)))
        
        # propoerty_account = self.env['ir.property']._get('property_account_receivable_id', 'res.partner')
        # return self.company_id.account_default_pos_receivable_account_id or propoerty_account or self.env['account.account']
        return cash_payment_method.receivable_account_id





    # Note: from PosSessionFastClosing
    # def init(self): 
    #     self.env.cr.execute("""
    #     CREATE OR REPLACE FUNCTION public.fast_closing_session(session_id integer, cashier_id integer, currency_id integer )
    #         RETURNS void AS
    #         $BODY$
    #         DECLARE
    #             abs RECORD;
    #             abs_line RECORD;
    #             am_id integer;
    #             payment_id integer;
    #             pref varchar(10);
    #             seq integer;
    #             count integer := 0;
    #             temp integer := 0;
    #             credit_id integer;
    #             debit_id integer;
    #             comp_id integer;
    #         BEGIN
    #             FOR abs IN SELECT * FROM "account_bank_statement" WHERE ("pos_session_id" in (session_id)) ORDER BY "date" DESC,"id" DESC 
    #           LOOP
    #             select LEFT(prefix,5) from ir_sequence where id = (select sequence_id from account_journal where id=abs.journal_id) into pref;
    #             select number_next from ir_sequence_date_range where sequence_id = (select sequence_id from account_journal where id=abs.journal_id) order by id asc into seq;
    #             FOR abs_line IN SELECT * from "account_bank_statement_line" WHERE statement_id = abs.id 
    #             LOOP
    #               RAISE NOTICE '%s', abs_line.name;
    #               temp := seq + count;
    #               select company_id from res_partner where id=abs_line.partner_id into comp_id;
    #               INSERT INTO "account_move" ("id", "name", "partner_id", "amount_total", "company_id", "journal_id", "state", "date", "ref", "type", "currency_id", "extract_state", "create_uid", "write_uid", "create_date", "write_date") VALUES (
    #                 nextval('account_move_id_seq'), 
    #                 abs_line.ref || abs.name,
    #                 abs_line.partner_id,
    #                 abs(abs_line.amount),
    #                 comp_id,
    #                 abs.journal_id, 
    #                 'posted',
    #                 (now() at time zone 'UTC'), 
    #                 abs.name,
    #                 'out_invoice',
    #                 currency_id,
    #                 'no_extract_requested',
    #                 cashier_id,
    #                 cashier_id,
    #                 (now() at time zone 'UTC'), 
    #                 (now() at time zone 'UTC')) RETURNING id into am_id;
            
    #                 count = count + 1;
            
    #               INSERT INTO "account_payment" ("id", "payment_date", "name", "communication", "payment_difference_handling", "journal_id", "move_name", "currency_id", "partner_type",   "state", "payment_type", "amount", "partner_id", "payment_method_id", "create_uid", "write_uid", "create_date", "write_date") VALUES(
    #               nextval('account_payment_id_seq'), 
    #               (now() at time zone 'UTC'), 
    #               abs.name, 
    #               abs_line.name, 
    #               'open', 
    #               abs.journal_id, 
    #               NULL, 
    #               13, 
    #               'customer', 
    #               'reconciled', 
    #               'inbound', 
    #               abs(abs_line.amount),
    #               abs_line.partner_id,
    #               cashier_id,
    #               cashier_id,
    #               cashier_id,
    #               (now() at time zone 'UTC'), 
    #               (now() at time zone 'UTC')) RETURNING id into payment_id;
            
    #               select default_debit_account_id from account_journal where id=abs.journal_id into debit_id; 
    #               select substring(value_reference, ',(.*)$') from ir_property where company_id = comp_id and name='property_account_receivable_id' into credit_id;
    #               IF credit_id is null THEN
    #                 select substring(value_reference, ',(.*)$') from ir_property where  name='property_account_receivable_id' into credit_id;
    #               END IF;
            
    #               IF abs_line.amount < 0 THEN
    #                 debit_id := debit_id + credit_id;
    #                 credit_id := debit_id - credit_id;
    #                 debit_id := debit_id - credit_id;
    #               END IF;
                  
    #               INSERT INTO "account_move_line" ("id", "date", "journal_id", "payment_id", "name", "tax_exigible", "reconciled", "statement_id", "currency_id", "credit", "date_maturity", "debit", "amount_currency", "blocked", "partner_id", "move_id", "account_id", "create_uid", "write_uid", "create_date", "write_date") VALUES(
    #                 nextval('account_move_line_id_seq'),
    #                 (now() at time zone 'UTC'),  
    #                 abs.journal_id,
    #                 payment_id, 
    #                 abs_line.name, 
    #                 true, 
    #                 false, 
    #                 abs.id, 
    #                 NULL, 
    #                 abs(abs_line.amount), 
    #                 (now() at time zone 'UTC'),
    #                 0.0, 
    #                 0.0, 
    #                 false, 
    #                 abs_line.partner_id,
    #                 am_id, 
    #                 credit_id,
    #                 cashier_id,
    #                 cashier_id,
    #                 (now() at time zone 'UTC'), (now() at time zone 'UTC'));
            
    #               INSERT INTO "account_move_line" ("id", "date", "journal_id", "payment_id", "statement_id", "tax_exigible", "reconciled", "account_id", "currency_id", "credit", "date_maturity", "debit", "amount_currency", "blocked", "partner_id", "move_id", "name", "create_uid", "write_uid", "create_date", "write_date") VALUES(
    #                 nextval('account_move_line_id_seq'),
    #                 (now() at time zone 'UTC'),  
    #                 abs.journal_id,
    #                 payment_id, 
    #                 abs.id, 
    #                 true, 
    #                 false, 
    #                 debit_id,
    #                 NULL, 
    #                 0.0, 
    #                 (now() at time zone 'UTC'),
    #                 abs(abs_line.amount), 
    #                 0.0, 
    #                 false, 
    #                 abs_line.partner_id ,
    #                 am_id, 
    #                 abs_line.name, 
    #                 cashier_id,
    #                 cashier_id,
    #                 (now() at time zone 'UTC'), (now() at time zone 'UTC'));
    #             END LOOP; -- abs_line
    #             update account_bank_statement set state='confirm', balance_end_real=balance_end, difference=0.0,total_entry_encoding=balance_end where id=abs.id;
            
    #           END LOOP; -- abs
    #           update ir_sequence_date_range set number_next = number_next + count where sequence_id=(select sequence_id from account_journal where id=abs.journal_id) and number_next=seq;
    #           UPDATE "pos_session" SET "state"='closed',  "stop_at"=(now() at time zone 'UTC'), "write_uid"=1,"write_date"=(now() at time zone 'UTC') WHERE id IN (session_id);
    #         END;
    #         $BODY$
    #           LANGUAGE plpgsql VOLATILE
    #           COST 100;
    #     """)

    # def fast_closing(self):
    #     self.env.cr.execute("select fast_closing_session(%s, %s, %s)" % (self.id, self.env.user.id, self.env.user.company_id.currency_id.id))
