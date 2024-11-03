from odoo import api, fields, models, _
from datetime import datetime

class HourGroup(models.Model):
	_name = 'hour.group'
	_description = 'Hour Group'

	name = fields.Char()
	start_hour = fields.Float()
	end_hour = fields.Float()
	active = fields.Boolean(default=True)