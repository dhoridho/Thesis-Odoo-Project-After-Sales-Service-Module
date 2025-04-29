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


class replace_product_wizard(models.TransientModel):
    _name = "replace.product.wizard"
    _description = 'Replace Product'
    
    product_id  = fields.Many2one('product.product', string='Old Product')
    replace_product_id = fields.Many2one('product.product', string='Replace Product')
    replace_qty = fields.Float('Replace Qty')
    is_same_product = fields.Boolean(string='Same Product')
    
    @api.onchange('replace_product_id')
    def onchange_replace_product_id(self):
        if self.replace_product_id:
            if self.replace_product_id != self.product_id:
                self.is_same_product = True
            else:
                self.is_same_product = False
        else:
            self.is_same_product = False
    
    
    def action_replace(self):
        active_ids = self._context.get('active_ids')
        line_id = self.env['dev.rma.line'].browse(active_ids)
        if self.is_same_product and self.replace_qty <= 0:
            raise ValidationError(_("Quatity Must be Positive"))
        if line_id:
            line_id.replace_product_id = self.replace_product_id and self.replace_product_id.id or False,
            line_id.replace_qty = self.replace_qty or 0.0
        
    

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:    
    
