# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class purchase_order(models.Model):
    _inherit = 'purchase.order.line'

    branch_id = fields.Many2one('res.branch', string='Branch')


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    branch_id = fields.Many2one('res.branch', string='Branch')
