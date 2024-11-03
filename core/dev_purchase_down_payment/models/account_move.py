# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2015 DevIntelle Consulting Service Pvt.Ltd (<http://www.devintellecs.com>).
#
#    For Module Support : devintelle@gmail.com  or Skype : devintelle
#
##############################################################################

from odoo import models, api, fields, _
from odoo.exceptions import UserError
import time


class AccountMove(models.Model):
    _inherit = 'account.move'

    down_payment_amount = fields.Float(string='Down Payment', compute='_compute_down_payment_amount', store=True)
    total_down_payment_amount = fields.Float(string='Total', compute='_compute_amount', store=True)
    is_down_payment = fields.Boolean(string='Is Down Payment Invoice')
    down_payment_purchase_id = fields.Many2one('purchase.order', string="Purchase Order")
    is_record_created = fields.Boolean(default=False, compute="_update_subtotal")

    def _update_subtotal(self):
        for record in self:
            record.is_record_created = True

    @api.depends('invoice_line_ids', 'invoice_line_ids.is_down_payment', 'invoice_line_ids.product_id')
    def _compute_down_payment_amount(self):
        for record in self:
            record.down_payment_amount = sum(record.invoice_line_ids.filtered(lambda r:r.is_down_payment).mapped('price_unit'))

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
    def _compute_amount(self):
        res = super(AccountMove, self)._compute_amount()
        for record in self:
            if record.is_invoice(include_receipts=True):
                total_disc = 0.0
                discount_total = record.line_ids.filtered(lambda line: line.account_id.discount_account and line.exclude_from_invoice_tab)
                if discount_total:
                    total_disc = sum(discount_total.mapped('balance'))
                down_payment_amount = sum(record.invoice_line_ids.filtered(lambda r:r.is_down_payment).mapped('price_unit'))
                if len(record.invoice_line_ids) > 1 and record.is_down_payment:
                    lines = record.invoice_line_ids.filtered(lambda r: not r.is_down_payment)
                    # record.amount_untaxed = sum(lines.mapped('price_subtotal')) - total_disc
                    # record.amount_tax = sum(lines.mapped('price_tax')) - total_disc
                    record.total_down_payment_amount = (record.amount_untaxed + record.amount_tax) - abs(down_payment_amount)
                # else:
                #     # THIS CAUSE BUG
                #     # record.amount_untaxed = down_payment_amount
                #     record.amount_untaxed = sum(record.invoice_line_ids.mapped('price_subtotal'))
                #     record.total_down_payment_amount = down_payment_amount
        return res

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    is_down_payment = fields.Boolean(string='Is Down Payment')

    def _check_reconciliation(self):
        for line in self:
            if line.move_id and line.move_id.is_down_payment:
                continue
            else:
                if line.matched_debit_ids or line.matched_credit_ids:
                    raise UserError(_("You cannot do this modification on a reconciled journal entry. "
                                      "You can just change some non legal fields or you must unreconcile first.\n"
                                      "Journal Entry (id): %s (%s)") % (line.move_id.name, line.move_id.id))

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: