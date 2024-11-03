# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2015 DevIntelle Consulting Service Pvt.Ltd (<http://www.devintellecs.com>).
#
#    For Module Support : devintelle@gmail.com  or Skype : devintelle
#
##############################################################################

from odoo import models, fields, api


class purchase_order(models.Model):
    _inherit = "purchase.order"
    
    
    @api.model
    def _get_default_team_id(self, user_id=None):
        if not user_id:
            user_id = self.env.uid
        company_id = self.sudo(user_id).env.user.company_id.id
        team_id = self.env['dev.purchase.team'].sudo().search([
            '|', ('user_id', '=', user_id), ('member_ids', '=', user_id),
            '|', ('company_id', '=', False), ('company_id', 'child_of', [company_id])
        ], limit=1)
        if team_id:
            team_id = team_id.ids
            return team_id[0]
        
    
    team_id = fields.Many2one('dev.purchase.team', string='Purchase Team', default=_get_default_team_id)
    
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: