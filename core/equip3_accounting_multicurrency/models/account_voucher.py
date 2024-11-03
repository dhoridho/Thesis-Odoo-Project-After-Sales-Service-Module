from odoo import models, fields, api, _, tools
from odoo.exceptions import UserError, ValidationError
from dateutil.relativedelta import relativedelta
import datetime

class AccountVoucher(models.Model):
    _inherit = "account.voucher"

    apply_manual_currency_exchange = fields.Boolean(string='Apply Manual Currency Exchange')
    manual_currency_exchange_inverse_rate = fields.Float(string="Inverse Rate")
    manual_currency_exchange_rate = fields.Float(string="Manual Currency Exchange Rate", digits=(12, 12), default=0.0)
    invisible_manual_currency = fields.Boolean(string="invisible manual currency", default=False)
    invisible_conversion = fields.Boolean(string="invisible conversion", default=False)

    @api.onchange('currency_id')
    def _oncange_currency_id(self):
        if self.currency_id == self.env.company.currency_id:
            self.invisible_manual_currency = True
            self.apply_manual_currency_exchange = False
        else:
            self.invisible_manual_currency = False
            self.apply_manual_currency_exchange = False


    @api.onchange('invisible_manual_currency','currency_id','apply_manual_currency_exchange')
    def _oncange_invisible_conversion(self):
        if self.invisible_manual_currency == False and self.env.company.is_inverse_rate == True:
            if self.apply_manual_currency_exchange:
                self.invisible_conversion = False
            else:
                self.invisible_conversion = True
        else:
            self.invisible_conversion = True

    @api.onchange('manual_currency_exchange_inverse_rate')
    def _oncange_rate_conversion(self):
        if self.manual_currency_exchange_inverse_rate:
            self.manual_currency_exchange_rate = 1 / self.manual_currency_exchange_inverse_rate

    @api.onchange('manual_currency_exchange_rate')
    def _oncange_rate(self):
        if self.manual_currency_exchange_rate:
            self.manual_currency_exchange_inverse_rate = 1 / self.manual_currency_exchange_rate

    def round(self, amount):
        self.ensure_one()
        return tools.float_round(amount, precision_rounding=self.currency_id.rounding)

    def _convert(self, amount):
        for voucher in self:
            if voucher.currency_id == voucher.company_id.currency_id:
                res = voucher.currency_id._convert(amount, voucher.company_id.currency_id, voucher.company_id, voucher.account_date)

            else : 
                if self.apply_manual_currency_exchange == False:

                    # convert currency using rate ongoing period
                    # first_day_period = voucher.account_date.replace(day=1)
                    # end_day_period = first_day_period + relativedelta(months=1, days=-1)
                    # currency_rate = self.env['res.currency.rate'].search([('currency_id', '=', voucher.currency_id.id), ('name', '>=', first_day_period), ('name', '<=', end_day_period)], limit=1)
                    
                    # convert currency using last rate
                    currency_rate = self.env['res.currency.rate'].search([('currency_id', '=', voucher.currency_id.id), ('name', '<=', voucher.account_date)], limit=1)
                    
                    if not currency_rate:
                        raise UserError(_('No currency rate found for the currency %s and the period %s.') % (voucher.currency_id.name, voucher.account_date))
                    res = amount / currency_rate.rate
                else:
                    res = amount / self.manual_currency_exchange_rate
                
            return self.round(res)

    def account_move_get(self):
        move = super(AccountVoucher, self).account_move_get()
        for rec in self:
            move.update({'branch_id': rec.branch_id.id,
                         'analytic_group_ids': [(6, 0, rec.analytic_group_ids.ids)]})
        return move

    def first_move_line_get(self, move_id, company_currency, current_currency):
        debit = credit = 0.0
        if self.voucher_type == 'purchase':
            credit = self._convert(self.amount)
        elif self.voucher_type == 'sale':
            debit = self._convert(self.amount)
        if debit < 0.0: debit = 0.0
        if credit < 0.0: credit = 0.0
        sign = debit - credit < 0 and -1 or 1
        #set the first line of the voucher
        move_line = {
                'name': self.number,
                'debit': debit,
                'credit': credit,
                'account_id': self.account_id.id,
                'move_id': move_id,
                'journal_id': self.payment_journal_id.id if self.pay_now == 'pay_now' else self.journal_id.id,
                'partner_id': self.partner_id.commercial_partner_id.id,
                'currency_id': company_currency != current_currency and current_currency or False,
                'amount_currency': 0.0,
                'date': self.account_date,
                'date_maturity': self.date_due,
                'analytic_tag_ids': [(6, 0, self.analytic_group_ids.ids)],
            }
        
        if company_currency != current_currency: 
            move_line['amount_currency'] = sign * self.amount
            move_line['currency_id'] = current_currency
        return move_line
        
    def _prepare_voucher_move_line(self, line, amount, move_id, company_currency, current_currency, tax_amount):
        line_subtotal = line.price_subtotal

        amount = self._convert(amount)
        if self.voucher_type == 'sale':
            line_subtotal = -1 * self._convert(line.price_subtotal)
            amount *= -1
        
        # convert the amount set on the voucher line into the currency of the voucher's company
        
        
        # FIX BUG SINGLETON
        # *TAXES BISA LEBIH DARI SATU, TOLONG CODE LAIN YG BERHUBUNGAN SAMA TAXES DI CEK JUGA
        # amount_ppn = 0
        # for tax in line.tax_ids:
        #     amount_ppn += tax.price_include
        # if amount_ppn:
        #     amount = amount_ppn - tax_amount
        # ppn_id = line.tax_ids.price_include
        # if ppn_id:
        #     amount = amount - tax_amount


        #===================================================================
        # ALLOW DEBIT AND CREDIT BASED ON MINUS OR PLUS
        #===================================================================
        debit = credit = 0.0
        # if (self.voucher_type == 'sale' and amount > 0.0) or (self.voucher_type == 'purchase' and amount < 0.0):
        #     debit = 0.0
        #     credit = abs(amount)
        # elif (self.voucher_type == 'sale' and amount < 0.0) or (self.voucher_type == 'purchase' or amount > 0.0):
        #     debit = abs(amount)
        #     credit = 0.0
        if self.voucher_type == 'purchase':
            debit = abs(amount)
            credit = 0.0
        else:
            debit = 0.0
            credit = abs(amount)
        move_line = {
            'journal_id': self.journal_id.id,
            'name': line.name,
            'account_id': line.account_id.id,
            'move_id': move_id,
            # 'quantity': line.quantity,
            # 'product_id': line.product_id.id,
            'partner_id': self.partner_id.commercial_partner_id.id,
            'analytic_account_id': line.account_analytic_id and line.account_analytic_id.id or False,
            'analytic_tag_ids': [(6, 0, line.analytic_tag_ids.ids)],
            #===================================================================     
            'credit': abs(amount) if credit > 0.0 else 0.0,
            'debit': abs(amount) if debit > 0.0 else 0.0,
            #===================================================================
            'date': self.account_date,
            # 'tax_ids': [(4,t.id) for t in line.tax_ids],
            'amount_currency': line_subtotal if current_currency != company_currency else 0.0,
            'currency_id': company_currency != current_currency and current_currency or False,
            'payment_id': self._context.get('payment_id'),
        }

        if company_currency != current_currency:
            if self.voucher_type == 'sale':
                amount = -1 * (line.price_unit*line.quantity)
            else:
                amount = line.price_unit*line.quantity
            move_line['amount_currency'] = amount
            move_line['currency_id'] = current_currency
            

        return move_line
    
    def voucher_move_line_create(self, line_total, move_id, company_currency, current_currency):
        for line in self.line_ids:
            if not line.price_subtotal:
                continue
            amount_tax = 0
            amount_journal = line.price_subtotal
            amount = self._convert(line.price_unit * line.quantity)
            if (line.tax_ids):
                tax_group = line.tax_ids.compute_all(line.price_unit, line.currency_id, line.quantity, line.product_id, self.partner_id)
                for tax_vals in tax_group['taxes']:
                    if tax_vals['amount']:
                        tax_amount = tax_vals['amount']
                        tax = self.env['account.tax'].browse([tax_vals['id']])
                        if self.voucher_type == 'purchase':
                            debit = self._convert(abs(tax_amount))
                            credit = 0.0
                        else:
                            debit = 0.0
                            credit = self._convert(abs(tax_amount))
                        account_id = (amount > 0 and tax_vals['account_id'])
                        if not account_id:
                            account_id = line.account_id.id
                        temp = {
                            'account_id': account_id,
                            'name': line.name + ' ' + tax_vals['name'],
                            'move_id': move_id,
                            'date': self.account_date,
                            'partner_id': self.partner_id.id,
                            'credit': abs(credit) if credit > 0.0 else 0.0,
                            'debit': abs(debit) if debit > 0.0 else 0.0,
                            'analytic_account_id': line.account_analytic_id and line.account_analytic_id.id or False,
                            'analytic_tag_ids': [(6, 0, line.analytic_tag_ids.ids)] or False,
                        }
                        if company_currency != current_currency:
                            ctx = {}
                            if self.account_date:
                                ctx['date'] = self.account_date
                            temp['currency_id'] = current_currency
                            amount_curr = tax_vals['amount']
                            if temp['debit'] == 0:
                                if amount_curr > 0:
                                    amount_curr = -amount_curr
                            else:
                                if amount_curr < 0:
                                    amount_curr = -amount_curr

                            temp['amount_currency'] = amount_curr
                        self.env['account.move.line'].create(temp)
                amount_journal = tax_group["total_excluded"]
                amount_tax = tax_group["total_included"] - tax_group["total_excluded"]
            move_line = self._prepare_voucher_move_line(line, amount_journal, move_id, company_currency, current_currency, amount_tax)
            self.env['account.move.line'].create(move_line)
        return line_total

    def action_move_line_create(self):
        for voucher in self:
            local_context = dict(self._context)
            if voucher.move_id:
                continue
            company_currency = voucher.journal_id.company_id.currency_id.id
            current_currency = voucher.currency_id.id or company_currency
            ctx = local_context.copy()
            ctx['date'] = voucher.account_date
            ctx['check_move_validity'] = False
            # Create the account move record.
            move = self.env['account.move'].create(voucher.account_move_get())
            # Get the name of the account_move just created
            # Create the first line of the voucher
            move_line = self.env['account.move.line'].with_context(ctx).create(voucher.with_context(ctx).first_move_line_get(move.id, company_currency, current_currency))            
            line_total = move_line.debit - move_line.credit
            first_move_id=move_line.id
            if voucher.voucher_type == 'sale':
                line_total = line_total - voucher._convert(voucher.tax_amount)
            elif voucher.voucher_type == 'purchase':
                line_total = line_total + voucher._convert(voucher.tax_amount)
            # Create one move line per voucher line where amount is not 0.0            
            line_total = voucher.with_context(ctx).voucher_move_line_create(line_total, move.id, company_currency, current_currency)
            # Add tax correction to move line if any tax correction specified
            if voucher.tax_correction != 0.0:
                tax_move_line = self.env['account.move.line'].search([('move_id', '=', move.id), ('tax_line_id', '!=', False)], limit=1)
                if len(tax_move_line):
                    tax_move_line.write({'debit': tax_move_line.debit + voucher.tax_correction if tax_move_line.debit > 0 else 0,
                        'credit': tax_move_line.credit + voucher.tax_correction if tax_move_line.credit > 0 else 0})
            move._post()
            voucher.write({
                'name': move.name,
                'move_id': move.id,
                'state': 'posted',
            })
        return True
    

class AccountVoucherLine(models.Model):
    _inherit = 'account.voucher.line'

    def _convert_amount_budget(self, currency_id, amount):
        if self.voucher_id.currency_id == self.voucher_id.company_id.currency_id:
            return self.voucher_id.company_id.currency_id._convert(amount, currency_id, self.voucher_id.company_id, self.voucher_id.account_date)

        if self.voucher_id.apply_manual_currency_exchange:
            if self.voucher_id.manual_currency_exchange_inverse_rate:
                return amount / self.voucher_id.manual_currency_exchange_inverse_rate
            else:
                return self.voucher_id.company_id.currency_id._convert(amount, currency_id, self.voucher_id.company_id, self.voucher_id.account_date)    
        else:
            return self.voucher_id.company_id.currency_id._convert(amount, currency_id, self.voucher_id.company_id, self.voucher_id.account_date)

    @api.depends('product_id', 'account_id', 'analytic_tag_ids', 'currency_id', 'voucher_id.apply_manual_currency_exchange', 'voucher_id.manual_currency_exchange_inverse_rate', 'voucher_id.manual_currency_exchange_rate' )
    def _get_expense_budget_id(self):
        super(AccountVoucherLine, self)._get_expense_budget_id()