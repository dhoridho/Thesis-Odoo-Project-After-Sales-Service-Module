# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class stock_inventory(models.Model):
    _inherit = 'stock.inventory'

    branch_id = fields.Many2one('res.branch', string='Branch')
