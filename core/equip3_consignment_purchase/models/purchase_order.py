# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from itertools import groupby

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    down_payment_by = fields.Selection(selection_add=[
        ('bill', 'Bill Base on sold Quantity')
    ])

    def action_create_invoice(self):
        context = dict(self.env.context) or {}
        if context.get('down_payment_by') == 'bill':
            
            # 1) Prepare invoice vals and clean-up the section lines
            invoice_vals_list = []
            for order in self:
                
                order = order.with_company(order.company_id)
                pending_section = None
                # Invoice values.
                invoice_vals = order._prepare_invoice()
                if order.partner_invoice_id:
                    invoice_vals.update({
                        'purchase_order_id' : order.id,
                        'partner_id': order.partner_invoice_id.id,
                    })
                else:
                    invoice_vals.update({
                        'purchase_order_id' : order.id,
                        'partner_id': self.partner_id.id,
                    })
                for line in order.order_line:
                    pending_section = line
                    invoice_vals['invoice_line_ids'].append((0, 0, {
                        'product_id' : line.product_id,
                        'tax_ids': line.taxes_id.ids,
                        'analytic_tag_ids' : line.analytic_tag_ids,
                        'product_uom_id' : line.product_uom.id,
                        'price_unit': line.price_unit,
                        'quantity' : context.get('amount')
                    }))
                    invoice_line_vals = line._prepare_account_move_line()
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


    @api.depends('order_line.invoice_lines.move_id', 'is_down_payment')
    def _compute_invoice(self):
        res = super(PurchaseOrder, self)._compute_invoice()
        for order in self:
            if order.down_payment_by == 'bill':
                invoice_ids = self.env['account.move'].search([('down_payment_purchase_id', '=', order.id)])
                order.invoice_ids = invoice_ids
                order.invoice_count = len(invoice_ids)
        return res