
from odoo import api, fields, models, _

class ResUsers(models.Model):
    _inherit = 'res.users'

    default_warehouse_id = fields.Many2one('stock.warehouse', string="Default Warehouse")
    allowed_warehouse_ids = fields.Many2many('stock.warehouse', 'user_warhouse_rel', 'warehouse_id', 'user_id', string="Allowed Warehouses")
    access_rights_profile_id = fields.Many2one('access.rights.profile', string="Access Rights Profile", required="1")
    user_delegation_id = fields.Many2one('res.users', string='Approval Delegation')

    def preference_change_password(self):
        return {
            'type': 'ir.actions.client',
            'tag': 'change_password',
            'target': 'new',
            'name':'Change Password'
        }

    def set_groups(self,values):
        if values.get('access_rights_profile_id'):
            group_obj = self.env['access.rights.profile'].browse(values.get('access_rights_profile_id'))
            values['groups_id'] = [(6,0,group_obj.group_ids.ids)]
        return values

    @api.model
    def create(self, values):
        values = self.set_groups(values)
        return super(ResUsers, self).create(values)

    def write(self, values):
        values = self.set_groups(values)
        return super(ResUsers, self).write(values)
    
    @api.onchange('default_warehouse_id')
    def _onchange_warehouse_set(self):
        for record in self:
            if record.default_warehouse_id:
                record.warehouse_id = record.default_warehouse_id.id
                record.property_warehouse_id = record.default_warehouse_id.id
                record.allowed_warehouse_ids = [(6, 0, record.default_warehouse_id.ids)]

    @api.onchange('allowed_warehouse_ids')
    def onchange_allowed_warehouse_ids(self):
        location_ids = []
        new_final_location = []
        if self.restrict_locations:
            for record in self.allowed_warehouse_ids:
                location_obj = self.env['stock.location']
                store_location_id = record.view_location_id.id
                addtional_ids = location_obj.search([('location_id', 'child_of', store_location_id), ('usage', '=', 'internal')])
                for location in addtional_ids:
                    if location.location_id.id not in addtional_ids.ids:
                        location_ids.append(location.id)
                child_location_ids = self.env['stock.location'].search([('id', 'child_of', location_ids), ('id', 'not in', location_ids)]).ids
                final_location = child_location_ids + location_ids
                new_final_location.extend(final_location)
            partner_location_id = self.env.ref('stock.stock_location_locations_partner')
            virtual_location_id = self.env.ref('stock.stock_location_locations_virtual')
            virtual_location = self.env['stock.location'].search([('location_id', 'child_of', virtual_location_id.id), ('usage', '!=', 'view')]).ids
            partner_location = self.env['stock.location'].search([('location_id', 'child_of', partner_location_id.id), ('usage', '!=', 'view')]).ids
            new_final_location.extend(virtual_location)
            new_final_location.extend(partner_location)
            self.stock_location_ids = [(6, 0, new_final_location)]
            operation_type_ids = self.env['stock.picking.type'].search([('warehouse_id', 'in', self.allowed_warehouse_ids.ids)]).ids
            self.default_picking_type_ids = [(6, 0, operation_type_ids)]
