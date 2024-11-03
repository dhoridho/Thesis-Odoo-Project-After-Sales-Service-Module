from odoo import models, fields, api, _
from odoo.exceptions import Warning
from odoo.exceptions import ValidationError
import json


class ProductCategory(models.Model):
	_inherit = 'product.category'
	
	product_limit = fields.Selection([('no_limit',"Don't Limit"),('limit_per','Limit by Precentage %'),('limit_amount','Limit by Amount'),('str_rule','Strictly Limit by Purchase Order')],
		string='Receiving Limit', default='no_limit')
	min_val = fields.Integer('Minimum Value')
	max_val = fields.Integer('Maximum Value')
	
	@api.onchange('min_val', 'max_val', 'product_limit')
	def _onchange_value(self):
		if self.product_limit == 'limit_per':
			if not 0 <= self.min_val <= 100 or not 0 <= self.max_val <= 100:
				raise ValidationError(_("The input value must range from 0 to 100."))

	@api.model
	def change_default_down_payment_product(self):
		product = self.env.ref('equip3_purchase_masterdata.down_payment_product_data', raise_if_not_found=False)
		if not product:
			return

		product.product_tmpl_id.sudo().write({
			'categ_id': self.env.ref('equip3_purchase_masterdata.down_payment_categ_data').id,
			'purchase_ok': False,
			'sale_ok': False
		})
		company_sudo = self.env['res.company'].sudo()
		company_ids = company_sudo.search([])
		for company in company_ids:
			company.write({'down_payment_product_id': product.id})
			
		ICP = self.env['ir.config_parameter'].sudo()
		ICP.set_param('down_payment_product_id', product.id)

		try:
			params = json.loads(ICP.get_param('temporary_params'))
		except TypeError:
			return
			
		for model in ['purchase.order.line', 'account.move.line', 'stock.move', 'stock.valuation.layer']:

			model_sudo = self.env[model].sudo()
			record_ids = model_sudo.browse(params.get(model, []))

			for record in  record_ids:
				if not record.exists():
					continue
				record.write({'product_id': product.id})
