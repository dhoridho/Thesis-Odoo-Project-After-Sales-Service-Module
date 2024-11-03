from odoo import models, fields, api


class StockPicking(models.Model):
	_inherit = 'stock.picking'

	kitchen_id = fields.Many2one('kitchen.production.record', 'Kitchen Production', copy=False)
	is_readonly_origin = fields.Boolean()
	
	@api.onchange('location_id', 'location_dest_id')
	def onchange_location_id(self):
		super(StockPicking, self).onchange_location_id()
		force_kitchen_picking_type = self.env.context.get('force_kitchen_picking_type')
		if force_kitchen_picking_type:
			self.picking_type_id = self.env.context.get('default_picking_type_id', False)
