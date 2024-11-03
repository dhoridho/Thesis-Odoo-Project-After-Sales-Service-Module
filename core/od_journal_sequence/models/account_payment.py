# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    name = fields.Char(readonly=False, copy=False, default='/')

    @api.onchange('posted_before', 'state', 'journal_id', 'date')
    def _onchange_journal_date(self):
        return

    def action_post(self):
        for rec in self:
            if rec.state not in ('draft', 'to_approve', 'approved'):
                raise UserError(_("Only a draft payment can be posted."))
            if any(inv.state != 'posted' for inv in rec.reconciled_invoice_ids):
                raise ValidationError(_("The payment cannot be processed because the invoice is not open!"))
            if rec.name == '/':
                if rec.payment_type == 'transfer':
                    sequence_code = 'account.payment.transfer'
                else:
                    if rec.partner_type == 'customer':
                        if rec.payment_type == 'inbound':
                            sequence_code = 'account.payment.customer.invoice'
                        if rec.payment_type == 'outbound':
                            sequence_code = 'account.payment.customer.refund'
                    if rec.partner_type == 'supplier':
                        if rec.payment_type == 'inbound':
                            sequence_code = 'account.payment.supplier.refund'
                        if rec.payment_type == 'outbound':
                            sequence_code = 'account.payment.supplier.invoice'
                rec.name = self.env['ir.sequence'].next_by_code(sequence_code, sequence_date=rec.date)
        res = super(AccountPayment, self).action_post()
        return res
