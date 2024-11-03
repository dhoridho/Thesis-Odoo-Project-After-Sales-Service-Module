from odoo import models, fields, api


class KitchenProduction(models.Model):
	_name = 'kitchen.production'
	_description = 'Kitchen Production'

	company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company)
	product_id = fields.Many2one('product.product', check_company=True, required=True, readonly=True, copy=False)
	default_code = fields.Char(related='product_id.default_code')
	qty_available = fields.Float(related='product_id.qty_available')
	incoming_qty = fields.Float(related='product_id.incoming_qty')
	outgoing_qty = fields.Float(related='product_id.outgoing_qty')
	uom_id = fields.Many2one('uom.uom', related='product_id.uom_id')
	to_produce = fields.Float(string='To Produce', default=1.0)

	def action_produce(self):
		context = self.env.context.copy()
		context.update({
			'default_branch_id': self.env.user.branch_id.id,
			'default_create_uid': self.env.user.id,
			'default_create_date': fields.Datetime.now()
		})
		action = {
			'name': 'Kitchen Production Records',
			'type': 'ir.actions.act_window',
			'res_model': 'kitchen.production.record',
			'view_mode': 'form',
			'target': 'new',
			'context': context
		}
		return action
	