# -*- coding: utf-8 -*-
#################################################################################
#
#   Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#   See LICENSE file for full copyright and licensing details.
#   License URL : <https://store.webkul.com/license.html/>
#
#################################################################################

from odoo import api, fields, models


class InheritAccountMove(models.Model):
    _inherit = 'account.move'

    partial_payment_remark = fields.Char(string="Remark")



class InheritAccountMoveLine(models.Model):
    _inherit = 'account.move.line'


    def _prepare_reconciliation_partials(self):
        if self._context.get('coming_from_pos'):
            debit_lines = iter(self.filtered('debit'))
            credit_lines = iter(self.filtered('credit'))
            debit_line = None
            credit_line = None

            debit_amount_residual = 0.0
            debit_amount_residual_currency = 0.0
            credit_amount_residual = 0.0
            credit_amount_residual_currency = 0.0
            debit_line_currency = None
            credit_line_currency = None

            partials_vals_list = []

            while True:

                # Move to the next available debit line.
                if not debit_line:
                    debit_line = next(debit_lines, None)
                    if not debit_line:
                        break
                    debit_amount_residual = debit_line.amount_residual

                    if debit_line.currency_id:
                        debit_amount_residual_currency = debit_line.amount_residual_currency
                        debit_line_currency = debit_line.currency_id
                    else:
                        debit_amount_residual_currency = debit_amount_residual
                        debit_line_currency = debit_line.company_currency_id

                # Move to the next available credit line.
                if not credit_line:
                    credit_line = next(credit_lines, None)
                    if not credit_line:
                        break
                    credit_amount_residual = credit_line.amount_residual

                    if credit_line.currency_id:
                        credit_amount_residual_currency = credit_line.amount_residual_currency
                        credit_line_currency = credit_line.currency_id
                    else:
                        credit_amount_residual_currency = credit_amount_residual
                        credit_line_currency = credit_line.company_currency_id

                min_amount_residual = min(debit_amount_residual, -credit_amount_residual)

                if debit_line_currency == credit_line_currency:
                    # Reconcile on the same currency.

                    # The debit line is now fully reconciled.
                    if debit_line_currency.is_zero(debit_amount_residual_currency) or debit_amount_residual_currency < 0.0:
                        debit_line = None
                        continue

                    # The credit line is now fully reconciled.
                    if credit_line_currency.is_zero(credit_amount_residual_currency) or credit_amount_residual_currency > 0.0:
                        credit_line = None
                        continue

                    min_amount_residual_currency = min(debit_amount_residual_currency, -credit_amount_residual_currency)
                    min_debit_amount_residual_currency = min_amount_residual_currency
                    min_credit_amount_residual_currency = min_amount_residual_currency

                else:
                    # The debit line is now fully reconciled.
                    if debit_line.company_currency_id.is_zero(debit_amount_residual) or debit_amount_residual < 0.0:
                        debit_line = None
                        continue

                    # The credit line is now fully reconciled.
                    if credit_line.company_currency_id.is_zero(credit_amount_residual) or credit_amount_residual > 0.0:
                        credit_line = None
                        continue

                    min_debit_amount_residual_currency = credit_line.company_currency_id._convert(
                        min_amount_residual,
                        debit_line.currency_id,
                        credit_line.company_id,
                        credit_line.date,
                    )
                    min_credit_amount_residual_currency = debit_line.company_currency_id._convert(
                        min_amount_residual,
                        credit_line.currency_id,
                        debit_line.company_id,
                        debit_line.date,
                    )
                debit_amount_residual -= min_amount_residual
                debit_amount_residual_currency -= min_debit_amount_residual_currency
                credit_amount_residual += min_amount_residual
                credit_amount_residual_currency += min_credit_amount_residual_currency

                partials_vals_list.append({
                    'amount': min_amount_residual,
                    'debit_amount_currency': min_debit_amount_residual_currency,
                    'credit_amount_currency': min_credit_amount_residual_currency,
                    'debit_move_id': debit_line.id,
                    'credit_move_id': credit_line.id,
                })
                debit_line = False

            return partials_vals_list
        else:
            res = super(InheritAccountMoveLine,self)._prepare_reconciliation_partials()
            return res
