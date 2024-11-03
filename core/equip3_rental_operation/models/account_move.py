
from odoo import api , fields , models
from datetime import datetime, date


class AccountMove(models.Model):
	_inherit = "account.move"

	rental_order_id = fields.Many2one('rental.order', string="Rental Order")
	is_deposit_invoice = fields.Boolean(string="Is Deposit Invoice")
	is_deposit_return_invoice = fields.Boolean(string="Is Deposit Return Invoice")
	is_invoice_from_rental =  fields.Boolean(default=False,string="Invoice from Rental Order")

	@api.model
	def create(self, vals):
		if 'rental_id' in vals:
			rental_id = self.env['rental.order'].browse(vals['rental_id'])
			vals['currency_id'] = rental_id.currency_id.id
			if rental_id.is_reccuring_invoice:
				if date.today() < rental_id.start_date.date():
					vals['invoice_date'] = rental_id.start_date
					vals['invoice_date_due'] = rental_id.start_date
		return super(AccountMove, self).create(vals)