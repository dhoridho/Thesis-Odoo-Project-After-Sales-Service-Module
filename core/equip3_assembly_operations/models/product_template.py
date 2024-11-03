from odoo import models, fields, api


class ProductTemplate(models.Model):
	_inherit = 'product.template'

	@api.depends_context('show_assembly_tab')
	def _compute_is_from_assembly(self):
		self.is_from_assembly = self.env.context.get('show_assembly_tab', False)

	@api.model
	def _default_is_from_assembly(self):
		return self.env.context.get('show_assembly_tab', False)

	produceable_in_assembly = fields.Boolean(string='Can be Assembly/Disassembly')
	is_from_assembly = fields.Boolean(compute=_compute_is_from_assembly, default=_default_is_from_assembly)
