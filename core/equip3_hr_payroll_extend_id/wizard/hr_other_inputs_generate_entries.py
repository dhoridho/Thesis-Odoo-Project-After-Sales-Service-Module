# -*- coding: utf-8 -*-
import calendar
from odoo.tools.safe_eval import safe_eval
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.osv import expression

class HROtherInputsGenerateEntries(models.TransientModel):
	_name = 'hr.other.inputs.generate.entries'

	employee_ids = fields.Many2many('hr.employee', string='Employees', required=True)
	payslip_period_id = fields.Many2one('hr.payslip.period', string='Payslip Period',
										domain="[('state','=','open')]", required=True)

	def _compute_month_selection(self):
		month_list = []
		for x in range(1, 13):
			month_list.append((str(calendar.month_name[x]), str(calendar.month_name[x])))
		return month_list

	month = fields.Selection(selection=lambda self: self._compute_month_selection(), string="Month", required=True, default="none")
	periode_start_date = fields.Date("Start Date", required=True, readonly=True)
	periode_end_date = fields.Date("End Date", required=True, readonly=True)
	hr_other_input_id = fields.Many2one('hr.other.inputs', string='Other Inputs')

	@api.onchange('payslip_period_id','month')
	def _onchange_month(self):
		if self.payslip_period_id:
			if self.month:
				period_line_obj = self.env['hr.payslip.period.line'].search([('period_id','=',self.payslip_period_id.id),('month','=',self.month)], limit=1)
				if period_line_obj:
					for rec in period_line_obj:
						self.periode_start_date = rec.start_date
						self.periode_end_date = rec.end_date
				else:
					self.periode_start_date = False
					self.periode_end_date = False


	def action_generate(self):
		employee_ids = self.employee_ids
		for rec in employee_ids:
			eval_context = {
				'employee': rec.with_context({}),
			}
			employee = rec.id
			employee_id = rec.sequence_code
			contract = ''
			contract_id = False
			contract_obj = self.env['hr.contract'].search(
				[('employee_id', '=', rec.id), ('state', '=', 'open')], limit=1)
			if contract_obj:
				for con in contract_obj:
					contract_id = con.id
					contract = con.name
			other_input_id = self.hr_other_input_id.id
			code = self.hr_other_input_id.code
			input_type = ''
			if self.hr_other_input_id.input_type == 'manual_entries':
				input_type = 'Manual Entries'
			elif self.hr_other_input_id.input_type == 'get_from_other_object':
				input_type = 'Get from Other Object'
			amount = 0.0
			obj_name = self.hr_other_input_id.model_id.model
			obj_domain = []
			if self.hr_other_input_id.domain_filter:
				domain_filter = self.hr_other_input_id.domain_filter
				dom = safe_eval(domain_filter, eval_context) if domain_filter else []
				dom = expression.normalize_domain(dom)
				obj_domain.append(dom)
				obj_domain = expression.AND(obj_domain)
			if self.hr_other_input_id.calculate_type == 'count':
				row_count = len(self.env[obj_name].sudo().search(obj_domain))
				amount = float(row_count)
			elif self.hr_other_input_id.calculate_type in ['sum', 'average'] and self.hr_other_input_id.record_field:
				field = self.hr_other_input_id.record_field.name
				record = self.env[obj_name].sudo().read_group(obj_domain, [field], [], lazy=False)
				if record and len(record) > 0:
					record = record[0]
					if self.hr_other_input_id.calculate_type == 'sum' and record.get('__count', False) and (record.get(field)):
						record_sum = record.get(field, 0)
						amount = float(record_sum)
					elif self.hr_other_input_id.calculate_type == 'average' and record.get('__count', False) and (record.get(field)):
						record_average = record.get(field, 0) / record.get('__count', 1)
						amount = float(record_average)
			payslip_period_id = self.payslip_period_id.id
			month = self.month
			periode_start_date = self.periode_start_date
			periode_end_date = self.periode_end_date

			input_entries_search = self.env['hr.other.input.entries'].search([('employee','=',employee),
																	('other_input_id','=',other_input_id),
																	('payslip_period_id','=',payslip_period_id),
																	('month','=',month),
																	('periode_start_date','=',periode_start_date),
																	('periode_end_date','=',periode_end_date)])
			if input_entries_search:
				input_entries_search.write({
					'amount': amount
				})
			else:
				input_entries_vals = {'employee': employee,
									  'employee_id': employee_id,
									  'contract_id': contract_id or False,
									  'contract': contract,
									  'other_input_id': other_input_id,
									  'code': code,
									  'input_type': input_type,
									  'payslip_period_id': payslip_period_id,
									  'month': month,
									  'periode_start_date': periode_start_date,
									  'periode_end_date': periode_end_date,
									  'amount': amount
									  }
				input_entries = self.env['hr.other.input.entries'].create(input_entries_vals)
		return {'type': 'ir.actions.act_window_close'}

