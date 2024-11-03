# -*- coding: utf-8 -*-
import base64
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class HrMyPayslips(models.TransientModel):
	_name = 'hr.my.payslips'

	@api.returns('self')
	def _get_employee(self):
		return self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1) or False

	employee_id = fields.Many2one('hr.employee', string='Employee', required=True, help="Employee", default=_get_employee)
	payslip_type = fields.Many2many('hr.payslip.type', string='Payslip Type', required=True)
	payslip_period_id = fields.Many2one('hr.payslip.period', string='Payslip Period', domain="[('state','=','open')]",
										required=True)
	month = fields.Many2one('hr.payslip.period.line', string="Month", domain="[('period_id','=',payslip_period_id)]",
							required=True)
	month_name = fields.Char('Month Name', readonly=True)
	year = fields.Char('Year', readonly=True)
	date_from = fields.Date(string='Date From', readonly=True, required=True, help="Start date")
	date_to = fields.Date(string='Date To', readonly=True, required=True, help="End date")

	@api.onchange('payslip_period_id')
	def _onchange_payslip_period_id(self):
		for res in self:
			if res.payslip_period_id:
				res.date_from = False
				res.date_to = False

	@api.onchange('month')
	def _onchange_month(self):
		for res in self:
			if res.payslip_period_id:
				if res.month:
					period_line_obj = self.env['hr.payslip.period.line'].search(
						[('id', '=', res.month.id)], limit=1)
					if period_line_obj:
						for rec in period_line_obj:
							res.date_from = rec.start_date
							res.date_to = rec.end_date
							res.month_name = res.month.month
							res.year = res.month.year
					else:
						res.date_from = False
						res.date_to = False
						res.month_name = False
						res.year = False

	def action_print(self):
		data = {
			'employee_id': self.employee_id.id,
			'payslip_type': self.payslip_type.ids,
			'month': self.month.id,
			'date_from': self.date_from,
			'date_to': self.date_to,
		}
		pdf = self.env.ref('equip3_hr_payroll_extend_id.action_report_my_payslip')._render_qweb_pdf([self.id], data=data)
		attachment = base64.b64encode(pdf[0])
		attachment_name = "My Payslips " + self.month.month + "-" + self.month.year
		export_id = self.env['hr.my.payslips.attachment'].create({'attachment_file': attachment, 'file_name': attachment_name})
		return {
			'view_mode': 'form',
			'res_id': export_id.id,
			'name': 'My Payslips',
			'res_model': 'hr.my.payslips.attachment',
			'view_type': 'form',
			'type': 'ir.actions.act_window',
			'target': 'new',
		}

class HrMyPayslipsReport(models.AbstractModel):
	_name = 'report.equip3_hr_payroll_extend_id.report_my_payslip'

	def _get_report_values(self, docids, data=None):
		domain = [('state', '=', 'done'), ('payslip_pesangon', '=', False)]
		if data.get('employee_id'):
			domain.append(('employee_id', '=', data.get('employee_id')))
		if data.get('date_from'):
			domain.append(('date_from', '=', data.get('date_from')))
		if data.get('date_to'):
			domain.append(('date_to', '=', data.get('date_to')))
		docs = self.env['hr.payslip'].search(domain, limit=1)
		if not docs:
			raise ValidationError("Payslip not found")
		slip_line = docs.line_ids
		payslip = 0.0
		bonus_payslip = 0.0
		thr_payslip = 0.0
		for line in slip_line:
			for rec in line.salary_rule_id.payslip_type:
				if rec.name == 'Employee Payslip':
					payslip += 1.0
				if rec.name == 'Bonus Payslip':
					bonus_payslip += 1.0
				if rec.name == 'THR Payslip':
					thr_payslip += 1.0

		payslip_type = data.get('payslip_type')
		return {
			'doc_ids': docs.ids,
			'doc_model': 'hr.payslip',
			'payslip_type': payslip_type,
			'payslip': payslip,
			'bonus_payslip': bonus_payslip,
			'thr_payslip': thr_payslip,
			'docs': docs,
			'datas': data
		}

class HrMyPayslipsAttachment(models.TransientModel):
    _name = "hr.my.payslips.attachment"
    _description = "My Payslips Attachment"

    attachment_file = fields.Binary('Attachment File')
    file_name = fields.Char('File Name')