from odoo import models, fields, api, _


class AccountMove(models.Model):
    _inherit = 'account.move'

    inventory_id = fields.Many2one('stock.inventory', string='Inventory Adjustment')

    @api.model
    def create(self, vals):
        if self.env.context.get('inventory_id', False):
            vals['inventory_id'] = self.env.context.get('inventory_id', False)
        return super(AccountMove, self).create(vals)
