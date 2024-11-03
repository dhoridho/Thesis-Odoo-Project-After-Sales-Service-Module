# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, float_round, float_is_zero, pycompat



class InventoryIn(models.Model):

	_inherit = 'stock.inventory'

	def _get_inventory_lines_values(self):
		# TDE CLEANME: is sql really necessary ? I don't think so
		locations = self.env['stock.location']
		if self.location_ids:
			locations = self.env['stock.location'].search([('id', 'child_of', self.location_ids.ids)])
		else:
			locations = self.env['stock.location'].search([('company_id', '=', self.company_id.id), ('usage', 'in', ['internal', 'transit'])])
		domain = ' location_id in %s AND quantity != 0 AND active = TRUE'
		args = (tuple(locations.ids),)

		vals = []
		Product = self.env['product.product']
		# Empty recordset of products available in stock_quants
		quant_products = self.env['product.product']

		# If inventory by company
		if self.company_id:
			domain += ' AND company_id = %s'
			args += (self.company_id.id,)
		if self.product_ids:
			domain += ' AND product_id in %s'
			args += (tuple(self.product_ids.ids),)

		self.env['stock.quant'].flush(['company_id', 'product_id', 'quantity', 'location_id', 'lot_id', 'package_id', 'owner_id', 'product_category'])
		self.env['product.product'].flush(['active'])
		self.env.cr.execute("""SELECT product_id, sum(quantity) as product_qty, location_id, stock_quant.lot_id as prod_lot_id, stock_quant.package_id, stock_quant.owner_id as partner_id, product_category as category_uom_id
			FROM stock_quant
			LEFT JOIN product_product
			ON product_product.id = stock_quant.product_id
			WHERE %s
			GROUP BY product_id, location_id, stock_quant.lot_id, stock_quant.package_id, partner_id,product_category """ % domain, args)

		for product_data in self.env.cr.dictfetchall():
			product_data['company_id'] = self.company_id.id
			product_data['inventory_id'] = self.id
			# replace the None the dictionary by False, because falsy values are tested later on
			for void_field in [item[0] for item in product_data.items() if item[1] is None]:
				product_data[void_field] = False
			product_data['theoretical_qty'] = product_data['product_qty']
			if self.prefill_counted_quantity == 'zero':
				product_data['product_qty'] = 0
			if product_data['product_id']:
				product_data['product_uom_id'] = Product.browse(product_data['product_id']).uom_id.id
				product_data['unit_price'] = Product.browse(product_data['product_id']).standard_price
				product_data['uom_id'] = Product.browse(product_data['product_id']).uom_id.id
				product_data['category_uom_id'] = Product.browse(product_data['product_id']).uom_id.category_id.id
				
				
				quant_products |= Product.browse(product_data['product_id'])
			vals.append(product_data)
		return vals

