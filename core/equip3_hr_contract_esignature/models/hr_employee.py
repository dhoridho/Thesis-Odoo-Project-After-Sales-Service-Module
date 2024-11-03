# -*- coding: utf-8 -*-

from odoo import models, fields, api


class hrEmployee(models.Model):
    _inherit = 'hr.employee'
    
    
    user_partner_id = fields.Many2one(related='user_id.partner_id', related_sudo=False, string="User's partner",store=True)
    
    
    def action_view_contact(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner',
            'name': 'Contact',
            'view_mode': 'form',
            'target': 'current',
            'context':{},
            'res_id':self.user_partner_id.id
        }
    