# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, exceptions, fields, models, _
from odoo.addons import decimal_precision as dp
import datetime
from datetime import datetime
from dateutil import relativedelta
from odoo.exceptions import UserError, ValidationError
from odoo.exceptions import except_orm, Warning, RedirectWarning


class account_payment_term(models.Model):
	_inherit = "account.payment.term"

	interest_type = fields.Selection([('daily', 'Daily'),
								   ('monthly', 'Monthly'),
								   ], 'Interest Type')
	interest_percentage = fields.Float('Interest Percentage', digits=(16, 6))
	account_id = fields.Many2one('account.account', 'Account')


class account_invoice(models.Model):
	_inherit = "account.move"

	@api.depends('invoice_line_ids.price_subtotal',
				 'currency_id', 'company_id', 'invoice_date', 'type')
	def _compute_interest_amount(self, flag=1):
		round_curr = self.currency_id.round
		apt_per = self.env['account.payment.term']
		apt_per_record = apt_per.browse(self.invoice_payment_term_id.id)
		per = apt_per_record.interest_percentage
		if self.move_type in('out_invoice'):
			if flag == 0:
				int_per = 0.0 
				self.update({'interest':int_per})
			if self.invoice_date_due and self.invoice_payment_term_id:
				date1 = self.invoice_date_due
				date2 = datetime.now().date()
				r = relativedelta.relativedelta(date2, date1)
				no_of_months = r.months + 1
				no_of_days = (date2 - date1).days
				if date1 and date2:
					if date2 > date1 :
						self.show_intrest = True
						if apt_per_record.interest_type == 'monthly':
							int_per = (self.amount_untaxed + self.amount_tax) * (per / 100) * (no_of_months)
							self.update({'interest':int_per})
							self._check_interest_date_update_move_line()
						elif apt_per_record.interest_type == 'daily':
							int_per = (self.amount_untaxed + self.amount_tax) * (per / 100) * (no_of_days)
							self.update({'interest':int_per})
							self._check_interest_date_update_move_line()
						
						else:
							self.write({'interest':0.0})
			return							

	show_intrest = fields.Boolean('is_intrest', default=False)
	interest = fields.Float(string="Interest", readonly=True)
	check_date = fields.Date(string='check Date')
	check_month = fields.Char(string='check month')

	@api.onchange('invoice_date_due' , 'invoice_date','invoice_line_ids')
	def _onchange_date_due(self):
		if self.invoice_date_due and self.invoice_date :
			date1 = self.invoice_date_due
			date2 = self.invoice_date
			if date2 < date1:
				self.show_intrest = True
			else:
				self.show_intrest = False    
		if self.invoice_line_ids:
			self.show_intrest = True

	def _check_interest_date_update_move_line(self):
		if self.invoice_line_ids:
			for i  in self.invoice_line_ids:
				if i.name == "Interest Entry":
					i.with_context(check_move_validity=False).unlink()
		vals = {
			'name' : 'Interest Entry',
			'price_unit': self.interest ,
			'account_id': self.invoice_payment_term_id.account_id.id,
		}
		self.write({'invoice_line_ids' :([(0,0,vals)])})	


	@api.model
	def cron_interest(self):
		payment_term = self.env['account.payment.term']
		apt_type_record = payment_term.browse(self.invoice_payment_term_id.id)
		pay_type = apt_type_record.interest_type
		date1 = datetime.now().date()
		date3 = date1.month

		res = self.env['account.move'].search([('payment_state','in',['not_paid','in_payment'])])
		for i in res :
			if i.state == 'draft':
				if(pay_type == 'daily'): 
					if str(i.check_date) == str(date1):
						pass
					else:
						i.check_date=str(date1)
						i._compute_interest_amount(1)			

				else:
					if int(i.check_month) == date1.month:
						pass
					else:
						i.check_month=date1.month
						i._compute_interest_amount(1)
			elif i.state == 'posted':
				if i.payment_state == "not_paid":
					if(pay_type == 'daily'): 
						if str(i.check_date) == str(date1):
							pass
						else:
							i.check_date=str(date1)
							i.button_draft()
							i._compute_interest_amount(1)
							i.action_post()

					else:
						if int(i.check_month) == date1.month:
							pass
						else:
							i.check_month=date1.month
							i.button_draft()
							i._compute_interest_amount(1)
							i.action_post()

	def button_add_interest(self):
		payment_term = self.env['account.payment.term']
		apt_type_record = payment_term.browse(self.invoice_payment_term_id.id)
		pay_type = apt_type_record.interest_type
		date1 = datetime.now().date()
		date3 = date1.month

		if(pay_type == 'daily'): 
			if str(self.check_date) == str(date1):
				raise ValidationError('Your payment term is daily , and you can update it only once in day')
				return
			else:
				self.check_date=str(date1)
				self._compute_interest_amount(1)			

		else:
			if int(self.check_month) == date1.month:
				raise ValidationError('Your payment term is monthly , and you can update it only once in month')
				return
			else:
				self.check_month=date1.month
				self._compute_interest_amount(1)
				

	def button_reset_interest(self):

		self._compute_interest_amount(0)

		if self.line_ids:
			for i  in self.line_ids:
				if i.name == "Interest Entry":
					i.with_context(check_move_validity=False).unlink()
		if self.move_type == 'out_invoice':
			for i  in self.line_ids:
				if i.account_id.user_type_id.type == 'receivable':
					i.debit = self.amount_total	
		
		self.interest = 0.0
	 
	def action_interest_update_cancel(self):
		if self.filtered(lambda inv: inv.state not in ['draft', 'posted']):
			raise UserError(_("Invoice must be in draft or open state in order to be cancelled."))
		payment_term = self.env['account.payment.term']
		apt_type_record = payment_term.browse(self.invoice_payment_term_id.id)
		pay_type = apt_type_record.interest_type
		date1 = datetime.now().date()
		date3 = date1.month

		if(pay_type == 'daily'): 
			if str(self.check_date) == str(date1):
				raise ValidationError('Your payment term is daily , and you can update it only once in day')
				return
			else:
				if self.payment_state == "not_paid":
					self.check_date=str(date1)
					self.button_draft()
					self._compute_interest_amount(1) 
					self.action_post()
				return 
		else:
			if int(self.check_month) == date1.month:
				raise ValidationError('Your payment term is monthly , and you can update it only once in month')
				return
			else:
				if self.payment_state == "not_paid":
					self.check_month=date1.month
					self.button_draft()
					self._compute_interest_amount(1)		
					self.action_post()
				return 
