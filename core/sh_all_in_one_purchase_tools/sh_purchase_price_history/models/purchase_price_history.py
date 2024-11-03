# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    item_limit_purchase = fields.Integer("Item Limit (Purchase)", default="30")
    record_based_on_purchase = fields.Selection([
        ("purchase", "Order Confirm"),
        ("done", "Done (Locked)"),
        ("both", "Both")],
        string="Price History Based On (Purchase)",
        default="purchase"
    )


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    item_limit_purchase = fields.Integer(
        related="company_id.item_limit_purchase",
        string="Item Limit (Purchase)",
        readonly=False
    )
    record_based_on_purchase = fields.Selection(
        readonly=False,
        string="Price History Based On (Purchase)",
        related="company_id.record_based_on_purchase"
    )

    group_enable_purchase_price_history = fields.Boolean(
        "Enable Purchase Price History", implied_group='sh_all_in_one_purchase_tools.group_enable_purchase_price_history')
    
class PurchasePriceHistory(models.Model):
    _name = "purchase.price.history"
    _description = "Purchase Price History"

    name = fields.Many2one("purchase.order.line", string="Purchase Order Line")

    partner_id = fields.Many2one(
        "res.partner",
        related="name.partner_id",
        string="Supplier"
    )
    variant_id = fields.Many2one(
        "product.product",
        related="name.product_id",
        string="Product"
    )
    purchase_order_id = fields.Many2one(
        "purchase.order",
        related="name.order_id",
        string="Purchase Order"
    )
    order_date = fields.Datetime(
        "Order Date",
        related="name.order_id.date_order"
    )
    quantity = fields.Float("Quantity", related="name.product_qty")
    purchase_price = fields.Float("Purchase Price", related="name.price_unit")
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency Id",
        related="name.currency_id"
    )
    total_price = fields.Monetary(
        string="Total",
        related="name.price_subtotal"
    )


class ProductTemplate(models.Model):
    _inherit = "product.template"

    purchase_price_history_line_ids = fields.Many2many(
        "purchase.price.history",
        string="Price History Lines",
        compute="_compute_get_product_supplier_price"
    )

    def _compute_get_product_supplier_price(self):
        if self and self.id:
            if self.env.user.company_id:

                cond = self.env.user.company_id.record_based_on_purchase
                itm_limit = self.env.user.company_id.item_limit_purchase
                purchase_price_line = []

                if cond == "both":
                    purchase_line_obj = self.env["purchase.order.line"].sudo().search(
                        [("product_id", "in", self.product_variant_ids.ids),
                         ("state", "in", ("purchase", "done"))],
                        limit=itm_limit,
                        order="create_date desc"
                    )
                else:
                    purchase_line_obj = self.env["purchase.order.line"].sudo().search(
                        [("product_id", "in", self.product_variant_ids.ids),
                         ("state", "=", str(cond))],
                        limit=itm_limit,
                        order="create_date desc"
                    )

                if purchase_line_obj:
                    for record in purchase_line_obj:

                        vals = {}
                        vals.update({"name": record.id})

                        if record.partner_id:
                            vals.update({"partner_id": record.partner_id.id})

                        if record.product_id:
                            vals.update({"variant_id": record.product_id.id})
                        if record.order_id:
                            vals.update(
                                {"purchase_order_id": record.order_id.id})

                        if record.order_id.date_order:
                            vals.update(
                                {"order_date": record.order_id.date_order})
                        if record.product_qty:
                            vals.update({"quantity": record.product_qty})
                        if record.price_unit:
                            vals.update({"purchase_price": record.price_unit})
                        if record.price_subtotal:
                            vals.update({"total_price": record.price_subtotal})

                        if vals:
                            purchase_price_obj = self.env["purchase.price.history"].create(
                                vals)

                            if purchase_price_obj:
                                purchase_price_line.append(
                                    purchase_price_obj.id)

                self.purchase_price_history_line_ids = purchase_price_line


class ProductProduct(models.Model):
    _inherit = "product.product"

    purchase_price_history_line_ids = fields.Many2many(
        "purchase.price.history",
        string="Price History Lines",
        compute="_compute_get_product_supplier_price"
    )

    def _compute_get_product_supplier_price(self):
        if self and self.id:
            if self.env.user.company_id:

                cond = self.env.user.company_id.record_based_on_purchase
                itm_limit = self.env.user.company_id.item_limit_purchase
                purchase_price_line = []

                if cond == "both":
                    purchase_line_obj = self.env["purchase.order.line"].sudo().search(
                        [("product_id", "in", [self.id]),
                         ("state", "in", ("purchase", "done"))],
                        limit=itm_limit,
                        order="create_date desc"
                    )
                else:
                    purchase_line_obj = self.env["purchase.order.line"].sudo().search(
                        [("product_id", "in", [self.id]),
                         ("state", "=", str(cond))],
                        limit=itm_limit,
                        order="create_date desc"
                    )

                if purchase_line_obj:
                    for record in purchase_line_obj:

                        vals = {}
                        vals.update({"name": record.id})

                        if record.partner_id:
                            vals.update({"partner_id": record.partner_id.id})

                        if record.product_id:
                            vals.update({"variant_id": record.product_id.id})
                        if record.order_id:
                            vals.update(
                                {"purchase_order_id": record.order_id.id})

                        if record.order_id.date_order:
                            vals.update(
                                {"order_date": record.order_id.date_order})
                        if record.product_qty:
                            vals.update({"quantity": record.product_qty})
                        if record.price_unit:
                            vals.update({"purchase_price": record.price_unit})
                        if record.price_subtotal:
                            vals.update({"total_price": record.price_subtotal})

                        if vals:
                            purchase_price_obj = self.env["purchase.price.history"].create(
                                vals)

                            if purchase_price_obj:
                                purchase_price_line.append(
                                    purchase_price_obj.id)

                self.purchase_price_history_line_ids = purchase_price_line
