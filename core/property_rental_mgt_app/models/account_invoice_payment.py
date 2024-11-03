# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import date, datetime
import calendar

class AccountInvoice(models.Model):
	_inherit = 'account.move'

	property_id = fields.Many2one('product.product')

	def action_cancel(self):
		for move in self:
			# We remove all the analytics entries for this journal
			move.mapped('line_ids.analytic_line_ids').unlink()

		self.mapped('line_ids').remove_move_reconcile()
		self.write({'state': 'cancel'})
		return True

	def commission_calculation(args_list):
		commi_data = {}
		for user_id,comm_amount in args_list:
			total_commission = commi_data.get(user_id,0) + comm_amount
			commi_data[user_id] = total_commission
		return list(commi_data.items())


class AccountPayment(models.Model):
	_inherit = 'account.payment'

	def action_post(self):
		
		active_id = self._context.get('active_id')
		invoice_id = self.env['account.move'].browse(active_id)
		property_id = self.env['product.product'].search([('is_property','=',True),('name','=',invoice_id.invoice_origin)], limit=1)

		for each in property_id:
			print('\n\neach.user_commission_ids=====',each.user_commission_ids)
			if each.user_commission_ids:
				for comm in each.user_commission_ids:
					values = {}
					values.update({'pay_reference':invoice_id.payment_reference,'payment_origin':self.name,'user_id' :comm.user_id.id,'property_id':each.id,'percentage':comm.percentage,'commission':(invoice_id.amount_total * comm.percentage)/100,'inv_pay_source':invoice_id.name, 'invoice_id':invoice_id.id})
					commission_id=self.env['commission.line'].create(values)
					# print('commission_id======',commission_id)
					commission_id.write({'name':self.env['ir.sequence'].next_by_code('commission.line') or _('New')})
		res = super(AccountPayment, self).action_post()
		return res

	# auto generate commission worksheet line every month of last day.
	def generate_commission_worksheet(self):
		month_last_date = date.today().replace(day=calendar.monthrange(date.today().year, date.today().month)[1])
		if month_last_date.day == datetime.now().day:
			commission_obj = self.env['commission.line'].search([('is_created_worksheet','!=',True)])
			payment_obj = self.env['account.payment'].search([('state','=','posted')])
			for each in commission_obj:
				for payment in payment_obj:

					if each.inv_pay_source == payment.ref or each.pay_reference == payment.ref and each.invoice_id.invoice_origin == each.property_id.name:
						values = {}
						each.write({'is_created_worksheet':True})
						values.update({'user_id':each.user_id.id,'percentage':each.percentage,'commission':each.commission, 'payment_origin':payment.name,'invoice_origin':each.inv_pay_source,'property_origin':each.property_id.name, 'property_id':each.property_id.id})
						self.env['merge.worksheet'].create(values)

			worksheet_obj=self.env['merge.worksheet'].search([])
			user_list = []
			same_user = []
			unique_list = []
			unique_user_list = []
			data_list2 = [] 
			for each in worksheet_obj:
				comm_dict ={}
				comm_dict = {'user_id':each.user_id.id,'percentage':each.percentage,'commission':each.commission, 'property_origin':each.property_origin, 'invoice_origin':each.invoice_origin,'payment_origin':each.payment_origin}
				data_list2.append(comm_dict)
				user_list.append([each.user_id.id,each.commission])
			same_user = commission_calculation(user_list)
			for val in same_user:
				unique_list.append(list(val))

			w_list = []
			for each in worksheet_obj:
				for val in unique_list:
					if val[0] == each.user_id.id:
						if each.user_id.id not in unique_user_list:
							unique_user_list.append(each.user_id.id)
							commission_values = {}
							commission_values.update({'user_id':each.user_id.id, 'commission':val[1]})
							worksheet_id = self.env['commission.worksheet'].create(commission_values)
							worksheet_id.write({'name':self.env['ir.sequence'].next_by_code('commission.worksheet') or _('New')})
							w_list.append(worksheet_id.id)
				each.unlink()
			for w in w_list:
				wk_id = self.env['commission.worksheet'].browse(w)
				comm_work_list = []
				for d in data_list2:
					user_id = self.env['res.users'].browse(d['user_id'])
					if wk_id.user_id.id == user_id.id:
						comm_line_data = {'commission':d['commission'], 'percentage':d['percentage'], 'property_origin':d['property_origin'], 'invoice_origin':d['invoice_origin'], 'payment_origin':d['payment_origin']}
						comm_work_list.append((0, 0,comm_line_data))
				wk_id.write({'comm_work_line_ids':comm_work_list})
			return True
