from odoo import models, fields, api, _


class PurchaseRequest(models.Model):
	_inherit = 'purchase.request'

	kitchen_id = fields.Many2one('kitchen.production.record', 'Kitchen Production', copy=False)
	is_readonly_origin = fields.Boolean()

	@api.onchange('branch_id', 'company_id')
	def set_warehouse(self):
		if self.env.context.get('default_destination_warehouse'):
			return
		return super(PurchaseRequest, self).set_warehouse()

	@api.onchange('is_single_delivery_destination')
	def onchange_destination_warehouse(self):
		if self.env.context.get('default_destination_warehouse'):
			return
		return super(PurchaseRequest, self).onchange_destination_warehouse()
