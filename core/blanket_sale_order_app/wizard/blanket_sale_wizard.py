from odoo import models, fields, api, _
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
import xlsxwriter
import xlrd
import xlwt
import base64
from io import BytesIO
from odoo.exceptions import UserError, ValidationError


class BlanketWizard(models.TransientModel):
	
	_name='blanketwiz.blanketwiz'
	_description = 'Sale Blanket Wizard'

	wiz_line_ids = fields.One2many('orderwizline.orderwizline','reverse_id')

	@api.model
	def default_get(self, fields):
		res=super(BlanketWizard, self).default_get(fields)
		active_ids=self._context.get('active_ids')
		invoice_order_ids=self.env['saleblanket.saleblanket'].browse(active_ids)
		split_order_lines=[]
		for order in invoice_order_ids:
			for line in order.order_line_ids:
				split_order_lines.append((0,0, {
							'partner_id': order.partner_id.id,
							'product_id':line.product_id.id,
							'remaining_quantity':line.remaining_quantity,
							'new_quatation_quantity':0.00,
							'blanket_order_line_id':line.id,
							'unit_of_measure_id':line.product_uom.id,
							'unit_price':line.price_unit,
							'taxes_id':[(6,0,line.tax_id.ids)],
							'subtotal':line.price_subtotal,
							
					}))
		res.update({
			'wiz_line_ids': split_order_lines
		})
		
		return res

	def create_quatation(self):
		line_order_id = self.env['saleblanket.saleblanket'].browse(self.env.context.get('active_ids'))
		env_id = self.env['orderwizline.orderwizline'].browse(self.env.context.get('active_ids'))

		for rec in self.wiz_line_ids:
			if rec.new_quatation_quantity > rec.remaining_quantity:
				raise ValidationError("Quatation quantity is more then remaining quantity. ")

			sale_order_id=self.env['sale.order'].create({
											'partner_id':rec.partner_id.id,
											'validity_date' : line_order_id.expiry_date,
											'payment_term_id': line_order_id.payment_term_id.id,
											'pricelist_id': line_order_id.pricelist_id.id,
											'origin': line_order_id.name
											})

			sale_order_id.order_line.create({'product_id': rec.product_id.id,
											'product_uom_qty':rec.new_quatation_quantity,
											'product_uom':rec.unit_of_measure_id.id,
											'price_unit':rec.unit_price,
											'tax_id':[(6,0,rec.taxes_id.ids)],
											'price_subtotal':rec.subtotal,
											'order_id':sale_order_id.id
											})
			store=rec.blanket_order_line_id.remaining_quantity - rec.new_quatation_quantity
			rec.blanket_order_line_id.write({'remaining_quantity':store,'quantity':store})

class OrderWizline(models.TransientModel):
	_name="orderwizline.orderwizline"
	_description = 'Sale Blanket Wizard Order line'

	reverse_id = fields.Many2one('blanketwiz.blanketwiz')
	product_id = fields.Many2one('product.product', string="Product", required=True)
	partner_id = fields.Many2one('res.partner', string='Customer')
	remaining_quantity = fields.Float(string="Remaining Quantity")
	new_quatation_quantity = fields.Float(string="New Quatation Quantity")
	unit_of_measure_id=fields.Many2one('uom.uom',string="Unit of Measure")
	unit_price=fields.Float(string="Unit Price")
	taxes_id=fields.Many2many('account.tax',string="Taxes")
	subtotal=fields.Float(string="Subtotal")
	blanket_order_line_id=fields.Many2one('orderline.orderline',string="Analytic Account")