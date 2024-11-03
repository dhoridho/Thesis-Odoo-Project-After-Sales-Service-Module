from odoo import models, fields, api


class StockMoveInherit(models.Model):
    _inherit = "stock.move"

    lot_id = fields.Many2one("stock.production.lot", string="Serial Number")
    partner_shipping_id = fields.Many2one("res.partner", string="Delivery Address")
    location_dest_id = fields.Many2one("stock.location", check_company=False)
    picking_id = fields.Many2one('stock.picking', check_company=False)

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context

        if context.get("allowed_company_ids"):
            domain += [("company_id", "in", context.get("allowed_company_ids"))]

        if context.get("allowed_branch_ids"):
            domain += [
                "|",
                ("branch_id", "in", context.get("allowed_branch_ids")),
                ("branch_id", "=", False),
            ]

        result = super(StockMoveInherit, self).search_read(
            domain=domain, fields=fields, offset=offset, limit=limit, order=order
        )

        return result

    @api.model
    def read_group(
        self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True
    ):
        domain = domain or []
        context = self.env.context

        if context.get("allowed_company_ids"):
            domain.extend([("company_id", "in", self.env.companies.ids)])

        if context.get("allowed_branch_ids"):
            domain.extend(
                [
                    "|",
                    ("branch_id", "in", context.get("allowed_branch_ids")),
                    ("branch_id", "=", False),
                ]
            )
        return super(StockMoveInherit, self).read_group(
            domain,
            fields,
            groupby,
            offset=offset,
            limit=limit,
            orderby=orderby,
            lazy=lazy,
        )


class StockRuleInherit(models.Model):
    """A rule describe what a procurement should do; produce, buy, move, ..."""

    _inherit = "stock.rule"

    lot_id = fields.Many2one("stock.production.lot", string="Serial Number")
    rental_line_id = fields.Many2one("rental.order.line", string="Rental Line")
    for_rental_move = fields.Boolean("For Rental Move")
    partner_shipping_id = fields.Many2one("res.partner", string="Delivery Address")
    branch_id = fields.Many2one("res.branch", string="Branch")

    def _get_stock_move_values(
        self,
        product_id,
        product_qty,
        product_uom,
        location_id,
        name,
        origin,
        company_id,
        values,
    ):
        res = super(StockRuleInherit, self)._get_stock_move_values(
            product_id,
            product_qty,
            product_uom,
            location_id,
            name,
            origin,
            company_id,
            values,
        )
        if "rental_line_id" not in res and "rental_line_id" in values:
            res["rental_line_id"] = values["rental_line_id"]
        if "for_rental_move" not in res and "for_rental_move" in values:
            res["for_rental_move"] = True
        if "lot_id" not in res and "lot_id" in values:
            res["lot_id"] = values["lot_id"]
        if "partner_shipping_id" not in res and "partner_shipping_id" in values:
            res["partner_shipping_id"] = values["partner_shipping_id"]
        if "branch_id" not in res and "branch_id" in values:
            res["branch_id"] = values["branch_id"]
        return res


class StockMoveLineInherit(models.Model):
    _inherit = "stock.move.line"

    location_dest_id = fields.Many2one("stock.location", check_company=False)
    picking_id = fields.Many2one('stock.picking', check_company=False)

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context

        if context.get("allowed_company_ids"):
            domain += [("company_id", "in", context.get("allowed_company_ids"))]

        result = super(StockMoveLineInherit, self).search_read(
            domain=domain, fields=fields, offset=offset, limit=limit, order=order
        )

        return result

    @api.model
    def read_group(
        self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True
    ):
        domain = domain or []
        context = self.env.context

        if context.get("allowed_company_ids"):
            domain.extend([("company_id", "in", self.env.companies.ids)])

        return super(StockMoveLineInherit, self).read_group(
            domain,
            fields,
            groupby,
            offset=offset,
            limit=limit,
            orderby=orderby,
            lazy=lazy,
        )
