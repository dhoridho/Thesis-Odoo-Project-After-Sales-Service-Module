from odoo import models, fields


class StockScrap(models.Model):
	_inherit = 'stock.scrap'

	scrap_qty = fields.Float(digits='Product Unit of Measure')
