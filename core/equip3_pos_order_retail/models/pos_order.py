from odoo import api, fields, models, _
import pytz
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

class PosOrder(models.Model):
	_inherit = "pos.order"

	pos_order_day = fields.Char('Day')
	pos_order_hour = fields.Float('Time')
	hour_group_id = fields.Many2one('hour.group','Hour Group')

	@api.model
	def create(self,vals):
		res = super(PosOrder,self).create(vals)
		if res.date_order:
			user_tz = self.env.user.tz or pytz.utc
			local = pytz.timezone(user_tz)
			dt = pytz.utc.localize(datetime.strptime(str(res.date_order),DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(local) 
			curr_week_day = dt.strftime('%A')
			ord_time = dt.hour+dt.minute/60.0
			hour_group = self.env['hour.group'].search([('start_hour','<=',ord_time),('end_hour','>=',ord_time)],limit=1)
			res.pos_order_hour = dt.hour+dt.minute/60.0
			if curr_week_day:
				res.pos_order_day = curr_week_day

			if hour_group:
				res.hour_group_id = hour_group.id
		return res