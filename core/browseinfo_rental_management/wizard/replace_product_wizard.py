# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import SUPERUSER_ID
from datetime import datetime, timedelta
from odoo import api, fields, models, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError, ValidationError
from dateutil.relativedelta import relativedelta
from odoo.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT

class RentalRenew(models.TransientModel):
	_name = 'rental.renew'
	_rec_name="date"
	_description = "Rental Renew"

	def get_rental_start_date(self):
		rental = self.env['rental.order'].browse(self._context.get('active_id'))
		if rental:
			return rental.start_date

	def get_rental_initial(self):
		rental = self.env['rental.order'].browse(self._context.get('active_id'))
		if rental:
			return rental.rental_initial

	def get_rental(self):
		rental = self.env['rental.order'].browse(self._context.get('active_id'))
		if rental:
			return rental

	date = fields.Datetime(string="New Extended Date", required=False)
	rental_start_date = fields.Datetime(string="Rental Start Date", default=get_rental_start_date)
	rental_initial = fields.Integer(string="Initial Terms", default=get_rental_initial)
	rental_id = fields.Many2one('rental.order', string="Rental Order", default=get_rental)
	rental_initial_type = fields.Selection(string="Initial Terms", related='rental_id.rental_initial_type', readonly=False)

	@api.onchange('rental_initial_type', 'rental_initial')
	def _onchange_rental_initial_type(self):
		if self.rental_initial < 0:
			raise UserError(_("Initials Terms Cannot be Zero"))
		for rental in self:
			internal = rental.rental_initial or 0
			if rental.rental_initial_type == 'days' and rental.rental_start_date:
				rental.date = rental.rental_start_date + relativedelta(days=internal)
			elif rental.rental_initial_type == 'weeks' and rental.rental_start_date:
				rental.date = rental.rental_start_date + relativedelta(days=7 * internal)
			elif rental.rental_initial_type == 'months' and rental.rental_start_date:
				rental.date = rental.rental_start_date + relativedelta(months=internal)
			if rental.rental_initial_type == 'hours':
				if rental.rental_start_date:
					rental.date = rental.rental_start_date + relativedelta(hours=internal)

	def extend_rental(self):
		rental = self.env['rental.order'].browse(self._context.get('active_id'))
		if self.date.date() == self.rental_start_date.date() and rental.rental_initial_type != 'hours':
			raise ValidationError(_("Sorry !!! You cannot change  initials terms for same date"))
		if self.date < self.rental_start_date:
			raise ValidationError(_("Please Select Proper Date"))
		rental.end_date = self.date
		rental.rental_initial_type = self.rental_initial_type
		rental.rental_initial = self.rental_initial
		rental._onchange_rental_initial_type()
		return

class PurchasePrice(models.TransientModel):

	_name = 'purchase.price'
	_description = 'Purchase Price Change'

	product_purchase_price = fields.Float('Purchase Price')

	def set_price(self):
		if self._context == None:
			self._context = {}
		if self._context.get('active_id'):
			active_id = self._context.get('active_id')
			rental_order_obj = self.env['rental.order']
			browse_record = rental_order_obj.browse(active_id)
			browse_record.rental_purchase_price = self.product_purchase_price


class RentalProductReplace(models.Model):
	_name = "rental.product.replace"
	_description = "Rental Product Replace"

	existing_product_ids = fields.One2many('replace.existing.product.line', 'replace_id', string=' Existing Products ')
	replace_product_ids = fields.One2many('replace.new.product.line', 'replace_id', string=' Replace Products ')

	# It should be commented or removed to make new flow work
	# Equip3-moduleboard/core/equip3_rental_operation/models/rental_product_replace.py
	# @api.model
	# def default_get(self, fields):
	# 	rec = super(RentalProductReplace, self).default_get(fields)
	# 	rental = self._context.get('active_id')
	# 	rental_lines = self.env['rental.order'].browse(rental).rental_line
	# 	exlines = []
	# 	for line in rental_lines:
	# 		exlines.append((0, 0, {
	# 			'ro_line_id' : line.id,
	# 			'replace_id' : self.id,
	# 			'replace_item' : True,
	# 			'product_id' : line.product_id.id,
	# 			'product_categ_id' : line.product_id.categ_id.id,
	# 			'lot_id':line.lot_id.id,
	# 			'product_qty':1
	# 		}))
	# 	rec.update({'existing_product_ids': exlines})
	# 	return rec

	
	def replace_product(self):
		rental_id = self._context.get('active_id')
		rental = self.env['rental.order'].browse(rental_id)
		replace_lines = []
		is_replace = []
		move_lines = []
		pick_ids = self.env['stock.picking'].search([('group_id', '=', rental.procurement_group.id),('for_rental_move','=',True)])

		if not self.replace_product_ids :
			raise UserError(_('Select atleast one product to Replace!'))

		for line in self.replace_product_ids :
			for product in rental.rental_line :
				if product.product_id.id == line.product_id.id and product.lot_id.id == line.lot_id.id :
					raise UserError(_('You Can Not Replace Product With Same Lot Number!'))

		for pick in pick_ids:
			if pick.state != 'done':
				raise UserError(_('You can only replace products those are delivered!'))
		
		for rl in self.existing_product_ids:
			lot_id = rl.ro_line_id.lot_id
			rh_ids = self.env['rental.history'].search([('production_lot_id_custom', '=', lot_id.id), ('rental_id', '=', rental.id)])
			for rh in rh_ids:
				rh.state = 'close'    


		exist_p_id=[]
		for line in self.existing_product_ids:
			if line.replace_item == True and line.ro_line_id:
				flag = True
				exist_p_id.append(line.ro_line_id.product_id.id)
				exist_p_id.sort()

		replace_p_id=[]
		for line2 in self.replace_product_ids:
			replace_p_id.append(line2.product_id.id)
			replace_p_id.sort()

		if exist_p_id != replace_p_id:
			raise UserError(_('You have to select Same Product!'))
		
		for line in self.existing_product_ids:
			if line.replace_item == True and line.ro_line_id:
				is_replace.append(line.id)
				line.ro_line_id.unlink()

		if len(is_replace) == 0:
			raise UserError(_('Select atleast one product to Replace!'))
		else:
			pick_ids.action_cancel()        

		move_lines2 = []
		for rline in self.replace_product_ids:
			if rental.rental_initial_type == 'months':
				rline.product_id.replacement_value = rline.unit_price
			if rental.rental_initial_type == 'weeks':
				rline.product_id.weekly_replacement_value = rline.unit_price
			if rental.rental_initial_type == 'days':
				rline.product_id.daily_replacement_value = rline.unit_price
			product = rline.product_id
			name = product.name_get()[0][1]
			pick_type = self.env['stock.picking.type'].search([('name', '=', _('Delivery Orders')), ('warehouse_id', '=', rental.warehouse_id.id)], limit=1).id
			if product.description_sale:
				name += '\n' + product.description_sale

			vals = {'name' : name,
					'product_categ_id' : rline.product_id.categ_id.id,
					'product_id' : rline.product_id.id,
					'price_unit': rental.rental_initial * rline.unit_price,
					'lot_id' : rline.lot_id.id,
					'rental_id' : rental_id}
			replace_lines.append(self.env['rental.order.line'].create(vals).id)
			self.env['rental.history'].create({
				'production_lot_id_custom': vals['lot_id'],
				'start_date': rental.start_date,
				'end_date': rental.end_date,
				'rental_id': vals['rental_id'],
				'state': 'confirm'
			})  

		if replace_lines:
			for i in self.env['rental.order.line'].browse(replace_lines):
				i._action_launch_procurement_rule_custom() # picking is creating from this       
		return

class ReplaceExistingProductLine(models.Model):
	_name = "replace.existing.product.line"
	_description = "Replace Existing Product Line"

	lot_id = fields.Many2one('stock.production.lot', string='Serial Number')
	replace_id = fields.Many2one('rental.product.replace', string='Replace Wiz Id')
	replace_item = fields.Boolean(string='Replace?', default=True)
	product_categ_id = fields.Many2one('product.category',related="product_id.categ_id",string='Product Category', required=True)
	product_id = fields.Many2one('product.product', string='Product', domain=[('rent_ok', '=', True)])
	product_qty = fields.Float(string='Quantity', digits='Product Unit of Measure', default=1.0)
	ro_line_id = fields.Many2one('rental.order.line', string='RentLine')


class ReplaceNewProductLine(models.Model):
	_name = "replace.new.product.line"
	_description = "Replace New Product Line"

	lot_id = fields.Many2one('stock.production.lot', string='Serial Number')
	replace_id = fields.Many2one('rental.product.replace', string='Replace Wiz Id', required=True)
	product_id = fields.Many2one('product.product', string='Product', domain=[('rent_ok', '=', True)], required=True)
	unit_price = fields.Float('Unit Price', default=0.0)

	@api.onchange('product_id')
	def product_id_change(self):
		rental_id = self.env['rental.order'].browse(
			self.env.context.get('active_id'))

		vals = {}

		if not self.product_id:
			return self.update(vals)
		else:
			product = self.product_id
			vals.update({'unit_price': product.rent_per_month or 0.0, })
			if rental_id.rental_initial_type == 'weeks':
				vals.update({'unit_price': product.rent_per_week or 0.0})
			if rental_id.rental_initial_type == 'days':
				vals.update({'unit_price': product.rent_per_day or 0.0})
		return self.update(vals)
