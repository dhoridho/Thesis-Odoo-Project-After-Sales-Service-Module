# -*- coding: utf-8 -*-

from odoo import models, fields, api

class SaleOrder(models.Model):
	_inherit = 'sale.order'
	
	@api.depends('partner_id', 'team_id', 'user_id', 'commission_calc', 'amount_total')
	def _compute_commission_data(self):
		for res in self:
			member_lst = []
			commission_pay_on = self.env['ir.config_parameter'].sudo().get_param(
				'aspl_sales_commission.commission_pay_on') or ''
			if res.user_id and commission_pay_on == 'order_confirm':
				emp_id = self.env['hr.employee'].search([('user_id', '=', res.user_id.id)], limit=1)
				if emp_id:
					if res.commission_calc == 'product':
						for soline in res.order_line:
							for lineid in soline.product_id.product_comm_ids:
								lines = {'user_id': res.user_id.id, 'job_id': emp_id.job_id.id}
								if lineid.user_ids and res.user_id.id in [user.id for user in lineid.user_ids]:
									lines['commission'] = soline.price_subtotal * lineid.commission / 100 if lineid.compute_price_type == 'per' else lineid.commission * soline.product_uom_qty
									member_lst.append(lines)
									break
								elif lineid.job_id and not lineid.user_ids:
									if res.user_id.id in res.job_related_users(lineid.job_id):
										lines[
											'commission'] = soline.price_subtotal * lineid.commission / 100 if lineid.compute_price_type == 'per' else lineid.commission * soline.product_uom_qty
										member_lst.append(lines)
										break
					elif res.commission_calc == 'product_categ':
						for soline in res.order_line:
							for lineid in soline.product_id.categ_id.prod_categ_comm_ids:
								lines = {'user_id': res.user_id.id, 'job_id': emp_id.job_id.id}
								if lineid.user_ids and res.user_id.id in [user.id for user in lineid.user_ids]:
									lines[
										'commission'] = soline.price_subtotal * lineid.commission / 100 if lineid.compute_price_type == 'per' else lineid.commission * soline.product_uom_qty
									member_lst.append(lines)
									break
								elif lineid.job_id and not lineid.user_ids:
									if res.user_id.id in res.job_related_users(lineid.job_id):
										lines[
											'commission'] = soline.price_subtotal * lineid.commission / 100 if lineid.compute_price_type == 'per' else lineid.commission * soline.product_uom_qty
										member_lst.append(lines)
										break
					elif res.commission_calc == 'customer' and res.partner_id:
						for lineid in res.partner_id.comm_ids:
							lines = {'user_id': res.user_id.id, 'job_id': emp_id.job_id.id}
							if lineid.user_ids and res.user_id.id in [user.id for user in lineid.user_ids]:
								lines[
									'commission'] = res.amount_total * lineid.commission / 100 if lineid.compute_price_type == 'per' else lineid.commission
								member_lst.append(lines)
								break
							elif lineid.job_id and not lineid.user_ids:
								if res.user_id.id in res.job_related_users(lineid.job_id):
									lines[
										'commission'] = res.amount_total * lineid.commission / 100 if lineid.compute_price_type == 'per' else lineid.commission
									member_lst.append(lines)
									break
					elif res.commission_calc == 'sale_team' and res.team_id:
						for lineid in res.team_id.sale_team_comm_ids:
							lines = {'user_id': res.user_id.id, 'job_id': emp_id.job_id.id}
							if lineid.user_ids and res.user_id.id in [user.id for user in lineid.user_ids]:
								lines[
									'commission'] = res.amount_total * lineid.commission / 100 if lineid.compute_price_type == 'per' else lineid.commission
								member_lst.append(lines)
								break
							elif lineid.job_id and not lineid.user_ids:
								if res.user_id.id in res.job_related_users(lineid.job_id):
									lines[
										'commission'] = res.amount_total * lineid.commission / 100 if lineid.compute_price_type == 'per' else lineid.commission
									member_lst.append(lines)
									break
			userby = {}
			for member in member_lst:
				if member['user_id'] in userby:
					userby[member['user_id']]['commission'] += member['commission']
				else:
					userby.update({member['user_id']: member})
			member_lst = []
			for user in userby:
				member_lst.append((0, 0, userby[user]))
			res.sale_order_comm_ids = member_lst