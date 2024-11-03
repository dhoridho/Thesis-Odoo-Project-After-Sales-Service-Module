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
from odoo.exceptions import UserError, ValidationError

class stock_picking(models.Model):
    _inherit = 'stock.picking'
    
    rma_id = fields.Many2one('dev.rma.rma', string='RMA')
    
    
    
    def button_validate(self):
        if self.rma_id and self.rma_id.state == 'confirm':
            raise ValidationError(_('Process the RMA then after Validate Shipment'))
        
        return super(stock_picking,self).button_validate()
            
    
    
# vim:expandtab:smartindent:tabstop=4:4softtabstop=4:shiftwidth=4:
