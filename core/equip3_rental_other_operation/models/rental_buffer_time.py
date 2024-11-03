from odoo import api, fields, models

class RantalBufferTime(models.Model):
	_name = 'rental.buffer.time'

	name = fields.Char(string='Rental Order Line', readonly=True)
	rental_order_line_id = fields.Many2one('rental.order.line', string="Rental Order Line")
	buffer_start_time = fields.Datetime(string="Buffer Start Time")
	buffer_end_time = fields.Datetime(string="Buffer End Time")
	serial_no = fields.Many2one('stock.production.lot', string='Serial Number')
	product_id = fields.Many2one('product.product', string='Product')
	state = fields.Selection([('confirm', 'Confirmed')], string="State")
	branch_id = fields.Many2one('res.branch', related='product_id.branch_id', string="Branch")
