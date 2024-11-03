# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class PropertyMaintanance(models.Model):
	_name = 'property.maintanance'
	_description = "Property Maintenance"

	@api.depends('invoice_id')
	def _compute_invoice_count(self):
		self.invoice_count = self.env['account.move'].search_count([('id','=',self.invoice_id.id)])

	name = fields.Char()
	state = fields.Selection([('new','New'),('invoice','Invoiced'),('cancel','Cancelled')], default='new')
	property_id = fields.Many2one('product.product', required=True, domain=[('is_property','=',True),('property_book_for','=','rent')])
	date = fields.Date("Date",default=fields.Date.today())
	maintain_cost = fields.Float("Maintenance Cost", required=True,)
	operation = fields.Selection([('service','Service'),('repair','Repair')],required=True)
	invoice_id =  fields.Many2one('account.move', "Invoice Status", readonly=True)
	responsible_id = fields.Many2one('res.partner', required=True)
	description = fields.Text()
	invoice_count = fields.Integer("#Invoice", compute='_compute_invoice_count')


	def unlink(self):
		for line in self:
			if line.state != 'new':
				raise UserError(_('You cannot delete Maintenance Records (name: %s)') % (line.name,))
		return super(PropertyMaintanance, self).unlink()

	def button_cancel(self):
		for record in self:
			record.invoice_id.action_cancel()
			record.write({'invoice_id': False, 'state': 'cancel'})

	def action_draft(self):
		for record in self:
			record.state = 'new'

	def action_view_invoice(self):
		invoices = self.env['account.move'].search([('id','=',self.invoice_id.id)])
		action = self.env.ref('account.action_move_out_invoice_type').read()[0]
		if len(invoices) > 1:
			action['domain'] = [('id', 'in', invoices.ids)]
		elif len(invoices) == 1:
			action['views'] = [(self.env.ref('account.view_move_form').id, 'form')]
			action['res_id'] = invoices.ids[0]
		else:
			action = {'type': 'ir.actions.act_window_close'}
		return action

	@api.onchange('property_id')
	def get_maintain_cost(self):
		if self.property_id:
			self.maintain_cost = self.property_id.maintain_charge
			self.responsible_id = self.property_id.user_id.partner_id

	def create_maintanance_invoice(self):
		product_id = self.property_id
		# Search for the income account
		if product_id.property_account_income_id:
			income_account = product_id.property_account_income_id.id
		elif product_id.categ_id.property_account_income_categ_id:
			income_account = product_id.categ_id.property_account_income_categ_id.id
		else:
			raise UserError(_('Please define income '
							  'account for this product: "%s" (id:%d).')
							% (product_id.name, product_id.id))

		vals  = {
			'property_id':self.property_id.id,
			'move_type': 'out_invoice',
			'invoice_origin':self.name,
			'partner_id': self.responsible_id.id,
			'invoice_date_due':self.date,
			'invoice_date':self.date,
			'invoice_user_id':self.property_id.salesperson_id.id,
			'invoice_line_ids': [(0,0,{
				'name':self.name,
				'product_id':self.property_id.id,
				'account_id': income_account,
				'price_unit': self.maintain_cost})],
			}
		invoice_id = self.env["account.move"].create(vals)
		if invoice_id:
			self.invoice_id = invoice_id
			self.state = "invoice"