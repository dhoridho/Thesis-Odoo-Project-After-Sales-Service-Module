# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ResPartnerIn(models.Model):
    _inherit = 'res.partner'

    branch_id = fields.Many2one('res.branch', string='Branch')
