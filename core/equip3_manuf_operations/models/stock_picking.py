from odoo import models, fields, api, _


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    is_transfer_good = fields.Boolean()
    is_readonly_origin = fields.Boolean()

    @api.onchange('picking_type_id', 'partner_id')
    def onchange_picking_type(self):
        result = super(StockPicking, self).onchange_picking_type()
        force_location_id = self.env.context.get('force_location_id', False)
        force_location_dest_id = self.env.context.get('force_location_dest_id', False)
        if force_location_id:
            self.location_id = force_location_id
        if force_location_dest_id:
            self.location_dest_id = force_location_dest_id
        return result
