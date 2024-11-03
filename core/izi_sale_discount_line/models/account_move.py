    # -*- coding: utf-8 -*-

from odoo import fields, models, api


class AccountMove(models.Model):
    _inherit = 'account.move'


    def _post(self, soft=True):
        # OVERRIDE

        # Don't change anything on moves used to cancel another ones.
        if self._context.get('move_reverse_cancel'):
            return super()._post(soft)

        # Create additional COGS lines for customer invoices.
        self.env['account.move.line'].create(self._account_prepare_discount_lines_vals())

        # Post entries.
        posted = super()._post(soft)
        return posted

    
    def _stock_account_prepare_anglo_saxon_out_lines_vals(self):
        lines_vals_list = super(AccountMove, self)._stock_account_prepare_anglo_saxon_out_lines_vals()
        for line_vals_list in lines_vals_list:
            if not line_vals_list.get('price_subtotal'):
                line_vals_list['price_subtotal'] = line_vals_list['debit'] > 0 and line_vals_list['debit'] or -line_vals_list['credit'] 
                
        for move in self:
            # Check Invoice Type
            if move.move_type not in ('out_invoice', 'out_refund'):
                continue
            # Give Away. Change COGS to Promotion Account
            if move.sale_channel_id.name == 'Giveaway':
                for index, line_vals in enumerate(lines_vals_list):
                    if line_vals['move_id'] == move.id:
                        for line in move.invoice_line_ids:
                            # Check For Invoice Line With Price Retail = 0. Give Away.
                            if line.price_unit == 0 and line.product_id.id == line_vals['product_id'] and line.quantity == line_vals['quantity']:
                                accounts = (
                                    line.product_id.product_tmpl_id
                                    .with_company(line.company_id)
                                    .get_product_accounts(fiscal_pos=move.fiscal_position_id)
                                )
                                # Find COGS Line, Then Replace COGS Account With Giveaway Account
                                if line_vals['account_id'] == accounts['expense'].id:
                                    lines_vals_list[index].update({
                                        'account_id': accounts['giveaway'].id
                                    })
                                    if line.tax_ids:
                                        lines_vals_list[index].update({
                                            'tax_ids': [(6, 0, line.tax_ids.ids)],
                                            'recompute_tax_line_on_create': True,
                                        })
                                break
        return lines_vals_list
    
    def _account_prepare_discount_lines_vals(self):
        lines_vals_list = []
        for move in self:
            # Check Invoice Type
            if move.move_type not in ('out_invoice', 'out_refund'):
                continue
            # Exception Giveaway
            if move.sale_channel_id.name != 'Giveaway':
                # Normal Discount Line. Add Journal Entry
                for line in move.invoice_line_ids:
                    accounts = (
                        line.product_id.product_tmpl_id
                        .with_company(line.company_id)
                        .get_product_accounts(fiscal_pos=move.fiscal_position_id)
                    )
                    # Check Discount
                    if line.price_discount:
                        if move.move_type == 'out_invoice':
                            positive_amount = line.price_discount > 0.0 and line.price_discount or 0.0
                            negative_amount = line.price_discount < 0.0 and -line.price_discount or 0.0
                        elif move.move_type == 'out_refund':
                            positive_amount = line.price_discount < 0.0 and -line.price_discount or 0.0
                            negative_amount = line.price_discount > 0.0 and line.price_discount or 0.0

                        # Add Sales
                        lines_vals_list.append({
                            'name': line.name[:64],
                            'move_id': move.id,
                            'product_id': line.product_id.id,
                            'product_uom_id': line.product_uom_id.id,
                            'quantity': line.quantity,
                            'price_unit': line.price_discount,
                            'debit': negative_amount,
                            'credit': positive_amount,
                            'account_id': accounts['income'].id,
                            'analytic_account_id': line.analytic_account_id.id,
                            'analytic_tag_ids': [(6, 0, line.analytic_tag_ids.ids)],
                            'exclude_from_invoice_tab': True,
                            'is_anglo_saxon_line': True,
                        })
                        # Add Discount
                        lines_vals_list.append({
                            'name': line.name[:64],
                            'move_id': move.id,
                            'product_id': line.product_id.id,
                            'product_uom_id': line.product_uom_id.id,
                            'quantity': line.quantity,
                            'price_unit': -line.price_discount,
                            'debit': positive_amount,
                            'credit': negative_amount,
                            'account_id': accounts['discount'].id,
                            'analytic_account_id': line.analytic_account_id.id,
                            'analytic_tag_ids': [(6, 0, line.analytic_tag_ids.ids)],
                            'exclude_from_invoice_tab': True,
                            'is_anglo_saxon_line': True,
                        })
        return lines_vals_list

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    price_retail = fields.Float('Retail Price')
    price_discount = fields.Float('Disc.')
    recompute_tax_line_on_create = fields.Boolean(default=False)
    
    @api.onchange('product_id', 'price_retail', 'price_discount')
    def _onchange_discount(self):
        self.price_retail = self.product_id.lst_price
        self.price_unit = self.price_retail - self.price_discount
    
    @api.model_create_multi
    def create(self, vals_list):
        def _compute_base_line_taxes(base_line):
            ''' Compute taxes amounts both in company currency / foreign currency as the ratio between
            amount_currency & balance could not be the same as the expected currency rate.
            The 'amount_currency' value will be set on compute_all(...)['taxes'] in multi-currency.
            :param base_line:   The account.move.line owning the taxes.
            :return:            The result of the compute_all method.
            '''
            move = base_line.move_id

            if move.is_invoice(include_receipts=True):
                handle_price_include = True
                sign = -1 if move.is_inbound() else 1
                quantity = base_line.quantity
                is_refund = move.move_type in ('out_refund', 'in_refund')
                price_unit_wo_discount = sign * base_line.price_unit * (1 - (base_line.discount / 100.0))
            else:
                handle_price_include = False
                quantity = 1.0
                tax_type = base_line.tax_ids[0].type_tax_use if base_line.tax_ids else None
                is_refund = (tax_type == 'sale' and base_line.debit) or (tax_type == 'purchase' and base_line.credit)
                price_unit_wo_discount = base_line.amount_currency

            balance_taxes_res = base_line.tax_ids._origin.with_context(force_sign=move._get_tax_force_sign()).compute_all(
                price_unit_wo_discount,
                currency=base_line.currency_id,
                quantity=quantity,
                product=base_line.product_id,
                partner=base_line.partner_id,
                is_refund=is_refund,
                handle_price_include=handle_price_include,
            )

            if move.move_type == 'entry':
                repartition_field = is_refund and 'refund_repartition_line_ids' or 'invoice_repartition_line_ids'
                repartition_tags = base_line.tax_ids.flatten_taxes_hierarchy().mapped(repartition_field).filtered(lambda x: x.repartition_type == 'base').tag_ids
                tags_need_inversion = self._tax_tags_need_inversion(move, is_refund, tax_type)
                if tags_need_inversion:
                    balance_taxes_res['base_tags'] = base_line._revert_signed_tags(repartition_tags).ids
                    for tax_res in balance_taxes_res['taxes']:
                        tax_res['tag_ids'] = base_line._revert_signed_tags(self.env['account.account.tag'].browse(tax_res['tag_ids'])).ids

            return balance_taxes_res

        lines = super(AccountMoveLine, self).create(vals_list)
        for line in lines:
            if line.recompute_tax_line_on_create:
                move = line.move_id
                tax = line.tax_ids[0]
                compute_all_vals = _compute_base_line_taxes(line)
                grouping_dict = {}
                total_amount = 0
                recompute_line_values = []
                for tax_vals in compute_all_vals['taxes']:
                    grouping_dict = move._get_tax_grouping_key_from_base_line(line, tax_vals)
                    amount = tax_vals['amount']
                    total_amount += amount
                    # Check Invoice or Refund
                    if move.move_type == 'out_invoice':
                        positive_amount = amount > 0.0 and amount or 0.0
                        negative_amount = amount < 0.0 and -amount or 0.0
                    elif move.move_type == 'out_refund':
                        positive_amount = amount < 0.0 and -amount or 0.0
                        negative_amount = amount > 0.0 and amount or 0.0
                    recompute_line_values.append((0, 0, {
                        'amount_currency': amount,
                        'currency_id': grouping_dict['currency_id'],
                        'debit': negative_amount,
                        'credit': positive_amount,
                        'name': tax.name,
                        'move_id': self.id,
                        'partner_id': line.partner_id.id,
                        'company_id': line.company_id.id,
                        'company_currency_id': line.company_currency_id.id,
                        'tax_base_amount': amount,
                        'exclude_from_invoice_tab': True,
                        'tax_exigible': tax.tax_exigibility == 'on_invoice',
                        'is_anglo_saxon_line': True,
                        **grouping_dict
                    }))
                # Check Invoice or Refund
                if move.move_type == 'out_invoice':
                    positive_amount = total_amount > 0.0 and total_amount or 0.0
                    negative_amount = total_amount < 0.0 and -total_amount or 0.0
                elif move.move_type == 'out_refund':
                    positive_amount = total_amount < 0.0 and -total_amount or 0.0
                    negative_amount = total_amount > 0.0 and total_amount or 0.0
                recompute_line_values.append((0, 0, {
                    'name': line.name[:64],
                    'move_id': move.id,
                    'product_id': line.product_id.id,
                    'product_uom_id': line.product_uom_id.id,
                    'quantity': line.quantity,
                    'price_unit': -total_amount,
                    'price_subtotal' : positive_amount > 0 and positive_amount or -negative_amount,
                    'debit': positive_amount,
                    'credit': negative_amount,
                    'account_id': line.account_id.id,
                    'analytic_account_id': line.analytic_account_id.id,
                    'analytic_tag_ids': [(6, 0, line.analytic_tag_ids.ids)],
                    'exclude_from_invoice_tab': True,
                    'is_anglo_saxon_line': True,
                }))

                self.env['account.move.line'].create(recompute_line_values)
                # move.line_ids = recompute_line_values
        return lines