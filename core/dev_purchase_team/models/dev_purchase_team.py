# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2015 DevIntelle Consulting Service Pvt.Ltd (<http://www.devintellecs.com>).
#
#    For Module Support : devintelle@gmail.com  or Skype : devintelle
#
##############################################################################

from odoo import models, fields

class purchase_team(models.Model):
    _name = "dev.purchase.team"
    _description = "Purchase Team"
    
    name = fields.Char('Purchase Name', required="1")
    user_id = fields.Many2one('res.users', string='Team Leader')
    company_id = fields.Many2one('res.company', default=lambda self:self.env.user.company_id, required="1")
    member_ids = fields.One2many('res.users', 'purchase_team_id', string='Members')
    active = fields.Boolean(default=True)
    

class res_users(models.Model):
    _inherit = 'res.users'
    
    purchase_team_id = fields.Many2one('dev.purchase.team', string='Purchase Team')
    
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: