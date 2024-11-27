from odoo import models, fields, api

class VariableSale(models.Model):
	_name = 'warranty.period'

	name = fields.Char("Warranty Name", tracking=True)
	duration = fields.Integer("Duration (Days)", default=30, copy=False)
