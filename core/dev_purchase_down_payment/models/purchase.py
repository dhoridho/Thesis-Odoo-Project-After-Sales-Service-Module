# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2015 DevIntelle Consulting Service Pvt.Ltd (<http://www.devintellecs.com>).
#
#    For Module Support : devintelle@gmail.com  or Skype : devintelle
#
##############################################################################

from odoo import models, fields, api
from datetime import datetime, date
from itertools import groupby
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_is_zero
from odoo.exceptions import AccessError, UserError, ValidationError
import json


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def get_purchase_total_invoices_amount(self):
        for purchase in self:
            payment = 0
            if purchase.invoice_ids:
                for bill in purchase.invoice_ids:
                    payment += bill.amount_total
            purchase.total_invoices_amount = payment

    def hide_create_bill_status(self):
        for purchase in self:
            if purchase.total_invoices_amount >= purchase.amount_total:
                purchase.hide_create_bill = True
            else:
                purchase.hide_create_bill = False

    total_invoices_amount = fields.Float(string='Advance Payment Amount', compute='get_purchase_total_invoices_amount')
    down_payment_by = fields.Selection(selection=[('dont_deduct_down_payment', 'Billable lines'),
                                                  ('deduct_down_payment', 'Billable lines (deduct advance payments)'),
                                                  ('percentage', 'Advance payment (percentage)'),
                                                  ('fixed', 'Advance payment (fixed amount)')],
                                       string='What do you want to bill?')
    amount = fields.Float(string='Amount')
    dp_journal_id = fields.Many2one('account.journal', string='Journal')
    hide_create_bill = fields.Boolean(string='Hide Create Bill', copy=False, compute='hide_create_bill_status')
    payment_status = fields.Selection([('partial', 'Partially Paid'), ('full', 'Fully Paid')], string='Payment Status', compute='_compute_payment_status')
    down_payment_amount = fields.Float(string='Down Payment', compute='_compute_down_payment_amount', store=True)
    total_down_payment_amount = fields.Float(string='Total', compute='_compute_amount', store=True)
    is_down_payment = fields.Boolean(string='Is Down Payment Invoice')

    @api.depends('order_line.price_total')
    def _amount_all(self):
        res = super(PurchaseOrder, self)._amount_all()
        for record in self:
            lines = record.order_line.filtered(lambda r: not r.is_down_payment)
            record.amount_untaxed = record.currency_id.round(sum(lines.mapped('price_subtotal')))
            # record.amount_tax = record.currency_id.round(sum(lines.mapped('price_tax')))
            record.amount_total = record.amount_untaxed + record.amount_tax
        return res

    @api.depends('order_line.invoice_lines.move_id', 'is_down_payment')
    def _compute_invoice(self):
        res = super(PurchaseOrder, self)._compute_invoice()
        for order in self:
            if order.is_down_payment:
                if 'invoice_dp' in self.env.context:
                    invoice_ids = self.env.context['invoice_dp']
                else:
                    invoice_ids = self.env['account.move'].search([('down_payment_purchase_id', '=', order.id)]).ids
                order.invoice_ids = [(6,0,invoice_ids)]

                order.invoice_count = len(invoice_ids)
        return res

    @api.depends('order_line', 'order_line.is_down_payment', 'order_line.price_unit')
    def _compute_down_payment_amount(self):
        for record in self:
            down_payment_amount = sum(record.order_line.filtered(lambda r: r.is_down_payment).mapped('price_unit'))
            record.down_payment_amount = down_payment_amount

    @api.depends('amount_total', 'down_payment_amount')
    def _compute_amount(self):
        for record in self:
            record.total_down_payment_amount = record.amount_total - record.down_payment_amount

    @api.depends('invoice_ids', 'invoice_ids.state', 'invoice_ids.payment_state')
    def _compute_payment_status(self):
        for record in self:
            invoice_ids = record.invoice_ids.filtered(lambda r: r.is_down_payment)
            record.payment_status = False
            if invoice_ids and all(invoice.state == 'posted' and invoice.payment_state == 'paid' for invoice in invoice_ids):
                record.payment_status = 'full'
            elif invoice_ids and all(invoice.state == 'posted' and invoice.payment_state != 'paid' for invoice in invoice_ids):
                record.payment_status = 'partial'

    def _prepare_invoice(self):
        res = super(PurchaseOrder, self)._prepare_invoice()
        context = dict(self.env.context) or {}
        if context.get('down_payment'):
            ICP = self.env['ir.config_parameter'].sudo()
            product_id = self.env['product.product'].browse(int(ICP.get_param('down_payment_product_id')))
            if not product_id:
                product_id = self.env.ref('dev_purchase_down_payment.down_payment_product', raise_if_not_found=False)
                if not product_id:
                    product_id = self.env['product.product']
            amount = 0
            is_down_payment = False
            if context.get('down_payment_by') == "percentage":
                amount = round((self.amount_total * context.get('amount')) / 100, 2)
                is_down_payment = True
            elif context.get('down_payment_by') == "fixed":
                amount = context.get('amount')
                is_down_payment = True
            if is_down_payment:
                self.is_down_payment = True
                sequence = self.order_line and self.order_line[-1].sequence2 or 0
                line_sequence = (int(sequence) + 1) if int(sequence) > 0 else 0
                self.order_line = [(0, 0, {
                    'sequence': line_sequence,
                    'product_id': product_id.id,
                    'name': product_id.display_name,
                    'product_qty': 1,
                    'taxes_id': [(6, 0, [])],
                    "is_down_payment": True,
                    'price_unit': amount,
                    'order_id': self.id
                })]
        res.update({
            'down_payment_purchase_id': self.id,
            'invoice_date': date.today(),
        })
        return res

    def action_create_invoice(self):
        context = dict(self.env.context) or {}
        if context.get('down_payment'):
            precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')

            # 1) Prepare invoice vals and clean-up the section lines
            invoice_vals_list = []
            for order in self:
                if order.invoice_status != 'to invoice' and context.get('down_payment_by') not in ('percentage', 'fixed'):
                    continue

                order = order.with_company(order.company_id)
                pending_section = None
                # Invoice values.
                invoice_vals = order._prepare_invoice()
                invoice_vals.update({
                    'partner_id': self.partner_id.id,
                })
                if context.get('down_payment_by') == 'deduct_down_payment':
                    invoice_vals.update({
                        'is_down_payment': True,
                    })

                # Invoice line values (keep only necessary sections).
                if context.get('down_payment_by') not in ('percentage', 'fixed'):
                    for line in order.order_line:
                        if line.display_type == 'line_section':
                            pending_section = line
                            continue
                        if not float_is_zero(line.qty_to_invoice, precision_digits=precision) or line.is_down_payment:
                            if pending_section:
                                invoice_vals['invoice_line_ids'].append((0, 0, pending_section._prepare_account_move_line()))
                                pending_section = None
                            invoice_line_vals = line._prepare_account_move_line()
                            if line.is_down_payment:
                                invoice_line_vals.update({
                                    'tax_ids': [(6, 0, [])],
                                    'price_unit': - (line.price_unit),
                                    'is_down_payment': line.is_down_payment,
                                })
                            invoice_vals['invoice_line_ids'].append((0, 0, invoice_line_vals))
                else:
                    ICP = self.env['ir.config_parameter'].sudo()
                    product_id = self.env['product.product'].browse(int(ICP.get_param('down_payment_product_id')))
                    if not product_id:
                        product_id = self.env.ref('dev_purchase_down_payment.down_payment_product', raise_if_not_found=False)
                        if not product_id:
                            product_id = self.env['product.product']
                    amount = 0
                    is_down_payment = False
                    if context.get('down_payment_by') == "percentage":
                        amount = round((self.amount_total * context.get('amount')) / 100, 2)
                        is_down_payment = True
                    elif context.get('down_payment_by') == "fixed":
                        amount = context.get('amount')
                        is_down_payment = True
                    if is_down_payment:
                        invoice_vals['is_down_payment'] = True
                        invoice_vals["invoice_line_ids"].append((0, 0, {
                            'product_id': product_id.id,
                            'name': product_id.display_name,
                            'quantity': 1,
                            'tax_ids': [(6, 0, [])],
                            'price_unit': amount,
                            "is_down_payment": True
                        }))

                invoice_vals_list.append(invoice_vals)
            # 2) group by (company_id, partner_id, currency_id) for batch creation
            new_invoice_vals_list = []
            for grouping_keys, invoices in groupby(invoice_vals_list, key=lambda x: (x.get('company_id'), x.get('partner_id'), x.get('currency_id'))):
                origins = set()
                payment_refs = set()
                refs = set()
                ref_invoice_vals = None
                for invoice_vals in invoices:
                    if not ref_invoice_vals:
                        ref_invoice_vals = invoice_vals
                    else:
                        ref_invoice_vals['invoice_line_ids'] += invoice_vals['invoice_line_ids']
                    origins.add(invoice_vals['invoice_origin'])
                    payment_refs.add(invoice_vals['payment_reference'])
                    refs.add(invoice_vals['ref'])
                ref_invoice_vals.update({
                    'ref': ', '.join(refs)[:2000],
                    'invoice_origin': ', '.join(origins),
                    'payment_reference': len(payment_refs) == 1 and payment_refs.pop() or False,
                })
                new_invoice_vals_list.append(ref_invoice_vals)
            invoice_vals_list = new_invoice_vals_list

            # 3) Create invoices.
            moves = self.env['account.move']
            AccountMove = self.env['account.move'].with_context(default_move_type='in_invoice')
            for vals in invoice_vals_list:
                moves |= AccountMove.with_company(vals['company_id']).create(vals)
                moves._compute_down_payment_amount()
                self._compute_invoice()
            # 4) Some moves might actually be refunds: convert them if the total amount is negative
            # We do this after the moves have been created since we need taxes, etc. to know if the total
            # is actually negative or not
            moves.filtered(lambda m: m.currency_id.round(m.amount_total) < 0).action_switch_invoice_into_refund_credit_note()

            return self.action_view_invoice(moves)
        else:
            return super(PurchaseOrder, self).action_create_invoice()

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    is_down_payment = fields.Boolean(string='Advance Payment')

    @api.model
    def delete_down_payment_product(self):
        product = self.env.ref('dev_purchase_down_payment.down_payment_product', raise_if_not_found=False)
        if not product:
            return

        product_sudo = self.env['product.product'].sudo()
        temp_product = product_sudo.search([('id', '!=', product.id)], limit=1)

        params = {}
        for model in ['purchase.order.line', 'account.move.line', 'stock.move', 'stock.valuation.layer']:
            model_sudo = self.env[model].sudo()

            record_ids = model_sudo.search([('product_id', '=', product.id)])
            params[model] = record_ids.ids

            for record in record_ids:
                record.write({'product_id': temp_product.id})

        ICP = self.env['ir.config_parameter'].sudo()
        ICP.set_param('temporary_params', json.dumps(params, default=str))
