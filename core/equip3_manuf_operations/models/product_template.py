from odoo import models, fields

class ProductTemplate(models.Model):
	_inherit = 'product.template'

	manuf_type = fields.Selection(
		selection=[
			('type_fg', 'Finished Goods'),
			('type_wip', 'Work in Progress'),
			('type_material', 'Materials')
		],
		string='Manuf Product Type'
	)
