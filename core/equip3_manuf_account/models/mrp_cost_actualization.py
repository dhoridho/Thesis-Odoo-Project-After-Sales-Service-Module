from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from odoo.addons.equip3_manuf_account.models.product_template import COST_ACT_ACCOUNT_TYPES
from odoo.addons.base.models.ir_model import quote
from collections import defaultdict
from odoo.tools import float_is_zero


class MRPCostActualization(models.Model):
	_name = 'mrp.cost.actualization'
	_inherit = ['mail.thread', 'mail.activity.mixin']
	_description = 'Production Cost Actualization'

	@api.depends('line_ids', 'line_ids.cost')
	def _compute_total_cost(self):
		for record in self:
			record.total_cost = sum(record.line_ids.mapped('cost'))

	@api.model
	def create(self, values):
		if values.get('name', _('New')) == _('New'):
			values['name'] = self.env['ir.sequence'].next_by_code(
				'mrp.cost.actualization.day', sequence_date=None
			) or _('New')
		return super(MRPCostActualization, self).create(values)

	name = fields.Char(default=lambda self: _('New'), required=True, readonly=True, copy=False)
	company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True, default=lambda self: self.env.company)
	currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
	branch_id = fields.Many2one('res.branch', string='Branch', default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False,
								domain=lambda self: [('id', 'in', self.env.branches.ids)], readonly=True,
								states={'draft': [('readonly', False)]}, required=True, tracking=True)
	state = fields.Selection(
		selection=[('draft', 'Draft'), ('post', 'Posted'), ('cancel', 'Cancelled')],
		required=True,
		copy=False,
		default='draft',
		tracking=True
	)
	create_uid = fields.Many2one('res.users', default=lambda self: self.env.user, readonly=True)
	date_from = fields.Date(string='From Date', readonly=True, states={'draft': [('readonly', False)]}, default=fields.Date.today(), tracking=True)
	date_to = fields.Date(string='To Date', readonly=True, states={'draft': [('readonly', False)]}, default=fields.Date.today(), tracking=True)
	production_ids = fields.Many2many('mrp.production', readonly=True, states={'draft': [('readonly', False)]}, string='Production Order', copy=False, domain="[('state', '=', 'done'), ('date_start', '>=', date_from), ('date_finished', '<=', date_to), ('branch_id', '=', branch_id), ('branch_id', '!=', False)]")
	operation_ids = fields.Many2many('mrp.routing.workcenter', compute='_compute_operations')
	
	bill_type = fields.Selection(selection=[('create', 'Create Bill'), ('choose', 'Choose Bill')], string='Vendor Bill Type', default='create', required=False, readonly=True, states={'draft': [('readonly', False)]})
	bill_ids = fields.Many2many('account.move', string='Bills', domain="[('state', '=','posted'), ('move_type', '=','in_invoice'), ('branch_id', '=', branch_id), ('branch_id', '!=', False)]", readonly=True, states={'draft': [('readonly', False)]})
	
	account_move_id = fields.Many2one('account.move', string='Journal Entry', copy=False, readonly=True)
	line_ids = fields.One2many('mrp.cost.actualization.line', 'mrp_cost_actualization_id', string='Cost Lines')
	
	""" Keep these fields readonly, let force_save do the job """
	valuation_line_ids = fields.One2many('mrp.cost.actualization.valuation', 'mrp_cost_actualization_id', string='Valuation Adjusments', readonly=True)
	production_line_ids = fields.One2many('mrp.cost.actualization.production','mrp_cost_actualization_id', string='Production Cost Lines', readonly=True)
	
	total_cost = fields.Monetary(string='Total', compute=_compute_total_cost)

	actualization_on = fields.Selection(selection=[
		('all', 'All Operations'),
		('specific', 'Sprecific Operations')
	], default='all', string='Actualization On', readonly=True, states={'draft': [('readonly', False)]})

	@api.depends('production_ids')
	def _compute_operations(self):
		for record in self:
			record.operation_ids = [(6, 0, record.production_ids.workorder_ids.mapped('operation_id').ids)]

	@api.model
	def _get_svl_types(self):
		return ['material', 'labor', 'overhead']

	@api.onchange('date_from', 'date_to', 'branch_id')
	def _onchange_production_ids(self):
		if self.date_from and self.date_to and self.branch_id:
			production_ids = self.env['mrp.production'].search([
				('state', '=', 'done'),
				('branch_id', '=', self.branch_id.id),
				('branch_id', '!=', False),
				('date_start', '>=', self.date_from),
				('date_finished', '<=', self.date_to)
			])
			self.production_ids = [(6, 0, production_ids.ids)]

	@api.onchange('bill_type', 'bill_ids')
	def _onchange_bill_ids(self):
		cost_line = [(5,)]
		if self.bill_type == 'choose':
			for line in self.bill_ids.mapped('invoice_line_ids'):
				cost_line.append([0, 0, {
					'product_id' : line.product_id,
					'account_id' : line.account_id,
					'cost_category' : 'overhead',
					'description' : line.name,
					'split_method': 'equal',
					'cost': line.price_subtotal,
				}])
		self.line_ids = cost_line

	@api.onchange('line_ids', 'production_ids', 'company_id', 'actualization_on')
	def _onchange_line_ids(self):
		company_id = self.company_id
		production_ids = self.production_ids
		line_ids = self.line_ids
		actualization_on = self.actualization_on

		total_qty = sum(production_ids.mapped('product_qty'))

		valuation_values = [(5,)]
		for mo in production_ids:
			production_id = mo.id or mo._origin.id
			production_operations = mo.workorder_ids.mapped('operation_id')
			product_qty = mo.product_qty
			for line in line_ids:
				cost_category = line.cost_category
				operation = line.operation_id
				specific_operation = actualization_on == 'specific' and cost_category in ('labor', 'overhead')

				if specific_operation and operation not in production_operations:
					continue

				if line.split_method == 'equal':
					add_cost = line.cost / len(production_ids)
				else:
					add_cost = (product_qty / total_qty) * line.cost
				valuation_values.append([0, 0, {
					'company_id': company_id.id,
					'service_product_id': line.product_id.id,
					'production_id': production_id,
					'category': line.cost_category,
					'account_id': line.account_id.id,
					'operation_id': operation.id if specific_operation else False,
					'add_cost': add_cost
				}])
		self.valuation_line_ids = valuation_values

	@api.onchange('valuation_line_ids')
	def _onchange_valuation_line_ids(self):
		company_id = self.company_id
		production_ids = self.production_ids
		valuation_line_ids = self.valuation_line_ids

		production_line_values = [(5,)]
		mca_types = self._get_svl_types()
		for mo in production_ids:
			production_id = mo.id or mo._origin.id
			valuations = valuation_line_ids.filtered(lambda v: v.production_id.id == production_id)
			finished_svls = mo.move_finished_ids.stock_valuation_layer_ids
			former_cost = 0.0
			for finished_svl in finished_svls:
				former_cost += (finished_svl.mca_last_unit_cost or finished_svl.unit_cost) * finished_svl.quantity
			production = {
				'company_id': company_id.id,
				'production_id': production_id,
				'former_cost': former_cost
			}
			for mca_type in mca_types:
				production['total_%s' % mca_type] = sum(valuations.filtered(lambda v: v.category == mca_type).mapped('add_cost'))
			
			production_line_values.append((0,0,production))
		self.production_line_ids = production_line_values
	
	def action_validate(self):
		self.ensure_one()
		return getattr(self, 'action_validate_%s_bill' % (self.bill_type,))()

	def action_validate_create_bill(self):
		self.ensure_one()

		self = self.with_company(self.company_id)
		valuation_layers = self.valuation_line_ids._update_valuations()
		in_layers = valuation_layers.filtered(lambda o: o.value > 0.0)

		vendor_bill_journal = self.env['account.journal'].search([
			('company_id', '=', self.company_id.id), 
			('type', '=', 'purchase')
		], limit=1)

		move_vals = {
			'invoice_date': fields.Datetime.now(),
			'journal_id': vendor_bill_journal.id,
			'move_type': 'in_invoice',
			'stock_valuation_layer_ids': [(6, None, in_layers.ids)],
			'invoice_line_ids': [(0, 0, {
				'name': o.description,
				'product_id': o.product_id.id,
				'account_id': o.account_id.id,
				'quantity': 1,
				'price_unit': o.cost,
			}) for o in self.line_ids]
		}

		move = self.env['account.move'].create(move_vals)
		self.write({'state': 'post', 'account_move_id': move.id})
		
		return True

	def action_validate_choose_bill(self):
		self.ensure_one()

		self = self.with_company(self.company_id)
		valuation_layers = self.valuation_line_ids._update_valuations()
		in_layers = valuation_layers.filtered(lambda o: o.value > 0.0)
		self.bill_ids.write({'stock_valuation_layer_ids': [(6, 0, in_layers.ids)]})

		self.write({'state': 'post'})

		return True

	def action_cancel(self):
		self.ensure_one()
		self.state = 'cancel'

	def _debug_before(self):
		try:
			from prettytable import PrettyTable
		except ImportError:
			return
		is_cost_per_warehouse = eval(self.env['ir.config_parameter'].get_param('equip3_inventory_base.is_cost_per_warehouse', 'False'))

		table1 = PrettyTable()

		production_products = self.production_ids.move_finished_ids.mapped('product_id')
		lines = self.env['stock.valuation.layer.line'].sudo().search([('product_id', 'in', production_products.ids)])

		rows1 = []
		if is_cost_per_warehouse:
			for product in production_products:
				for warehouse in lines.filtered(lambda o: o.product_id == product).mapped('warehouse_id'):
					rows1 += [[
						product.display_name,
						warehouse.display_name,
						product.with_context(price_for_warehouse=warehouse.id).standard_price
					]]

			table1.field_names = ["Product", "Warehouse", "Cost"]
			table1.add_rows(rows1)
		else:
			for product in production_products:
				rows1 += [[
					product.display_name,
					product.standard_price
				]]
			table1.field_names = ["Product", "Cost"]
			table1.add_rows(rows1)

		print(table1)

	def _debug_after(self):
		try:
			from prettytable import PrettyTable
		except ImportError:
			return
		is_cost_per_warehouse = eval(self.env['ir.config_parameter'].get_param('equip3_inventory_base.is_cost_per_warehouse', 'False'))

		table1 = PrettyTable()
		table2 = PrettyTable()

		production_products = self.production_ids.move_finished_ids.mapped('product_id')
		lines = self.env['stock.valuation.layer.line'].sudo().search([('product_id', 'in', production_products.ids)])

		rows1 = []
		if is_cost_per_warehouse:
			for product in production_products:
				for warehouse in lines.filtered(lambda o: o.product_id == product).mapped('warehouse_id'):
					rows1 += [[
						product.display_name,
						warehouse.display_name,
						product.with_context(price_for_warehouse=warehouse.id).standard_price
					]]

			table1.field_names = ["Product", "Warehouse", "Cost"]
			table1.add_rows(rows1)
		else:
			for product in production_products:
				rows1 += [[
					product.display_name,
					product.standard_price
				]]
			table1.field_names = ["Product", "Cost"]
			table1.add_rows(rows1)
		
		rows2 = []
		for line in lines:
			rows2 += [[
				line.svl_id.id,
				line.product_id.display_name,
				line.lot_id.display_name,
				line.location_id.display_name,
				line.quantity,
				line.unit_cost,
				line.value,
				line.remaining_qty,
				line.remaining_value
			]]

		table2.field_names = ["SVL ID", "Product", "Lot", "Location", "Quantity", "Unit Cost", "Value", "Rem. Qty", "Rem. Value"]
		table2.add_rows(rows2)

		print(table1)
		print(table2)
		raise ValidationError('Error')

	def action_view_created_bill(self):
		self.ensure_one()
		action = self.env['ir.actions.act_window']._for_xml_id('account.action_move_in_invoice_type')
		action.update({'domain': [('id', 'in', self.bill_ids.ids)]})
		return action


class MRPCostActualizationLine(models.Model):
	_name = 'mrp.cost.actualization.line'
	_description = 'Production Cost Actualization Line'

	@api.model
	def _default_allowed_account_types(self):
		return [(6, 0, [self.env.ref(xml_id).id for xml_id in COST_ACT_ACCOUNT_TYPES])]

	def _compute_allowed_account_types(self):
		self.allowed_account_type_ids = self._default_allowed_account_types()

	@api.model
	def _get_account_type_selection(self):
		selection = []
		for xml_id in COST_ACT_ACCOUNT_TYPES:
			account_type_id = self.env.ref(xml_id)
			selection += [(str(account_type_id.id), account_type_id.display_name)]
		return selection

	mrp_cost_actualization_id = fields.Many2one('mrp.cost.actualization', copy=False, required=True, ondelete='cascade')
	company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
	currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
	product_id = fields.Many2one('product.product', string='Product', domain="[('type', '=', 'service')]", required=True)
	cost_category = fields.Selection(
		selection=[('material', 'Material'), ('overhead', 'Overhead'), ('labor', 'Labor')],
		required=False,
		string='Cost Category'
	)

	allowed_account_type_ids = fields.Many2many('account.account.type', compute=_compute_allowed_account_types, default=_default_allowed_account_types)
	
	account_id = fields.Many2one('account.account', string='Account', required=True, domain="[('user_type_id', 'in', allowed_account_type_ids)]")
	description = fields.Char(string='Description', copy=False)
	split_method = fields.Selection(
		selection=[('equal', 'Equal'), ('by_quantity', 'By Quantity')],
		string='Split Method',
		required=True,
		default='equal'
	)
	cost = fields.Monetary(string='Cost')

	operation_id = fields.Many2one('mrp.routing.workcenter', string='Operation')
	actualization_on = fields.Selection(related='mrp_cost_actualization_id.actualization_on')

	@api.onchange('product_id')
	def _onchange_product_id(self):
		self.cost_category = self.product_id.manuf_cost_category
		self.account_id = self.product_id.categ_id.property_account_expense_categ_id.id
			
	@api.onchange('cost_category')
	def _onchange_cost_category(self):
		if self.cost_category:
			self.description = dict(self.fields_get(allfields=['cost_category'])['cost_category']['selection']).get(self.cost_category, False)

	@api.onchange('actualization_on', 'cost_category')
	def _onchange_actualization_on(self):
		if self.cost_category != 'overhead' or self.actualization_on == 'specific':
			self.operation_id = False


class MRPCostActualizationValuation(models.Model):
	_name = 'mrp.cost.actualization.valuation'
	_description = 'Production Cost Actualization Valuation Adjusment'

	@api.model
	def _default_allowed_account_types(self):
		return [(6, 0, [self.env.ref(xml_id).id for xml_id in COST_ACT_ACCOUNT_TYPES])]

	def _compute_allowed_account_types(self):
		self.allowed_account_type_ids = self._default_allowed_account_types()

	@api.model
	def _get_account_type_selection(self):
		selection = []
		for xml_id in COST_ACT_ACCOUNT_TYPES:
			account_type_id = self.env.ref(xml_id)
			selection += [(str(account_type_id.id), account_type_id.display_name)]
		return selection

	mrp_cost_actualization_id = fields.Many2one('mrp.cost.actualization', copy=False, required=True, ondelete='cascade')
	company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
	currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
	production_id = fields.Many2one('mrp.production', string='Production', copy=False)
	product_id = fields.Many2one('product.product', string='Production Product', related='production_id.product_id')
	service_product_id = fields.Many2one('product.product', string='Product', required=True)
	quantity = fields.Float(string='Quantity', related='production_id.finished_product_qty', digits='Product Unit of Measure')
	category = fields.Selection(
		string='Category',
		selection=[('material', 'Material'), ('overhead', 'Overhead'), ('labor', 'Labor')],
		copy=False
	)

	allowed_account_type_ids = fields.Many2many('account.account.type', compute=_compute_allowed_account_types, default=_default_allowed_account_types)
	
	account_id = fields.Many2one('account.account', string='Account', required=True, domain="[('user_type_id', 'in', allowed_account_type_ids)]")
	add_cost = fields.Monetary(string='Additional Cost', copy=False)

	operation_id = fields.Many2one('mrp.routing.workcenter', string='Operation')

	def _get_svl_line_domain(self):
		self.ensure_one()
		finished_moves = self.production_id.move_finished_ids
		svls = finished_moves.stock_valuation_layer_ids
		last_svl_id = max(svls.mapped('id'))
		return [
			('svl_id', '>', last_svl_id),
			('product_id', 'in', finished_moves.mapped('product_id').ids),
		]

	def _update_valuations(self):
		is_cost_per_warehouse = eval(self.env['ir.config_parameter'].get_param('equip3_inventory_base.is_cost_per_warehouse', 'False'))

		svl_vals_list = []
		for line in self:
			actualization = line.mrp_cost_actualization_id
			service_product_id = line.service_product_id

			company_id = actualization.company_id
			currency_id = company_id.currency_id

			mca_type = line.category
			production = line.production_id
			plan = production.mrp_plan_id

			operations = self.env['mrp.routing.workcenter']
			labors = self.env['res.users']
			if mca_type in ('labor', 'overhead'):
				if actualization.actualization_on == 'all':
					operations = production.workorder_ids.mapped('operation_id')
				else:
					operations = line.operation_id
				
				if mca_type == 'labor':
					for operation in operations:
						labors |= operation._get_workcenter().labor_ids.mapped('user_id')

			finished_moves = production.move_finished_ids
			byproduct_moves = production.move_byproduct_ids
			svls = finished_moves.stock_valuation_layer_ids
			linked_layer = svls and svls[-1] or self.env['stock.valuation.layer']

			domain = line._get_svl_line_domain()
			svl_lines = svls.line_ids | self.env['stock.valuation.layer.line'].search(domain)

			group = defaultdict(lambda: self.env['stock.valuation.layer.line'])
			for svl_line in svl_lines:
				svl_type = 'out' if svl_line.quantity < 0 else 'in'
				group[svl_line.product_id, svl_line.warehouse_id, svl_line.location_id, svl_type] |= svl_line

			operation_names = []
			for operation in operations:
				operation_names += [operation.display_name]

			if not operation_names:
				description = actualization.display_name
			else:
				description = '%s - %s' % (actualization.display_name, ', '.join(operation_names))

			additional_cost = line.add_cost
			if currency_id.is_zero(additional_cost):
				continue

			total_byproduct_cost = 0.0
			finished_moves_group = defaultdict(lambda: {'product_qty': 0.0, 'add_cost': 0.0})
			for finished_move in finished_moves:
				finished_moves_group[finished_move.product_id, finished_move.location_dest_id]['product_qty'] += finished_move.product_qty
				if finished_move.byproduct_id:
					byproduct_cost = (additional_cost * finished_move.allocated_cost) / 100
					finished_moves_group[finished_move.product_id, finished_move.location_dest_id]['add_cost'] += byproduct_cost
					total_byproduct_cost += byproduct_cost

			fg_cost = additional_cost - total_byproduct_cost
			fg_unit_cost = fg_cost / line.quantity

			for finished_move in finished_moves.filtered(lambda o: not o.byproduct_id):
				finished_moves_group[finished_move.product_id, finished_move.location_dest_id]['add_cost'] += fg_unit_cost * finished_move.product_qty

			for (product, location), values in finished_moves_group.items():
				values['unit_cost'] = values['add_cost'] / values['product_qty']

			svl_line_group = defaultdict(lambda: [])
			for (product, warehouse, location, svl_type), group_svl_lines in group.items():
				line_values = []
				for svl_line in group_svl_lines:
					unit_cost = finished_moves_group.get((product, location), {}).get('unit_cost', 0.0)
					value = unit_cost * svl_line.quantity

					if currency_id.is_zero(value):
						continue
					
					values = {
						'quantity': 0,
						'unit_cost': 0,
						'value': value,
						'lot_id': svl_line.lot_id.id,
						'description': description
					}

					if svl_type == 'in':
						svl_line.remaining_value += unit_cost * svl_line.remaining_qty

					line_values += [values]

				svl_vals_list += [{
					'type': 'mca_%s' % (mca_type,),
					'company_id': company_id.id,
					'product_id': product.id,
					'description': description,
					'value': sum(o['value'] for o in line_values),
					'quantity': 0,
					'unit_cost': 0,
					'warehouse_id': warehouse.id,
					'location_id': location.id,
					'stock_valuation_layer_id': linked_layer.id,
					'mca_id': actualization.id,
					'mca_operation_ids': [(6, 0, operations.ids)],
					'mca_labor_ids': [(6, 0, labors.ids)],
					'mrp_production_id': production.id,
					'mrp_plan_id': plan.id,
					'lot_ids': [(6, 0, [o['lot_id'] for o in line_values if o['lot_id']])],
					'line_ids': [(0, 0, o) for o in line_values]
				}]

				svl_line_group[(warehouse.id, location.id, plan.id, production.id)] += line_values

			for svl in svl_lines.mapped('svl_id').filtered(lambda o: o.remaining_qty):
				remaining_value = sum(svl.line_ids.mapped('remaining_value'))
				svl.write({
					'remaining_value': remaining_value,
					'mca_last_unit_cost': remaining_value / svl.remaining_qty
				})

			# service product svl
			for (warehouse_id, location_id, plan_id, production_id), line_values in svl_line_group.items():
				svl_value = sum(-o['value'] for o in line_values)
				svl_lot_ids = [o['lot_id'] for o in line_values if o['lot_id']]

				svl_vals_list += [{
					'type': 'mca_%s' % (mca_type,),
					'company_id': company_id.id,
					'product_id': service_product_id.id,
					'description': description,
					'value': svl_value,
					'quantity': 0,
					'unit_cost': 0,
					'warehouse_id': warehouse_id,
					'location_id': location_id,
					'mca_id': actualization.id,
					'mca_operation_ids': [(6, 0, operations.ids)],
					'mca_labor_ids': [(6, 0, labors.ids)],
					'mrp_production_id': production_id,
					'mrp_plan_id': plan_id,
					'lot_ids': [(6, 0, svl_lot_ids)],
					'line_ids': [(0, 0, {
						'quantity': 0,
						'unit_cost': 0,
						'value': -o['value'],
						'lot_id': o['lot_id'],
						'description': o['description']
					}) for o in line_values]
				}]

		stock_valuation_layers = self.env['stock.valuation.layer'].create(svl_vals_list)

		groups = defaultdict(lambda: self.env['stock.valuation.layer'])
		for svl in stock_valuation_layers:
			groups[svl.product_id, svl.warehouse_id, svl.company_id] |= svl.stock_valuation_layer_id

		for (product, warehouse, company), linked_layers in groups.items():

			product_contexed = product.with_company(company)
			if is_cost_per_warehouse:
				product_contexed = product_contexed.with_context(price_for_warehouse=warehouse.id)

			if product.cost_method == 'fifo':
				domain = [
					('company_id', '=', company.id),
					('product_id', '=', product.id),
					('remaining_qty', '>', 0.0)
				]
				if is_cost_per_warehouse:
					domain += [('warehouse_id', '=', warehouse.id)]
				
				next_candidate = self.env['stock.valuation.layer.line'].sudo().search(domain, limit=1)
				if next_candidate:
					product_contexed.with_context(disable_auto_svl=True).standard_price = next_candidate.remaining_value / next_candidate.remaining_qty

			elif product.cost_method == 'average':
				quantity_svl = product_contexed.quantity_svl
				if not float_is_zero(quantity_svl, precision_rounding=product.uom_id.rounding):
					value_svl = product_contexed.value_svl
					product_contexed.with_context(disable_auto_svl=True).standard_price = value_svl / quantity_svl

		account_move_vals_list = []
		for svl in stock_valuation_layers.filtered(lambda o: o.value < 0.0): # out layers
			# prepare journal entries
			account_move_vals_list  += [svl._production_prepare_account_move_vals()]

		if account_move_vals_list:
			self.env['stock.valuation.layer']._production_create_account_moves(account_move_vals_list)

		return stock_valuation_layers


class MRPCostActualizationProduction(models.Model):
	_name = 'mrp.cost.actualization.production'
	_description = 'Production Cost Actualization Production Cost Lines'

	@api.depends('total_material', 'total_overhead', 'total_labor', 'former_cost')
	def _compute_total(self):
		for record in self:
			total = record.total_material + record.total_overhead + record.total_labor
			new_cost = total + record.former_cost
			
			record.total = total
			record.new_cost = new_cost

	mrp_cost_actualization_id = fields.Many2one('mrp.cost.actualization', copy=False, required=True, ondelete='cascade')
	company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
	currency_id = fields.Many2one('res.currency', related='company_id.currency_id')

	production_id = fields.Many2one('mrp.production', string='Production', copy=False)
	product_id = fields.Many2one('product.product', related='production_id.product_id', string='Product')
	quantity = fields.Float(string='Quantity', related='production_id.finished_product_qty', digits='Product Unit of Measure')
	product_uom_id = fields.Many2one('uom.uom', related='production_id.product_uom_id')

	total_material = fields.Monetary(string='Total Material', copy=False)
	total_labor = fields.Monetary(string='Total Labor', copy=False)
	total_overhead = fields.Monetary(string='Total Overhead',  copy=False)
	
	former_cost = fields.Monetary(string='Former Cost', copy=False)
	total = fields.Monetary(string='Total Cost', compute=_compute_total)
	new_cost = fields.Monetary(string='New Cost', compute=_compute_total)
