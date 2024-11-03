from odoo import models, fields, api
from lxml import etree


PIVOT_SELECTED_FIELDS = ['bom_id', 'product_id', 'name', 'create_uid', 'confirm_date', 'warehouse_id']
PIVOT_SELECTED_MEASURES = ['product_qty', 'svl_value']


class AssemblyProductionRecord(models.Model):
	_inherit = 'assembly.production.record'

	def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
		res = super(AssemblyProductionRecord, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)

		if view_type != 'pivot':
			return res

		view_pivot_id = self.env.ref('equip3_assembly_reports.view_finished_product_pivot')[0].id
		if view_id != view_pivot_id:
			return res

		doc = etree.XML(res['arch'])
		pivot = doc.xpath('//pivot')
		
		all_fields = self.fields_get()
		label_to_change = {
			'create_uid': 'User', 
			'confirm_date': 'Date'
		}

		measure_selected = PIVOT_SELECTED_MEASURES[:]

		record_type = self.env.context.get('default_record_type')
		if record_type == 'disassembly':
			label_to_change['product_qty'] = 'Consumed Quantity'
			label_to_change['product_id'] = 'Materials Consumed'

		for i, (field_name, field) in enumerate(all_fields.items()):
			if field['type'] in ['one2many', 'many2many']:
				continue
			field_element = etree.SubElement(pivot[0], 'field')
			field_element.set('name', field_name)

			if field_name in label_to_change:
				attrs = 'string' if field_name not in measure_selected else 'add_string'
				field_element.set(attrs, label_to_change[field_name])

			if field_name in measure_selected:
				field_element.set('type', 'measure')

			else:
				if field_name not in PIVOT_SELECTED_FIELDS:
					field_element.set('invisible', '1')

		res['arch'] = etree.tostring(doc, encoding='unicode')
		return res

	@api.depends('move_raw_ids', 'move_raw_ids.product_uom_qty')
	def _compute_component_consumed_qty(self):
		for production in self:
			production.component_consumed_qty = sum(production.move_raw_ids.mapped('product_uom_qty'))

	@api.depends('move_finished_ids', 'move_finished_ids.product_id', 
		'product_id', 'move_finished_ids.stock_valuation_layer_ids', 'move_finished_ids.stock_valuation_layer_ids.value')
	def _compute_svl_value(self):
		for production in self:
			svl_ids = production.move_finished_ids.filtered(
				lambda move: move.product_id == production.product_id
			).stock_valuation_layer_ids
			production.svl_value = sum(svl_ids.mapped('value'))

	component_consumed_qty = fields.Float(string='Consumed Quantity', compute=_compute_component_consumed_qty, store=True, copy=False)
	svl_value = fields.Float(string='Cost', compute=_compute_svl_value, store=True)
