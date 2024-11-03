from odoo import fields, models


class BlacklistPartnerWizard(models.TransientModel):
    _name = 'blacklist.partner.wiz'
    _description = 'Blacklist Partner Wizard'

    partner_id = fields.Many2one(comodel_name='res.partner', string='Partner')
    user_id = fields.Many2one(comodel_name='res.users', string='Blacklisted by', default=lambda self:self.env.user.id)
    type = fields.Selection(string='Type', selection=[('blacklist', 'Blacklist'), ('whitelist', 'Unblock'),],default="blacklist")
    reason = fields.Char(string='Reason')
    
    def action_submit(self):
        partner = self.partner_id
        vals_history = {
            'partner_id':partner.id,
            'user_id':self.user_id and self.user_id.id or self.env.user.id,
            'date':fields.Date.today(),
            'reason':self.reason or '',
            'type':self.type+'ed'
        }
        history = self.env['partner.blacklist.history'].create(vals_history)
        if self.type == 'blacklist':
            partner.action_blacklisted()
        else:
            partner.action_whitelisted()
    
    
    