from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class SaleChannel(models.Model):
    _name = 'sale.channel'
    _inherit = 'sale.channel'
    
    platform = fields.Selection([
        ('mp', 'Marketplace'),
    ], default=False, string='Platform')
    mp_account_id = fields.Many2one('mp.account', string='Marketplace')
    outlet_id = fields.Many2one('sale.outlet', string='Outlet')
    allocation_percentage = fields.Float('Percentage')
    total_allocation_percentage = fields.Float('Total Percentage', compute='_compute_total_allocation')
    allocation_safety = fields.Float('Safety Stock')
    allocate_on = fields.Selection([('sale', 'Sale Order'), ('picking', 'Picking')], default=False, string='Allocate On')
    check_allocation = fields.Boolean('Check Allocation', default=False)
    picking_type_id = fields.Many2one('stock.picking.type', string='Picking Type')

    def _compute_total_allocation(self):
        for record in self:
            total_allocation_percentage = 0
            if record.parent_id:
                for child in record.parent_id.child_ids:
                    total_allocation_percentage += child.allocation_percentage
            else:
                head_channels = self.search([('parent_id', '=', False)])
                for head_channel in head_channels:
                    total_allocation_percentage += head_channel.allocation_percentage
            record.total_allocation_percentage = total_allocation_percentage

    def get_last_child_channels(self, allocation_percentage=100, total_allocation_percentage=100):
        self.ensure_one()
        child_values = []
        for child in self.child_ids:
            if child.child_ids:
                child_values.extend(
                    child.get_last_child_channels(
                        child.allocation_percentage * allocation_percentage / 100, 
                        child.total_allocation_percentage * total_allocation_percentage / 100)
                )
            else:
                child_values.append({
                    'id': child.id,
                    'name': child.name,
                    'allocation_percentage': child.allocation_percentage * allocation_percentage / 100,
                    'total_allocation_percentage': child.total_allocation_percentage * total_allocation_percentage / 100,
                })
        return child_values

    def raise_get_last_child_channels(self):
        child_values = self.get_last_child_channels()
        raise UserError(str(child_values))

    @api.onchange('platform')
    def onchange_platform(self):
        if self.platform == 'mp':
            mp_account = self.env['mp.account'].search([('sale_channel_id', '=', self._origin.id)], limit=1)
            if mp_account:
                self.mp_account_id = mp_account.id