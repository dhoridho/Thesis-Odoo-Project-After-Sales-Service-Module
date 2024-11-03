# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

from odoo import fields, models, api


class PurchaseOrderHistory(models.Model):
    _name = "purchase.order.history"
    _description = "Purchase Order History"

    purchase_reorder = fields.Boolean("Reorder")
    name = fields.Many2one("purchase.order.line", "Purchase Order Line")
    order_id = fields.Many2one(
        "purchase.order",
        "Current Purchase Order",
        readonly=True
    )
    po_id = fields.Char("Purchase Order")
    product_id = fields.Many2one(
        "product.product",
        related="name.product_id",
        readonly=True
    )
    price_unit = fields.Float(
        "Price",
        related="name.price_unit",
        readonly=True
    )
    product_qty = fields.Float(
        "Quantity",
        related="name.product_qty",
        readonly=True
    )
    product_uom = fields.Many2one(
        "uom.uom",
        "Unit",
        related="name.product_uom",
        readonly=True
    )
    currency_id = fields.Many2one(
        "res.currency",
        "Currency Id",
        related="name.currency_id"
    )
    price_subtotal = fields.Monetary(
        "Subtotal",
        readonly=True,
        related="name.price_subtotal"
    )

    #Reorder Button
    def purchases_reorder(self):
        vals = {"price_unit": self.price_unit,
                "product_qty": self.product_qty,
                "price_subtotal": self.price_subtotal,
                "date_planned": fields.Datetime.now()}

        if self.product_id:
            vals.update({"name": self.product_id.display_name,
                         "product_id": self.product_id.id})

        if self.product_uom:
            vals.update({"product_uom": self.product_uom.id})

        if self.order_id:
            vals.update({"order_id": self.order_id.id})

        self.order_id.write({"order_line": [(0, 0, vals)]})
        self._cr.commit()

        return {"type": "ir.actions.client", "tag": "reload"}


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    order_history_line = fields.One2many(
        "purchase.order.history", "order_id", string="Order History")

    #All Lines Reorder Button
    def action_all_purchase_reorder(self):
        order_history = self.env["purchase.order.history"].search(
            [("order_id", "=", self.id)])
        for rec in order_history:
            if rec.purchase_reorder:
                vals = {"price_unit": rec.price_unit,
                        "product_qty": rec.product_qty,
                        "price_subtotal": rec.price_subtotal,
                        "date_planned": fields.Datetime.now()}
                if rec.product_id:
                    vals.update({"name": rec.product_id.display_name,
                                 "product_id": rec.product_id.id})

                if rec.product_uom:
                    vals.update({"product_uom": rec.product_uom.id})

                if rec.order_id:
                    vals.update({"order_id": rec.order_id.id})
                rec.order_id.write({"order_line": [(0, 0, vals)]})
                self._cr.commit()

        return {"type": "ir.actions.client", "tag": "reload"}

    @api.model
    @api.onchange("partner_id")
    def _onchange_partner(self):

        self.order_history_line = None
        if self.partner_id:
            limit = self.env.user.company_id.sh_purchase_configuration_limit
            purchase_order_search = self.env["purchase.order"].search(
                [("partner_id", "=", self.partner_id.id),
                 ("state", "=", "purchase")],
                limit=limit, order="date_order desc")

            purchase_ordr_line = []
            if purchase_order_search:
                for record in purchase_order_search:

                    if record.order_line:
                        for rec in record.order_line:

                            purchase_ordr_line.append((0, 0, {
                                "po_id": record.name,
                                "name": rec.id,
                                "product_id": rec.product_id,
                                "price_unit": rec.price_unit,
                                "product_qty": rec.product_qty,
                                "product_uom": rec.product_uom,
                                "price_subtotal": rec.price_subtotal
                            }))

            self.order_history_line = purchase_ordr_line
