# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class ProductProduct(models.Model):
	_inherit = "product.product"

	def set_product_last_purchase(self, order_id=False):
		pass

	@api.model
	def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
		domain = domain or []
		context = dict(self.env.context) or {}
		domain.extend(['|',('branch_id', '=', False), ('branch_id', 'in', self.env.branches.ids)])
		return super().read_group(domain, fields, groupby, offset=offset, limit=limit,orderby=orderby, lazy=lazy)

	@api.model
	def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
		domain = domain or []
		domain.extend(['|',('branch_id', '=', False), ('branch_id', 'in', self.env.branches.ids)])
		return super().search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)


class ProductTemplateIn(models.Model):
	_inherit = 'product.template'
	
	
	@api.onchange('min_val', 'max_val', 'product_limit')
	def _onchange_value(self):
		if self.product_limit == 'limit_per':
			if not 0 <= self.min_val <= 100 or not 0 <= self.max_val <= 100:
				raise ValidationError(_("The input value must range from 0 to 100."))