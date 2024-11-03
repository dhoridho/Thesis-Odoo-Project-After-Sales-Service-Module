from odoo import api, fields, models, _
from datetime import timedelta,datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
import pytz

class ReserveOrder(models.Model):
	_name = 'reserve.order'
	_description = 'Reserve Order'

	name = fields.Char(string="Reservation ID", readonly=True)
	state = fields.Selection([('reserved', 'Reserved'),('arrived', 'Arrived'),('cancel', 'Cancelled')],string="State",default='reserved')
	customer_name = fields.Char(string="Customer Name", required=True)
	cust_phone_no = fields.Char(string="Phone Number")
	reservation_from = fields.Datetime(string="Reservation From", required=True)
	reservation_to = fields.Datetime(string="Reservation To", required=True)
	table_no = fields.Many2one('restaurant.table',string="Table No")
	table_floor = fields.Many2one('restaurant.floor',string="Table Floor")
	reservation_seat = fields.Char(string="Reservation Seat")
	arrived_time = fields.Datetime()

	def guest_arrived(self):
		print('---------- data ---------', self)
		self.state = 'arrived'

	def guest_cancel_order(self):
		print('---------- data ---------', self)
		self.state = 'cancel'

	@api.model
	def create(self, vals):
		sequence_no = self.env['ir.sequence'].next_by_code('reserve.order')
		vals.update({'name': sequence_no})
		return super(ReserveOrder, self).create(vals)
	
	def write(self, vals):
		for rec in self:
			if 'state' in vals and vals.get('state') == 'arrived'  and rec.state != 'arrived':
				vals.update({'arrived_time': datetime.now()})
		return super(ReserveOrder, self).write(vals)

	@api.model
	def check_customer_arrived_time(self, floor_id, config_id):
		orders = self.search([('state', '=', 'arrived'),('arrived_time','!=',False),('table_floor','=',floor_id)])
		seat_time = self.env['pos.config'].browse(config_id).seat_time
		result =[]
		user_tz = self.env.user.tz or pytz.utc
		local = pytz.timezone(user_tz)
		for order in orders:
			estimated_time = (order.arrived_time + timedelta(minutes=seat_time))
			display_time = datetime.strftime(pytz.utc.localize(datetime.strptime(order.arrived_time.strftime("%Y-%m-%d %H:%M:%S"), DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(local),"%H:%M:%S")

			vals = {
				'table_no': order.table_no.id,
				'arrived_time': display_time,
				# 'arrived_time': order.arrived_time.strftime("%H:%M:%S"),
				'in_time':1 if estimated_time > datetime.now() else 0
			}
			result.append(vals)
			# (datetime.now() + timedelta(minutes=seat_time)).strftime("%Y-%m-%d %H:%M:%S")
		return result

	# 10 + 15 < 40