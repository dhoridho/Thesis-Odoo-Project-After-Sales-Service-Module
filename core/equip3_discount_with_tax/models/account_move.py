import odoo.addons.decimal_precision as dp
from odoo import api, fields, models, _
from odoo.tools import float_is_zero, float_compare
from odoo.exceptions import UserError, ValidationError


class AccountAccount(models.Model):
    _inherit = 'account.account'

    discount_account = fields.Boolean('Discount Account')

class AccountMove(models.Model):
    _inherit = 'account.move'

    discount_method = fields.Selection([('fix', 'Fixed'), ('per', 'Percentage')], 'Discount Method', tracking=True)
    discount_amount = fields.Float('Discount Amount', tracking=True)
    discount_amount_fix = fields.Float('Discount Amount Fix', tracking=True)
    discount_amount_per = fields.Float('Discount Amount Per', tracking=True)
    discount_type = fields.Selection([('line', 'Order Line'), ('global', 'Global')], 'Discount Applies to', default='line', tracking=True)
    discount_amt = fields.Float(string='- Discount', readonly=True, store=True, digits='Discount', tracking=True)
    discount_amt_line = fields.Float(string='- Line Discount', digits='Discount', store=True, readonly=True, tracking=True)
    discount_account_id = fields.Many2one('account.account', 'Discount Account', store=True)
    discount_amount_line = fields.Float(string="Discount Line", digits='Discount', store=True, readonly=True, tracking=True)
    tax_applies_on = fields.Char(string="Tax Applies to", readonly=True, store=True)
    subtotal_amount = fields.Monetary(string='Subtotal', compute='_compute_amount', store=True)
    amount_untaxed = fields.Float(string='Subtotal', digits='Account', store=True, readonly=True, compute='_compute_amount')
    amount_tax = fields.Float(string='Tax', digits='Account', store=True, readonly=True, compute='_compute_amount')
    amount_total = fields.Float(string='Total', digits='Account', store=True, readonly=True, compute='_compute_amount')
    amount_tax2 = fields.Monetary(string='Total Taxes', store=True)

    @api.model
    def default_get(self, fields):
        res = super(AccountMove, self).default_get(fields)
        res_config = self.company_id.tax_discount_policy or False
        tax_information = False
        if res_config:
            if res_config == 'untax':
                tax_information = 'After Discount'
            else:
                tax_information = 'Before Discount'
        for rec in self:
            rec.tax_applies_on = tax_information
        return res
        
    def _create_discount_line(self):
        self.ensure_one()
        in_draft_mode = self != self._origin
        line_discount = self.line_ids.filtered(lambda line: line.is_discount_line)
        line_ids = self.line_ids.filtered(lambda line: not line.tax_repartition_line_id and not line.is_discount_line)
        discount_total = sum(line_ids.mapped('discount_amt'))        
        post_discount_account = self.company_id.post_discount_account
        if post_discount_account:
            if line_ids:
                if self.move_type == 'entry' or self.is_outbound():
                    sign = -1
                else:
                    sign = 1
                discount_total = sign * discount_total
                currency = self.env['res.currency'].browse(self.currency_id.id)
                if discount_total == 0:
                    self.line_ids -= line_discount
                else:
                    if self.move_type in ['out_invoice', 'out_receipt', 'in_refund']:
                        discount_account_id = self.company_id.sale_account_id
                    elif self.move_type in ['in_invoice', 'in_receipt', 'out_refund']:
                        discount_account_id = self.company_id.purchase_account_id
                    else:
                        discount_account_id = False

                    if discount_account_id:
                        amount_currency = discount_total
                        balance = self.currency_id._convert(amount_currency, self.company_currency_id, self.company_id, self.invoice_date or fields.Date.context_today(self))
                        data = []
                        to_write_on_line = { 
                                             'amount_currency': amount_currency,
                                             'currency_id': self.currency_id.id,
                                             'debit': balance > 0.0 and balance or 0.0,
                                             'credit': balance < 0.0 and -balance or 0.0,
                                           }
                        if line_discount:
                            line_discount.update(to_write_on_line)
                        else:
                            create_method = in_draft_mode and self.env['account.move.line'].new or self.env['account.move.line'].create
                            line_discount =  create_method({ **to_write_on_line,
                                                                'move_id': self.id,
                                                                'name': 'Discount',
                                                                'account_id': discount_account_id.id,
                                                                'currency_id': self.currency_id.id,
                                                                'partner_id': self.partner_id.id,
                                                                'company_id': self.company_id.id,
                                                                'company_currency_id': self.company_currency_id.id,
                                                                'analytic_tag_ids': self.analytic_group_ids.ids,
                                                                'exclude_from_invoice_tab': True,
                                                                'is_discount_line' : True,
                                                                 })
                        if in_draft_mode:
                            line_discount.update(line_discount._get_fields_onchange_balance(force_computation=True))
            else:
                if line_discount:
                     self.line_ids -= line_discount

    def _recompute_dynamic_lines(self, recompute_all_taxes=False, recompute_tax_base_amount=False):
        for invoice in self:
            if invoice.line_ids:
                invoice._recompute_discount_lines()
        super(AccountMove, self)._recompute_dynamic_lines(recompute_all_taxes=recompute_all_taxes, recompute_tax_base_amount=recompute_tax_base_amount)

    def _recompute_discount_lines(self):
        for invoice in self:
            post_discount_account = invoice.company_id.post_discount_account
            if post_discount_account:
                if invoice.is_invoice(include_receipts=True):
                    invoice._create_discount_line()

    @api.onchange('discount_type')
    def _onchange_discount_type(self):
        for rec in self:
            rec.discount_amount = 0
            for line in rec.invoice_line_ids:
                if rec.discount_type == 'global':
                    # line.discount_method = rec.discount_method
                    line.discount_method = False
                    line.multi_discount = 0
                    line.discount_amount = 0 
                    line.discount_amt = 0
                    line.discount = 0
                elif rec.discount_type == 'line':
                    line.discount_method = False
                    line.discount_amount = 0
                    line.discount_amt = 0
                    line.discount = 0
                
            rec._onchange_method_amount()
            
    @api.onchange('discount_method', 'discount_amount')
    def _onchange_method_amount(self):
        for rec in self:
            if rec.discount_method:
                if rec.discount_type == 'global':
                    for line in rec.invoice_line_ids:
                        line.discount_method = rec.discount_method
                        line.discount = 0
                        if rec.discount_method == 'per':
                            line.discount_amount = False
                            if rec.multi_discount == False:
                                rec.discount_amount = 0

                            if rec.multi_discount :
                                line.discount_amount = rec.discount_amount

                            # line.discount_amount = rec.discount_amount_per
                            # line.discount_amount = False

                        elif rec.discount_method == 'fix':
                            rec.multi_discount = False
                            # rec.discount_amount = 0
                            # line.discount_amount = 0
                            line.multi_discount = False
                            if rec.multi_discount == False and line.discount_amount > 0:
                                rec.discount_amount = 0
                            total_qty_invoice = sum(rec.invoice_line_ids.mapped('total_qty_price_unit'))
                            if total_qty_invoice != 0:
                                line.discount_amount = round((rec.discount_amount / total_qty_invoice),12) *  line.total_qty_price_unit
                            else:
                                line.discount_amount = 0
                        else:
                            line.discount_amount = 0
                        line._onchange_discount_amt_balance()
                    rec._recompute_dynamic_lines(recompute_all_taxes=True)
                elif rec.discount_type == 'line':
                    for line in rec.invoice_line_ids:
                        line.discount_method = False
                        line.discount_amount = 0
                        line.discount_amt = 0
                        line.discount = 0
                        if line.discount_method == 'per':
                            if line.multi_discount == False:
                                line.discount_amount = 0
                            if line.multi_discount:
                                line.discount_amount = rec.discount_amount
                        line._onchange_discount_amt_balance()
                    rec._recompute_dynamic_lines(recompute_all_taxes=True)
                rec._onchange_invoice_line_ids()

    @api.depends(
        'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual',
        'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual_currency',
        'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual',
        'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual_currency',
        'line_ids.debit',
        'line_ids.credit',
        'line_ids.currency_id',
        'line_ids.amount_currency',
        'line_ids.amount_residual',
        'line_ids.amount_residual_currency',
        'line_ids.payment_id.state',
        'line_ids.full_reconcile_id',
        'line_ids.discount_amt',)
    def _compute_amount(self):
        res = super(AccountMove, self)._compute_amount()
        for move in self:
            if move.is_invoice(include_receipts=True):
                total_disc = subtotal_amount = subtotal_amount_currency = discount_amt = discount_amt_line = discount_amount_line = 0.0
                total_untaxed = total_untaxed_currency = total_tax = total_tax_currency = 0.0
                total_to_pay = total_residual = total_residual_currency = total = total_currency = 0.0
                currencies = move._get_lines_onchange_currency().currency_id

                if move.move_type == 'entry' or move.is_outbound():
                    sign = 1
                else:
                    sign = -1

                if move.move_type in ['out_invoice', 'out_receipt', 'in_refund']:
                    disc_sign = 1
                elif move.move_type in ['in_invoice', 'in_receipt', 'out_refund']:
                    disc_sign = -1
                else:
                    disc_sign = 1

                post_discount_account = move.company_id.post_discount_account
                discount_total = move.line_ids.filtered(lambda line: line.account_id.discount_account and line.exclude_from_invoice_tab)
                if post_discount_account:
                    total_disc = (sum(discount_total.mapped('amount_currency')) if len(currencies) == 1 else sum(discount_total.mapped('balance')))or 0.0
                else:
                    total_disc = (sign * sum(move.invoice_line_ids.mapped('discount_amt'))) or 0.0

                total_disc = disc_sign * total_disc
                if move.discount_type == 'global':
                    discount_amt = sign * total_disc
                else:
                    discount_amt_line = sign * total_disc
                    discount_amount_line = sign * total_disc
                untaxed_amount = move.line_ids.filtered(lambda x: not x.exclude_from_invoice_tab)
                if untaxed_amount:
                    if move.tax_applies_on == 'Before Discount':
                        total_untaxed = sign * sum(untaxed_amount.mapped('balance'))
                        total_untaxed_currency = sign * sum(untaxed_amount.mapped('amount_currency'))
                        subtotal_amount = total_untaxed
                        subtotal_amount_currency = total_untaxed_currency
                        tax_amount = move.line_ids.filtered(lambda x: x.tax_line_id)
                        if tax_amount:
                            total_tax = sign * sum(tax_amount.mapped('balance'))
                            total_tax_currency = sign * sum(tax_amount.mapped('amount_currency'))
                        total = ((total_untaxed + total_tax) - abs(total_disc))
                        total_currency = ((total_untaxed_currency + total_tax_currency) - abs(total_disc))
                    else:
                        total_untaxed = ((sign * sum(untaxed_amount.mapped('balance'))) - total_disc)
                        total_untaxed_currency = ((sign * sum(untaxed_amount.mapped('amount_currency'))) - total_disc)
                        subtotal_amount = (sign * sum(untaxed_amount.mapped('balance')))
                        subtotal_amount_currency = (sign * sum(untaxed_amount.mapped('amount_currency')))
                        tax_amount = move.line_ids.filtered(lambda x: x.tax_line_id)
                        if tax_amount:
                            total_tax = sign * sum(tax_amount.mapped('balance'))
                            total_tax_currency = sign * sum(tax_amount.mapped('amount_currency'))
                        total = ((total_untaxed + total_tax))
                        total_currency = ((total_untaxed_currency + total_tax_currency))
                
                residual_amount = move.line_ids.filtered(lambda x: x.account_id.user_type_id.type in ('receivable', 'payable'))
                if residual_amount:
                    total_to_pay = sign * sum(residual_amount.mapped('balance'))
                    total_residual = sum(residual_amount.mapped('amount_residual'))
                    total_residual_currency = sum(residual_amount.mapped('amount_residual_currency'))
            
                move.amount_untaxed = abs(total_untaxed_currency if len(currencies) == 1 else total_untaxed)
                move.amount_tax = abs(total_tax_currency if len(currencies) == 1 else total_tax)
                move.amount_total = abs(total_currency if len(currencies) == 1 else total)
                move.amount_residual = abs(total_residual_currency if len(currencies) == 1 else total_residual)
                move.amount_untaxed_signed = abs(total_untaxed)
                move.amount_tax_signed = abs(total_tax)
                move.amount_total_signed = abs(total)
                move.amount_residual_signed = abs(total_residual)
                move.discount_amt = -abs(discount_amt)
                move.discount_amt_line = -abs(discount_amt_line)
                move.discount_amount_line = -abs(discount_amount_line)
                move.subtotal_amount = abs((subtotal_amount_currency if len(currencies) == 1 else subtotal_amount))
                

    def _recompute_tax_lines(self, recompute_tax_base_amount=False):
        self.ensure_one()
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
            tax_base_amount = currency._convert(tax_base_amount, self.company_currency_id, self.company_id, self.date or fields.Date.context_today(self))
            # Recompute only the tax_base_amount.
            if taxes_map_entry['tax_line'] and recompute_tax_base_amount:
                taxes_map_entry['tax_line'].tax_base_amount = tax_base_amount
                continue
            balance = currency._convert(taxes_map_entry['amount'],
                                        self.journal_id.company_id.currency_id,
                                        self.journal_id.company_id,
                                        self.date or fields.Date.context_today(self)
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
                                                            })
            if in_draft_mode and taxes_map_entry['tax_line']:
                taxes_map_entry['tax_line'].update(taxes_map_entry['tax_line']._get_fields_onchange_balance(force_computation=True))

    def _move_autocomplete_invoice_lines_values(self):
        self.ensure_one()
        self._recompute_discount_lines()
        rslt = super(AccountMove, self)._move_autocomplete_invoice_lines_values()
        return rslt

    @api.model
    def _move_autocomplete_invoice_lines_create(self, vals_list, create_line_discount=False):
        if create_line_discount:
            new_vals_list = []
            for vals in vals_list:
                vals = dict(vals)
                if vals.get('invoice_date') and not vals.get('date'):
                    vals['date'] = vals['invoice_date']
                default_move_type = vals.get('move_type') or self._context.get('default_move_type')
                ctx_vals = {}
                if default_move_type:
                    ctx_vals['default_move_type'] = default_move_type
                if vals.get('journal_id'):
                    ctx_vals['default_journal_id'] = vals['journal_id']
                    journal_company = self.env['account.journal'].browse(vals['journal_id']).company_id
                    allowed_companies = self._context.get('allowed_company_ids', journal_company.ids)
                    reordered_companies = sorted(allowed_companies, key=lambda cid: cid != journal_company.id)
                    ctx_vals['allowed_company_ids'] = reordered_companies
                self_ctx = self.with_context(**ctx_vals)
                vals = self_ctx._add_missing_default_values(vals)
                is_invoice = vals.get('move_type') in self.get_invoice_types(include_receipts=True)
                if is_invoice:
                    if vals.get('line_ids') and vals.get('invoice_line_ids'):
                        vals.pop('line_ids', None)
                    
                    if 'invoice_line_ids' in vals:
                        vals['line_ids'] = vals['invoice_line_ids']

                move = self_ctx.new(vals)
                move_cek = move._move_autocomplete_invoice_lines_values()
                new_vals_list.append(move_cek)
            if new_vals_list:
                return new_vals_list
            else:
                rslt = super(AccountMove, self)._move_autocomplete_invoice_lines_create(vals_list)
                return rslt
        else:
            rslt = super(AccountMove, self)._move_autocomplete_invoice_lines_create(vals_list)
            return rslt

    @api.model_create_multi
    def create(self, vals_list):
        # OVERRIDE
        vals_list = self._move_autocomplete_invoice_lines_create(vals_list, create_line_discount=True)
        rslt = super(AccountMove, self).create(vals_list)
        for invoice in rslt:
            res_config = invoice.company_id.tax_discount_policy or False
            if res_config:
                if res_config == 'untax':
                    for line in invoice.invoice_line_ids:
                        if not line.exclude_from_invoice_tab and not line.sale_line_ids.is_reward_line:
                            move_type = line.move_id.move_type
                            post_discount_account = invoice.company_id.post_discount_account
                            if post_discount_account:
                                tmp_tax_include = line.tax_ids.filtered(lambda r: r.price_include == True)
                                line_ids = invoice.line_ids.filtered(lambda line_tax: line_tax.tax_repartition_line_id and line_tax.tax_repartition_line_id.tax_id.id in tmp_tax_include.ids)
                                line_tax_include = sum(line_ids.mapped('amount_currency'))
                                if tmp_tax_include:
                                    if line.quantity != 0:
                                        line.update({'price_unit' : (abs(line.amount_currency) + abs(line_tax_include)) / line.quantity})
                                    else :
                                        line.update({'price_unit' : 0})
                            else:
                                tmp_tax_include = line.tax_ids.filtered(lambda r: r.price_include == True)
                                line_ids = invoice.line_ids.filtered(lambda line_tax: line_tax.tax_repartition_line_id and line_tax.tax_repartition_line_id.tax_id.id in tmp_tax_include.ids)
                                line_tax_include = sum(line_ids.mapped('amount_currency'))
                                if tmp_tax_include:
                                    if line.quantity != 0:
                                        line.update({'price_unit' : (abs(line.amount_currency) + abs(line_tax_include) + abs(line.discount_amt)) / line.quantity})
                                    else :
                                        line.update({'price_unit' : 0})
                                tmp_tax_exclude = line.tax_ids.filtered(lambda r: r.price_include == False)
                                if tmp_tax_exclude:
                                    if line.quantity != 0:
                                        line.update({'price_unit' : (abs(line.amount_currency) + abs(line.discount_amt)) / line.quantity})
                                    else:
                                        line.update({'price_unit' : 0})
                        line._onchange_discount_amt_balance()
                    invoice._onchange_invoice_line_ids()
        return rslt

    def write(self, vals):
        res = super(AccountMove, self).write(vals)
        res_config = self.company_id.tax_discount_policy
        if res_config:
            for move in self.with_context(check_move_validity=False, skip_account_move_synchronization=True):
                if vals.get('discount_type') or vals.get('discount_method') or vals.get('discount_amount'):
                    move._onchange_method_amount()
                    move._recompute_discount_lines()
        return res

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'
    

    # discount_method = fields.Selection(related='move_id.discount_method', string="Discount Method", readonly=False)
    discount_type = fields.Selection(related='move_id.discount_type', string="Discount Applies to", store=True, tracking=True)
    discount_method = fields.Selection([('fix', 'Fixed'), ('per', 'Percentage')], string='Discount Method', store=True, tracking=True)
    # discount_type = fields.Selection([('line', 'Order Line'), ('global', 'Global')], string='Discount Applies to', default=_get_default_discount_type)
    discount_amount = fields.Float('Discount Amount', store=True, tracking=True)
    discount_amt = fields.Float('Discount Final Amount', store=True, tracking=True)
    price_tax_discount = fields.Float(string='Product Tax Discount', tracking=True, digits='Product Price', store=True)
    total_qty_price_unit = fields.Monetary(string='total_qty_price_unit', store=True, readonly=True, currency_field='currency_id', compute="_get_total_qty_price_unit", tracking=True)
    is_discount_line = fields.Boolean(string='is discount', default=False, store=True, tracking=True)
    price_tax = fields.Monetary(string='Tax Amount', compute='', currency_field='currency_id')


    @api.onchange('discount_method')
    def _onchange_discount_method(self):
        for rec in self:
            if rec.discount_method:
                if rec.discount_method == 'per':
                    rec.discount_amount = 0
                elif rec.discount_method == 'fix':
                    rec.multi_discount = False
                    rec.discount_amount = 0

    @api.model
    def default_get(self, fields):
        vals = super(AccountMoveLine, self).default_get(fields)
        for line in self:
            if line.move_id:
                if line.move_id.discount_type:
                    if line.move_id.discount_type == 'global':
                        if line.move_id.discount_method:
                            vals['discount_method'] = self.move_id.discount_method
        return vals

    @api.onchange('discount_type')
    def _get_discount_method(self):
        for rec in self:
            move_id = rec.move_id
            if move_id:
                rec.discount_method = move_id.discount_method


    @api.depends('quantity', 'price_unit')
    def _get_total_qty_price_unit(self):
        for rec in self:
            if (rec.quantity and rec.price_unit) and rec.quantity != 0 and rec.price_unit != 0:
                rec.total_qty_price_unit = rec.quantity * rec.price_unit
            else:
                rec.total_qty_price_unit = 0

    @api.model
    def _get_price_total_and_subtotal_model(self, price_unit, quantity, discount, currency, product, partner, taxes, move_type):
        res = super(AccountMoveLine, self)._get_price_total_and_subtotal_model(price_unit = price_unit, quantity = quantity, discount = discount, currency = currency, product = product, partner = partner, taxes = taxes, move_type = move_type)
        res_config = self.company_id.tax_discount_policy or False
        if res_config:
            subtotal = quantity * price_unit
            if subtotal == 0:
                return res
            force_sign = -1 if move_type in ('out_invoice', 'in_refund', 'out_receipt') else 1
            if res_config == 'untax':
                if self.discount_method:
                    if self.discount_method == 'per':
                        final_discount = (subtotal * round((self.discount_amount / 100),12))
                        disc_percent = self.discount_amount
                    elif self.discount_method == 'fix':
                        final_discount = self.discount_amount
                        if self.discount_amount != 0:
                            total_disc = 0
                            total_disc = round(self.discount_amount / subtotal,12)
                            disc_percent = round(total_disc * 100, 12)
                        else:
                            disc_percent = 0
                    else:
                        final_discount = 0
                        disc_percent = 0
                else:
                    final_discount = 0
                    disc_percent = 0
                discount_amt = final_discount

                if self.discount_method == 'per':
                    line_discount_price_unit = (price_unit * (1 - (discount / 100.0))) * (1 - (disc_percent / 100.0))
                else:
                    if quantity:
                        line_discount_price_unit = (price_unit - (discount_amt/quantity)) * (1 - (discount / 100.0))
                    else:
                        line_discount_price_unit = 0                
                subtotal = quantity * line_discount_price_unit

                if taxes:
                    taxes_res = taxes._origin.with_context(force_sign=force_sign).compute_all(line_discount_price_unit, quantity=quantity, currency=currency, product=product, partner=partner, is_refund=move_type in ('out_refund', 'in_refund'))
                    res['price_tax'] = taxes_res['total_included'] - taxes_res['total_excluded']
                    res['price_tax_discount'] = taxes_res['total_included'] - taxes_res['total_excluded']
                    res['price_subtotal'] = taxes_res['total_excluded']
                    res['price_total'] = taxes_res['total_included']
                    res['discount_amt'] = discount_amt
                else:
                    res['price_total'] = subtotal
                    res['price_subtotal'] = subtotal
                    res['price_tax'] = 0
                    res['price_tax_discount'] = 0
                    res['discount_amt'] = discount_amt            
            else:                
                if taxes:
                    taxes_res = taxes._origin.with_context(force_sign=force_sign).compute_all(price_unit, quantity=quantity, currency=currency, product=product, partner=partner, is_refund=move_type in ('out_refund', 'in_refund'))
                    subtotal = taxes_res['total_included']
                if self.discount_method:
                    if self.discount_method == 'per':
                        final_discount = ((subtotal) * round((self.discount_amount / 100),12))
                        disc_percent = self.discount_amount
                    elif self.discount_method == 'fix':
                        final_discount = self.discount_amount
                        if self.discount_amount != 0:
                            total_disc = 0
                            if subtotal:
                                total_disc = round(self.discount_amount / (subtotal),12)
                            disc_percent = round(total_disc * 100, 12)
                        else:
                            disc_percent = 0
                    else:
                        final_discount = 0
                        disc_percent = 0
                else:
                    final_discount = 0
                    disc_percent = 0
                discount_amt = final_discount

                res_config = self.company_id.tax_discount_policy or False
                subtotal = quantity * price_unit

                if taxes_res:
                    disc_tax = 0
                    tmp_tax_include = taxes.filtered(lambda r: r.price_include == True)
                    if tmp_tax_include:
                        taxes_in = tmp_tax_include._origin.with_context(force_sign=force_sign).compute_all(final_discount, quantity=1, currency=currency, product=product, partner=partner, is_refund=move_type in ('out_refund', 'in_refund'))
                        disc_tax = taxes_in['total_included'] - taxes_in['total_excluded']

                    res['price_tax'] = taxes_res['total_included'] - taxes_res['total_excluded'] + disc_tax
                    res['price_tax_discount'] = taxes_res['total_included'] - taxes_res['total_excluded'] + disc_tax
                    res['price_subtotal'] = taxes_res['total_excluded']
                    res['price_total'] = taxes_res['total_included'] - final_discount
                    res['discount_amt'] = discount_amt
                else:
                    res['price_total'] = subtotal + final_discount
                    res['price_subtotal'] = subtotal + final_discount
                    res['price_tax'] = 0
                    res['price_tax_discount'] = 0
                    res['discount_amt'] = discount_amt
        if currency:
            res = {k: currency.round(v) for k, v in res.items()}
        return res


    @api.model
    def _get_fields_onchange_subtotal_model(self, price_subtotal, move_type, currency, company, date):
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
                balance = currency._convert(amount_currency, company.currency_id, company, date or fields.Date.context_today(self))
                res['price_unit'] = self.price_unit
                res['amount_currency'] = amount_currency
                res['discount_amt'] = self.discount_amt
                res['currency_id'] = currency.id
                res['debit'] = balance > 0.0 and balance or 0.0
                res['credit'] = balance < 0.0 and -balance or 0.0

            else:                
                amount_currency = price_subtotal * sign
                balance = currency._convert(amount_currency, company.currency_id, company, date or fields.Date.context_today(self))
                res['amount_currency'] = amount_currency
                res['discount_amt'] = self.discount_amt
                res['currency_id'] = currency.id
                res['debit'] = balance > 0.0 and balance or 0.0
                res['credit'] = balance < 0.0 and -balance or 0.0                
        return res

    @api.model
    def _get_fields_onchange_balance_model(self, quantity, discount, amount_currency, move_type, currency, taxes, price_subtotal, force_computation=False):
        res = super(AccountMoveLine, self)._get_fields_onchange_balance_model(quantity = quantity, discount = discount, amount_currency = amount_currency, move_type = move_type, currency = currency, taxes = taxes, price_subtotal = price_subtotal, force_computation = force_computation)
        res_config = self.company_id.tax_discount_policy or False
        if res_config:
            if self.discount_method:
                if self.discount_method == 'per':
                    final_discount = ((self.price_unit * quantity) * round((self.discount_amount / 100),12))
                    disc_percent = self.discount_amount
                elif self.discount_method == 'fix':
                    final_discount = self.discount_amount
                    if self.discount_amount:
                        total_disc = round(self.discount_amount / (self.price_unit * quantity),12)
                        disc_percent = round(total_disc * 100, 12)
                    else:
                        disc_percent = 0
                else:
                    final_discount = 0
                    disc_percent = 0
            else:
                final_discount = 0
                disc_percent = 0
            discount_amt = final_discount

            if ((self.price_unit * quantity) !=0) and (discount_amt == (self.price_unit * quantity)):
                discount_amt = 0

            if res_config == 'untax':
                final_discount = 0

            if move_type in self.move_id.get_outbound_types():
                sign = 1
            elif move_type in self.move_id.get_inbound_types():
                sign = -1
            else:
                sign = 1
            amount_currency *= sign

            if not force_computation and currency.is_zero(amount_currency - price_subtotal):
                return {}

            taxes = taxes.flatten_taxes_hierarchy()
            if taxes and any(tax.price_include for tax in taxes):
                force_sign = -1 if move_type in ('out_invoice', 'in_refund', 'out_receipt') else 1
                taxes_res = taxes._origin.with_context(force_sign=force_sign).compute_all(amount_currency, currency=currency, handle_price_include=True)
                for tax_res in taxes_res['taxes']:
                    tax = self.env['account.tax'].browse(tax_res['id'])
                    if tax.price_include:
                        amount_currency += tax_res['amount']

            discount_factor = 1 - (discount / 100.0)
            discount_factor2 = 1 - ( disc_percent/ 100.0)
            if amount_currency and discount_factor and discount_factor2:
                if self.discount_method == 'per':                
                    res['quantity'] = quantity or 1.0
                    res['price_unit'] = (amount_currency + self.discount_amt) / discount_factor/ discount_factor2 / (quantity or 1.0)
                else:
                    res['quantity'] = quantity or 1.0
                    res['price_unit'] = amount_currency / discount_factor/ discount_factor2 / (quantity or 1.0)

            elif amount_currency and not discount_factor:
                res['quantity'] = quantity or 1.0
                res['discount'] = 0.0
                res['price_unit'] = amount_currency / (quantity or 1.0)
            elif discount_factor:
                res['price_unit'] = 0.0

            post_discount_account = self.company_id.post_discount_account
            if post_discount_account:
                if 'price_unit' in res:
                    res['price_unit'] = self.price_unit
        return res

    @api.onchange('discount_amt', 'discount_method', 'discount_amount', 'discount_type')
    def _onchange_discount_amt_balance(self):
        for line in self:
            if not line.move_id.is_invoice(include_receipts=True):
                continue
            line.update(line._get_fields_onchange_balance())
            line.update(line._get_price_total_and_subtotal())
            line.update(line._get_fields_onchange_subtotal())


    @api.onchange('amount_currency', 'currency_id', 'debit', 'credit', 'tax_ids', 'account_id', 'price_unit', 'discount_amt', 'discount_method', 'discount_amount', 'discount_type')
    def _onchange_mark_recompute_taxes(self):
        super(AccountMoveLine, self)._onchange_mark_recompute_taxes()

    @api.onchange('quantity', 'discount', 'price_unit', 'tax_ids','discount_amt', 'discount_method', 'discount_amount', 'discount_type')
    def _onchange_price_subtotal(self):
        super(AccountMoveLine, self)._onchange_price_subtotal()