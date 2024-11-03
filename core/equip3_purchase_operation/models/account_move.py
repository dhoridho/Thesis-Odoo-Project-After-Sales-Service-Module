
from odoo import api , fields , models, _
from odoo.exceptions import ValidationError, UserError, Warning


class AccountMove(models.Model):
    _inherit = 'account.move'

    purchase_order_id = fields.Many2one('purchase.order', string="Order", compute='_compute_order', store=True)
    swo = fields.Boolean("SWO")
    swo_ids = fields.One2many(comodel_name='service.work.order', inverse_name='move_id', string='Service Work Order')
    amount_swo = fields.Float('- Remaining Amount SWO', compute='_compute_amount', store=True)
    is_services_orders = fields.Boolean("Is Services orders", compute='_compute_order', store=True)
    is_from_swo = fields.Boolean(string='Is From SWO', default=False)

    @api.model
    def default_get(self, fields):
        res = super(AccountMove, self).default_get(fields)
        if 'purchase_id' in self.env.context:
            po = self.env['purchase.order'].browse(self.env.context['purchase_id'])
            if po:
                if self.analytic_group_ids != po.analytic_account_group_ids:
                    self.analytic_group_ids = [(6, 0, po.analytic_account_group_ids.ids)]
        return res

    @api.depends('invoice_line_ids', 'invoice_line_ids.purchase_line_id')
    def _compute_order(self):
        for record in self:
            order_id = record.invoice_line_ids.mapped('purchase_line_id.order_id')
            record.purchase_order_id = order_id and order_id[0].id or False
            if record.purchase_order_id:
                record.is_services_orders = record.purchase_order_id.is_services_orders
            else:
                record.is_services_orders = False


    @api.model
    def create(self, vals):
        if 'swo' in self.env.context:
           vals['swo'] = self.env.context['swo']
           vals['amount_swo'] = self.env.context['amount_total']
           vals['swo_ids'] = self.env.context['swo_ids']

        if vals.get('is_down_payment') is True :
            vals['discount_method'] = False
            vals['discount_amount'] = 0
            vals['discount_amt'] = 0
        
        records = super(AccountMove, self).create(vals)
        for record in records:
            if not record.swo:
                record.amount_swo = record.amount_total
        return records

    def _compute_down_payment_lines(self):
        self.ensure_one()
        purchase_id = self.down_payment_purchase_id
        if not self.is_down_payment or not purchase_id or not purchase_id.discount_method in ('per', 'fix'):
            return
        down_payment_line = self.line_ids.filtered(lambda l: l.is_down_payment)
        payable_line = self.line_ids.filtered(lambda l: l.account_id.user_type_id.type == 'payable')
        if self.invoice_payment_term_id and len(payable_line) > 1:
            res_payable_line = False
            for line in payable_line:
                if not res_payable_line:
                    res_payable_line = line
                    continue
                line.unlink()
            payable_line = res_payable_line
        name = str(purchase_id.discount_amount)
        name = name if purchase_id.discount_method == 'fix' else name + '%'
        amount = purchase_id.down_payment_discount_amount - down_payment_line.price_unit

        company = self.company_id
        balance_debit = company.currency_id._convert(amount, self.currency_id, self.company_id, self.date or fields.Date.context_today(self))
        balance_credit  = company.currency_id._convert(payable_line.credit + amount, self.currency_id, self.company_id, self.date or fields.Date.context_today(self))
        if amount <= 0.0:
            return

        account_id = self.env.company.purchase_account_id.id
        self.line_ids = [
            (0, 0, {
                'name': name,
                'account_id' : account_id,
                'amount_currency': balance_debit,
                'debit': amount,
                'is_down_payment_discount': True,
                'exclude_from_invoice_tab': True
            }),
            (1, payable_line.id, {
                'amount_currency': -(balance_credit),
                'credit': payable_line.credit + amount
            })
            ]

    def _check_down_payment_balance(self):
        self.ensure_one()
        line_ids = self.line_ids
        # for line in line_ids:
        #     if line.amount_currency != line.debit - line.credit and line.currency_id == self.currency_id:
        #         line.amount_currency = line.debit - line.credit
        delta = sum(line_ids.mapped('debit')) - sum(line_ids.mapped('credit'))
        if delta <= 0.0:
            return
        payable_line = line_ids.filtered(lambda l: l.account_id.user_type_id.type == 'payable')
        values = {
            'credit': delta > 0.0 and payable_line.credit + delta or payable_line.credit,
            'debit': delta < 0.0 and payable_line.debit + delta or payable_line.debit
        }
        # if payable_line.currency_id != self.currency_id:
        #     values.update({
        #         'amount_currency': values.get('debit', 0.0) - values.get('credit', 0.0)
        #     })
        payable_line.write(values)

    @api.depends('discount_amount')
    def _calculate_discount(self):
        res = super(AccountMove, self)._calculate_discount()
        for move in self:
            if move.discount_type == 'global' and move.discount_method == 'per' and not move.is_down_payment:
                down_payment_line = move.line_ids.filtered(lambda l: l.is_down_payment)
                res = (move.amount_untaxed + abs(down_payment_line.price_subtotal)) * (move.discount_amount / 100)
        return res
    
    
    def _compute_amount(self):
        res = super()._compute_amount()
        for move in self:
            if move.is_from_swo:
                if move.payment_state == 'invoicing_legacy':
                    # invoicing_legacy state is set via SQL when setting setting field
                    # invoicing_switch_threshold (defined in account_accountant).
                    # The only way of going out of this state is through this setting,
                    # so we don't recompute it here.
                    move.payment_state = move.payment_state
                    continue
    
                total_untaxed = 0.0
                total_untaxed_currency = 0.0
                total_tax = 0.0
                total_tax_currency = 0.0
                total_to_pay = 0.0
                total_residual = 0.0
                total_residual_currency = 0.0
                total = 0.0
                total_currency = 0.0
                currencies = move._get_lines_onchange_currency().currency_id
    
                for line in move.line_ids:
                    
                    if move.is_invoice(include_receipts=True):
                        # === Invoices ===
    
                        if not line.exclude_from_invoice_tab:
                            # Untaxed amount.
                            total_untaxed += line.balance
                            total_untaxed_currency += line.amount_currency
                            total += line.balance
                            total_currency += line.amount_currency
                        elif line.tax_line_id:
                            # Tax amount.
                            total_tax += line.balance
                            total_tax_currency += line.amount_currency
                            total += line.balance
                            total_currency += line.amount_currency
                        elif line.account_id.user_type_id.type in ('receivable', 'payable'):
                            # Residual amount.
                            total_to_pay += line.balance
                            total_residual += line.amount_residual
                            total_residual_currency += line.amount_residual_currency
                    else:
                        # === Miscellaneous journal entry ===
                        if line.debit:
                            total += line.balance
                            total_currency += line.amount_currency
                            # total_untaxed += line.balance #point 1
    
                if move.move_type == 'entry' or move.is_outbound():
                    sign = 1
                    total_untaxed_currency += line.amount_currency
                    
                else:
                    sign = -1
                # amount_untaxed_swo = sign * (total_untaxed_currency if len(currencies) == 1 else total_untaxed)
                # move.amount_untaxed = abs(amount_untaxed_swo)
                move.amount_untaxed = sign * (total_currency if len(currencies) == 1 else total)
                move.amount_tax = sign * (total_tax_currency if len(currencies) == 1 else total_tax)
                move.amount_total = sign * (total_currency if len(currencies) == 1 else total)
                move.amount_residual = -sign * (total_residual_currency if len(currencies) == 1 else total_residual)
                move.amount_untaxed_signed = -total_untaxed
                move.amount_tax_signed = -total_tax
                move.amount_total_signed = abs(total) if move.move_type == 'entry' else -total
                move.amount_residual_signed = total_residual
                
                move.amount_total = sign * (total_currency if len(currencies) == 1 else total)
                move.amount_total_signed = abs(total) if move.move_type == 'entry' else -total
                
    
                currency = len(currencies) == 1 and currencies or move.company_id.currency_id
    
                # Compute 'payment_state'.
                new_pmt_state = 'not_paid' if move.move_type != 'entry' else False
    
                if move.is_invoice(include_receipts=True) and move.state == 'posted':
    
                    if currency.is_zero(move.amount_residual):
                        reconciled_payments = move._get_reconciled_payments()
                        if not reconciled_payments or all(payment.is_matched for payment in reconciled_payments):
                            new_pmt_state = 'paid'
                        else:
                            new_pmt_state = move._get_invoice_in_payment_state()
                    elif currency.compare_amounts(total_to_pay, total_residual) != 0:
                        new_pmt_state = 'partial'
    
                if new_pmt_state == 'paid' and move.move_type in ('in_invoice', 'out_invoice', 'entry'):
                    reverse_type = move.move_type == 'in_invoice' and 'in_refund' or move.move_type == 'out_invoice' and 'out_refund' or 'entry'
                    reverse_moves = self.env['account.move'].search([('reversed_entry_id', '=', move.id), ('state', '=', 'posted'), ('move_type', '=', reverse_type)])
    
                    # We only set 'reversed' state in cas of 1 to 1 full reconciliation with a reverse entry; otherwise, we use the regular 'paid' state
                    reverse_moves_full_recs = reverse_moves.mapped('line_ids.full_reconcile_id')
                    if reverse_moves_full_recs.mapped('reconciled_line_ids.move_id').filtered(lambda x: x not in (reverse_moves + reverse_moves_full_recs.mapped('exchange_move_id'))) == move:
                        new_pmt_state = 'reversed'
    
                move.payment_state = new_pmt_state
        return res

    def button_cancel(self):
        res = super().button_cancel()
        for rec in self:
            if rec.is_down_payment and rec.purchase_order_ids:
                for line in rec.invoice_line_ids:
                    if line.purchase_line_id:
                        line.purchase_line_id.write({
                            'price_unit': 0
                        })
                        line.purchase_order_id.write({
                            'is_down_payment': False
                        })
        return res

    def button_draft(self):
        res = super().button_draft()
        for rec in self:
            if rec.is_down_payment and rec.purchase_order_ids:
                for line in rec.invoice_line_ids:
                    if line.purchase_line_id:
                        line.purchase_line_id.write({
                            'price_unit': line.price_unit
                        })
                        line.purchase_order_id.write({
                            'is_down_payment': True
                        })
        return res
    

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    is_down_payment_discount = fields.Boolean()
    res_dp_amount = fields.Float("DP")

    @api.model
    def create(self, vals):
        res = super().create(vals)
        return res

    def unlink(self):
        # deleting DP line from PO line when bill is deleted using ondelete does not work, must be done manually
        po_id = False
        for rec in self:
            if rec.is_down_payment and rec.purchase_line_id:
                po_id = rec.purchase_line_id.order_id
                self.env.cr.execute("DELETE FROM purchase_order_line WHERE id = %s" % self.purchase_line_id.id)
        res = super().unlink()
        if po_id:
            po_id.is_down_payment = False
            po_id._compute_down_payment_amount()
        return res


    def write(self, vals):

        """ Handle for `equip3_accounting_operation/models/account.py` on `write`. Yeah, crazy. """
        context = dict(self.env.context) or {}
        is_forced = len(self) == 1 and len(vals) == 1 and ('debit' in vals or 'credit' in vals) and \
            self.env.context.get('check_move_validity') is False

        if is_forced:
            move_id = self.move_id
            if move_id.is_down_payment:
                down_payment_amount = abs(move_id.down_payment_amount) + sum(move_id.line_ids.filtered(lambda l: l.is_down_payment_discount).mapped('balance'))
                if move_id.currency_id == move_id.company_id.currency_id:
                    to_compute_currency = down_payment_amount
                else:
                    to_compute_currency = move_id.currency_id._convert(down_payment_amount, move_id.company_currency_id, move_id.company_id, move_id.date)

                if 'debit' in vals and vals['debit'] > 0:
                    vals['debit'] = to_compute_currency
                    vals['amount_currency'] = to_compute_currency
                elif 'credit' in vals and vals['credit'] > 0:
                    vals['credit'] = to_compute_currency
                    vals['amount_currency'] = -to_compute_currency

            elif sum(move_id.line_ids.mapped('debit')) == sum(move_id.line_ids.mapped('credit')):
                # already balanced, do not write amount
                vals = dict()
        if 'dp_amount' in context:
            for i in self:
                if i.is_down_payment:
                    if not i.res_dp_amount:
                        vals['res_dp_amount'] = context.get('dp_amount')
        res = super(AccountMoveLine, self).write(vals)
        for i in self:
            # if i.is_down_payment and i.exclude_from_invoice_tab == False and i.id in i.move_id.invoice_line_ids.ids and i.price_unit != i.res_dp_amount:
            if i.move_id.is_down_payment and i.price_unit != i.res_dp_amount:
                if i.price_unit > 0:
                    i.price_unit = i.res_dp_amount
                elif i.price_unit < 0 and i.price_unit != - i.res_dp_amount:
                    i.price_unit = -i.res_dp_amount
        return res

    def _get_discount_value(self, force_final_discount=None):
        if not self.move_id.is_down_payment and self.move_id.line_ids.filtered(lambda l: l.is_down_payment):
            force_final_discount = 0.0
        return super(AccountMoveLine, self)._get_discount_value(force_final_discount=force_final_discount)
