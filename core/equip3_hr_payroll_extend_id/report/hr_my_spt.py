# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import datetime

class HrGenerateSpt(models.Model):
	_name = 'hr.my.spt'

	employee_id = fields.Many2one('hr.employee', string='Employee')
	year = fields.Char('Year')
	month = fields.Char('Month')
	kpp = fields.Many2one('hr.tax.kpp', string='KPP')
	spt_type = fields.Many2one('hr.spt.type', string='SPT Type')
	spt_type_name = fields.Char('SPT Type Name')
	attachment = fields.Binary()
	attachment_fname = fields.Char(compute='get_attachment_fname')
	sequence = fields.Integer('Sequence')

	@api.depends('attachment')
	def get_attachment_fname(self):
		for record in self:
			if record.attachment:
				month_datetime = datetime.strptime(record.month, "%B")
				month_number = month_datetime.month
				record.attachment_fname = f"{record.employee_id.name}_{record.spt_type.name}_{record.year}{str('{:02d}'.format(month_number))}"
			else:
				record.attachment_fname = ""