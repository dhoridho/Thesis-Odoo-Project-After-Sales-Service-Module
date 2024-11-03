from odoo import models, fields, api


class ProductTemplate(models.Model):
	_inherit = 'product.template'

	@api.depends_context('show_kitchen_tab')
	def _compute_is_from_kitchen(self):
		self.is_from_kitchen = self.env.context.get('show_kitchen_tab', False)

	@api.model
	def _default_is_from_kitchen(self):
		return self.env.context.get('show_kitchen_tab', False)

	produceable_in_kitchen = fields.Boolean(string='Producible in Kitchen')
	is_from_kitchen = fields.Boolean(compute=_compute_is_from_kitchen, default=_default_is_from_kitchen)
