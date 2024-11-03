# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

class RentalHistory(models.Model):
	_name = "rental.history"
	_description = "Rental History"

	production_lot_id_custom = fields.Many2one('stock.production.lot', string="Production Lot Reference")
	start_date = fields.Date(string="Start Date", required=False, )
	end_date = fields.Date(string="End Date", required=False, )
	rental_id = fields.Many2one('rental.order', string="Rental Order")
	invoice_amount = fields.Float('Invoice Amount')
	state = fields.Selection([
		('draft', 'Quotation'),
		('confirm', 'Confirm Rental'),
		('close', 'Close Rental'),
	], string='Status')


class product_product(models.Model):
	_inherit = "product.product"

	rent_ok = fields.Boolean('Can be Rented', help="Specify if the product can be selected in a rent orders.")
	rent_per_month = fields.Float('Monthly Rental', help="Rental per month.")
	rent_per_week = fields.Float('Weekly Rental', help="Rental per week.")
	rent_per_day = fields.Float('Daily Rental', help="Rental per day.")
	rent_per_hour = fields.Float('Hourly Rental', help="Hourly Rent.")
	replacement_value = fields.Float('Replacement Value', readonly="1", help="Replacement Value")
	weekly_replacement_value = fields.Float('Weekly Replacement Value', readonly="1", help="Week Replacement Value")
	daily_replacement_value = fields.Float('Daily Replacement Value', readonly="1", help="Day Replacement Value")
	description_rental = fields.Text(string="Rental Description", required=False, )
	

class stock_production_lot(models.Model):
	_inherit = "stock.production.lot"

	def rh_calc_invoice_amount(self):
		for rhinv in self.rental_history:
			in_amt = 0
			for rl in rhinv.rental_id.invoice_ids:
				in_amt += rl.amount_total
			rhinv.invoice_amount = in_amt

	def _compute_total_invoice_amount(self):
		self.rh_calc_invoice_amount()
		for spl in self:
			sum = 0
			for rl in spl.rental_history:
				sum += rl.invoice_amount
			spl.total_invoice_amount = sum
	rental_history = fields.One2many(comodel_name="rental.history", inverse_name="production_lot_id_custom", string="Rental History", required=False, )
	total_invoice_amount = fields.Float('Total Invoice Amount',compute="_compute_total_invoice_amount")

class ResPartner(models.Model):
	_inherit = "res.partner"

	rental_count  =  fields.Integer('Rentals', compute='_get_rental_count')

	def _get_rental_count(self):
		for res in self:
			rental_ids = self.env['rental.order'].search([('partner_id','=',res.id)])
			res.rental_count = len(rental_ids)
		
	def rental_on_rental_order_button(self):
		self.ensure_one()
		return {
			'name': 'Rental Order',
			'type': 'ir.actions.act_window',
			'view_mode': 'tree,form',
			'res_model': 'rental.order',
			'domain': [('partner_id', '=', self.id)],
		}

