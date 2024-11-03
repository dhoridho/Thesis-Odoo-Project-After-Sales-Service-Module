# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import date, datetime, timedelta

class AccountMove(models.Model):
    _inherit = 'account.move'

    cashback_line_ids = fields.One2many('cashback.line','invoice_id', string='Cashback')
    show_cashback = fields.Boolean("Show Cashback")
    is_cn_from_cashback = fields.Boolean(string='Have Credit Note from Cashback')
    so_cashback_id = fields.Many2one(comodel_name='sale.order', string='SO Cashback')
    is_dp = fields.Boolean("Is Down Payment")
    

    @api.model
    def create(self, vals):
        vals['is_dp'] = self.env.context.get('is_dp')
        res = super().create(vals)
        if res.move_type == 'out_invoice':
            if res.sale_order_ids:
                for order in res.sale_order_ids:
                    if order.cashback_line_ids and order.show_cashback:
                        order.cashback_line_ids.write({
                            'invoice_id':res.id,
                        })
                        res.show_cashback = True
        return res
    
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
        res = super(AccountMove,self)._compute_amount()
        for rec in self:
            if rec.is_dp == False and rec.payment_state == 'paid' and rec.move_type == 'out_invoice' and rec.cashback_line_ids and not rec.is_cn_from_cashback:
                # cn_wizard = rec.env['account.move.reversal'].create({
                #     'reason':'Cashback from {}'.format(rec.name),
                #     'move_ids':[(6,0,rec.ids)]
                # })
                # cn_wizard.reverse_moves()
                line_ids = [(5,0,0)]                
                for cashback in rec.cashback_line_ids:
                    vals_line = {
                        'product_id':cashback.product_id.id,
                        'name':cashback.name,                        
                        'analytic_tag_ids':[(6,0,rec.analytic_group_ids.ids)],
                        'quantity':cashback.product_uom_qty,
                        'product_uom_id':cashback.product_id.uom_id.id,
                        'price_unit':cashback.price_unit,
                    }
                    line_ids.append((0,0,vals_line))
                
                # Duplicate Invoicenya tetapi
                # ubah tipe nya jadi Credit Note
                # ubah linennya sesuai cashback
                sale_id = rec.sale_order_ids and rec.sale_order_ids[0] or False
                
                credit_note = rec.copy()
                credit_note.write({
                    'invoice_line_ids':line_ids,
                    'move_type':'out_refund',
                    'ref':'Cashback from {}'.format(rec.name),
                    'so_cashback_id':sale_id.id,
                    'invoice_date': date.today()
                })
                credit_note.action_post()
                if sale_id:
                    sale_id.cashback_line_ids.write({
                            'invoice_id':rec.id,
                        })
                rec.is_cn_from_cashback = True
        return res