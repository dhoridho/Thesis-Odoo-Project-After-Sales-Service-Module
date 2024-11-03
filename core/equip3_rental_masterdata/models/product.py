# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.
from datetime import date

from odoo import api, fields, models,_
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
	_inherit = "product.template"

	rent_ok = fields.Boolean('Can be Rented', help="Specify if the product can be selected in a rent orders.", tracking=True)
	rent_per_month = fields.Float('Monthly Rental', help="Rental per month.", tracking=True)
	rent_per_week = fields.Float('Weekly Rental', help="Rental per week.", tracking=True)
	rent_per_day = fields.Float('Daily Rental', help="Rental per day.", tracking=True)
	rent_per_hour = fields.Float('Hourly Rental', help="Hourly Rent.", tracking=True)
	replacement_value = fields.Float('Replacement Value', readonly="1", help="Replacement Value", tracking=True)
	weekly_replacement_value = fields.Float('Weekly Replacement Value', readonly="1", help="Week Replacement Value", tracking=True)
	daily_replacement_value = fields.Float('Daily Replacement Value', readonly="1", help="Day Replacement Value", tracking=True)
	description_rental = fields.Text(string="Rental Description", required=False, tracking=True)
	backup_start_time = fields.Float(string="Backup Start Time", tracking=True, help="Hours Before The Product will be Used")
	backup_end_time = fields.Float(string="Backup End Time", tracking=True, help="Additional Hours Until The Product is Available After Rental End Date")
	is_asset_generated = fields.Boolean("Is Asset Generated", default=False)
	rent_per_year = fields.Float('Yearly Rental', help="Yearly Rent.", tracking=True)
	yearly_replacement_value = fields.Float('Yearly Replacement Value', readonly="1", help="Yearly Replacement Value", tracking=True)

	@api.model
	def _default_branch(self):
		default_branch_id = self.env.context.get('default_branch_id',False)
		if default_branch_id:
			return default_branch_id
		return self.env.company_branches[0].id if len(self.env.company_branches) == 1 else False

	@api.model
	def _domain_branch(self):
		return [('id', 'in', self.env.branches.ids), ('company_id','=', self.env.company.id)]

	branch_id = fields.Many2one(
		'res.branch',
		domain=_domain_branch,
		default = _default_branch,
		readonly=False
	)

	@api.model
	def create(self, vals_list):
		res = super(ProductTemplate, self).create(vals_list)
		for template in self:
			product_ids = self.env['product.product'].search([('product_tmpl_id', '=', res.id)])
			for product in product_ids:
				product.update({
					'rent_ok': template.rent_ok,
					'rent_per_month': template.rent_per_month,
					'rent_per_week': template.rent_per_week,
					'rent_per_day': template.rent_per_day,
					'rent_per_hour': template.rent_per_hour,
					'replacement_value': template.replacement_value,
					'weekly_replacement_value': template.weekly_replacement_value,
					'daily_replacement_value': template.daily_replacement_value,
					'description_rental': template.description_rental,
				})
		return res

	def write(self, values):
		res = super(ProductTemplate, self).write(values)
		for template in self:
			product_ids = self.env['product.product'].search([('product_tmpl_id', '=', template.id)])
			for product in product_ids:
				product.update({
					'rent_ok': template.rent_ok,
					'rent_per_month': template.rent_per_month,
					'rent_per_week': template.rent_per_week,
					'rent_per_day': template.rent_per_day,
					'rent_per_hour': template.rent_per_hour,
					'replacement_value': template.replacement_value,
					'weekly_replacement_value': template.weekly_replacement_value,
					'daily_replacement_value': template.daily_replacement_value,
					'description_rental': template.description_rental,
				})

		return res
	
	@api.model
	def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
		domain = domain or []
		context = self.env.context
		
		if context.get('allowed_company_ids'):
			domain += [('company_id', 'in', context.get('allowed_company_ids'))]

		if context.get('allowed_branch_ids'):
			domain += [
				'|',
				('branch_id', 'in', context.get('allowed_branch_ids'))
				,('branch_id', '=', False)
			]

		result = super(ProductTemplate, self).search_read(
			domain=domain, fields=fields, offset=offset, limit=limit, order=order
		)

		return result
    
	@api.model
	def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
		domain = domain or []
		context = self.env.context

		if context.get('allowed_company_ids'):
			domain.extend([('company_id', 'in', self.env.companies.ids)])

		if context.get('allowed_branch_ids'):
			domain.extend(
				[
					'|',
					('branch_id', 'in', context.get('allowed_branch_ids')),
					('branch_id', '=', False)
				]
			)
		return super(ProductTemplate, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)


	@api.constrains('tracking')
	def check_tracking(self):
		if self.rent_ok == True:
			for res in self:
				if res.tracking:
					if res.tracking == 'lot' or res.tracking == 'none':
						raise ValidationError("Rental Product can only use traceability by By Unique Serial Number")

	@api.constrains('rent_ok', 'type')
	def check_product_type(self):
		if self.rent_ok == True:
			if self.type == 'consu' or self.type == 'service':
				raise ValidationError("Rental Product can only have Storable Product or Asset product Type")
	
	@api.constrains('rent_per_month', 'rent_per_week', 'rent_per_day', 'rent_per_hour', 'rent_ok')
	def check_rent_duration_fields(self):
		if (
			self.rent_per_month == 0
			and self.rent_per_week == 0
			and self.rent_per_day == 0
			and self.rent_per_hour == 0
			and self.rent_ok
		):
			raise ValidationError(
				f"You haven't set rental value (Monthly Rental/Weekly Rental/Daily Rental/Hourly Rental) for this product."
			)

class ProductProduct(models.Model):
	_inherit = "stock.production.lot"

	is_available_today = fields.Boolean('Is available Today')

	@api.model
	def create(self, vals):
		vals['is_available_today'] = True
		return super(ProductProduct, self).create(vals)

	def check_rental_product_available_for_today(self):
		fmt = '%Y-%m-%d %H:%M:%S'
		today_date = date.today()
		date_from = today_date.strftime(fmt)
		date_to = today_date.strftime('%Y-%m-%d 23:59:59')

		sql = """select 
					spl.id 
				from 
					stock_production_lot spl 
				join product_product pp on pp.id = spl.product_id 
				where 
					pp.rent_ok = true AND
					spl.id NOT IN
					(select 
						rl.lot_id 
					from rental_order ro, rental_order_line rl
					Where 
						ro.state NOT IN('draft','close') AND 
						ro.id=rl.rental_id AND 
						(
							((ro.start_date BETWEEN %s AND %s) OR (ro.end_date BETWEEN %s AND %s)) OR  
							((%s BETWEEN ro.start_date AND ro.end_date) OR (%s BETWEEN ro.start_date AND ro.end_date))
						)
					)
				group by spl.id 
				"""

		self.env.cr.execute(sql, (
			date_from, date_to, date_from, date_to,
			date_from, date_to
		))

		query_result = self.env.cr.dictfetchall()
		if query_result:
			lot_ids = []
			for result in query_result:
				line_data = self.env['rental.order.line'].search([('lot_id', '=', result['id']),
																  '&', ('buffer_end_time', '>', date_from),
																  ('buffer_start_time', '<', date_to)])
				if not line_data:
					lot_ids.append(result['id'])
					product = self.search([('id', '=', result['id'])])
					product.is_available_today = True

		product_ids = self.search([])
		for product_id in product_ids:
			if product_id.id not in lot_ids:
				if product_id.product_id.rent_ok == True:
					product_id.is_available_today = False
