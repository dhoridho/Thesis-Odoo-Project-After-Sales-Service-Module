# -*- coding: utf-8 -*-

import calendar
from odoo import fields, models, api


class PosOrderForPaymentReport(models.Model):
	_name = "pos.report.payment"
	_description ="POS Report Payment"

	def get_crnt_ssn_payment_pos_order(self,smry,cshr,curr_session,is_current_session,pay_st_date,pay_ed_date):
		config_obj = self.env['pos.config'].search([])
		if is_current_session == True:
			if smry == 'Salespersons':
				orders = self.env['pos.order'].search([
					('state', 'in', ['paid','invoiced','done']),
					('user_id', '=', cshr),
					('session_id', '=', curr_session),
					('config_id', 'in', config_obj.ids)])
			else:
				orders = self.env['pos.order'].search([
					('state', 'in', ['paid','invoiced','done']),
					('session_id', '=', curr_session),
					('config_id', 'in', config_obj.ids),
					])
		else:
			if smry == 'Salespersons':
				orders = self.env['pos.order'].search([
					('state', 'in', ['paid','invoiced','done']),
					('user_id', '=', cshr),
					('date_order', '>=', pay_st_date+ ' 00:00:00'),
					('date_order', '<=', pay_ed_date + ' 23:59:59'),
					('config_id', 'in', config_obj.ids)])
			else:
				orders = self.env['pos.order'].search([
					('state', 'in', ['paid','invoiced','done']),
					('date_order', '>=', pay_st_date+ ' 00:00:00'),
					('date_order', '<=', pay_ed_date + ' 23:59:59'),
					('config_id', 'in', config_obj.ids),
					])
		st_line_ids = self.env["pos.payment"].search([('pos_order_id', 'in', orders.ids)]).ids
		if st_line_ids:
			self.env.cr.execute("""
				SELECT ppm.name, sum(amount) total
				FROM pos_payment AS pp,
					pos_payment_method AS ppm
				WHERE  pp.payment_method_id = ppm.id 
					AND pp.id IN %s 
				GROUP BY ppm.name
			""", (tuple(st_line_ids),))
			payments = self.env.cr.dictfetchall()
		else:
			payments = []


		st_ids = self.env["pos.payment"].search([('pos_order_id', 'in', orders.ids)])
		journal_data = {}
		final_total =0.0
		for line in st_ids:
			journal = line.payment_method_id.name
			month = line.payment_date.strftime('%B')+" "+str(line.payment_date.year)
			if month in journal_data.keys():
				for i in journal_data[month]:
					if journal in i:
						old_subtotal = i.get(journal)
						i.update({
						journal : old_subtotal+line.amount,
						})
						final_total += line.amount
				if not any(journal in d for d in journal_data[month]):
					final_total += line.amount
					journal_data[month].append({
						journal : line.amount,
					})
			else:
				final_total += line.amount
				journal_data.update({ month : [{
					 journal : line.amount,
				}]})

		def get_month_from_key(item):
			months = {calendar.month_name[i]: i for i in range(1, 13)}
			# Convert '2015:November' to (2015, 11)
			# Return value of this function is used to compare dictionary keys.
			month,year = item[0].split(' ')  # item[0] is key
			return int(year), months.get(month, -1)

		final_jrnl = sorted(journal_data.items(), key=get_month_from_key,reverse=True)
		return [final_total,final_jrnl,payments]