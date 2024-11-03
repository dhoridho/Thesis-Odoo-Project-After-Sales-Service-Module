from odoo import models, fields
from datetime import timedelta
from datetime import datetime


class IrSequence(models.Model):
	_inherit = 'ir.sequence'

	def _create_date_range_seq(self, date):
		if self.code not in (
			'kitchen.production.record.day', 
			'assemble.production.record.day', 
			'disassemble.production.record.day'
		):
			return super(IrSequence, self)._create_date_range_seq(date)

		first_date = datetime.now().date().replace(month=1, day=1)
		end_date = datetime.now().date().replace(month=12, day=31)

		date_from = first_date.strftime('%Y-%m-%d')
		date_to = end_date.strftime('%Y-%m-%d')

		date_range = self.env['ir.sequence.date_range'].search([('sequence_id', '=', self.id), ('date_from', '>=', date), ('date_from', '<=', date_to)], order='date_from desc', limit=1)
		if date_range:
			date_to = date_range.date_from + timedelta(days=-1)

		date_range = self.env['ir.sequence.date_range'].search([('sequence_id', '=', self.id), ('date_to', '>=', date_from), ('date_to', '<=', date)], order='date_to desc', limit=1)
		if date_range:
			date_from = date_range.date_to + timedelta(days=1)

		seq_date_range = self.env['ir.sequence.date_range'].sudo().create({
			'date_from': date_from,
			'date_to': date_to,
			'sequence_id': self.id,
		})
		return seq_date_range