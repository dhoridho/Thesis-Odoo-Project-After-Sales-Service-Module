# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

import datetime
from odoo import api, fields, models, SUPERUSER_ID, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError, ValidationError, Warning
from odoo.tools import float_is_zero, float_compare, DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, float_compare
from dateutil.relativedelta import relativedelta
from itertools import groupby
from operator import itemgetter
from functools import partial
from odoo.tools.misc import formatLang

class res_company(models.Model):
	_inherit = "res.company"

	sale_note = fields.Text(string='Sale Default Terms and Conditions', translate=True)


class ProcurementGroup(models.Model):
	_inherit = 'procurement.group'

	rental_id = fields.Many2one('rental.order', string="Rental Order")

class AccountInvoice(models.Model):
	_inherit = 'account.move'

	rental_id =  fields.Many2one('rental.order')
	rental_start_date = fields.Date(string="Rental Start Date")
	rental_end_date = fields.Date(string="Rental End Date")
	from_rent_order = fields.Boolean(string="Invoice From Rental Order",Default='False')

	def invoice_validate(self):
		res = super(AccountInvoice, self).invoice_validate()
		if self.rental_id:
			for a in self.invoice_line_ids:
				history_ids = self.env['rental.history'].search([('rental_id','=',self.rental_id.id)])
				for hi in history_ids:
					if hi.production_lot_id_custom.product_id.id == a.product_id.id:
						hi.invoice_amount  = a.price_subtotal
		return res


class AccountInvoiceLine(models.Model):
	_inherit = 'account.move.line'

	rental_line_ids = fields.Many2many('rental.order.line', string='Rental Order Lines', readonly=True, copy=False)
	sale_rental_line_ids = fields.Many2many('sale.rental.order.line', string='Sale Rental Order Lines', readonly=True, copy=False)

class MailTemplate(models.Model):
	_inherit = 'mail.template'

	def send_mail(self, res_id, force_send=False, raise_exception=False, email_values=None):
		res = super(MailTemplate, self).send_mail(res_id, force_send=False, raise_exception=False, email_values=None)
		
		if self._context.get('auther'):
			self.env['mail.mail'].sudo().browse(res).author_id = self._context.get('auther').id # [(6,0,[self._context.get('attachment').id])]
		return res



class RentalOrder(models.Model):
	_name = "rental.order"
	_inherit = ['mail.thread',]
	_description = "Rental Order"
	_order = 'date_order desc, id desc'

	def _amount_by_group(self):
		for order in self:
			currency = order.company_id.currency_id
			fmt = partial(formatLang, self.with_context(lang=order.partner_id.lang).env, currency_obj=currency)
			res = {}
			for line in order.rental_line:
				price_reduce = line.price_unit
				taxes = line.tax_id.compute_all(price_reduce, quantity=line.product_uom_qty, product=line.product_id, partner=order.partner_shipping_id)['taxes']
				for tax in line.tax_id:
					group = tax.tax_group_id
					res.setdefault(group, {'amount': 0.0, 'base': 0.0})
					for t in taxes:
						if t['id'] == tax.id or t['id'] in tax.children_tax_ids.ids:
							res[group]['amount'] += t['amount']
							res[group]['base'] += t['base']
			res = sorted(res.items(), key=lambda l: l[0].sequence)
			order.amount_by_group = [(
				l[0].name, l[1]['amount'], l[1]['base'],
				fmt(l[1]['amount']), fmt(l[1]['base']),
				len(res),
			) for l in res]


	@api.depends('rental_line.price_total','sale_line.price_total')
	def _amount_all(self):
		"""
		Compute the total amounts of the SO.
		"""
		for order in self:
			amount_untaxed = amount_tax = 0.0
			for line in order.rental_line:
				amount_untaxed += line.price_subtotal
				amount_tax += line.price_tax
			for line in order.sale_line:
				amount_untaxed += line.price_subtotal
				amount_tax += line.price_tax
			order.update({
				'amount_untaxed': amount_untaxed,
				'amount_tax': amount_tax,
				'amount_total': amount_untaxed + amount_tax,
			})


	@api.constrains('start_date','end_date')
	def _check_date(self):
		if self.end_date and self.start_date :
			if self.end_date < self.start_date:
				raise UserError(_('End Date must be grater then Start Date!!!'))

	
	@api.constrains('rental_bill_freq','rental_bill_freq_type')
	def _check_bill_freq_type(self):
		warning = {}
		if self.rental_bill_freq_type == 'days':
			calc = self.rental_bill_freq/30
			if calc > self.rental_initial:
				raise UserError(_('Invoice cycle period should not be grater then total rental period'))
		if self.rental_bill_freq_type == 'months':
			if self.rental_bill_freq > self.rental_initial:
				raise UserError(_('Invoice cycle period should not be grater then total rental period'))

	
	@api.constrains('rental_initial','rental_bill_freq', 'rental_initial_type', 'rental_bill_freq_type')
	def _check_amount(self):        
		if self.rental_bill_freq == 0:
			raise UserError(_('Rental Bill Frequency can not set to Zero !!!'))
		else:
			if self.rental_initial_type == 'hours':
				if (self.rental_initial % self.rental_bill_freq) != 0:
					raise ValidationError(_('Rental Bill Frequency Must be In multiple of Initial Rental Terms.'))
		if self.rental_initial > 24 and self.rental_initial_type == 'hours':
			raise ValidationError(_('Sorry !!! You Cannot Enter More then 24 hrs'))


	def rental_order_remainder(self):
		config_setting = self.env['res.config.settings'].search([], limit=1, order="id desc")
		today_date = datetime.datetime.today().date()
		if not config_setting.remainder_mail:
			return False
		remainder_date = datetime.datetime.today().date() - datetime.timedelta(days=config_setting.remainder_mail)
		for record in self.sudo().search([]):
			if record.end_date.date() == remainder_date:
				template_id = self.env.ref('browseinfo_rental_management.email_template_rental_expired_remainder')
				auther = record.user_id.partner_id
				template_id.sudo().with_context(auther=auther).send_mail(record.id, force_send=True)
		return True

	def check_expired_contract(self):
		today_date = datetime.datetime.today().date()
		for record in self.search([]):
			if record.end_date.date() >= today_date and record.expired_email_check == False:
				record.sudo().write({
					'expired_email_check' : True
				})
				template_id = self.env.ref('browseinfo_rental_management.email_template_rental_expired')
				auther = record.user_id.partner_id
				template_id.sudo().with_context(auther=auther).send_mail(record.id, force_send=True)
		return True

	
	def check_contract(self):
		today_date = datetime.datetime.today().date()
		for record in self.search([('state','=','confirm')]):
			renew_date = False
			if record.rental_bill_freq_type == 'hours':
				if record.next_invoice_counter > 0:
					next_invoice_counter = record.next_invoice_counter - 1
					record.sudo()._create_invoice()
					record.sudo().write({'next_invoice_counter' : next_invoice_counter})
			else:
				if record.renew_date == today_date and today_date <= record.end_date.date():
					record.sudo()._create_invoice()
					if record.rental_bill_freq_type == 'days': 
						renew_date = datetime.datetime.today().date() + relativedelta(days=record.rental_bill_freq)
					elif record.rental_bill_freq_type == 'months':
						renew_date = datetime.datetime.today().date() + relativedelta(months=record.rental_bill_freq)
					elif record.rental_bill_freq_type == 'weeks':
						renew_date = datetime.datetime.today().date() + relativedelta(days=7*record.rental_bill_freq)

					next_invoice_counter = record.next_invoice_counter - 1

					record.sudo().write({
						'renew_date' : renew_date,
						'next_invoice_counter' : next_invoice_counter
					})
		return True

	@api.model
	def _default_warehouse_id(self):
		company = self.env.user.company_id.id
		warehouse_ids = self.env['stock.warehouse'].search([('company_id', '=', company)], limit=1)
		return warehouse_ids

	@api.model
	def _default_note(self):
		return self.env.user.company_id.sale_note


	expired_email_check = fields.Boolean(string="Expired Email Checked",default=False)
	amount_by_group = fields.Binary(string="Tax amount by group", compute='_amount_by_group', help="type: [(name, amount, base, formated amount, formated base)]")
	name = fields.Char(string='Order Reference', required=True, readonly=True, default='New', copy=False)
	origin = fields.Char(string='Source Document', help="Reference of the document that generated this rental orders request.")
	date_order = fields.Datetime(string='Order Date', required=True, readonly=True, default=fields.Datetime.now)#,states={'draft': [('readonly', False)], 'sent': [('readonly', False)]})
	partner_id = fields.Many2one('res.partner', string='Customer', required=True)
	state = fields.Selection([
		('draft', 'Quotation'),
		('confirm', 'Confirmed Rental'),
		('close', 'Closed Rental'),
	], string='Status', readonly=True, default='draft')
	agrement_ok = fields.Boolean(string='Agreement Received?', default=False)
	partner_invoice_id = fields.Many2one('res.partner', string='Invoice Address', required=True, help="Invoice address for current sales order.")
	partner_shipping_id = fields.Many2one('res.partner', string='Delivery Address', required=True, help="Delivery address for current sales order.")
	start_date = fields.Datetime(string='Start Date')
	end_date = fields.Datetime(string='End Date')
	renew_date = fields.Date('Date Of Next Invoice', copy=False)
	
	confirmation_date = fields.Datetime('Confirmation Date', readonly=True)

	rental_initial = fields.Integer(string='Initial Terms')
	
	rental_initial_type = fields.Selection(string="Initial Terms Type", selection=[
		('hours', 'Hours'), 
		('days', 'Days'), 
		('weeks', 'Weeks'), 
		('months', 'Months')], required=False, default="days" , copy=False)

	rental_bill_freq_type = fields.Selection(string="Freq Type", 
		selection=[
		('hours', 'Hours'), 
		('days', 'Days'), 
		('weeks', 'Weeks'), 
		('months', 'Months')], required=False, default="days", copy=False)
	rental_bill_freq = fields.Integer(string='Rental bill freq',default=0)
	

	rental_purchase_price = fields.Float(string='Purchase Price')
	
	client_order_ref = fields.Char(string='Reference')
	warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse',
								   required=True,default=_default_warehouse_id)
	pricelist_id = fields.Many2one('product.pricelist', string='Pricelist', required=True, help="Pricelist for current sales order.")
	close_date = fields.Datetime(string='Close Date', readonly = True)
	user_id = fields.Many2one('res.users', string='Salesperson', default=lambda self: self.env.user)
	note = fields.Text('Terms and conditions', default=_default_note)
	sale_line = fields.One2many('sale.rental.order.line', 'rental_id', string=' Asset Sale Order Line ',copy =False)
	rental_line = fields.One2many('rental.order.line', 'rental_id', string=' Asset Rental Line ' ,copy =False)
	rental_serial_line = fields.One2many('asset.serial.wrapper', 'rental_id', string='Rental Serial Lines' ,copy =False)
	company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env['res.company']._company_default_get('rental.order'))
	invoice_id = fields.Many2one('account.move', 'Invoice')
	invoice_count = fields.Integer(string='# of Invoices',  readonly=True,compute='_get_invoiced')
	invoice_ids = fields.Many2many("account.move", string='Invoices', readonly=True,compute="_get_invoiced")
	picking_ids = fields.Many2many('stock.picking', compute='_compute_picking_ids', string='Picking associated to this Rental')
	delivery_count = fields.Integer(string='Delivery Orders', compute='_compute_picking_ids')
	procurement_group = fields.Many2one('procurement.group', string="Procurement Group",copy=False)
	amount_untaxed = fields.Float(compute='_amount_all',string='Untaxed Amount', store=True, readonly=True, track_visibility='onchange')
	amount_tax = fields.Float(compute='_amount_all',string='Taxes', store=True, readonly=True)
	amount_total = fields.Float(compute='_amount_all',string='Total', store=True, readonly=True,  track_visibility='always')
	check_saleable = fields.Boolean(string="check saleable product" )
	next_invoice_counter = fields.Integer('Invoice Next Counter', default=0, readonly=True, copy=False)

	@api.model
	def default_get(self,fields):
		res = super(RentalOrder, self).default_get(fields)
		config_id = self.env['res.config.settings'].sudo().search([],order="id desc", limit=1)
		res.update({
			'check_saleable' : config_id.saleable_rental_details
			})
		return res
	
	def _compute_picking_ids(self):
		pickings = []
		for order in self:
			procurement_group_id = self.env['procurement.group'].search([('name','=',order.name)])
			pickings = self.env['stock.picking'].search([('group_id', 'in', procurement_group_id.ids)])
			order.picking_ids = self.env['stock.picking'].search([('group_id', 'in', procurement_group_id.ids)])
			order.delivery_count = len(pickings)

	def unlink(self):
		for rental in self:
			if rental.state != 'draft':
				raise UserError(_('You can only delete draft Rental Orders!'))
		return super(RentalOrder, self).unlink()

	@api.model
	def create(self, vals):
		if vals.get('name', 'New') == 'New':
			vals['name'] = self.env['ir.sequence'].next_by_code('rental.order') or 'New'

		if any(f not in vals for f in ['partner_invoice_id', 'partner_shipping_id', 'pricelist_id']):
			partner = self.env['res.partner'].browse(vals.get('partner_id'))
			addr = partner.address_get(['delivery', 'invoice'])
			vals['partner_invoice_id'] = vals.setdefault('partner_invoice_id', addr['invoice'])
			vals['partner_shipping_id'] = vals.setdefault('partner_shipping_id', addr['delivery'])
			vals['pricelist_id'] = vals.setdefault('pricelist_id', partner.property_product_pricelist and partner.property_product_pricelist.id)

		if not vals.get('start_date'):
			vals['start_date'] = datetime.datetime.today().date()
		if vals.get('rental_bill_freq_type') == 'days':
			calc = int(vals['rental_bill_freq'])/30
			if calc > int(vals['rental_initial']):
				raise Warning('Invoice cycle period should not be grater then total rental period')
		if vals.get('rental_bill_freq_type') == 'months':
			if vals['rental_bill_freq'] > vals['rental_initial']:
				raise Warning('Invoice cycle period should not be grater then total rental period')

		result = super(RentalOrder, self).create(vals)
		return result

	def onchange_rental_product_lines(self, internal):
		rit = self.rental_initial_type
		for line in self.rental_line:
			if rit == 'hours':
				line.price_unit = line.product_id.rent_per_hour * internal or 0
			if rit == 'days':
				line.price_unit = line.product_id.rent_per_day * internal or 0
			if rit == 'weeks':
				line.price_unit = line.product_id.rent_per_week * internal or 0
			if rit == 'months':
				line.price_unit = line.product_id.rent_per_month * internal or 0

	@api.onchange('rental_initial', 'rental_initial_type', 'start_date', 'rental_bill_freq')
	def _onchange_rental_initial_type(self):
		for rental in self:
			internal = rental.rental_initial or 0
			if rental.rental_initial_type == 'days' and rental.start_date:
				rental.end_date = rental.start_date + relativedelta(days=internal)
			elif rental.rental_initial_type == 'weeks' and rental.start_date:
				rental.end_date = rental.start_date + relativedelta(days=7 * internal)
			elif rental.rental_initial_type == 'months' and rental.start_date:
				rental.end_date = rental.start_date + relativedelta(months=internal)
			if rental.rental_initial_type == 'hours':
				rental.rental_bill_freq_type = 'days'
				if rental.start_date:
					rental.end_date = rental.start_date + relativedelta(hours=internal)
			self.onchange_rental_product_lines(internal)

	def _create_serial_wrapper(self):
		for rental in self:
			for line in rental.rental_line:
				vals = {'product_id' : line.product_id.id,
						'lot_id' : line.lot_id.id,
						'rental_id' : line.rental_id.id}
				self.env['asset.serial.wrapper'].create(vals)
		return

	def _create_invoice_with_saleable(self , force=False):
		inv_obj = self.env['account.move']
		inv_line = []

		for rental in self:
			for line in rental.rental_line:
				account_id = False
				if line.product_id.id:
					account_id = line.product_id.categ_id.property_account_income_categ_id.id
				if not account_id:
					raise UserError(
						_('There is no income account defined for this product: "%s". You may have to install a chart of account from Accounting app, settings menu.') % \
						(line.product_id.name,))
				name = _('Down Payment')
				inv_line.append((0, 0, {
					'name' : line.product_id.description_rental or line.name or " ",
					'account_id': account_id,
					'price_unit': line.price_unit,
					'quantity': 1.0,
					'rental_line_ids': [(6, 0, [line.id])],
					'product_uom_id': line.product_id.uom_id.id,
					'product_id': line.product_id.id,
					'tax_ids': [(6, 0, line.tax_id.ids)],
				}))
			if rental.check_saleable:
				for line in rental.sale_line:
					account_id = False
					if line.product_id.id:
						account_id = line.product_id.categ_id.property_account_income_categ_id.id
					if not account_id:
						raise UserError(
							_('There is no income account defined for this product: "%s". You may have to install a chart of account from Accounting app, settings menu.') % \
							(line.product_id.name,))
					name = _('Down Payment')
					inv_line.append((0, 0, {
						'name' : line.product_id.description_rental or line.name or " ",
						'account_id': account_id,
						'price_unit': line.price_unit,
						'quantity': line.product_uom_qty,
						'sale_rental_line_ids': [(6, 0, [line.id])],
						'product_uom_id': line.product_id.uom_id.id,
						'product_id': line.product_id.id,
						'tax_ids': [(6, 0, line.tax_id.ids)],
					}))                    
			invoice = inv_obj.create({
				'name': rental.client_order_ref or rental.name or " ",
				'invoice_origin': rental.name or " ",
				'move_type': 'out_invoice',
				'rental_id': rental.id,
				'ref': False,
				'partner_id': rental.partner_invoice_id.id,
				'invoice_line_ids': inv_line,
				'currency_id': rental.pricelist_id.currency_id.id,
				'user_id':rental.user_id.id,
				'rental_start_date': rental.start_date,
				'rental_end_date' : rental.end_date,
				'from_rent_order' :True,
			})
		return invoice

	def _create_invoice(self,force=False):
		inv_obj = self.env['account.move']
		inv_line = []
		for rental in self:
			for line in rental.rental_line:
				account_id = False
				if line.product_id.id:
					account_id = line.product_id.categ_id.property_account_income_categ_id.id
				if not account_id:
					raise UserError(
						_('There is no income account defined for this product: "%s". You may have to install a chart of account from Accounting app, settings menu.') % \
						(line.product_id.name,))
				name = _('Down Payment')
				inv_line.append((0, 0, {
					'name' : line.product_id.description_rental or line.name or " ",
					'account_id': account_id,
					'price_unit': line.price_unit,
					'quantity': 1.0,
					'rental_line_ids': [(6, 0, [line.id])],
					'product_uom_id': line.product_id.uom_id.id,
					'product_id': line.product_id.id,
					'tax_ids': [(6, 0, line.tax_id.ids)],
				}))
			invoice = inv_obj.create({
				'name': rental.client_order_ref or rental.name or " ",
				'type': 'out_invoice',
				'rental_id': rental.id,
				'ref': False,
				'partner_id': rental.partner_invoice_id.id,
				'invoice_line_ids': inv_line,
				'currency_id': rental.pricelist_id.currency_id.id,
				'user_id':rental.user_id.id,
				'rental_start_date': rental.start_date,
				'rental_end_date' : rental.end_date,
				'from_rent_order' :True,
			})
		return invoice


	def _create_picking(self):
		pick_obj = self.env['stock.picking']
		move_lines = []
		group_id = self.env['procurement.group'].search([('name','=',self.name)])
		for rental in self:
			# pick_type = self.env['stock.picking.type'].search([('name', '=', _('Delivery Orders')), ('warehouse_id', '=', rental.warehouse_id.id)]).id
			picking_type_id = self.env['stock.picking.type'].search([('code','=','outgoing'),
																			('warehouse_id.company_id','=', rental.company_id.id)], limit=1)

			for line in rental.rental_line:
				if line.product_id.type in ['asset'] :
					move_lines.append ((0, 0, {
						'name': rental.name,
						'company_id':  rental.company_id.id,
						'product_id': line.product_id.id,
						'product_uom': line.product_id.uom_id.id,
						'product_uom_qty': line.product_uom_qty,
						'group_id' : group_id.id,
						'partner_id': rental.partner_id.id or False,
						'location_id': picking_type_id.default_location_src_id.id,
						'location_dest_id': rental.partner_id.property_stock_customer.id,
						'origin': rental.name,
						'warehouse_id': rental.warehouse_id.id,
						'priority': '1',
					}))
			for line in rental.sale_line:
				if line.product_id.type in ['consu','product','asset'] :
					location_search_id = self.env['stock.location'].search([('usage','=', 'internal'),('company_id','=',rental.company_id.id )])
					move_lines.append ((0, 0, {
						'name': rental.name,
						'company_id':  rental.company_id.id,
						'product_id': line.product_id.id,
						'product_uom': line.product_id.uom_id.id,
						'product_uom_qty': line.product_uom_qty,
						'group_id' : group_id.id,
						'partner_id': rental.partner_id.id or False,
						'location_id': picking_type_id.default_location_src_id.id,
						'location_dest_id': rental.partner_id.property_stock_customer.id,
						'origin': rental.name,
						'warehouse_id': rental.warehouse_id.id,
						'priority': '1',
					}))
			picking = pick_obj.create({
				'partner_id': rental.partner_id.id,
				'origin': rental.name,
				'move_type' : 'direct',
				'company_id' : rental.company_id.id,
				'move_lines': move_lines,
				'picking_type_id': picking_type_id.id,
				'group_id':group_id.id,
				'location_id': picking_type_id.default_location_src_id.id,
				'location_dest_id': rental.partner_id.property_stock_customer.id,
				'rental_ref_id' : rental.id
			})
			picking.action_confirm()
			picking.action_assign()
			picking.update({
				'group_id':group_id.id
				})
		return picking

	def action_button_confirm_rental(self):
		for rental in self:
			if rental.rental_line:
				for rl in rental.rental_line:
					if rl.lot_id.rental_history:
						for rh in rl.lot_id.rental_history:
							if rh.state == 'confirm':
								continue
								# raise Warning('This product has already been rented. \n You can not rent already rented product. \n Change the start date and end date for the rent. \n Close the already created rental for this product')
							else:
								pass
					else:
						pass
			else:
				raise Warning('You can not confirm with out rental line')


			if rental.rental_line:
				for rl in rental.rental_line:
					self.env['rental.history'].create({
						'production_lot_id_custom': rl.lot_id.id,
						'start_date': rl.rental_id.start_date,
						'end_date': rl.rental_id.end_date,
						'rental_id': rl.rental_id.id,
						'state': 'confirm'
					})
		

			if rental.rental_bill_freq_type == 'days':
				rental.renew_date = datetime.datetime.today().date() + relativedelta(days=rental.rental_bill_freq)
			elif rental.rental_bill_freq_type == 'months':
				rental.renew_date = datetime.datetime.today().date() + relativedelta(months=rental.rental_bill_freq)
			elif rental.rental_bill_freq_type == 'weeks':
				rental.renew_date = datetime.datetime.today().date() + relativedelta(weeks=rental.rental_bill_freq)

			next_invoice_counter = int(rental.rental_initial / rental.rental_bill_freq) - 1

			rental.write({
				'next_invoice_counter' : next_invoice_counter,
				'confirmation_date' : datetime.datetime.now()
			})

			rental._create_serial_wrapper()
			invoice = rental._create_invoice_with_saleable(force=True)
			self.rental_line._action_launch_procurement_rule_custom()
			if rental.check_saleable:
				if any(line.product_id for line in rental.sale_line):
					
					pick = rental._create_picking()
					rental.update({'invoice_id' : invoice.id,
								'picking_ids' : [(4,pick.id)]})
			# else:
			# 	if any((line.product_id.type == 'asset') for line in rental.rental_line) or any((line.product_id.type == 'asset') for line in rental.sale_line):
			# 		pick = rental._create_picking()
			# 		rental.update({'picking_ids' : [(4,pick.id)]})
			# 	rental.update({'invoice_id' : invoice.id})
				
			rental.state = 'confirm'



	@api.depends('state')
	def _get_invoiced(self):
		"""
		Compute the invoice status of a SO. Possible statuses:
		- no: if the SO is not in status 'sale' or 'done', we consider that there is nothing to
		  invoice. This is also hte default value if the conditions of no other status is met.
		- to invoice: if any SO line is 'to invoice', the whole SO is 'to invoice'
		- invoiced: if all SO lines are invoiced, the SO is invoiced.
		- upselling: if all SO lines are invoiced or upselling, the status is upselling.

		The invoice_ids are obtained thanks to the invoice lines of the SO lines, and we also search
		for possible refunds created directly from existing invoices. This is necessary since such a
		refund is not directly linked to the SO.
		"""
		for rental in self:
			invoice = self.env['account.move'].search([('rental_id','=',rental.id)])
			rental.update({
				'invoice_count': len(set(invoice)),
				'invoice_ids': invoice.ids,
			})

	def action_view_invoice_rental(self):
		invoice_ids = self.mapped('invoice_ids')
		views = [(self.env.ref('account.view_invoice_tree').id, 'tree'), (self.env.ref('account.view_move_form').id, 'form')]
		
		
		result = {
			'name': 'Invoices',
			'type': 'ir.actions.act_window',
			'view_mode': 'tree,form',
			'view_type': 'form',
			'view_id': False,
			'views': views,
			'res_model': 'account.move',
		}
		if len(invoice_ids) > 1:
			result['domain'] = "[('id','in',%s)]" % invoice_ids.ids
		elif len(invoice_ids) == 1:
			result['views'] = [(self.env.ref('account.view_move_form').id, 'form')]
			result['res_id'] = invoice_ids.ids[0]
		else:
			result = {'type': 'ir.actions.act_window_close'}
		return result

	def action_view_delivery_rental(self):
		'''
		This function returns an action that display existing delivery orders
		of given sales order ids. It can either be a in a list or in a form
		view, if there is only one delivery order to show.
		'''
		
		result = {
			'name': 'Picking',
			'type': 'ir.actions.act_window',
			'binding_view_types': 'list,form',
			'view_mode': 'tree,form',
			'res_model': 'stock.picking',
		}
		pick_ids = sum([rental.picking_ids.ids for rental in self], [])

		if len(pick_ids) > 1:
			result['domain'] = "[('id','in',["+','.join(map(str, pick_ids))+"])]"
		elif len(pick_ids) == 1:
			form = self.env.ref('stock.view_picking_form', False)
			form_id = form.id if form else False
			result['views'] = [(form_id, 'form')]
			result['res_id'] = pick_ids[0]
		return result

	
	def action_button_close_rental(self):
		move_lines = []
		for inv in self.invoice_ids:
			inv.button_cancel()
		picking_rental_obj = self.env['stock.picking'].search([('origin','=',self.name)])
		picking_rental_return_obj = self.env['stock.return.picking']
		picking_return_line_obj = self.env['stock.return.picking.line']
		rol_active = self.env['rental.order.line'].search([('rental_id','=', self.id)])
		return_rent = False
		
		
		for clrp in picking_rental_obj: 
			for mvv in clrp.move_lines:
				for mvv_lns in mvv.move_line_ids:
					for x in rol_active :
						if mvv_lns.lot_id.id == x.lot_id.id :
							if  clrp.state =='done':
								return_rent = picking_rental_return_obj.create({'picking_id': clrp.id, 'location_id': clrp.location_id.id})
							else:
								raise UserError(_('You can only close rental while the replaced products are delivered!'))

		for rent in self:
			for rl in rent.rental_line:
				lot_id = rl.lot_id
				rh_ids = self.env['rental.history'].search([('production_lot_id_custom', '=', lot_id.id), ('rental_id', '=', rl.rental_id.id)])
				for rh in rh_ids:
					rh.state = 'close'

		for clrp1 in picking_rental_obj: 
			for mv in clrp1.move_lines:
				for mv_lns in mv.move_line_ids:
					for x1 in rol_active :
						if mv_lns.lot_id.id == x1.lot_id.id : 
							return_line = picking_return_line_obj.create({'product_id': mv.product_id.id, 'quantity':1, 'wizard_id': return_rent.id, 'move_id': mv.id})

		if return_rent:
			ret = return_rent.create_returns()
			ret_move_obj = self.env['stock.move'].search([('picking_id','=', ret['res_id'])])
		else:
			ret_move_obj = False
		for clrp2 in picking_rental_obj: 
			ori_move_obj = self.env['stock.move'].search([('picking_id','=', clrp2.id)])
			for mv in clrp2.move_lines:
				for mv_lns in mv.move_line_ids:
					for x1 in rol_active :
						if mv_lns.lot_id.id == x1.lot_id.id :
							for mv_l in ori_move_obj:
								if mv_lns.lot_id.id == x1.lot_id.id :
									for mv_line in mv_l.move_line_ids:
										if mv_lns.lot_id.id == x1.lot_id.id :
											for rt1 in ret_move_obj:
												if mv_lns.lot_id.product_id.id == x1.lot_id.product_id.id :
													for mvline in rt1.move_line_ids:    
														if mvline.product_id.id == mv_line.product_id.id:
															if mv_line.lot_id.id == x1.lot_id.id:
																mvline.update({'lot_id': mv_line.lot_id.id, 'qty_done':mv_line.qty_done})
												rt1.picking_id.button_validate()
		
		for rental in self:
			rental.update ({'close_date' :datetime.datetime.now(), 'state' : 'close' })    

	@api.onchange('partner_id')
	def onchange_partner_id(self):
		"""
		Update the following fields when the partner is changed:
		- Pricelist
		- Invoice address
		- Delivery address
		"""
		values = {}
		addr = self.partner_id.address_get(['delivery', 'invoice'])
		values = {
			'pricelist_id': self.partner_id.property_product_pricelist and self.partner_id.property_product_pricelist.id or False,
			'partner_invoice_id': addr['invoice'],
			'partner_shipping_id': addr['delivery'],
			'note': self.with_context(lang=self.partner_id.lang).env.user.company_id.sale_note,
		}
		if self.partner_id.user_id:
			values['user_id'] = self.partner_id.user_id.id
		self.update(values)

class SaleRentalOrderLine(models.Model):
	_name = "sale.rental.order.line"
	_description = 'Sale Rental Order Line'
	_order = 'rental_id desc, sequence, id'

	rental_id = fields.Many2one('rental.order', string='Rental Reference', required=True, ondelete='cascade', index=True, copy=False)
	name = fields.Text(string='Description')
	sequence = fields.Integer(string='Sequence', default=10)
	product_categ_id = fields.Many2one('product.category', related="product_id.categ_id" ,string='Product Category', required=True)
	product_id = fields.Many2one('product.product', string='Product', domain=[('sale_ok', '=', True)], required=True)
	product_uom_qty = fields.Float(string='Quantity', digits='Product Unit of Measure', default=1.0)
	price_unit = fields.Float('Price Unit',related="product_id.lst_price" ,required=True, digits='Product Price', default=0.0)
	lot_id = fields.Many2one('stock.production.lot', string='Serial Number', change_default=True)
	invoice_lines = fields.Many2many('account.move.line', string='Invoice Lines', copy=False)
	tax_id = fields.Many2many('account.tax', string='Taxes', domain=[('type_tax_use','!=','none'), '|', ('active', '=', False), ('active', '=', True)])
	price_subtotal = fields.Float(compute='_compute_amount', string='Subtotal', readonly=True, store=True)
	price_tax = fields.Float(compute='_compute_amount', string='Price Taxes', readonly=True, store=True)
	price_total = fields.Float(compute='_compute_amount', string='Total', readonly=True, store=True)

	@api.depends('price_unit', 'tax_id')
	def _compute_amount(self):
		"""
		Compute the amounts of the SO line.
		"""
		for line in self:
			taxes = line.tax_id.compute_all(line.price_unit)
			line.update({
				'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
				'price_total': taxes['total_included']* line.product_uom_qty,
				'price_subtotal': taxes['total_excluded']* line.product_uom_qty,
			})

class RantalOrderLine(models.Model):
	_name = 'rental.order.line'
	_description = 'Rental Order Line'
	_order = 'rental_id desc, sequence, id'

	rental_id = fields.Many2one('rental.order', string='Rental Reference', required=True, ondelete='cascade', index=True, copy=False)
	name = fields.Text(string='Description')
	sequence = fields.Integer(string='Sequence', default=10)
	product_categ_id = fields.Many2one('product.category',related="product_id.categ_id", string='Product Category', required=True)
	product_id = fields.Many2one('product.product', string='Product', domain=[('rent_ok', '=', True)], required=True)
	product_uom_qty = fields.Float(string='Quantity', digits='Product Unit of Measure', default=1.0)
	price_unit = fields.Float('Rent', required=True, digits='Product Price', default=0.0)
	lot_id = fields.Many2one('stock.production.lot', string='Serial Number', change_default=True)
	invoice_lines = fields.Many2many('account.move.line', string='Invoice Lines', copy=False)
	tax_id = fields.Many2many('account.tax', string='Taxes', domain=[('type_tax_use','!=','none'), '|', ('active', '=', False), ('active', '=', True)])
	price_subtotal = fields.Float(compute='_compute_amount', string='Subtotal', readonly=True, store=True)
	price_tax = fields.Float(compute='_compute_amount', string='Price Taxes', readonly=True, store=True)
	price_total = fields.Float(compute='_compute_amount', string='Total', readonly=True, store=True)

	@api.depends('price_unit', 'tax_id')
	def _compute_amount(self):
		"""
		Compute the amounts of the SO line.
		"""
		for line in self:
			taxes = line.tax_id.compute_all(line.price_unit)
			line.update({
				'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
				'price_total': taxes['total_included'],
				'price_subtotal': taxes['total_excluded'],
			})

	def _action_launch_procurement_rule_custom(self):
		"""
		Launch procurement group run method with required/custom fields genrated by a
		sale order line. procurement group will launch '_run_move', '_run_buy' or '_run_manufacture'
		depending on the sale order line product rule.
		"""
		precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
		errors = []
		products=[]
		for line in self:
			if not line.product_id.type in ('consu','product','asset'):
				continue
			qty = 0.0
			group_id = line.rental_id.procurement_group
			if not group_id:
				group_id = self.env['procurement.group'].create({
					'name': line.rental_id.name, 
					'move_type': 'direct',
					'rental_id': line.rental_id.id,
					'partner_id': line.rental_id.partner_id.id,
				})
				line.rental_id.procurement_group = group_id
				
			else:
				updated_vals = {}
				if group_id.partner_id != line.rental_id.partner_id:
					updated_vals.update({'partner_id': line.rental_id.partne_id.id})
				if group_id.move_type != 'direct':
					updated_vals.update({'move_type': 'direct'})
				if updated_vals:
					group_id.write(updated_vals)
				

			values = line._prepare_procurement_values_custom(group_id=group_id)
			product_qty = line.product_uom_qty - qty
			try:
				self.env['procurement.group'].run([self.env['procurement.group'].Procurement(
						line.product_id, 
						product_qty, 
						line.product_id.uom_id, 
						line.rental_id.partner_id.property_stock_customer, 
						line.product_id.name, 
						line.rental_id.name, 
						line.rental_id.company_id,
						values)])
			except UserError as error:
				errors.append(error.name)
			if errors:
				raise UserError('\n'.join(errors))
			orders = list(set(x.rental_id for x in self))
			for order in orders:
				
				reassign = order.picking_ids.filtered(
					lambda x: x.state == 'confirmed' or (x.state in ['waiting', 'assigned'] and not x.printed))
				
				if reassign:
					
					reassign.update({
						'for_rental_move' : True
						})
					reassign.action_assign()
					for lines in reassign.move_line_ids:
						
						if lines.product_id == line.product_id:
							
							move=lines.write({'lot_id':line.lot_id.id})

		return True


	@api.model
	def create(self, values):

		if any(f not in values for f in ['product_categ_id', 'product_id', 'price_unit']):
			lot = self.env['stock.production.lot'].browse(values.get('lot_id'))
			values['product_categ_id'] = values.setdefault('product_categ_id', lot.product_id.categ_id.id)
			values['product_id'] = values.setdefault('product_id', lot.product_id.id)
			values['price_unit'] = values.setdefault('price_unit', lot.product_id.rent_per_month)

		line = super(RantalOrderLine, self).create(values)
		return line

	@api.onchange('lot_id')
	def lot_id_change(self):
		vals = {}

		if not self.lot_id:
			return self.update(vals)

		product = self.lot_id.product_id
		name = product.name_get()[0][1]
		if product.description_rental:
			name += '\n' + product.description_rental
		vals['name'] = name

		vals.update({ 'product_id' : product or False,
					  'product_categ_id' : product.categ_id or False,
					  'price_unit' : product.rent_per_month or 0.0,
					  })
		if self.rental_id.rental_initial_type == 'weeks':
			vals.update({'price_unit': (product.rent_per_week * self.rental_id.rental_initial) or 0.0})
		if self.rental_id.rental_initial_type == 'days':
			vals.update({'price_unit': (product.rent_per_day * self.rental_id.rental_initial) or 0.0})
		if self.rental_id.rental_initial_type == 'hours':
			vals.update({'price_unit': (product.rent_per_hour * self.rental_id.rental_initial) or 0.0})
		if self.rental_id.rental_initial_type == 'months':
			vals.update({'price_unit': (product.rent_per_month * self.rental_id.rental_initial) or 0.0})
		return self.update(vals)

	def _prepare_procurement_values_custom(self, group_id=False):
		""" Prepare specific key for moves or other components that will be created from a procurement rule
		comming from a sale order line. This method could be override in order to add other custom key that could
		be used in move/po creation.
		"""
		values = {}
		self.ensure_one()
		date_planned = self.rental_id.date_order
		values.update({
			'group_id': group_id,
			'rental_line_id': self.id,
			'date_planned': date_planned.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
			'warehouse_id': self.rental_id.warehouse_id or False,
		})

		return values

class ProcurementRule(models.Model):
	_inherit = 'stock.rule'

	def _get_stock_move_values(self, product_id, product_qty, product_uom, location_id, name, origin, values, group_id):
		res = super(ProcurementRule, self)._get_stock_move_values(product_id, product_qty, product_uom, location_id, name, origin, values, group_id)
		if res.get('rental_line_id', False):
			res['rental_line_id'] = values['rental_line_id']
			res['for_rental_move'] = True
		return res


class StockMove(models.Model):
	_inherit = "stock.move"

	rental_line_id = fields.Many2one('rental.order.line', 'Rental Line')
	for_rental_move = fields.Boolean("stock move for rental")

	def rental_moves(self):
		return self.filtered(lambda m: m.rental_line_id)

	# def _action_assign(self):
	# 	""" Reserve stock moves by creating their stock move lines. A stock move is
	# 	considered reserved once the sum of `product_qty` for all its move lines is
	# 	equal to its `product_qty`. If it is less, the stock move is considered
	# 	partially available.
	# 	"""
	# 	assigned_moves = self.env['stock.move']
	# 	partially_available_moves = self.env['stock.move']
	# 	for move in self.filtered(lambda m: m.state in ['confirmed', 'waiting', 'partially_available']):
	# 		if move.location_id.usage in ('supplier', 'inventory', 'production', 'customer')\
	# 				or move.product_id.type == 'consu':
	# 			if move.product_id.tracking == 'serial' and (move.picking_type_id.use_create_lots or move.picking_type_id.use_existing_lots):
	# 				for i in range(0, int(move.product_qty - move.reserved_availability)):
	# 					self.env['stock.move.line'].create(move._prepare_move_line_vals(quantity=1))
	# 			else:
	# 				to_update = move.move_line_ids.filtered(lambda ml: ml.product_uom_id == move.product_uom and
	# 														ml.location_id == move.location_id and
	# 														ml.location_dest_id == move.location_dest_id and
	# 														ml.picking_id == move.picking_id and
	# 														not ml.lot_id and
	# 														not ml.package_id and
	# 														not ml.owner_id)
	# 				if to_update:
	# 					to_update[0].product_uom_qty += move.product_qty - move.reserved_availability
	# 				else:
	# 					abc = self.env['stock.move.line'].create(move._prepare_move_line_vals(quantity=move.product_qty - move.reserved_availability))
	# 			assigned_moves |= move
	# 		else:
	# 			if not move.move_orig_ids:
	# 				if move.procure_method == 'make_to_order':
	# 					continue
	# 				available_quantity = self.env['stock.quant']._get_available_quantity(move.product_id, move.location_id)
	# 				if available_quantity <= 0:
	# 					continue
	# 				need = move.product_qty - move.reserved_availability
	# 				if move.rental_line_id:
	# 					lot_id = move.rental_line_id.lot_id
	# 					taken_quantity = move._update_reserved_quantity(need, available_quantity, move.location_id,lot_id,
	# 																	strict=False)
	# 				else:
	# 					taken_quantity = move._update_reserved_quantity(need, available_quantity, move.location_id, strict=False)
	# 				if need == taken_quantity:
	# 					assigned_moves |= move
	# 				else:
	# 					partially_available_moves |= move
	# 			else:
	# 				move_lines_in = move.move_orig_ids.filtered(lambda m: m.state == 'done').mapped('move_line_ids')
	# 				keys_in_groupby = ['location_dest_id', 'lot_id', 'result_package_id', 'owner_id']

	# 				def _keys_in_sorted(ml):
	# 					return (ml.location_dest_id.id, ml.lot_id.id, ml.result_package_id.id, ml.owner_id.id)

	# 				grouped_move_lines_in = {}
	# 				for k, g in groupby(sorted(move_lines_in, key=_keys_in_sorted), key=itemgetter(*keys_in_groupby)):
	# 					qty_done = 0
	# 					for ml in g:
	# 						qty_done += ml.product_uom_id._compute_quantity(ml.qty_done, ml.product_id.uom_id)
	# 					grouped_move_lines_in[k] = qty_done
	# 				move_lines_out_done = (move.move_orig_ids.mapped('move_dest_ids') - move)\
	# 					.filtered(lambda m: m.state in ['done'])\
	# 					.mapped('move_line_ids')
	# 				moves_out_siblings = move.move_orig_ids.mapped('move_dest_ids') - move
	# 				moves_out_siblings_to_consider = moves_out_siblings & (assigned_moves + partially_available_moves)
	# 				reserved_moves_out_siblings = moves_out_siblings.filtered(lambda m: m.state in ['partially_available', 'assigned'])
	# 				move_lines_out_reserved = (reserved_moves_out_siblings | moves_out_siblings_to_consider).mapped('move_line_ids')
	# 				keys_out_groupby = ['location_id', 'lot_id', 'package_id', 'owner_id']

	# 				def _keys_out_sorted(ml):
	# 					return (ml.location_id.id, ml.lot_id.id, ml.package_id.id, ml.owner_id.id)

	# 				grouped_move_lines_out = {}
	# 				for k, g in groupby(sorted(move_lines_out_done, key=_keys_out_sorted), key=itemgetter(*keys_out_groupby)):
	# 					qty_done = 0
	# 					for ml in g:
	# 						qty_done += ml.product_uom_id._compute_quantity(ml.qty_done, ml.product_id.uom_id)
	# 					grouped_move_lines_out[k] = qty_done
	# 				for k, g in groupby(sorted(move_lines_out_reserved, key=_keys_out_sorted), key=itemgetter(*keys_out_groupby)):
	# 					grouped_move_lines_out[k] = sum(self.env['stock.move.line'].concat(*list(g)).mapped('product_qty'))
	# 				available_move_lines = {key: grouped_move_lines_in[key] - grouped_move_lines_out.get(key, 0) for key in grouped_move_lines_in.keys()}
	# 				available_move_lines = dict((k, v) for k, v in available_move_lines.items() if v)

	# 				if not available_move_lines:
	# 					continue
	# 				for move_line in move.move_line_ids.filtered(lambda m: m.product_qty):
	# 					if available_move_lines.get((move_line.location_id, move_line.lot_id, move_line.result_package_id, move_line.owner_id)):
	# 						available_move_lines[(move_line.location_id, move_line.lot_id, move_line.result_package_id, move_line.owner_id)] -= move_line.product_qty
	# 				for (location_id, lot_id, package_id, owner_id), quantity in available_move_lines.items():
	# 					need = move.product_qty - sum(move.move_line_ids.mapped('product_qty'))
	# 					taken_quantity = move._update_reserved_quantity(need, quantity, location_id, lot_id, package_id, owner_id)
	# 					if need - taken_quantity == 0.0:
	# 						assigned_moves |= move
	# 						break
	# 					partially_available_moves |= move
	# 	partially_available_moves.write({'state': 'partially_available'})
	# 	assigned_moves.write({'state': 'assigned'})
	# 	self.mapped('picking_id')._check_entire_pack()

class AssetSerialWrapper(models.Model):
	_name = 'asset.serial.wrapper'
	_description = 'Asset Serial Wrapper'

	rental_id = fields.Many2one('rental.order', string='Rental Reference',)
	product_id = fields.Many2one('product.product', string='Product', domain=[('rent_ok', '=', True)], required=True)
	lot_id = fields.Many2one('stock.production.lot', string='Serial Number', change_default=True)

class stock_picking(models.Model):
	_inherit = 'stock.picking'

	rental_ref_id = fields.Many2one('rental.order', string='Rental Order Ref', readonly=True, copy=False)
	for_rental_move = fields.Boolean("stock move for rental")    

	def rental_pickings(self):
		return self.filtered(lambda m: m.rental_ref_id)
