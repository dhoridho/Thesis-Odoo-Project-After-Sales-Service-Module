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
            invoice_vals_list = []
            for order in self:
                order = order.with_company(order.company_id)
                pending_section = None
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
            # print('invoice vals list============',invoice_vals_list)
            #create
            moves = self.env['account.move']
            AccountMove = self.env['account.move'].with_context(default_move_type='in_invoice')
            # print('invoice_vals_listttttttttttttttttttttt ,', invoice_vals_list)
            for vals in invoice_vals_list:
                moves |= AccountMove.with_company(vals['company_id']).create(vals)
                moves._compute_down_payment_amount()
                # self._compute_invoice()
            # for order in self:
            #     invoices = order.mapped('order_line.invoice_lines.move_id')
            #     order.invoice_ids = invoices
            #     order.invoice_count = len(invoices)
            # print('movessssssssssssssss', moves.amount_untaxed)
            # 4) Some moves might actually be refunds: convert them if the total amount is negative
            # We do this after the moves have been created since we need taxes, etc. to know if the total
            # is actually negative or not
            moves.filtered(lambda m: m.currency_id.round(m.amount_total) < 0).action_switch_invoice_into_refund_credit_note()

            return self.action_view_invoice(moves)
            

        else:
            return super(PurchaseOrder, self).action_create_invoice()

# class PurchaseDownPayment(models.TransientModel):
#     _inherit = 'purchase.down.payment'

#     down_payment_by = fields.Selection(selection_add=[
#         ('bill', 'Bill Base on sold Quantity')
#     ])

#     down_payment_by_ordered = fields.Selection(selection_add=[
#         ('bill', 'Bill Base on sold Quantity')
#     ])

    # def create_bill2(self):
        # res = super(PurchaseDownPayment, self).create_bill2()
        # context = dict(self.env.context) or {}
        # active_id = self.env.context.get('active_id')
        # po_id = self.env['purchase.order'].browse('active_id')
        # print('======================', po_id, active_id)
        # account_move = self.env['account.move'].search(['purchase_order_id', '=', po_id])
        # print('account_moveaccount_moveaccount_move',account_move)
        # print('======================',context)
    #     total_swo = 0
    #     swo = False
    #     if self.swo_ids:
    #         print('self.swo_idsself.swo_idsself.swo_ids')
    #         swo = True
    #         for swo in self.swo_ids:
    #             swo.invoiced = True
    #             total_swo += swo.contract_term
    #     total_swo = total_swo / 100 * self.purchase_id.total_down_payment_amount
    #     total_swo = total_swo * 100 / self.purchase_id.amount_total
    #     self.purchase_id.paid_swo += total_swo
    #     amount_swo = self.purchase_id.total_down_payment_amount * (100 - total_swo) / 100
    #     if self.down_payment_by == 'bill':
    #         context.update({
    #             'down_payment': True,
    #             'down_payment_by': self.down_payment_by,
    #             'amount': 100,
    #             'swo': swo,
    #             'total_swo': total_swo,
    #             'amount_total': amount_swo,
    #             'swo_ids': self.swo_ids
    #         })
    #     print('sesudah res===========================')
        # return res


    # @api.onchange('down_payment_by_ordered', 'down_payment_by_received')
    # def _onchange_down_payment_by(self):
    #     if self.down_payment_by_ordered:
    #         self.down_payment_by = self.down_payment_by_ordered
    #         print('self.down_payment_by',self.down_payment_by)
    #     elif self.down_payment_by_received:
    #         self.down_payment_by = self.down_payment_by_received
    #     elif self.down_payment_by_billable:
    #         self.down_payment_by = self.down_payment_by_billable




# class equip3_consignment_purchase(models.Model):
#     _name = 'equip3_consignment_purchase.equip3_consignment_purchase'
#     _description = 'equip3_consignment_purchase.equip3_consignment_purchase'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100
