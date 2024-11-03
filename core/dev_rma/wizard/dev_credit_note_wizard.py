# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2015 DevIntelle Consulting Service Pvt.Ltd (<http://www.devintellecs.com>).
#
#    For Module Support : devintelle@gmail.com  or Skype : devintelle 
#
##############################################################################

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class dev_credit_note_wizard(models.TransientModel):
    _name = "dev.credit.note.wizard"
    _description = 'Credit Note Wizard'
    
    
    sale_id = fields.Many2one('sale.order', string='Sale Order', required="1")
    rma_id = fields.Many2one('dev.rma.rma', string='RMA')
    product_line_ids = fields.One2many('credit.note.product.lines','credit_note_id', string='Product Lines')
    
    
    def action_credit_notes(self):
        if self.sale_id and self.rma_id and self.product_line_ids:
            inv_val = self.sale_id._prepare_invoice()
            if inv_val:
                origin = inv_val.get('invoice_origin')
                if origin:
                    origin = origin + ' : '+ self.rma_id.name
                else:
                    origin = self.rma_id.name 
                inv_val.update({
                    'move_type':'out_refund',
                    'invoice_origin':origin,
                })
                invoice_id = self.env['account.move'].create(inv_val)
                if invoice_id:
                    vals = []
                    for line in self.product_line_ids:
                        val = line.sale_line_id._dev_invoice_line_val(invoice_id, line.quantity, line.price)
                        vals.append((0,0,val))
                    invoice_id.invoice_line_ids = vals
                    invoice_id._onchange_invoice_line_ids()
                    self.rma_id.invoice_id = invoice_id and invoice_id.id or False
                    
        self.rma_id.dev_process_rma()
            
            
        

class credit_note_product_lines(models.TransientModel):
    _name = 'credit.note.product.lines'
    _description = 'Credit Note Product Lines'
    
    
    
    product_id = fields.Many2one('product.product', string='Product', required="1")
    quantity = fields.Float('Quantity', default=1)
    price = fields.Float('Price')
    sale_line_id = fields.Many2one('sale.order.line', string='Sale Line')
    credit_note_id = fields.Many2one('dev.credit.note.wizard', string='Credit Note')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:    
    
