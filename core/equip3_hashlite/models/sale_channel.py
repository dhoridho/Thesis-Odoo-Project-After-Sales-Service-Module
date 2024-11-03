from odoo import fields, models

# handling issue if error 'sale.channel' does not in registry, will comment if module running as well
class SaleChannel(models.Model):
	_name = "sale.channel"

	name = fields.Char(string='Channel Name')