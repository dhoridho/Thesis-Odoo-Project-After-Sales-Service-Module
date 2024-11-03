# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class PurchaseDownPayment(models.TransientModel):
    _inherit = 'purchase.down.payment'

    def create_bill2(self):
        if self.down_payment_by in ['fixed', 'percentage']:
            self.check_dp()
        self.purchase_id.down_payment_by = self.down_payment_by
        self.purchase_id.amount = self.amount
        context = dict(self.env.context) or {}
        if self.purchase_id.down_payment_by == 'bill' and not self.purchase_id.is_consignment:
            raise ValidationError(_('''Bill Base on sold Quantity only for Consignment Purchase Order'''))
        if self.purchase_id.down_payment_by in ['fixed', 'percentage']:
            if self.amount <= 0:
                raise ValidationError(_('''Amount must be positive'''))
            if self.purchase_id.down_payment_by == 'percentage':
                payment = self.purchase_id.amount_untaxed * self.purchase_id.amount / 100
            else:
                payment = self.amount
            if self.purchase_id.total_invoices_amount == 0:
                if payment > self.purchase_id.amount_total:
                    raise ValidationError(_('''You are trying to pay: %s, but\n You can not pay more than: %s''') % (payment, self.purchase_id.amount_total))
            # if self.purchase_id.total_invoices_amount == self.purchase_id.amount_total:
            #     raise ValidationError(_('''Bills worth %s already created for this purchase order, check attached bills''') % (self.purchase_id.amount_total))
            if self.purchase_id.total_invoices_amount > 0:
                remaining_amount = self.purchase_id.amount_total - self.purchase_id.total_invoices_amount
                if payment > remaining_amount:
                    raise ValidationError(_('''You are trying to pay: %s, but\n You have already paid: %s for purchase order worth: %s''') % (payment, self.purchase_id.total_invoices_amount, self.purchase_id.amount_total))
            if payment > self.purchase_id.amount_total:
                raise ValidationError(_('''You are trying to pay: %s, but\n You can not pay more than: %s''') % (payment, self.purchase_id.amount_total))
        product = self.purchase_id.company_id.down_payment_product_id
        journal_id = self.env['account.journal'].search([('type', '=', 'purchase'), ('company_id', '=', self.purchase_id.company_id.id)], limit=1)
        if journal_id:
            self.purchase_id.dp_journal_id = journal_id.id
        else:
            raise ValidationError(_('''Please configure at least one Purchase Journal for %s Company''') % (self.purchase_id.company_id.name))
        if not product:
            raise ValidationError(_('''Please configure Advance Payment Product into : Purchase > Settings'''))
        total_swo = 0
        swo = False
        if self.swo_ids:
            swo = True
            for swo in self.swo_ids:
                swo.invoiced = True
                total_swo += swo.contract_term
        total_swo = total_swo / 100 * self.purchase_id.total_down_payment_amount
        total_swo = total_swo * 100 / self.purchase_id.amount_total
        self.purchase_id.paid_swo += total_swo
        amount_swo = self.purchase_id.total_down_payment_amount * (100 - total_swo) / 100
        if self.down_payment_by != 'dont_deduct_down_payment':
            context.update({
                'down_payment': True,
                'down_payment_by': self.down_payment_by,
                'amount': self.amount,
                'swo': swo,
                'total_swo': total_swo,
                'amount_total': amount_swo,
                'swo_ids': self.swo_ids
            })
            if self.purchase_id.down_payment_by in ['fixed', 'percentage']:
                context.update({
                    'dp_amount': payment
                })
        else:
            context.update({
                'down_payment_by': self.down_payment_by,
                'amount': self.amount,
                'swo': swo,
                'total_swo': total_swo,
                'amount_total': amount_swo,
                'swo_ids': self.swo_ids,
                'picking_ids': self.purchase_id.picking_ids.ids
            })
            if self.purchase_id.down_payment_by in ['fixed', 'percentage']:
                context.update({
                    'dp_amount': payment
                })
        invoice_ids = self.purchase_id.invoice_ids.filtered(lambda r: r.is_down_payment)
        purchase_line_ids = self.purchase_id.order_line.filtered(lambda r: r.product_id.purchase_method == 'receive' and not r.qty_received and not r.is_down_payment)
        if invoice_ids and purchase_line_ids:
            raise ValidationError('There are no invoiceable line, please receive the product!')
        if self.down_payment_by == 'deduct_down_payment':
            invoice_ids = self.purchase_id.invoice_ids
            purchase_line_ids = self.purchase_id.order_line.filtered(lambda r: r.product_id.purchase_method == 'receive' and not r.qty_received and not r.is_down_payment)
            if invoice_ids and purchase_line_ids:
                raise ValidationError('There are no invoiceable line, please receive the product!')
        
        # return self.purchase_id.with_context(context).action_create_invoice()

        invoices = self.purchase_id.with_context(context).action_create_invoice()

        if isinstance(invoices, dict):
            invoice_ids = invoices.get('res_id') or invoices.get('res_ids')
            if isinstance(invoice_ids, list):
                invoices = self.env['account.move'].browse(invoice_ids)
            else:
                invoices = self.env['account.move'].browse([invoice_ids])
        pickings = self.env['stock.picking'].search([('purchase_id', '=', self.purchase_id.id)])
        bills = self.env['account.move'].search([('id', 'in', invoices.ids)])
        for bill in bills:
            bill.write({'picking_ids': [(6, 0, pickings.ids)],
                        'po_reference_ids': [(6, 0, self.purchase_id.ids)],
                        'ro_reference_ids': [(6, 0, pickings.ids)]})

            # print('pickings', pickings)

        return {
                'type': 'ir.actions.act_window',
                'name': 'Bills',
                'res_model': 'account.move',
                'view_mode': 'form',
                'res_id': invoices.ids[0] if len(invoices) == 1 else False,
                'domain': [('id', 'in', invoices.ids)],
                'context': self.env.context,
            }

