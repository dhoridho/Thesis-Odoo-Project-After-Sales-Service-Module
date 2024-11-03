# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class dev_credit_note_wizard(models.TransientModel):
    _inherit = "dev.credit.note.wizard"

    picking_type_code = fields.Selection(related='rma_id.picking_type_code')
    sale_id = fields.Many2one('sale.order', string='Sale Order', required=False)
    purchase_id = fields.Many2one('purchase.order', string='Purchase Order', required=False)

    def action_vendor_credit_notes(self):
        if self.purchase_id and self.rma_id and self.product_line_ids:
            inv_val = self.purchase_id._prepare_invoice()
            journal = self.env['account.move'].with_context(default_move_type='in_refund')._get_default_journal()
            if inv_val:
                origin = inv_val.get('invoice_origin')
                if origin:
                    origin = origin + ' : '+ self.rma_id.name
                else:
                    origin = self.rma_id.name
                inv_val.update({
                    'branch_id' : self.rma_id.branch_id.id,
                    'move_type':'in_refund',
                    'invoice_origin':origin,
                    'journal_id': journal.id or ''
                })
                invoice_id = self.env['account.move'].create(inv_val)
                if invoice_id:
                    vals = []
                    for line in self.product_line_ids:
                        val = line.purchase_line_id._dev_invoice_line_val(invoice_id, line.quantity, line.price)
                        vals.append((0,0,val))
                    invoice_id.invoice_line_ids = vals
                    invoice_id._onchange_invoice_line_ids()
                    self.rma_id.invoice_id = invoice_id and invoice_id.id or False
        self.rma_id.dev_process_rma()
        return True

class credit_note_product_lines(models.TransientModel):
    _inherit = 'credit.note.product.lines'

    purchase_line_id = fields.Many2one('purchase.order.line', string='Purchases Line')
