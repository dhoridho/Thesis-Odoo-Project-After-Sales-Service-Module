# -*- coding: UTF-8 -*-
# Part of Softhealer Technologies.

from odoo import models, fields, api


class ShStockMove(models.Model):
    _inherit = "stock.move"

    sh_sec_qty = fields.Float(
        "Secondary Qty",
        digits='Product Unit of Measure',
        store=True,
        copy=False
    )
    sh_sec_done_qty = fields.Float(
        "Secondary Done Qty",
        digits='Product Unit of Measure',
        store=True,
        copy=False
    )
    sh_sec_uom = fields.Many2one(
        "uom.uom",
        'Secondary UOM',
        related="product_id.sh_secondary_uom",
        store=True,
        copy=False
    )
    sh_is_secondary_unit = fields.Boolean(
        "Related Sec Unit",
        related="product_id.sh_is_secondary_unit",
        store=True,
        copy=False
    )

    @api.onchange('quantity_done')
    def onchange_product_uom_done_qty_sh(self):
        if self and self.sh_is_secondary_unit and self.sh_sec_uom:
            self.sh_sec_done_qty = self.product_uom._compute_quantity(
                self.quantity_done,
                self.sh_sec_uom
            )

    @api.onchange('sh_sec_done_qty')
    def onchange_sh_sec_done_qty_sh(self):
        if self and self.sh_is_secondary_unit and self.product_uom:
            self.quantity_done = self.sh_sec_uom._compute_quantity(
                self.sh_sec_done_qty,
                self.product_uom
            )

    @api.onchange('product_uom_qty', 'product_uom')
    def onchange_product_uom_qty_sh(self):
        if self.sh_is_secondary_unit and self.sh_sec_uom:
            self.sh_sec_qty = self.product_uom._compute_quantity(
                self.product_uom_qty,
                self.sh_sec_uom
            )

    @api.onchange('sh_sec_qty', 'sh_sec_uom')
    def onchange_sh_sec_qty_sh(self):
        if self and self.sh_is_secondary_unit and self.product_uom:
            self.product_uom_qty = self.sh_sec_uom._compute_quantity(
                self.sh_sec_qty,
                self.product_uom
            )

    @api.model
    def create(self, vals):
        res = super(ShStockMove, self).create(vals)
        if res.sale_line_id and res.sale_line_id.sh_is_secondary_unit and res.sale_line_id.sh_sec_uom:
            res.update({
                'sh_sec_uom': res.sale_line_id.sh_sec_uom.id,
                'sh_sec_qty': res.sale_line_id.sh_sec_qty
            })
        elif res.purchase_line_id and res.purchase_line_id.sh_is_secondary_unit and res.purchase_line_id.sh_sec_uom:
            res.update({
                'sh_sec_uom': res.purchase_line_id.sh_sec_uom.id,
                'sh_sec_qty': res.purchase_line_id.sh_sec_qty
            })
        return res


class ShStockMoveLine(models.Model):
    _inherit = "stock.move.line"

    sh_sec_qty = fields.Float(
        "Secondary Qty",
        digits='Product Unit of Measure'
    )
    sh_sec_uom = fields.Many2one(
        "uom.uom",
        'Secondary UOM',
        related="move_id.sh_sec_uom"
    )
    sh_is_secondary_unit = fields.Boolean(
        "Related Sec Unit",
        related="move_id.product_id.sh_is_secondary_unit"
    )

    @api.onchange('qty_done')
    def onchange_product_uom_done_qty_sh_move_line(self):
        if self and self.sh_is_secondary_unit and self.sh_sec_uom:
            self.sh_sec_qty = self.product_uom_id._compute_quantity(
                self.qty_done,
                self.sh_sec_uom
            )
            self.move_id.sh_sec_done_qty = self.product_uom_id._compute_quantity(
                self.qty_done,
                self.move_id.sh_sec_uom
            )

    @api.onchange('sh_sec_qty')
    def onchange_product_sec_done_qty_sh_move_line(self):
        if self and self.sh_is_secondary_unit and self.sh_sec_uom:
            self.qty_done = self.sh_sec_uom._compute_quantity(
                self.sh_sec_qty,
                self.product_uom_id
            )
            self.move_id.quantity_done = self.sh_sec_qty
    
    def _get_aggregated_product_quantities(self, **kwargs):
        """ Returns a dictionary of products (key = id+name+description+uom) and corresponding values of interest.

        Allows aggregation of data across separate move lines for the same product. This is expected to be useful
        in things such as delivery reports. Dict key is made as a combination of values we expect to want to group
        the products by (i.e. so data is not lost). This function purposely ignores lots/SNs because these are
        expected to already be properly grouped by line.

        returns: dictionary {product_id+name+description+uom: {product, name, description, qty_done, product_uom}, ...}
        """
        super(ShStockMoveLine, self)._get_aggregated_product_quantities(**kwargs)
        aggregated_move_lines = {}
        for move_line in self:
            name = move_line.product_id.display_name
            description = move_line.move_id.description_picking
            if description == name or description == move_line.product_id.name:
                description = False
            uom = move_line.product_uom_id
            line_key = str(move_line.product_id.id) + "_" + name + (description or "") + "uom " + str(uom.id)

            if line_key not in aggregated_move_lines:
                aggregated_move_lines[line_key] = {'name': name,
                                                   'description': description,
                                                   'qty_done': move_line.qty_done,
                                                   'product_uom': uom.name,
                                                   'product': move_line.product_id,
                                                   'sh_sec_qty':move_line.sh_sec_qty,
                                                   'sh_sec_uom':move_line.sh_sec_uom.name,
                                                   }
            else:
                aggregated_move_lines[line_key]['qty_done'] += move_line.qty_done
        return aggregated_move_lines


class ShStockImmediateTransfer(models.TransientModel):
    _inherit = 'stock.immediate.transfer'

    def process(self):
        res = super(ShStockImmediateTransfer, self).process()
        for picking_ids in self.pick_ids:
            for moves in picking_ids.move_ids_without_package:
                if moves.sh_sec_uom:
                    moves.sh_sec_done_qty = moves.product_uom._compute_quantity(
                        moves.product_uom_qty,
                        moves.sh_sec_uom
                    )
                for move_lines in moves.move_line_ids:
                    if move_lines.sh_sec_uom:
                        move_lines.sh_sec_qty = move_lines.product_uom_id._compute_quantity(
                            move_lines.qty_done,
                            moves.sh_sec_uom
                        )
        return res
