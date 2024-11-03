from odoo import api, fields, models


class PartnerBlacklistHistory(models.Model):
    _name = 'partner.blacklist.history'
    _description = 'Partner Blacklist History'

    user_id = fields.Many2one(comodel_name='res.users', string='User')
    type = fields.Selection(string='Type', selection=[('blacklisted', 'Blacklisted'), ('whitelisted', 'Unblocked'),])
    reason = fields.Char(string='Reason')
    date = fields.Date(string='Date')
    partner_id = fields.Many2one(comodel_name='res.partner', string='Partner')
    
    
    
    
    
