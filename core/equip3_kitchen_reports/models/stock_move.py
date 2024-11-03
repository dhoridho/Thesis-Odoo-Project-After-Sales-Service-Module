from odoo import models, fields, api
from lxml import etree
from collections import OrderedDict
import logging

_logger = logging.getLogger(__name__)


PIVOT_SELECTED_FIELDS = [
	'warehouse_id', 'kitchen_product_id', 'kitchen_component_id', 
	'product_id', 'kitchen_confirm_date', 'create_uid', 'kitchen_bom_id',
]

PIVOT_SELECTED_MEASURES = [
	'product_uom_qty',
	'quantity_done',
	'kitchen_difference',
	'kitchen_svl_value'
]

PIVOT_MEASURE_SEQUENCE = {
	'product_uom_qty': 1,
	'quantity_done': 2,
	'kitchen_difference': 3,
	'kitchen_svl_value': 4
}


class StockMove(models.Model):
	_inherit = 'stock.move'

	@api.depends('kitchen_component_id', 'kitchen_finished_id', 'stock_valuation_layer_ids', 'stock_valuation_layer_ids.value')
	def _compute_kitchen_svl_value(self):
		for move in self:
			move.kitchen_svl_value = 0.0
			if not move.kitchen_component_id and not move.kitchen_finished_id:
				continue
			move.kitchen_svl_value = sum(move.stock_valuation_layer_ids.mapped('value'))

	@api.depends('product_uom_qty', 'quantity_done')
	def _compute_kitchen_difference(self):
		for record in self:
			record.kitchen_difference = record.product_uom_qty - record.quantity_done

	kitchen_confirm_date = fields.Datetime(related='kitchen_component_id.confirm_date', store=True, copy=False, string='Kitchen Confirmed On')
	kitchen_product_id = fields.Many2one('product.product', related='kitchen_component_id.product_id', store=True, copy=False, string='Kitchen Product')
	kitchen_bom_id = fields.Many2one('mrp.bom', related='kitchen_component_id.bom_id', store=True, string='Kitchen Bill of Materials')
	kitchen_svl_value = fields.Float(compute=_compute_kitchen_svl_value, string='Kitchen SVL Value', store=True)
	kitchen_difference = fields.Float(compute=_compute_kitchen_difference, string='Kitchen Difference', store=True)

	def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
		res = super(StockMove, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)

		if view_type != 'pivot':
			return res

		view_pivot_id = self.env.ref('equip3_kitchen_reports.view_material_consumed_pivot')[0].id
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
			'kitchen_confirm_date': 'Date', 
			'kitchen_component_id': 'Reference',
			'kitchen_product_id': 'Product',
			'product_id': 'Materials Consumed',
			'product_uom_qty': 'To Consume',
			'quantity_done': 'Consumed'
		}

		measure_selected = PIVOT_SELECTED_MEASURES[:]

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
