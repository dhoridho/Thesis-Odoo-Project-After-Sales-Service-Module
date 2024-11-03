# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class StockMove(models.Model):
	_inherit = 'stock.move'

	branch_id = fields.Many2one('res.branch', string='Branch')
