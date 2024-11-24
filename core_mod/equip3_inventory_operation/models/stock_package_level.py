# -*- coding: utf-8 -*-

from odoo import _, api, fields, models


class StockPackageLevel(models.Model):
    _inherit = 'stock.package_level'

    occupancy = fields.Selection(
        [("full", "Full"), ("partial", "Partial")], string='Occupancy')
    product_id = fields.Many2one('product.product', string="Product")

    @api.depends('move_ids', 'move_ids.state', 'move_line_ids', 'move_line_ids.state', 'picking_id', 'picking_id.move_line_ids_without_package')
    def _compute_state(self):
        for package_level in self:
            res = super(StockPackageLevel, self)._compute_state()
            for package_level in self:
                move_line_ids = package_level.picking_id.move_line_ids_without_package.filtered(
                    lambda r: r.package_id.id == package_level.package_id.id)
                if move_line_ids and not move_line_ids.filtered(lambda ml: ml.state == 'done'):
                    if package_level.is_fresh_package:
                        package_level.state = 'new'
                    elif package_level._check_move_lines_map_quant_package(package_level.package_id, 'product_uom_qty'):
                        package_level.state = 'assigned'
                    else:
                        package_level.state = 'confirmed'
                elif move_line_ids.filtered(lambda ml: ml.state == 'done'):
                    package_level.state = 'done'
                elif move_line_ids.filtered(lambda ml: ml.state == 'cancel') or package_level.move_ids.filtered(lambda m: m.state == 'cancel'):
                    package_level.state = 'cancel'
                else:
                    package_level.state = 'draft'
            return res
