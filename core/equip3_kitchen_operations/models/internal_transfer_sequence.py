from odoo import models, fields,api

class InternalTransfer(models.Model):
	_inherit = "internal.transfer"

	is_outlet_order = fields.Boolean(string='IS Outlet Order', default=False)

	@api.model
	def create(self, vals):
		if vals.get('is_outlet_order'):
			seq = self.env['ir.sequence'].next_by_code('outlet.order.transfer')
			vals['name'] = seq
			return super(InternalTransfer, self).create(vals)
		else:
			seq = self.env['ir.sequence'].next_by_code('internal.transfer')
			vals['name'] = seq
			return super(InternalTransfer, self).create(vals)