from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class AccountMove(models.Model):
    _inherit = 'account.move'
    
    total_ppn = fields.Monetary(string='PPN', currency_field='currency_id')
    total_pph = fields.Monetary(string='PPH', currency_field='currency_id')


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
        'line_ids.full_reconcile_id',)
    def _compute_amount(self):
        res = super(AccountMove, self)._compute_amount()
        for move in self:
            if move.is_invoice(include_receipts=True):
                total_ppn = total_pph = 0.0
                move_amount = move.line_ids.filtered(lambda x: not x.exclude_from_invoice_tab)
                if move_amount:
                    total_ppn = sum(move_amount.mapped('ppn_tax'))
                    total_pph = sum(move_amount.mapped('pph_tax'))
                move.total_ppn = abs(total_ppn)
                move.total_pph = abs(total_pph)

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'
    
    ppn_tax = fields.Monetary(string='PPN Amount', currency_field='currency_id')
    pph_tax = fields.Monetary(string='PPH Amount', currency_field='currency_id')

    @api.model
    def _get_price_total_and_subtotal_model(self, price_unit, quantity, discount, currency, product, partner, taxes, move_type):
        res = super(AccountMoveLine, self)._get_price_total_and_subtotal_model(price_unit = price_unit, quantity = quantity, discount = discount, currency = currency, product = product, partner = partner, taxes = taxes, move_type = move_type)
        res_config = self.company_id.tax_discount_policy or False
        if res_config:
            if res_config == 'untax':
                if self.discount_method:
                    if self.discount_method == 'per':
                        final_discount = ((price_unit * quantity) * round((self.discount_amount / 100),12))
                        disc_percent = self.discount_amount
                    elif self.discount_method == 'fix':
                        final_discount = self.discount_amount
                        if self.discount_amount != 0:
                            total_disc = 0
                            if price_unit * quantity:
                                total_disc = round(self.discount_amount / (price_unit * quantity),12)
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
                if res_config == 'untax':
                    final_discount = 0
                if self.discount_method == 'per':
                    line_discount_price_unit = (price_unit * (1 - (discount / 100.0))) * (1 - (disc_percent / 100.0))
                else:
                    if quantity:
                        line_discount_price_unit = (price_unit - (discount_amt/quantity)) * (1 - (discount / 100.0))
                    else:
                        line_discount_price_unit = 0
                res_config = self.company_id.tax_discount_policy or False
                subtotal = quantity * price_unit

                if res_config:
                    if res_config == 'untax':
                        subtotal = quantity * line_discount_price_unit

                force_sign = -1 if move_type in ('out_invoice', 'in_refund', 'out_receipt') else 1
                total_ppn = 0.00
                total_pph = 0.00
                if taxes:
                    taxes_res = taxes._origin.with_context(force_sign=force_sign).compute_all(line_discount_price_unit, quantity=quantity, currency=currency, product=product, partner=partner, is_refund=move_type in ('out_refund', 'in_refund'))
                    for tax_line in taxes_res['taxes']:
                        tax = self.env['account.tax'].search([('id', '=', tax_line['id'])])
                        if tax.is_ppn:
                            total_ppn += tax_line['amount']
                        if tax.is_pph:
                            total_pph += tax_line['amount']
                    res['ppn_tax'] = total_ppn
                    res['pph_tax'] = total_pph
                else:
                    res['ppn_tax'] = total_ppn
                    res['pph_tax'] = total_pph
            else:
                force_sign = -1 if move_type in ('out_invoice', 'in_refund', 'out_receipt') else 1
                total_ppn = 0.00
                total_pph = 0.00
                if taxes:
                    taxes_res = taxes._origin.with_context(force_sign=force_sign).compute_all(price_unit, quantity=quantity, currency=currency, product=product, partner=partner, is_refund=move_type in ('out_refund', 'in_refund'))
                    for tax_line in taxes_res['taxes']:
                        tax = self.env['account.tax'].search([('id', '=', tax_line['id'])])
                        if tax.is_ppn:
                            total_ppn += tax_line['amount']
                        if tax.is_pph:
                            total_pph += tax_line['amount']
                    res['ppn_tax'] = total_ppn
                    res['pph_tax'] = total_pph
                else:
                    res['ppn_tax'] = total_ppn
                    res['pph_tax'] = total_pph                
        else:
            force_sign = -1 if move_type in ('out_invoice', 'in_refund', 'out_receipt') else 1
            total_ppn = 0.00
            total_pph = 0.00
            if taxes:
                taxes_res = taxes._origin.with_context(force_sign=force_sign).compute_all(price_unit, quantity=quantity, currency=currency, product=product, partner=partner, is_refund=move_type in ('out_refund', 'in_refund'))
                for tax_line in taxes_res['taxes']:
                    tax = self.env['account.tax'].search([('id', '=', tax_line['id'])])
                    if tax.is_ppn:
                        total_ppn += tax_line['amount']
                    if tax.is_pph:
                        total_pph += tax_line['amount']
                res['ppn_tax'] = total_ppn
                res['pph_tax'] = total_pph
            else:
                res['ppn_tax'] = total_ppn
                res['pph_tax'] = total_pph
        if currency:
            res = {k: currency.round(v) for k, v in res.items()}
        return res