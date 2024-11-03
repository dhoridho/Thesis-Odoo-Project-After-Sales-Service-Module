# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2015 DevIntelle Consulting Service Pvt.Ltd (<http://www.devintellecs.com>).
#
#    For Module Support : devintelle@gmail.com  or Skype : devintelle
#
##############################################################################

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class PurchaseDownPayment(models.TransientModel):
    _name = 'purchase.down.payment'
    _description = ' '

    @api.model
    def default_get(self, fields):
        res = super(PurchaseDownPayment, self).default_get(fields)
        context = dict(self.env.context) or {}
        if context.get('active_model') == "purchase.order":
            purchase_id = self.env['purchase.order'].browse(context.get('active_ids'))
            order_line = purchase_id.order_line
            if all(line.product_id.purchase_method == 'purchase' for line in order_line) and \
                not purchase_id.invoice_ids.filtered(lambda r: r.is_down_payment):
                res['is_down_payment_by_ordered'] = True
                res['down_payment_by_ordered'] = 'fixed'
            elif purchase_id.invoice_ids and purchase_id.invoice_ids.filtered(lambda r: r.is_down_payment):
                res['is_down_payment_by_billable'] = True
                res['down_payment_by_billable'] = 'deduct_down_payment'
            elif all(line.product_id.purchase_method == 'receive' and line.date_received for line in order_line):
                res['is_down_payment_by_ordered'] = True
                res['down_payment_by_ordered'] = 'fixed'
            else:
                res['is_down_payment_by_received'] = True
                res['down_payment_by_received'] = 'fixed'
        return res

    def create_bill(self):
        self.purchase_id.down_payment_by = self.down_payment_by
        self.purchase_id.amount = self.amount
        context = dict(self.env.context) or {}
        if self.purchase_id.down_payment_by in ['fixed', 'percentage']:
            if self.amount <= 0:
                raise ValidationError(_('''Amount must be positive'''))
            if self.purchase_id.down_payment_by == 'percentage':
                payment = self.purchase_id.amount_total * self.purchase_id.amount / 100
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

        context.update({
            'down_payment': True,
            'down_payment_by': self.down_payment_by,
            'amount': self.amount
        })
        invoice_ids = self.purchase_id.invoice_ids.filtered(lambda r: r.is_down_payment)
        purchase_line_ids = self.purchase_id.order_line.filtered(lambda r: r.product_id.purchase_method == 'receive' and not r.qty_received)
        if invoice_ids and purchase_line_ids:
            raise ValidationError('There are no invoiceable line, please receive the product!')
        return self.purchase_id.with_context(context).action_create_invoice()

    down_payment_by = fields.Selection(selection=[('dont_deduct_down_payment', 'Billable lines'),
                                                  ('deduct_down_payment', 'Billable lines (deduct advance payments)'),
                                                  ('percentage', 'Advance payment (percentage)'),
                                                  ('fixed', 'Advance payment (fixed amount)')],
                                       string='What do you want to bill?', default='fixed')
    is_down_payment_by_received = fields.Boolean(string='Is Down Payment Received')
    down_payment_by_received = fields.Selection([('percentage', 'Advance payment (percentage)'),
                                                  ('fixed', 'Advance payment (fixed amount)')],
                                       string='What do you want to bill?')
    is_down_payment_by_ordered = fields.Boolean(string='Is Down Payment Ordered')
    down_payment_by_ordered = fields.Selection([
                                                ('dont_deduct_down_payment', 'Billable lines'),
                                                ('percentage', 'Advance payment (percentage)'),
                                                ('fixed', 'Advance payment (fixed amount)')],
                                       string='What do you want to bill?')
    down_payment_by_billable = fields.Selection([('deduct_down_payment', 'Billable lines (deduct advance payments)')],
                                       string='What do you want to bill?')
    is_down_payment_by_billable = fields.Boolean(string='Is Down Payment Billable')

    @api.onchange('down_payment_by_ordered', 'down_payment_by_received')
    def _onchange_down_payment_by(self):
        if self.down_payment_by_ordered:
            self.down_payment_by = self.down_payment_by_ordered
        elif self.down_payment_by_received:
            self.down_payment_by = self.down_payment_by_received
        elif self.down_payment_by_billable:
            self.down_payment_by = self.down_payment_by_billable

    amount = fields.Float(string='Amount')
    purchase_id = fields.Many2one('purchase.order', string='Purchase')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: