from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class SafetyStock(models.Model):
	_name = 'kitchen.safety.stock'
	_description = 'Safety Stock Management'

	@api.model
	def _default_branch(self):
		default_branch_id = self.env.context.get('default_branch_id', False)
		if default_branch_id:
			return default_branch_id
		return self.env.branch.id if len(self.env.branches) == 1 else False

	@api.model
	def _domain_branch(self):
		return [('id', 'in', self.env.branches.ids)]

	name = fields.Char(required=True)
	company_id = fields.Many2one('res.company', string='Company', required=True, copy=False, default=lambda x: x.env.company)
	is_branch_required = fields.Boolean(related='company_id.show_branch')
	branch_id = fields.Many2one('res.branch', string='Branch', copy=False, default=_default_branch, domain=_domain_branch)
	warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', required=True)
	stock_line_ids = fields.One2many('kitchen.safety.stock.line', 'stock_id', string='Products')

	def _check_warehouse(self, warehouse_id):
		safety_stock_id = self.search([('warehouse_id', '=', warehouse_id)])
		if safety_stock_id:
			warehouse_id = self.env['stock.warehouse'].browse(warehouse_id)
			raise ValidationError(_(f'Safety Stock for Warehouse {warehouse_id.name} already created!'))

	@api.model
	def create(self, values):
		if values.get('warehouse_id'):
			self._check_warehouse(values.get('warehouse_id'))
		return super(SafetyStock, self).create(values)

	def write(self, values):
		if values.get('warehouse_id'):
			self._check_warehouse(values.get('warehouse_id'))
		return super(SafetyStock, self).write(values)


class SafetyStockLine(models.Model):
	_name = 'kitchen.safety.stock.line'
	_description = 'Safety Stock Management Line'

	stock_id = fields.Many2one('kitchen.safety.stock', string='Safety Stock', copy=False, required=True, ondelete='cascade')
	product_id = fields.Many2one('product.product', required=True, string='Product')
	product_qty = fields.Float(string='Quantity', required=True, default=1.0, digits='Product Unit of Measure')

	def _check_product(self, stock_id, product_id):
		line_id = self.search([('stock_id', '=', stock_id), ('product_id', '=', product_id)])
		if line_id:
			raise ValidationError(_("You can't create same product on different line, please merge them!"))

	@api.model
	def create(self, values):
		self._check_product(values.get('stock_id'), values.get('product_id'))
		return super(SafetyStockLine, self).create(values)

	def write(self, values):
		if values.get('product_id'):
			self._check_product(self.stock_id.id, values['product_id'])
		return super(SafetyStockLine, self).write(values)
