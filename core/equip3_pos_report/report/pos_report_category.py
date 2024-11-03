# -*- coding: utf-8 -*-

from odoo import fields, models


class PosOrderForCategoryReport(models.Model):
	_name = "pos.report.category"
	_description = "POS Report Category"


	def get_category_pos_order(self,categ_st_date,categ_ed_date,curr_session,categ_current_session):
		config_obj = self.env['pos.config'].search([])
		current_lang = self.env.context

		orders = False
		if categ_current_session == True:
			orders = self.env['pos.order'].search([
				('session_id', '=', curr_session),
				('state', 'in', ['paid','invoiced','done']),
				('config_id', 'in', config_obj.ids)])
		else:
			orders = self.env['pos.order'].search([
				('date_order', '>=', categ_st_date + ' 00:00:00'),
				('date_order', '<=', categ_ed_date + ' 23:59:59'),
				('state', 'in', ['paid','invoiced','done']),
				('config_id', 'in', config_obj.ids)])

		order_ids = []
		if orders:
			order_ids = orders.ids

		if order_ids:
			self.env.cr.execute("""
				SELECT pc.name, sum(qty) total, sum(price_subtotal_incl)
				FROM pos_order_line AS pol,
					 pos_category AS pc,
					 product_product AS product,
					 product_template AS templ
				WHERE pol.product_id = product.id
					AND templ.pos_categ_id = pc.id
					AND product.product_tmpl_id = templ.id
					AND pol.order_id IN %s 
				GROUP BY pc.name
				""", (tuple(order_ids),))
			categ = self.env.cr.dictfetchall()
		else:
			categ = []

		return categ