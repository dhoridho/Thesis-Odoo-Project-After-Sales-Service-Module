# -*- coding: utf-8 -*-

from odoo import fields, models, api


class PosOrderForjournalReport(models.Model):
	_name = "pos.report.journal"
	_description ="POS Report Journal"


	def get_journal_pos_order(self,categ_st_date,categ_ed_date):
		config_obj = self.env['pos.config'].search([])
		# pos_session_obj = self.env['pos.session'].search([('start_at','>=',categ_st_date + ' 00:00:00'),('stop_at','<=',categ_ed_date + ' 23:59:59')])

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
				SELECT pc.name, sum(qty) total, sum(qty * price_unit)
				FROM pos_order_line AS pol,
					 pos_journal AS pc,
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