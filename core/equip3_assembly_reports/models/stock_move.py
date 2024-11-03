from odoo import models, fields, api
from lxml import etree
from collections import OrderedDict


PIVOT_SELECTED_FIELDS = [
	'warehouse_id', 'assembly_product_id', 'assembly_component_id', 
	'product_id', 'assembly_confirm_date', 'create_uid', 'assembly_bom_id',
]

PIVOT_SELECTED_MEASURES = [
	'product_uom_qty',
	'quantity_done',
	'assembly_difference',
	'assembly_svl_value'
]

PIVOT_MEASURE_SEQUENCE = {
	'product_uom_qty': 1,
	'quantity_done': 2,
	'assembly_difference': 3,
	'assembly_svl_value': 4
}


class StockMove(models.Model):
	_inherit = 'stock.move'

	@api.depends('assembly_component_id', 'assembly_finished_id', 'stock_valuation_layer_ids', 'stock_valuation_layer_ids.value')
	def _compute_assembly_svl_value(self):
		for move in self:
			move.assembly_svl_value = 0.0
			if not move.assembly_component_id and not move.assembly_finished_id:
				continue
			move.assembly_svl_value = sum(move.stock_valuation_layer_ids.mapped('value'))

	@api.depends('product_uom_qty', 'quantity_done')
	def _compute_assembly_difference(self):
		for record in self:
			record.assembly_difference = record.product_uom_qty - record.quantity_done

	assembly_record_type = fields.Selection(related='assembly_component_id.record_type', copy=False, store=True)
	assembly_confirm_date = fields.Datetime(related='assembly_component_id.confirm_date', store=True, copy=False, string='Assembly Confirmed On')
	assembly_product_id = fields.Many2one('product.product', related='assembly_component_id.product_id', store=True, copy=False, string='Assembly Product')
	assembly_bom_id = fields.Many2one('mrp.bom', related='assembly_component_id.bom_id', store=True, string='Assembly Bill of Materials')
	assembly_svl_value = fields.Float(compute=_compute_assembly_svl_value, string='Assembly SVL Value', store=True)
	assembly_difference = fields.Float(compute=_compute_assembly_difference, string='Assembly Difference', store=True)

	def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
		res = super(StockMove, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)

		if view_type != 'pivot':
			return res

		view_pivot_id = self.env.ref('equip3_assembly_reports.view_material_consumed_pivot')[0].id
		if view_id != view_pivot_id:
			return res

		doc = etree.XML(res['arch'])
		pivot = doc.xpath('//pivot')
		
		all_fields = self.fields_get()
		sorted_all_fields = OrderedDict()
		for key in sorted(all_fields.keys(), key=lambda k: PIVOT_MEASURE_SEQUENCE[k] if k in PIVOT_MEASURE_SEQUENCE else 0):
			sorted_all_fields[key] = all_fields[key]
	
		label_to_change = {
			'create_uid': 'User', 
			'assembly_confirm_date': 'Date', 
			'assembly_component_id': 'Reference',
			'assembly_product_id': 'Product',
			'product_id': 'Materials Consumed',
			'product_uom_qty': 'To Consume',
			'quantity_done': 'Consumed'
		}

		measure_selected = PIVOT_SELECTED_MEASURES[:]

		record_type = self.env.context.get('default_record_type')
		if record_type == 'disassembly':
			label_to_change['product_uom_qty'] = 'Produced Quantity'
			label_to_change['product_id'], label_to_change['assembly_product_id'] = label_to_change['assembly_product_id'], label_to_change['product_id']

		for i, (field_name, field) in enumerate(sorted_all_fields.items()):
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
