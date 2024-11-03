from odoo import models, fields, api, _
from odoo.http import request
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError
from lxml import etree
from ast import literal_eval
import json
import datetime
import logging


_logger = logging.getLogger(__name__)


class ProductProduct(models.Model):
	_inherit = 'product.product'

	def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
		res = super(ProductProduct, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
		if view_type != 'tree':
			return res

		kitchen_view_id = self.env.ref('equip3_kitchen_operations.view_product_kitchen_dashboard')
		if view_id != kitchen_view_id.id:
			return res

		record_type = self.env.context.get('default_record_type')
		if not record_type:
			raise UserError(_("Record type is not defined!"))

		doc = etree.XML(res['arch'])
		tmp_to_produce_qty = doc.xpath("//field[@name='tmp_to_produce_qty']")
		action_produce = doc.xpath("//button[@name='action_produce']")

		record_type = record_type == 'kitchen' and 'produce' or record_type

		if tmp_to_produce_qty:
			if record_type == 'disassemble':
				if 'modifiers' in tmp_to_produce_qty[0].attrib:
					modifiers = json.loads(tmp_to_produce_qty[0].attrib['modifiers'])
					modifiers['column_invisible'] = 'true'
					tmp_to_produce_qty[0].set("invisible", "1")
					tmp_to_produce_qty[0].set("modifiers", json.dumps(modifiers))
			
			tmp_to_produce_qty[0].set("string", "To %s" % record_type.title())

		if action_produce:
			action_produce[0].set("string", record_type.title())
		
		res['arch'] = etree.tostring(doc, encoding='unicode')
		return res

	@api.depends('stock_move_ids.product_qty', 'stock_move_ids.state')
	@api.depends_context(
		'lot_id', 'owner_id', 'package_id', 'from_date', 'to_date',
		'location', 'warehouse',
	)
	def _compute_quantities(self):
		products = self.filtered(lambda p: p.type != 'service')
		res = products._compute_quantities_dict(self._context.get('lot_id'), self._context.get('owner_id'), self._context.get('package_id'), self._context.get('from_date'), self._context.get('to_date'))
		for product in products:
			product.qty_available = res[product.id]['qty_available']
			product.incoming_qty = res[product.id]['incoming_qty']
			product.outgoing_qty = res[product.id]['outgoing_qty']
			product.virtual_available = res[product.id]['virtual_available']
			product.free_qty = res[product.id]['free_qty']
			product.safety_stock_qty = res[product.id]['safety_stock_qty']
			product.to_produce_qty = res[product.id]['to_produce_qty']
		# Services need to be set with 0.0 for all quantities
		services = self - products
		services.qty_available = 0.0
		services.incoming_qty = 0.0
		services.outgoing_qty = 0.0
		services.virtual_available = 0.0
		services.free_qty = 0.0
		services.safety_stock_qty = 0.0
		services.to_produce_qty = 0.0

	def _get_safety_stock_qty(self, warehouse):
		self.ensure_one()
		safety_stock_domain = [('warehouse_id', '=', warehouse)] if warehouse else []
		safety_stock_ids = self.env['safety.stock'].search(safety_stock_domain)
		safety_stock_line_ids = safety_stock_ids.mapped('stock_line_ids')
		return sum(safety_stock_line_ids.filtered(
				lambda s: s.product_id == self).mapped('product_qty'))

	def _compute_quantities_dict(self, lot_id, owner_id, package_id, from_date=False, to_date=False):
		res = super(ProductProduct, self)._compute_quantities_dict(lot_id, owner_id, package_id, from_date=from_date, to_date=to_date)

		for product_id in res:
			res[product_id]['safety_stock_qty'] = self.browse(product_id)._get_safety_stock_qty(self.env.context.get('warehouse'))
			if self.env.context.get('record_type') == 'disassemble':
				res[product_id]['to_produce_qty'] = 1.0
			else:
				res[product_id]['to_produce_qty'] = max(
					0.0,
					res[product_id]['safety_stock_qty'] - 
					res[product_id]['qty_available'] - 
					res[product_id]['incoming_qty'] + 
					res[product_id]['outgoing_qty']
				)

		return res

	@api.model
	def get_default_kitchen_dashboard_values(self, values=None):
		record_type = self.env.context.get('default_record_type')

		if values and isinstance(values, dict):
			values = list(values.values())[0]
			if 'false' in values['warehouses'] and values['warehouse_id'] != 'false':
				del values['warehouses']['false']
			return values

		now = fields.Datetime.now()
		values = {
			'date_start': fields.Date.to_date(now).strftime('%Y-%m-%d'),
			'date_end': fields.Date.to_date(now + relativedelta(days=7)).strftime('%Y-%m-%d'),
			'warehouse_id': False
		}

		request.session['kicthen_values'] = values

		result = values.copy()
		result['warehouses'] = {False: 'Please Select Warehouse'}
		for warehouse_id in self.env['stock.warehouse'].search([]):
			result['warehouses'][warehouse_id.id] = warehouse_id.name
		
		return result

	@api.model
	def get_product_based_warehouse(self, values):
		record_type = self.env.context.get('default_record_type')

		if values.get('warehouse_id') in ('false', False):
			values['warehouse_id'] = False
		else:
			values['warehouse_id'] = int(values['warehouse_id'])

		request.session['kicthen_values'] = values

		warehouse_id = values.get('warehouse_id', False)
		date_start = values.get('date_start', False)
		date_end = values.get('date_end', False)

		if date_end:
			date_end = (fields.Date.from_string(date_end) + relativedelta(days=1)).strftime('%Y-%m-%d')

		warehouse_id = self.env['stock.warehouse'].browse(warehouse_id)
		lot_stock_id = warehouse_id.lot_stock_id
		view_location_id = warehouse_id.view_location_id

		# filter product based stock.move and produceable_in_kitchen
		# domain = []
		# if date_start:
		# 	domain.append(('date', '>=', date_start))
		# if date_end:
		# 	domain.append(('date', '<', date_end))

		# stock_move_ids = self.env['stock.move'].search(domain)
		# stock_move_ids = stock_move_ids.filtered(
		# 	lambda s: s.location_id == lot_stock_id or s.location_dest_id == lot_stock_id
		# )

		# if not stock_move_ids:
		# 	return []

		# product_ids = stock_move_ids.mapped('product_id').filtered(lambda p: p.produceable_in_kitchen)

		# use produceable_in_kitchen only instead
		product_ids = self.search([('produceable_in_kitchen', '=', True)])

		product_ids._update_warehouse_quantities(
			record_type=self.env.context.get('default_record_type'),
			warehouse_id=warehouse_id.id,
			view_location_id=view_location_id.id, 
			date_start=date_start, 
			date_end=date_end
		)
		return product_ids.ids

	def _update_warehouse_quantities(self, record_type, warehouse_id, view_location_id, date_start, date_end):
		product_ids = self.with_context(
			warehouse=warehouse_id,
			location=view_location_id
		)

		res = product_ids._compute_quantities_dict(
			False, # lot_id
			False, # owner_id
			False, # package_id
			date_start, 
			date_end
		)

		safety_stock_domain = [('warehouse_id', '=', warehouse_id)] if warehouse_id else []
		safety_stock_ids = self.env['safety.stock'].search(safety_stock_domain)
		safety_stock_line_ids = safety_stock_ids.mapped('stock_line_ids')

		for product_id in product_ids:
			safety_stock_qty = sum(safety_stock_line_ids.filtered(
				lambda x: x.product_id == product_id
			).mapped('product_qty'))
			qty_available = res[product_id.id]['qty_available']
			incoming_qty = res[product_id.id]['incoming_qty']
			outgoing_qty = res[product_id.id]['outgoing_qty']
			to_produce_qty = max(0.0, safety_stock_qty - qty_available - incoming_qty + outgoing_qty)

			product_id.tmp_safety_stock_qty = safety_stock_qty
			product_id.tmp_qty_available = qty_available
			product_id.tmp_incoming_qty = incoming_qty
			product_id.tmp_outgoing_qty = outgoing_qty
			product_id.tmp_to_produce_qty = 1.0 if record_type == 'disassemble' else to_produce_qty

	def action_produce(self):
		self.ensure_one()

		record_type = self.env.context.get('default_record_type')

		if not record_type:
			raise UserError(_("Record type is not defined!"))

		kitchen_values = request.session.get('kicthen_values', dict())
		warehouse_id = kitchen_values.get('warehouse_id', False)

		if self.tmp_to_produce_qty > 0:
			context = self.env.context.copy()

			context.update({
				'default_create_date': fields.Datetime.now(),
				'default_create_uid': self.env.user.id,
				'default_product_id': self.id,
				'default_finished_qty': self.tmp_to_produce_qty,
				'default_warehouse_id': warehouse_id,
				'readonly_warehouse_id': True,
				'return_action': True
			})

			action = {
				'name': "%s Production Record" % record_type.title(),
				'type': 'ir.actions.act_window',
				'res_model': 'kitchen.production.record',
				'view_mode': 'form',
				'target': 'new',
				'context': context
			}
			return action

	# this fields used for display purposes do not use in your code
	tmp_incoming_qty = fields.Float(store=True, copy=False)
	tmp_outgoing_qty = fields.Float(store=True, copy=False)
	tmp_qty_available = fields.Float(store=True, copy=False)
	tmp_to_produce_qty = fields.Float(store=True, copy=False)
	tmp_safety_stock_qty = fields.Float(store=True, copy=False)

	safety_stock_qty = fields.Float(
		'Safety Stock', compute='_compute_quantities',
		digits='Product Unit of Measure', compute_sudo=False)
	to_produce_qty = fields.Float(
		'To Produce', compute='_compute_quantities',
		digits='Product Unit of Measure', compute_sudo=False)


class ProductTemplate(models.Model):
	_inherit = 'product.template'

	def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
		result = super(ProductTemplate, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
		record_type = self.env.context.get('default_record_type')

		if view_type != 'form' or self.env.company.central_kitchen:
			return result

		doc = etree.XML(result['arch'])
		kitchen_tab = doc.xpath("//page[@name='central_kitchen_tab']")
		if kitchen_tab:
			kitchen_tab[0].set('string', 'Assemble')

		produceable_in_kitchen = doc.xpath("//field[@name='produceable_in_kitchen']")
		if produceable_in_kitchen:
			produceable_in_kitchen[0].set('string', 'Can be Assemble/Disassemble?')

		result['arch'] = etree.tostring(doc, encoding='unicode')
		return result

	produceable_in_kitchen = fields.Boolean(string='Produceable in Kitchen')
