# -*- coding: UTF-8 -*-
# Part of Softhealer Technologies.

from odoo import models, fields, api


class ShAccountInvoice(models.Model):
    _inherit = 'account.move'

    def _prepare_invoice_line_from_po_line(self, line):
        res = super(ShAccountInvoice,
                    self)._prepare_invoice_line_from_po_line(line)
        res.update({
            'sh_sec_qty': line.sh_sec_qty,
            'sh_sec_uom': line.sh_sec_uom.id,
        })
        return res


class ShAccountInvoiceLine(models.Model):
    _inherit = "account.move.line"

    sh_sec_qty = fields.Float(
        "Secondary Qty",
        digits='Product Unit of Measure',
        compute="_compute_product_uom_qty_sh",
        readonly=False
    )
    sh_sec_uom = fields.Many2one(
        "uom.uom",
        'Secondary UOM',
        compute="_compute_secondary_uom",
        readonly=False
    )
    sh_is_secondary_unit = fields.Boolean(
        "Related Sec Unit",
        related="product_id.sh_is_secondary_unit"
    )
    category_id = fields.Many2one(
        "uom.category",
        "Account UOM Category",
        related="product_uom_id.category_id"
    )

    @api.depends('quantity', 'product_uom_id')
    def _compute_product_uom_qty_sh(self):
        if self:
            for rec in self:
                if rec.sh_is_secondary_unit and rec.sh_sec_uom:
                    rec.sh_sec_qty = rec.product_uom_id._compute_quantity(
                        rec.quantity,
                        rec.sh_sec_uom
                    )
                else:
                    rec.sh_sec_qty = 0.0

    @api.onchange('sh_sec_qty', 'sh_sec_uom')
    def onchange_sh_sec_qty_sh(self):
        if self:
            for rec in self:
                if rec.sh_is_secondary_unit and rec.product_uom_id:
                    rec.quantity = rec.sh_sec_uom._compute_quantity(
                        rec.sh_sec_qty,
                        rec.product_uom_id
                    )

    @api.depends('product_id', 'product_uom_id')
    def _compute_secondary_uom(self):
        if self:
            for rec in self:
                if rec.product_id and rec.product_id.sh_is_secondary_unit and rec.product_id.uom_id:
                    rec.sh_sec_uom = rec.product_id.sh_secondary_uom.id
                elif not rec.product_id.sh_is_secondary_unit:
                    rec.sh_sec_uom = False
                    rec.sh_sec_qty = 0.0
