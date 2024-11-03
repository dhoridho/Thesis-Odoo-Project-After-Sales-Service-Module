from odoo import api, fields, models

class RantalOrderLine(models.Model):
	_inherit = 'rental.order.line'

	rental_buffer_time_id = fields.Many2one('rental.buffer.time', string='Rental Buffer Time')
	buffer_start_time = fields.Datetime('Buffer Start Time')
	buffer_end_time = fields.Datetime('Buffer End Time')
