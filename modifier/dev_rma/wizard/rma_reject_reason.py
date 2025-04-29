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


class rma_reject_reason(models.TransientModel):
    _name = "rma.reject.reason"
    _description = 'Reject Reason'
    
    reason = fields.Text('Reason', required="1")
    
    def reject_rma(self):
        active_ids = self._context.get('active_ids')
        rma_ids = self.env['dev.rma.rma'].browse(active_ids)
        for rma in rma_ids:
            rma.reject_reason = self.reason
            rma.action_reject()
        
    

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:    
    
