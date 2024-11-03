from odoo import models, fields, api


class StockPicking(models.Model):
	_inherit = 'stock.picking'

	assembly_id = fields.Many2one('assembly.production.record', 'Assembly Production', copy=False)
	is_readonly_origin = fields.Boolean()
	
	@api.onchange('location_id', 'location_dest_id')
	def onchange_location_id(self):
		super(StockPicking, self).onchange_location_id()
		force_assembly_picking_type = self.env.context.get('force_assembly_picking_type')
		if force_assembly_picking_type:
			self.picking_type_id = self.env.context.get('default_picking_type_id', False)

	def action_confirm(self):
		res = super(StockPicking, self).action_confirm()
		assembly_id = self.env.context.get('assembly_pop_back')
		if assembly_id and isinstance(assembly_id, int):
			assembly_object = self.env['assembly.production.record'].with_context(picking_pop_back=self.id)
			return assembly_object.browse(assembly_id).action_get_stock_pickings()
		return res

	def button_validate(self):
		res = super(StockPicking, self).button_validate()

		if res is True or res is None:
			assembly_id = self.env.context.get('assembly_pop_back')
			if assembly_id and isinstance(assembly_id, int):
				record_type = self.env['assembly.production.record'].browse(assembly_id).record_type
				action = self.env['ir.actions.actions']._for_xml_id('equip3_assembly_operations.action_view_%s_production_record' % record_type)
				action['view_mode'] = 'form'
				action['views'] = [(False, 'form')]
				action['res_id'] = assembly_id
				action['target'] = 'new'
				return action
		return res