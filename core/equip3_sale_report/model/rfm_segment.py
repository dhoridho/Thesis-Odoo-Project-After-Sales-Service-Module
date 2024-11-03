from odoo import fields, models, api, _
from datetime import datetime
from dateutil import relativedelta

class SetuRFMSegment(models.Model):
	_inherit = 'setu.rfm.segment'
	
	desc = fields.Text("Description", compute="compute_desc")
	
	@api.depends('segment_description')
	def compute_desc(self):
		for res in self:
			res.desc = res.segment_description + " " + res.actionable_tips

class res_partner(models.Model):
	_inherit = "res.partner"

	index= fields.Integer("Qty", default=1)