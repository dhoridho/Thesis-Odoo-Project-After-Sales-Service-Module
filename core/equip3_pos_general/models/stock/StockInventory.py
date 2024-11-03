# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class StockInventory(models.Model):
    _inherit = 'stock.inventory'

    pos_branch_id = fields.Many2one(
        'res.branch',
        string='Branch'
    )

    @api.model
    def create(self, vals):
        if vals.get('location_id', None):
            location = self.env['stock.location'].browse(vals.get('location_id'))
            if location and location.pos_branch_id:
                vals.update({'pos_branch_id': location.pos_branch_id.id})
        if not vals.get('pos_branch_id'):
            vals.update({'pos_branch_id': self.env['res.branch'].sudo().get_default_branch()})
        return super(StockInventory, self).create(vals)