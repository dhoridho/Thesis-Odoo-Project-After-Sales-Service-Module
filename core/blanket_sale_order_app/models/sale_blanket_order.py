from odoo import models, fields, api, _
from datetime import datetime,date
from odoo.exceptions import UserError, ValidationError

class saleBlanket(models.Model):

	_name = 'saleblanket.saleblanket'
	_description = 'Sale Blanket'

	name = fields.Char(string='Quotation Number', required=True, copy=False, readonly=True, index=True, default=lambda self: _('New'))
	partner_id = fields.Many2one('res.partner', string='Customer')
	invoice_address = fields.Many2one('res.partner', string="Invoice Address")
	delivery_address = fields.Many2one('res.partner', string="Delivery Address")
	pricelist_id = fields.Many2one('product.pricelist', string='Pricelist')
	payment_term_id = fields.Many2one('account.payment.term', string='Payment Terms')
	expiry_date = fields.Date(string="Expiry Date")
	order_line_ids = fields.One2many('orderline.orderline','reverse_id')
	state = fields.Selection([
			('new','New'),
			('open', 'Open'),
			('expired', 'Expired'),
		], string='Status', readonly=True, default='new')
	creation_date = fields.Datetime(string='Creation Date', default=datetime.today())
	current_user = fields.Many2one('res.users','Sales Person', default=lambda self: self.env.user)
	current_company=fields.Many2one('res.company',string="Company", default=lambda self: self.env.user.company_id)

	sale_order_count = fields.Integer(compute='_sale_order_count', string='Attachments')

	def _sale_order_count(self):
		order_obj = self.env['sale.order']
		for lead in self:
			lead.sale_order_count = order_obj.search_count([('origin', 'ilike', lead.name)])

	@api.model
	def create(self, vals):
		if vals.get('name', _('New')) == _('New'):
			vals['name'] = self.env['ir.sequence'].next_by_code('saleblanket.sequence') or _('New')
		result = super(saleBlanket, self).create(vals)
		return result

	def open_button(self):
		return self.write({'state':'open'})

	def open_sale_order(self):
		return {
			'name': _('Sale orders'),
			'view_type': 'form',
			'view_mode': 'tree,form',
			'res_model': 'sale.order',
			'view_id': False,
			'type': 'ir.actions.act_window',
		}

	@api.onchange('partner_id')
	def onchange_partner_id(self):
		self.update({
			'invoice_address': self.partner_id,
			'delivery_address': self.partner_id,
			'pricelist_id':self.partner_id.property_product_pricelist,
			'payment_term_id':self.partner_id.property_payment_term_id,
			})
		return

	def action_view_sale_order(self):
		xml_id = 'sale.view_order_tree'
		tree_view_id = self.env.ref(xml_id).id
		xml_id = 'sale.view_order_form'
		form_view_id = self.env.ref(xml_id).id
		xml_id = 'sale.view_sale_order_kanban'
		kanban_view_id = self.env.ref(xml_id).id
		return {
			'name': _('Sale Orders'),
			'view_type': 'form',
			'view_mode': 'tree',
			'views': [(tree_view_id, 'tree'),(kanban_view_id, 'kanban'), 
					  (form_view_id, 'form')],
			'res_model': 'sale.order',
			'domain': [('origin', 'ilike', self.name)],
			'type': 'ir.actions.act_window',
		}

	def button_cancel(self):
		order_obj = self.env['sale.order']
		for order in self:
			sale_ids = order_obj.search([('origin','ilike',order.name)])
			sale_ids.unlink()
		return self.write({'state':'expired'})

	def to_draft(self):
		return self.write({'state':'new'})

	def unlink(self):
		for order in self:
			if order.state not in ('new', 'cancel'):
				raise UserError(_(
					'You can not delete an open blanket order! '
					'Try to cancel it before.'))
		return super().unlink()

class Orderline(models.Model):
	_name="orderline.orderline"
	_description = 'Sale Blanket Order line'

	reverse_id = fields.Many2one('saleblanket.saleblanket')
	product_id = fields.Many2one('product.product', string="Product", required=True)
	name = fields.Text(string='Description')
	quantity =   fields.Float(string="Quantity")
	remaining_quantity = fields.Float(string="Remaining Quantity")
	product_uom = fields.Many2one('uom.uom', string='Unit of Measure')
	price_unit = fields.Float('Unit Price')
	tax_id = fields.Many2many('account.tax', string='Taxes')
	price_subtotal = fields.Float(string="Subtotal",compute='_get_subtotal')


	@api.onchange('quantity','price_unit')
	def _get_subtotal(self):
		for rec in self:
			rec.price_subtotal=rec.quantity*rec.price_unit

	@api.onchange('product_id')
	def onchangee_partner_id(self):
		self.update({
				'name': self.product_id.name,
				'quantity':1,
				'price_unit':self.product_id.list_price,
				'product_uom':self.product_id.uom_id,
			})
		return

	@api.onchange('quantity')
	def onchangee_quantity(self):
		self.update({
				'remaining_quantity': self.quantity,
			})
		return