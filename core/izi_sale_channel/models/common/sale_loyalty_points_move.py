from odoo import api, fields, models

class SaleLoyaltyPointsMove(models.Model):
    _name = 'sale.loyalty.points.move'

    partner_id = fields.Many2one('res.partner', required=True)
    name = fields.Char('Name')
    loyalty_points = fields.Float('Loyalty Points')
    date = fields.Datetime('Date', required=True)
    move_id = fields.Many2one('account.move', 'Journal Entry')
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirm')], default='draft', string='State')

    def action_confirm(self):
        AccountMove = self.env['account.move']
        for record in self:
            # AccountMove.create({

            # })
            record.partner_id.loyalty_points = record.partner_id.loyalty_points + record.loyalty_points
            record.state = 'confirm'