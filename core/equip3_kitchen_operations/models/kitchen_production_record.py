import json
from ast import literal_eval
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, AccessError, UserError
from dateutil.relativedelta import relativedelta
from odoo.tools import float_compare, float_round
from lxml import etree


class KitchenProductionRecord(models.Model):
	_name = 'kitchen.production.record'
	_inherit = ['mail.thread', 'mail.activity.mixin']
	_description = 'Kitchen Production Record'

	@api.model
	def _get_default_picking_type(self):
		if self.env.context.get('default_warehouse_id'):
			picking_type_id = self.env['stock.picking.type'].search([
				('code', '=', 'mrp_operation'),
				('warehouse_id', '=', self.env.context['default_warehouse_id'])
			], limit=1)
			if picking_type_id:
				return picking_type_id.id

		company_id = self.env.context.get('default_company_id', self.env.company.id)
		return self.env['stock.picking.type'].search([
			('code', '=', 'mrp_operation'),
			('warehouse_id.company_id', '=', company_id),
		], limit=1).id

	@api.model
	def _get_default_location_src_id(self):
		location = False
		company_id = self.env.context.get('default_company_id', self.env.company.id)
		if self.env.context.get('default_picking_type_id'):
			location = self.env['stock.picking.type'].browse(self.env.context['default_picking_type_id']).default_location_src_id
		if not location:
			location = self.env['stock.warehouse'].search([('company_id', '=', company_id)], limit=1).lot_stock_id
		return location and location.id or False

	@api.model
	def _get_default_location_dest_id(self):
		location = False
		company_id = self.env.context.get('default_company_id', self.env.company.id)
		if self._context.get('default_picking_type_id'):
			location = self.env['stock.picking.type'].browse(self.env.context['default_picking_type_id']).default_location_dest_id
		if not location:
			location = self.env['stock.warehouse'].search([('company_id', '=', company_id)], limit=1).lot_stock_id
		return location and location.id or False

	@api.model
	def _get_default_date_planned_finished(self):
		if self.env.context.get('default_date_planned_start'):
			return fields.Datetime.to_datetime(self.env.context.get('default_date_planned_start')) + relativedelta(hours=1)
		return fields.Datetime.now() + relativedelta(hours=1)

	@api.model
	def _get_default_date_planned_start(self):
		if self.env.context.get('default_date_deadline'):
			return fields.Datetime.to_datetime(self.env.context.get('default_date_deadline'))
		return fields.Datetime.now()

	@api.model
	def _default_branch(self):
		default_branch_id = self.env.context.get('default_branch_id', False)
		if default_branch_id:
			return default_branch_id
		return self.env.branch.id if len(self.env.branches) == 1 else False

	@api.model
	def _default_warehouse(self):
		default_warehouse_id = self.env.context.get('default_warehouse_id', False)
		if default_warehouse_id:
			return default_warehouse_id
		company_id = self.env.context.get('default_company_id', self.env.company.id)
		return self.env['stock.warehouse'].search([
			('company_id', '=', company_id)
		], limit=1).id

	@api.model
	def _domain_branch(self):
		return [('id', 'in', self.env.branches.ids)]

	@api.depends('product_id', 'company_id')
	def _compute_production_location(self):
		if not self.company_id:
			return
		location_by_company = self.env['stock.location'].read_group([
			('company_id', 'in', self.company_id.ids),
			('usage', '=', 'production')
		], ['company_id', 'ids:array_agg(id)'], ['company_id'])
		location_by_company = {lbc['company_id'][0]: lbc['ids'] for lbc in location_by_company}
		for production in self:
			if production.product_id:
				production.production_location_id = production.product_id.with_company(production.company_id).property_stock_production
			else:
				production.production_location_id = location_by_company.get(production.company_id.id)[0]

	@api.depends('move_finished_ids.date_deadline')
	def _compute_date_deadline(self):
		for production in self:
			production.date_deadline = min(production.move_finished_ids.filtered('date_deadline').mapped('date_deadline'), default=production.date_deadline or False)

	def _set_date_deadline(self):
		for production in self:
			production.move_finished_ids.date_deadline = production.date_deadline

	@api.depends('state')
	def _compute_show_submit_button(self):
		for production in self:
			production.show_submit_button = False
			if production.state != 'draft':
				continue
			production.show_submit_button = True

	@api.depends('move_finished_ids')
	def _compute_move_byproduct_ids(self):
		for order in self:
			order.move_byproduct_ids = order.move_finished_ids.filtered(lambda m: m.product_id != order.product_id)

	def _set_move_byproduct_ids(self):
		move_finished_ids = self.move_finished_ids.filtered(lambda m: m.product_id == self.product_id)
		self.move_finished_ids = move_finished_ids | self.move_byproduct_ids

	@api.depends('product_id')
	def _compute_is_autogenerate(self):
		for record in self:
			product_id = record.product_id
			record.is_autogenerate = product_id and product_id._kitchen_is_auto_generate() or False

	@api.depends('product_tracking', 'product_qty', 'rejected_qty', 'finished_lot_ids', 
	'finished_lot_ids.kitchen_qty', 'rejected_lot_ids', 'rejected_lot_ids.kitchen_qty')
	def _compute_default_lot_qty(self):
		for record in self:
			product_qty = 0.0
			rejected_qty = 0.0
			if record.product_tracking == 'serial':
				product_qty = 1.0
				rejected_qty = 1.0
			elif record.product_tracking == 'lot':
				product_qty = record.product_qty - sum(record.finished_lot_ids.mapped('kitchen_qty'))
				rejected_qty = record.rejected_qty - sum(record.rejected_lot_ids.mapped('kitchen_qty'))
			record.default_finished_lot_qty = product_qty
			record.default_rejected_lot_qty = rejected_qty

	@api.depends('move_byproduct_ids', 'move_byproduct_ids.product_id', 'move_byproduct_ids.product_uom_qty', 'byproduct_lot_ids', 'byproduct_lot_ids.kitchen_qty')
	def _compute_byproduct_products(self):
		for record in self:
			product_ids = record.move_byproduct_ids.mapped('product_id')
			record.show_byproduct_lot_tab = any(p.tracking in ('lot', 'serial') for p in product_ids)

			manual_product_ids = product_ids.filtered(lambda p: p._kitchen_is_manual_generate())
			auto_product_ids = product_ids.filtered(lambda p: p._kitchen_is_auto_generate())

			manual_no_repeat_product_ids = manual_product_ids.filtered(lambda p:
				sum(record.move_byproduct_ids.filtered(lambda b: b.product_id == p).mapped('product_uom_qty')) > \
					sum(record.byproduct_lot_ids.filtered(lambda b: b.product_id == p).mapped('kitchen_qty')))
			
			default_lot = {p.id: sum(record.move_byproduct_ids.filtered(lambda b: b.product_id == p).mapped('product_uom_qty')) - \
				sum(record.byproduct_lot_ids.filtered(lambda b: b.product_id == p).mapped('kitchen_qty')) \
					for p in manual_no_repeat_product_ids.filtered(lambda p: p.tracking == 'lot')}

			record.byproduct_manual_product_ids = [(6, 0, manual_no_repeat_product_ids.ids)]
			record.default_byproduct_lot_qty = json.dumps(default_lot)
			record.default_next_byproduct_product_id = manual_no_repeat_product_ids and manual_no_repeat_product_ids[0].id or False
			record.any_byproduct_is_autogenerate = len(auto_product_ids) > 0
			record.all_byproduct_is_autogenerate = len(manual_product_ids) == 0

	def _compute_internal_transfer_count(self):
		itr = self.env['internal.transfer']
		for record in self:
			record.internal_transfer_count = itr.search_count([('source_document', '=', record.name)])

	name = fields.Char(
		'Reference', copy=False, readonly=True, default=lambda x: _('New'))
	company_id = fields.Many2one(
		'res.company', 'Company', default=lambda self: self.env.company,
		index=True, required=True, readonly=True, states={'draft': [('readonly', False)]})
	is_branch_required = fields.Boolean(related='company_id.show_branch')
	product_id = fields.Many2one(
		'product.product', 'Product',
		readonly=True, required=True, check_company=True)

	product_tmpl_id = fields.Many2one(
		'product.template', 'Product Template',
		readonly=True, required=True, check_company=True)

	product_qty = fields.Float(
		'Produced Quantity',
		default=0.0, digits='Product Unit of Measure',
		readonly=True, required=True, tracking=True,
		states={'draft': [('readonly', False)]})

	rejected_qty = fields.Float(
		'Rejected Quantity',
		default=0.0, digits='Product Unit of Measure',
		readonly=True, required=True, tracking=True,
		states={'draft': [('readonly', False)]})

	dashboard_to_produce_qty = fields.Float(
		'To Produce',
		default=0.0, digits='Product Unit of Measure',
		readonly=True)

	product_uom_id = fields.Many2one(
		'uom.uom', 'Product Unit of Measure',
		readonly=True, required=True,
		states={'draft': [('readonly', False)]}, domain="[('category_id', '=', product_uom_category_id)]")

	product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id')

	bom_id = fields.Many2one(
		'mrp.bom', 'Bill of Materials',
		readonly=True, states={'draft': [('readonly', False)]},
		domain="""[
			('equip_bom_type', '=', 'kitchen'),
			('type', '=', 'normal'),
			'|', ('company_id', '=', False), ('company_id', '=', company_id),
			'|', ('branch_id', '=', False), ('branch_id', '=', branch_id)
		]""",
		check_company=True,
		required=True,
		help="Bill of Materials allow you to define the list of required components to make a finished product.")
	
	branch_id = fields.Many2one('res.branch', string='Branch', default=_default_branch, domain=_domain_branch, tracking=True, readonly=True, states={'draft': [('readonly', False)]})
	confirm_date = fields.Datetime(string='Confirmed On')

	state = fields.Selection([
		('draft', 'Draft'),
		('confirm', 'Confirmed')], string='State',
		copy=False, index=True, readonly=True,
		tracking=True, required=True, default='draft')
	move_raw_ids = fields.One2many(
		'stock.move', 'kitchen_component_id', 'Components',
		copy=True, states={'done': [('readonly', True)], 'cancel': [('readonly', True)]},
		domain=[('scrapped', '=', False)])
	move_finished_ids = fields.One2many(
		'stock.move', 'kitchen_finished_id', 'Finished Products',
		copy=True, states={'done': [('readonly', True)], 'cancel': [('readonly', True)]},
		domain=[('scrapped', '=', False)])
	move_byproduct_ids = fields.One2many('stock.move', compute='_compute_move_byproduct_ids', inverse='_set_move_byproduct_ids')
	
	location_src_id = fields.Many2one(
		'stock.location', 'Components Location',
		default=_get_default_location_src_id,
		readonly=True, required=True,
		domain="[('usage','=','internal'), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
		states={'draft': [('readonly', False)]}, check_company=True,
		help="Location where the system will look for components.")
	location_dest_id = fields.Many2one(
		'stock.location', 'Finished Products Location',
		default=_get_default_location_dest_id,
		readonly=True, required=True,
		domain="[('usage','=','internal'), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
		states={'draft': [('readonly', False)]}, check_company=True,
		help="Location where the system will stock the finished products.")

	picking_type_id = fields.Many2one(
		'stock.picking.type', 'Operation Type',
		domain="[('code', '=', 'mrp_operation'), ('company_id', '=', company_id)]",
		default=_get_default_picking_type, required=True, check_company=True, readonly=True, states={'draft': [('readonly', False)]})
	use_create_lots = fields.Boolean(related='picking_type_id.use_create_lots')

	date_planned_start = fields.Datetime(
		'Scheduled Date', copy=False, default=_get_default_date_planned_start,
		help="Date at which you plan to start the production.",
		index=True, required=True, readonly=True, states={'draft': [('readonly', False)]})
	date_planned_finished = fields.Datetime(
		'Scheduled End Date',
		default=_get_default_date_planned_finished,
		help="Date at which you plan to finish the production.",
		copy=False, readonly=True, states={'draft': [('readonly', False)]})
	date_deadline = fields.Datetime(
		'Deadline', copy=False, store=True, readonly=True, compute='_compute_date_deadline', inverse='_set_date_deadline',
		help="Informative date allowing to define when the manufacturing order should be processed at the latest to fulfill delivery on time.")

	procurement_group_id = fields.Many2one(
		'procurement.group', 'Procurement Group',
		copy=False, readonly=True)

	move_dest_ids = fields.One2many('stock.move', 'created_kitchen_id',
		string="Stock Movements of Produced Goods")

	production_location_id = fields.Many2one('stock.location', "Production Location", compute="_compute_production_location", store=True)

	warehouse_id = fields.Many2one('stock.warehouse', check_company=True, copy=False, required=True, readonly=True, states={'draft': [('readonly', False)]}, default=_default_warehouse)
	product_tracking = fields.Selection(related='product_id.tracking')
	account_move_ids = fields.One2many('account.move', 'kitchen_id', string='Journal Entries', copy=False, readonly=True)

	purchase_request_ids = fields.One2many('purchase.request', 'kitchen_id', string='Purchase Requests', readonly=True)
	internal_transfer_count = fields.Integer(compute=_compute_internal_transfer_count)

	expiry_days = fields.Integer('Expiry Days', related='product_id.expiration_time')
	product_use_expiration_date = fields.Boolean(related='product_id.use_expiration_date')
	
	finished_lot_ids = fields.One2many(comodel_name='stock.production.lot', inverse_name='kitchen_production_finished_id', string='Finished Lot/Serial Number')
	byproduct_lot_ids = fields.One2many(comodel_name='stock.production.lot', inverse_name='kitchen_production_byproduct_id', string='ByProduct Lot/Serial Number')
	rejected_lot_ids = fields.One2many(comodel_name='stock.production.lot', inverse_name='kitchen_production_rejected_id', string='Rejected Lot/Serial Number')

	# technical fields
	show_submit_button = fields.Boolean(compute=_compute_show_submit_button)

	is_autogenerate = fields.Boolean(compute=_compute_is_autogenerate)
	default_finished_lot_qty = fields.Float(compute=_compute_default_lot_qty)
	default_rejected_lot_qty = fields.Float(compute=_compute_default_lot_qty)

	show_byproduct_lot_tab = fields.Boolean(compute=_compute_byproduct_products)
	byproduct_manual_product_ids = fields.Many2many('product.product', compute=_compute_byproduct_products)
	default_byproduct_lot_qty = fields.Text(compute=_compute_byproduct_products)
	default_next_byproduct_product_id = fields.Many2one('product.product', compute=_compute_byproduct_products) 
	any_byproduct_is_autogenerate = fields.Boolean(compute=_compute_byproduct_products)
	all_byproduct_is_autogenerate = fields.Boolean(compute=_compute_byproduct_products)

	def default_get(self, field_list):
		res = super(KitchenProductionRecord, self).default_get(field_list)
		if self.env.context.get('default_finished_qty', False):
			res['product_qty'] = self.env.context.get('default_finished_qty')
		return res

	def _get_moves_finished_values(self):
		moves = []
		for production in self:
			product_qty = production.product_qty + production.rejected_qty

			if production.product_id in production.bom_id.byproduct_ids.mapped('product_id'):
				raise UserError(_("You cannot have %s  as the finished product and in the Byproducts", self.product_id.name))
			move_for = 'finished'
			moves.append(production._get_move_values(
				move_for='finished',
				product_id=production.product_id,
				product_uom_qty=product_qty, 
				product_uom=production.product_uom_id
			))
			
			for byproduct_id in production.bom_id.byproduct_ids:
				product_uom_factor = production.product_uom_id._compute_quantity(production.product_qty + production.rejected_qty, production.bom_id.product_uom_id)
				qty = byproduct_id.product_qty * (product_uom_factor / production.bom_id.product_qty)
				moves.append(production._get_move_values(
					move_for='finished',
					product_id=byproduct_id.product_id, 
					product_uom_qty=qty,
					product_uom=byproduct_id.product_uom_id,
					operation_id=byproduct_id.operation_id,
					byproduct_id=byproduct_id
				))
		return moves

	def _get_moves_raw_values(self):
		moves = []
		for production in self:
			product_qty = production.product_qty + production.rejected_qty

			move_for = 'raw'
			factor = production.product_uom_id._compute_quantity(product_qty, production.bom_id.product_uom_id) / production.bom_id.product_qty
			boms, lines = production.bom_id.explode(production.product_id, factor, picking_type=production.bom_id.picking_type_id)
			for bom_line, line_data in lines:
				if bom_line.child_bom_id and bom_line.child_bom_id.type == 'phantom' or\
						bom_line.product_id.type not in ['product', 'consu']:
					continue
				operation_id = bom_line.operation_id.id or line_data['parent_line'] and line_data['parent_line'].operation_id
				prod_values = production._get_move_values(
					move_for='raw',
					product_id=bom_line.product_id,
					product_uom_qty=line_data['qty'],
					product_uom=bom_line.product_uom_id,
					operation_id=operation_id,
					bom_line_id=bom_line,
				)
				prod_values.update({'quantity_done': line_data['qty']})
				moves.append(prod_values)
		return moves

	def _get_move_values(self, move_for, product_id, product_uom_qty, product_uom, operation_id=False, bom_line_id=False, byproduct_id=False):

		if not isinstance(operation_id, int) and operation_id is not False:
			operation_id = operation_id.id

		location_production_id = self.product_id.with_company(self.company_id).property_stock_production.id

		if move_for == 'finished':
			date_planned_finished = self.date_planned_start + relativedelta(days=self.product_id.produce_delay)
			date_planned_finished = date_planned_finished + relativedelta(days=self.company_id.manufacturing_lead)
			if date_planned_finished == self.date_planned_start:
				date_planned_finished = date_planned_finished + relativedelta(hours=1)
			date = date_planned_finished
			date_deadline = self.date_deadline
			location_dest_id = self.location_dest_id.id
			location_id = location_production_id
			warehouse_location = location_dest_id
		else:
			date = self.date_planned_start
			date_deadline = self.date_planned_start
			location_dest_id = location_production_id
			location_id = self.location_src_id.id
			warehouse_location = location_id

		warehouse_id = self.env['stock.location'].browse(warehouse_location).get_warehouse()

		values = {
			'company_id': self.company_id.id,
			'date': date,
			'date_deadline': date_deadline,
			'group_id': self.procurement_group_id.id,
			'location_dest_id': location_dest_id,
			'location_id': location_id,
			'name': self.name,
			'operation_id': operation_id,
			'origin': self.name,
			'picking_type_id': self.picking_type_id.id,
			'price_unit': product_id.standard_price,
			'product_id': product_id.id,
			'product_uom': product_uom,
			'product_uom_qty': product_uom_qty,
			'warehouse_id': warehouse_id.id
		}

		if move_for == 'raw':
			extra_values = {
				'kitchen_product_uom_qty': product_uom_qty,
				'kitchen_component_id': self.id,
				'bom_line_id': bom_line_id.id if bom_line_id else False,
				'procure_method': 'make_to_stock',
				'sequence': bom_line_id.sequence if bom_line_id else 10,
				'state': 'draft'
			}
		else:
			group_orders = self.procurement_group_id.mrp_production_ids
			move_dest_ids = self.move_dest_ids
			if len(group_orders) > 1:
				move_dest_ids |= group_orders[0].move_finished_ids.filtered(lambda m: m.product_id == self.product_id).move_dest_ids
			extra_values = {
				'kitchen_finished_id': self.id,
				'byproduct_id': byproduct_id.id if byproduct_id else False,
				'move_dest_ids': [(4, x.id) for x in move_dest_ids],
			}

		values.update(extra_values)
		return values

	@api.onchange('company_id', 'branch_id')
	def _onchange_company_id(self):
		company_id = self.company_id.id
		branch_id = self.branch_id.id
		bom_id = self.bom_id
		if 'default_warehouse_id' not in self.env.context:
			self.warehouse_id = self.env['stock.warehouse'].search([
				('company_id', '=', company_id), ('branch_id', '=', branch_id)
			], limit=1).id
		if bom_id and (bom_id.company_id.id not in (company_id, False) or bom_id.branch_id.id not in (branch_id, False)):
			self.bom_id = False

	@api.onchange('bom_id')
	def _onchange_bom_id(self):
		self.product_tmpl_id = self.bom_id.product_tmpl_id.id
		self.product_id = self.bom_id.product_id.id or self.product_tmpl_id.product_variant_id.id
		self.product_qty = self.env.context.get('default_finished_qty', self.bom_id.product_qty)
		self.product_uom_id = self.env.context.get('default_product_uom_id', self.bom_id.product_uom_id.id)
		self.picking_type_id = self.env.context.get('default_picking_type_id', self.bom_id.picking_type_id.id) or self.picking_type_id.id

	@api.onchange('date_planned_start', 'product_id')
	def _onchange_date_planned_start(self):
		if self.date_planned_start:
			date_planned_finished = self.date_planned_start + relativedelta(days=self.product_id.produce_delay)
			date_planned_finished = date_planned_finished + relativedelta(days=self.company_id.manufacturing_lead)
			if date_planned_finished == self.date_planned_start:
				date_planned_finished = date_planned_finished + relativedelta(hours=1)
			self.date_planned_finished = date_planned_finished
			self.move_raw_ids = [(1, m.id, {'date': self.date_planned_start}) for m in self.move_raw_ids]
			self.move_finished_ids = [(1, m.id, {'date': date_planned_finished}) for m in self.move_finished_ids]

	@api.onchange('bom_id', 'product_id', 'product_qty', 'rejected_qty', 'product_uom_id')
	def _onchange_move_raw(self):
		if not self.bom_id and not self._origin.product_id:
			return
		# Clear move raws if we are changing the product. In case of creation (self._origin is empty),
		# we need to avoid keeping incorrect lines, so clearing is necessary too.
		if self.product_id != self._origin.product_id:
			self.move_raw_ids = [(5,)]

		if self.bom_id and self.product_qty + self.rejected_qty > 0:
			# keep manual entries
			list_move_raw = [(4, move.id) for move in self.move_raw_ids.filtered(lambda m: not m.bom_line_id)]
			moves_raw_values = self._get_moves_raw_values()

			move_raw_dict = {move.bom_line_id.id: move for move in self.move_raw_ids.filtered(lambda m: m.bom_line_id)}
			for move_raw_values in moves_raw_values:
				move_bom_line = move_raw_values.get('bom_line_id') 
				if move_bom_line and move_bom_line in move_raw_dict:
					# update existing entries
					list_move_raw += [(1, move_raw_dict[move_bom_line].id, move_raw_values)]
				else:
					# add new entries
					list_move_raw += [(0, 0, move_raw_values)]
			self.move_raw_ids = list_move_raw

		else:
			self.move_raw_ids = [(2, move.id) for move in self.move_raw_ids.filtered(lambda m: m.bom_line_id)]		

	@api.onchange('bom_id', 'product_id', 'product_qty', 'rejected_qty', 'product_uom_id')
	def _onchange_move_finished(self):
		if self.product_id and self.product_qty + self.rejected_qty > 0:
			# keep manual entries
			list_move_finished = [(4, move.id) for move in self.move_finished_ids.filtered(
				lambda m: not m.byproduct_id and m.product_id != self.product_id)]
			moves_finished_values = self._get_moves_finished_values()
			moves_byproduct_dict = {move.byproduct_id.id: move for move in self.move_finished_ids.filtered(lambda m: m.byproduct_id)}
			move_finished = self.move_finished_ids.filtered(lambda m: m.product_id == self.product_id)
			for move_finished_values in moves_finished_values:
				if move_finished_values.get('byproduct_id') in moves_byproduct_dict:
					# update existing entries
					list_move_finished += [(1, moves_byproduct_dict[move_finished_values['byproduct_id']].id, move_finished_values)]
				elif move_finished_values.get('product_id') == self.product_id.id and move_finished:
					list_move_finished += [(1, move_finished.id, move_finished_values)]
				else:
					# add new entries
					list_move_finished += [(0, 0, move_finished_values)]
			self.move_finished_ids = list_move_finished
		else:
			self.move_finished_ids = [(2, move.id) for move in self.move_finished_ids.filtered(lambda m: m.bom_line_id)]


	@api.onchange('location_src_id', 'move_raw_ids', 'bom_id')
	def _onchange_location(self):
		source_location = self.location_src_id
		update_value_list = []
		for move in self.move_raw_ids:
			update_value_list += [(1, move.id, ({
				'warehouse_id': source_location.get_warehouse().id,
				'location_id': source_location.id,
				'move_line_ids': [(1, move_line.id, {'location_id': source_location.id}) for move_line in move.move_line_ids]
			}))]
		self.move_raw_ids = update_value_list

	@api.onchange('location_dest_id', 'move_finished_ids', 'bom_id')
	def _onchange_location_dest(self):
		destination_location = self.location_dest_id
		update_value_list = []
		for move in self.move_finished_ids:
			update_value_list += [(1, move.id, ({
				'warehouse_id': destination_location.get_warehouse().id,
				'location_dest_id': destination_location.id,
				'move_line_ids': [(1, move_line.id, {'location_dest_id': destination_location.id}) for move_line in move.move_line_ids]
			}))]
		self.move_finished_ids = update_value_list

	@api.onchange('picking_type_id')
	def onchange_picking_type(self):
		location = self.env.ref('stock.stock_location_stock')
		try:
			location.check_access_rule('read')
		except (AttributeError, AccessError):
			location = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1).lot_stock_id
		(self.move_raw_ids | self.move_finished_ids).update({'picking_type_id': self.picking_type_id})
		
		self.location_src_id = self.env.context.get('default_location_src_id') or self.picking_type_id.default_location_src_id.id or location.id
		self.location_dest_id = self.env.context.get('default_location_dest_id') or self.picking_type_id.default_location_dest_id.id or location.id

	@api.onchange('warehouse_id')
	def _onchange_warehouse_id(self):
		if self.warehouse_id:
			picking_type_id = self.env['stock.picking.type'].search([
				('code', '=', 'mrp_operation'),
				('warehouse_id', '=', self.warehouse_id.id)
			], limit=1)
			if picking_type_id:
				self.picking_type_id = picking_type_id.id
			else:
				self.picking_type_id = False
		else:
			self.picking_type_id = False

	@api.model
	def create(self, values):
		if values.get('product_qty', 0.0) <= 0:
			raise UserError(_("The quantity must be positive!"))
		if values.get('move_finished_ids', False):
			values['move_finished_ids'] = list(filter(lambda move: move[2]['byproduct_id'] is False, values['move_finished_ids']))
		if values.get('move_byproduct_ids', False):
			values['move_finished_ids'] = values.get('move_finished_ids', []) + values['move_byproduct_ids']
			del values['move_byproduct_ids']
		if not values.get('name', False) or values['name'] == _('New'):
			values['name'] = self.env['ir.sequence'].next_by_code('kitchen.production.record') or _('New')
		if not values.get('procurement_group_id'):
			procurement_group_vals = {'name': values['name']}
			values['procurement_group_id'] = self.env["procurement.group"].create(procurement_group_vals).id
		production = super(KitchenProductionRecord, self).create(values)
		(production.move_raw_ids | production.move_finished_ids).write({
			'group_id': production.procurement_group_id.id,
			'origin': production.name
		})
		production.move_raw_ids.write({'date': production.date_planned_start})
		production.move_finished_ids.write({'date': production.date_planned_finished})
		# Trigger move_raw creation when importing a file
		if 'import_file' in self.env.context:
			production._onchange_move_raw()
			production._onchange_move_finished()

		return production

	def write(self, values):
		product_qty = values.get('product_qty', self.product_qty)
		if product_qty <= 0:
			raise UserError(_("The quantity must be positive!"))
		return super(KitchenProductionRecord, self).write(values)
	
	def _check_to_consume_qty(self):
		self.ensure_one()

		not_available = []
		for move in self.move_raw_ids:
			quantity_done = move.product_uom._compute_quantity(move.quantity_done, move.product_id.uom_id)
			if quantity_done <= 0.0:
				raise UserError(_('Consumed quantity must be postive!'))

			if quantity_done > move.kitchen_product_free_qty:
				not_available.append(move.product_id.name)

		if not_available:
			raise UserError(_('Quantity on following components is not available:\n%s' % '\n'.join(['- %s' % name for name in not_available])))

	def _check_tracking(self):
		self.ensure_one()

		# check finished goods tracking
		if self.product_tracking in ('lot', 'serial'):
			need_to_fill = []
			if self.product_qty != sum(self.finished_lot_ids.mapped('kitchen_qty')):
				need_to_fill += ['finished']
			if self.rejected_qty != sum(self.rejected_lot_ids.mapped('kitchen_qty')):
				need_to_fill += ['rejected']

			if need_to_fill:
				raise UserError(_('The amount of generated lot/serial number for %s product is not the same as produced quantity!\nGenerate/delete some lot/serial number first!' % ' and '.join(need_to_fill)))
		
		# check byproduct tracking
		byproduct_moves = self.move_finished_ids.filtered(lambda m: m.product_id != self.product_id)
		tracking_byproducts = byproduct_moves.filtered(lambda b: b.product_id.tracking in ('lot', 'serial'))
		for product_id in tracking_byproducts.mapped('product_id'):
			to_generate_qty = sum(tracking_byproducts.filtered(lambda b: b.product_id == product_id).mapped('product_uom_qty'))
			generated_qty = sum(self.byproduct_lot_ids.filtered(lambda l: l.product_id == product_id).mapped('kitchen_qty'))
			if to_generate_qty != generated_qty:
				raise UserError(_('The amount of generated lot/serial number for %s is not the same as produced quantity!\nGenerate/delete some lot/serial number first!' % product_id.display_name))

	def _get_accounting_journal(self):
		self.ensure_one()
		journal_id = None
		category_name = None
		for move in (self.move_raw_ids | self.move_finished_ids):
			move_journal_id = move.product_id.categ_id.property_stock_journal.id
			if not move_journal_id:
				raise UserError(_('Set Stock Journal for %s product category first!' % move.product_id.categ_id.name))
			
			if not journal_id:
				journal_id = move_journal_id
				category_name = move.product_id.categ_id.name
			else:
				if move_journal_id != journal_id:
					raise UserError(_('%s and %s product category has different Stock Journal' % (category_name, move.product_id.categ_id.name)))
		return journal_id

	def _account_entry_move(self):
		self.ensure_one()

		journal_id = self._get_accounting_journal()
		stock_valuation_layers = (self.move_finished_ids | self.move_raw_ids).stock_valuation_layer_ids
		move_lines = []

		cost_materials = -sum(self.move_raw_ids.stock_valuation_layer_ids.mapped('value'))
		if cost_materials == 0: return

		for svl in stock_valuation_layers:
			if not svl.product_id.valuation == 'real_time':
				continue
			if svl.currency_id.is_zero(svl.value):
				continue

			values = {
				'name': svl.description,
				'product_id': svl.product_id.id,
				'quantity': abs(svl.quantity),
				'product_uom_id': svl.product_id.uom_id.id,
				'ref': svl.description,
				'debit': svl.value if svl.value > 0 else 0,
				'credit': -svl.value if svl.value < 0 else 0,
				'account_id': svl.product_id.categ_id.property_stock_valuation_account_id.id,
			}
			move_lines.append((0, 0, values))

		account_move_values = {
			'name': '/',
			'kitchen_id': self.id,
			'journal_id': journal_id,
			'date': fields.Datetime.now(),
			'move_type': 'entry',
			'line_ids': move_lines,
			'stock_valuation_layer_ids': [(6, None, stock_valuation_layers.ids)]
		}
		account_move_id = self.env['account.move'].create(account_move_values)
		account_move_id._post()
		account_move_id.ref = self.name


	def action_confirm(self):
		self.ensure_one()

		self._check_to_consume_qty()
		self._check_tracking()

		# material moves
		for move in self.move_raw_ids.filtered(lambda m: m.state not in ('done', 'cancel')):
			move.product_uom_qty = move.kitchen_quantity_done
			move._action_done()
		material_cost = abs(sum(self.move_raw_ids.stock_valuation_layer_ids.mapped('value')))

		# byproduct moves
		byproduct_moves = self.move_finished_ids.filtered(lambda m: m.product_id != self.product_id)
		byproduct_cost = 0.0
		for move in byproduct_moves:
			move_cost = (move.byproduct_id.kitchen_allocated_cost * material_cost) / 100
			price_unit = move_cost / move.product_qty
			move.write({'price_unit': price_unit})
			byproduct_cost += move_cost

		tracking_byproduct_ids = byproduct_moves.filtered(lambda m: m.product_id.tracking in ('lot', 'serial'))
		byproduct_lot_ids = self.byproduct_lot_ids
		for product in set(tracking_byproduct_ids.mapped('product_id')):
			byproduct_ids = tracking_byproduct_ids.filtered(lambda m: m.product_id == product)
			byproduct_qty = sum(byproduct_ids.mapped('product_uom_qty'))
			byproduct_lots = byproduct_lot_ids.filtered(lambda b: b.product_id == product)
			self._handle_tracking(byproduct_ids, byproduct_qty, byproduct_lots)

		tracking_byproduct_ids._action_done()
		non_tracking_byproduct_ids = byproduct_moves - tracking_byproduct_ids
		if non_tracking_byproduct_ids:
			for move in non_tracking_byproduct_ids:
				move.quantity_done = move.product_uom_qty
			non_tracking_byproduct_ids._action_done()

		# finished moves
		finished_moves = self.move_finished_ids.filtered(lambda m: m.product_id == self.product_id)
		for move in finished_moves:
			move_cost = (material_cost - byproduct_cost) / len(finished_moves)
			price_unit = move_cost / move.product_qty
			move.write({'price_unit': price_unit})

		self._handle_tracking(finished_moves, self.product_qty, self.finished_lot_ids)
		finished_moves._action_done()

		self._account_entry_move()
		self.confirm_date = fields.Datetime.now()
		self.state = 'confirm'

		if self.env.context.get('return_action', False):
			return self._popup_self()

	def _popup_self(self):
		self.ensure_one()
		action = {
			'type': 'ir.actions.act_window',
			'res_model': 'kitchen.production.record',
			'view_mode': 'form', 
			'view_type': 'form',
			'res_id': self.id,
			'target': 'current'
		}

		if len(self) > 1:
			action.update({
				'view_mode': 'tree,form', 
				'view_type': 'tree,form',
				'domain': [('id', 'in', self.ids)]
			})
			del action['res_id']
		return action

	def action_get_account_moves(self):
		self.ensure_one()
		action_data = self.env['ir.actions.act_window']._for_xml_id('account.action_move_journal_line')
		action_data['domain'] = [('id', 'in', self.account_move_ids.ids)]
		return action_data

	def action_get_purchase_requests(self):
		self.ensure_one()
		action = {
			'name': 'Purchase Request',
			'type': 'ir.actions.act_window',
			'res_model': 'purchase.request',
			'target': 'current'
		}
		if len(self.purchase_request_ids) == 1:
			action['view_mode'] = 'form'
			action['res_id'] = self.purchase_request_ids[0].id
		else:
			action['name'] += 's'
			action['view_mode'] = 'tree,form'
			action['domain'] = [('id', 'in', self.purchase_request_ids.ids)]
		return action

	def action_view_transfer_request(self):
		self.ensure_one()
		transfers = self.env['internal.transfer'].search([('source_document', '=', self.name)])
		action = self.env['ir.actions.actions']._for_xml_id('equip3_inventory_operation.action_internal_transfer_request')
		action['views'] = [(self.env.ref('equip3_inventory_operation.view_form_internal_transfer').id, 'form')]
		if len(transfers) <= 1:
			action['view_mode'] = 'form'
			action['res_id'] = transfers[0].id
		else:
			action['views'] = [(self.env.ref('equip3_inventory_operation.view_tree_internal_transfer').id, 'tree')] + action['views']
			action['domain'] = [('id', 'in', transfers.ids)]
		
		action['target'] = 'new'
		return action

	def action_submit_transfer_request(self):
		self.ensure_one()

		now = fields.Datetime.now()
		line_values = []

		source_locations = []
		source_warehouse = []
		destination_locations = []
		destination_warehouse = []
		for sequence, move in enumerate(self.move_raw_ids):
			qty = move.product_uom_qty - move.kitchen_product_free_qty

			if qty <= 0:
				continue

			location = self.env['stock.location']
			location_dest = move.location_id
			warehouse = location.get_warehouse()
			warehouse_dest = location_dest.get_warehouse()

			if location not in source_locations:
				source_locations += [location]
			if location_dest not in destination_locations:
				destination_locations += [location_dest]
			if warehouse not in source_warehouse:
				source_warehouse += [warehouse]
			if warehouse_dest not in destination_warehouse:
				destination_warehouse += [warehouse_dest]

			values = {
				'sequence': sequence + 1,
				'source_location_id': location.id,
				'destination_location_id': location_dest.id,
				'product_id': move.product_id.id,
				'description': move.product_id.display_name,
				'qty': move.product_uom_qty,
				'uom': move.product_uom.id,
				'scheduled_date': now
			}

			line_values += [(0, 0, values)]

		source_location_id = source_locations[0].id if len(source_locations) == 1 else False
		source_warehouse_id = source_warehouse[0].id if len(source_warehouse) == 1 else False
		destination_location_id = destination_locations[0].id if len(destination_locations) == 1 else False
		destination_warehouse_id = destination_warehouse[0].id if len(destination_warehouse) == 1 else False

		is_single_source_location = len(source_locations) <= 1
		is_single_destination_location = len(destination_locations) <= 1

		values = {
			'default_requested_by': self.env.user.id,
			'default_source_location_id': source_location_id,
			'default_source_warehouse_id': source_warehouse_id,
			'default_destination_location_id': destination_location_id,
			'default_destination_warehouse_id': destination_warehouse_id,
			'default_company_id': self.company_id.id,
			'default_branch_id': self.branch_id.id,
			'default_scheduled_date': now,
			'default_source_document': self.name,
			'default_product_line_ids': line_values,
			'default_is_single_source_location': is_single_source_location,
			'default_is_single_destination_location': is_single_destination_location,
			'kitchen_pop_back': self.id
		}

		action = self.env['ir.actions.actions']._for_xml_id('equip3_inventory_operation.action_internal_transfer_request')
		context = dict(eval(action.get('context', '').strip() or '{}', self._context), create=False)
		context.update(values)
		action.update({
			'context': context,
			'views': [(self.env.ref('equip3_inventory_operation.view_form_internal_transfer').id, 'form')],
			'target': 'new',
		})

		return action

	def action_submit_purchase_request(self):
		warehouse_id = self.warehouse_id.id

		line_ids = []
		for sequence, move in enumerate(self.move_raw_ids.filtered(lambda o: o.product_uom_qty - o.kitchen_product_free_qty > 0.0)):
			qty = move.product_uom_qty - move.kitchen_product_free_qty

			values = {
				'sequence2': sequence + 1,
				'name': move.product_id.display_name,
				'product_id': move.product_id.id,
				'product_uom_id': move.product_uom.id,
				'product_qty': qty,
				'date_required': fields.Date.today(),
				'dest_loc_id': warehouse_id,
			}
			line_ids.append((0, 0, values))

		context = {
			'default_picking_type_id': self.picking_type_id.id,
			'default_company_id': self.company_id.id,
			'default_branch_id': self.branch_id.id,
			'default_line_ids': line_ids,
			'default_origin': self.name,
			'default_destination_warehouse': warehouse_id,
			'default_request_date': fields.Datetime.now(),
			'default_is_readonly_origin': True,
			'default_is_goods_orders': True,
			'default_is_single_request_date': True,
			'default_is_single_delivery_destination': True,
			'default_kitchen_id': self.id,
		}

		action = self.env['ir.actions.actions']._for_xml_id('purchase_request.purchase_request_form_action')
		action_context = dict(eval(action.get('context', '').strip() or '{}', self.env.context))
		action_context.update(context)

		action.update({
			'views':  [(self.env.ref('purchase_request.view_purchase_request_form').id, 'form')], 
			'target': 'new',
			'context': action_context
		})

		return action

	def action_view_stock_valuation_layers(self):
		self.ensure_one()
		domain = [('id', 'in', (self.move_raw_ids + self.move_finished_ids).stock_valuation_layer_ids.ids)]
		action = self.env["ir.actions.actions"]._for_xml_id("stock_account.stock_valuation_layer_action")
		context = literal_eval(action['context'])
		context.update(self.env.context)
		context['no_at_date'] = True
		context['search_default_group_by_product_id'] = False
		return dict(action, domain=domain, context=context)

	@api.model
	def _handle_tracking(self, moves, qty_to_produce, lot_producing_ids):
		for lot_producing_id in lot_producing_ids:
			lot_producing_id.expiration_date = lot_producing_id.kitchen_expiration_date

		for move in moves:
			tracking = move.product_id.tracking

			if tracking == 'serial':
				arange = len(lot_producing_ids)
				qty_done = [1.0] * arange
			elif tracking == 'lot':
				if move.product_id.is_in_autogenerate:
					arange = 1
					qty_done = [qty_to_produce]
				else:
					arange = len(lot_producing_ids)
					qty_done = [lot.kitchen_qty for lot in lot_producing_ids]
			else:
				arange = 1
				qty_done = [qty_to_produce]

			values = [(5,)]
			for i in range(arange):
				vals = move._prepare_move_line_vals(quantity=0)
				vals['qty_done'] = qty_done[i]

				if tracking in ('lot', 'serial'):
					if tracking == 'serial':
						vals['product_uom_id'] = move.product_uom.id

					if i < len(lot_producing_ids):
						vals['lot_id'] = lot_producing_ids[i].id

				values += [(0, 0, vals)]
			move.move_line_ids = values

	def _get_expiration_date(self):
		self.ensure_one()
		if self.product_use_expiration_date:
			now = fields.Datetime.now()
			return now + relativedelta(days=self.expiry_days)
		return False

	def action_generate_serial(self):
		self.ensure_one()
		self.action_generate_serial_finished_goods()
		self.action_generate_serial_byproducts()
		if self.env.context.get('return_action', False):
			action = self._popup_self()
			action['target'] = 'new'
			return action

	def action_generate_serial_byproducts(self):
		self.ensure_one()
		byproduct_product_ids = self.move_byproduct_ids.mapped('product_id').filtered(lambda p: p._kitchen_is_auto_generate())
		if not byproduct_product_ids:
			return
		
		exp_date = self._get_expiration_date()
		lot_values = []
		for product in byproduct_product_ids:
			lot_ids = self.byproduct_lot_ids.filtered(lambda b: b.product_id == product)
			generated_qty = sum(lot_ids.mapped('kitchen_qty'))
			to_generate_qty = sum(self.move_byproduct_ids.filtered(lambda b: b.product_id == product).mapped('product_uom_qty')) - generated_qty

			if to_generate_qty <= 0.0:
				continue

			if product.tracking == 'serial':
				lot_values += [(4, product.kitchen_create_next_lot(1.0, expiration_date=exp_date).id) for i in range(int(to_generate_qty))]
			else:
				if lot_ids:
					lot_values += [(1, lot_ids[-1].id, {'kitchen_qty': lot_ids[-1].kitchen_qty + to_generate_qty})]
				else:
					lot_values += [(4, product.kitchen_create_next_lot(to_generate_qty, expiration_date=exp_date).id)]
		if lot_values:
			self.byproduct_lot_ids = lot_values

	def action_generate_serial_finished_goods(self):
		self.ensure_one()
		product = self.product_id
		if not product._kitchen_is_auto_generate() or self.product_qty <= 0.0:
			return

		product_tracking = self.product_tracking
		exp_date = self._get_expiration_date()
		for ttype, field in [('finished', 'product'), ('rejected', 'rejected')]:
			lot_ids = self[ttype + '_lot_ids']
			generated_qty = sum(lot_ids.mapped('kitchen_qty'))
			to_generate_qty = self[field + '_qty'] - generated_qty

			if to_generate_qty <= 0.0:
				continue

			if product_tracking == 'serial':
				lot_values = [(4, product.kitchen_create_next_lot(1.0, expiration_date=exp_date).id) for i in range(int(to_generate_qty))]
			else:
				if lot_ids:
					lot_values = [(1, lot_ids[-1].id, {'kitchen_qty': lot_ids[-1].kitchen_qty + to_generate_qty})]
				else:
					lot_values = [(4, product.kitchen_create_next_lot(to_generate_qty, expiration_date=exp_date).id)]

			self[ttype + '_lot_ids'] = lot_values
