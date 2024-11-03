# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError

class MaintenanceSaleWizardCustom(models.TransientModel):
	_name = "maintenance.saleorder.wizard.custom"
	
	def create_mainteance_saleorder(self):
		maintenance_id = self._context.get('active_id')
		maint_request_id = self.env['maintenance.request'].browse(maintenance_id)
		
		if all(rec.is_so_line_created for rec in maint_request_id.maintenance_requestcustom_line_ids):
			raise UserError(_('No quotation product lines is found to create quotation.'))

		if not maint_request_id.maintenance_requestcustom_line_ids:
			raise UserError(_('Please add quotation product lines to create quotation.'))

		if not maint_request_id.partner_custom_id:
			raise UserError(_('Please select customer on maintenance request to create sales quotation.'))

		vals = {
			'maint_request_custom_id': maint_request_id.id,
			'partner_id': maint_request_id.partner_custom_id.id,
			'user_id': maint_request_id.user_id.id,
			'pricelist_id': maint_request_id.partner_custom_id.property_product_pricelist and maint_request_id.partner_custom_id.property_product_pricelist.id or False,
	    	}
		
		order_id = self.env['sale.order'].sudo().create(vals)
		
		for line in maint_request_id.maintenance_requestcustom_line_ids:

			if not line.product_id:
				raise UserError(_('Please define product on quotation product lines.'))
			
			price_unit = line.price
			if order_id.pricelist_id:
				price_unit, rule_id = order_id.pricelist_id.get_product_price_rule(
	                line.product_id,
	                line.qty or 1.0,
	                order_id.partner_id
	            )

			orderlinevals = {
				'order_id' : order_id.id,
				'product_id' : line.product_id.id,
				'product_uom_qty' : line.qty,
				'product_uom' : line.product_uom.id,
				'price_unit' : price_unit,
				'name' : line.notes or line.product_id.name or '/',
				}
			
			if not line.is_so_line_created:
				line_id = self.env['sale.order.line'].create(orderlinevals)

			line.is_so_line_created = True

		action = self.env.ref('sale.action_quotations')
		result = action.read()[0]
		result['domain'] = [('id', '=', order_id.id)]
		return result