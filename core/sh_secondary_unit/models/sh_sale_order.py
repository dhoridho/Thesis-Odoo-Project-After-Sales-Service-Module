# -*- coding: UTF-8 -*-
# Part of Softhealer Technologies.

from odoo import models, fields, api


class ShSaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    sh_sec_qty = fields.Float(
        "Secondary Qty",
        digits='Product Unit of Measure'
    )
    sh_sec_uom = fields.Many2one("uom.uom", 'Secondary UOM')
    sh_is_secondary_unit = fields.Boolean(
        "Related Sec Unit",
        related="product_id.sh_is_secondary_unit"
    )
    category_id = fields.Many2one(
        "uom.category",
        "Sale UOM Category",
        related="product_uom.category_id"
    )

    @api.onchange('product_uom_qty', 'product_uom')
    def onchange_product_uom_qty_sh(self):
        if self and self.sh_is_secondary_unit and self.sh_sec_uom:
            self.sh_sec_qty = self.product_uom._compute_quantity(
                self.product_uom_qty, self.sh_sec_uom
            )

    @api.onchange('sh_sec_qty', 'sh_sec_uom')
    def onchange_sh_sec_qty_sh(self):
        if self and self.sh_is_secondary_unit and self.product_uom:
            self.product_uom_qty = self.sh_sec_uom._compute_quantity(
                self.sh_sec_qty, self.product_uom
            )

    @api.onchange('product_id')
    def onchange_secondary_uom(self):
        if self:
            for rec in self:
                if rec.product_id and rec.product_id.sh_is_secondary_unit and rec.product_id.uom_id:
                    rec.sh_sec_uom = rec.product_id.sh_secondary_uom.id
                elif not rec.product_id.sh_is_secondary_unit:
                    rec.sh_sec_uom = False
                    rec.sh_sec_qty = 0.0

    def _prepare_invoice_line(self, **optional_values):
        res = super(ShSaleOrderLine, self)._prepare_invoice_line(
            **optional_values
        )
        res.update({
            'sh_sec_qty': self.sh_sec_qty,
            'sh_sec_uom': self.sh_sec_uom.id,
            })
        return res
