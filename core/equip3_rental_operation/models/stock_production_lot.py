# -*- coding: utf-8 -*-

from odoo import _, api, fields, models


class StockProductionLot(models.Model):
    _inherit = 'stock.production.lot'

    is_return_of_asset_created = fields.Boolean('Asset Control Created', default=False)

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context

        if context.get("allowed_company_ids"):
            domain += [("company_id", "in", context.get("allowed_company_ids"))]

        if context.get("allowed_branch_ids"):
            domain += [
                "|",
                ("product_id.branch_id", "in", context.get("allowed_branch_ids")),
                ("product_id.branch_id", "=", False),
            ]

        result = super(StockProductionLot, self).search_read(
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
                    ("product_id.branch_id", "in", context.get("allowed_branch_ids")),
                    ("product_id.branch_id", "=", False),
                ]
            )
        return super(StockProductionLot, self).read_group(
            domain,
            fields,
            groupby,
            offset=offset,
            limit=limit,
            orderby=orderby,
            lazy=lazy,
        )
