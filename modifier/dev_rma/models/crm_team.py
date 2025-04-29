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

class crm_team(models.Model):
    _inherit = 'crm.team'
    
    
    rma_draft_count = fields.Integer('Draft RMA', compute='count_rma')
    rma_confirm_count = fields.Integer('Confirm RMA', compute='count_rma')
    rma_process_count = fields.Integer('Process RMA', compute='count_rma')
    rma_close_count = fields.Integer('Close RMA', compute='count_rma')
    rma_reject_count = fields.Integer('Reject RMA', compute='count_rma')
    
    rma_ids = fields.One2many('dev.rma.rma', 'team_id', string='RMA')
    
    @api.depends('rma_ids')
    def count_rma(self):
        for team in self:
            draft_count = confirm_count = process_count = close_count = reject_count = 0
            for rma in team.rma_ids:
                if rma.state == 'draft':
                    draft_count+=1
                
                if rma.state == 'confirm':
                    confirm_count+=1
                    
                if rma.state == 'process':
                    process_count+=1
                
                if rma.state == 'close':
                    close_count+=1
                
                if rma.state == 'reject':
                    reject_count+=1
                    
            team.rma_draft_count = draft_count
            team.rma_confirm_count = confirm_count
            team.rma_process_count = process_count
            team.rma_close_count = close_count
            team.rma_reject_count = reject_count
            
                    
            
    

    


# vim:expandtab:smartindent:tabstop=4:4softtabstop=4:shiftwidth=4:
