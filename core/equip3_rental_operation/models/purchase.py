from odoo import models, fields, api


class PurchaseOrderInherit(models.Model):
    _inherit = "purchase.order"

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context

        if context.get("allowed_branch_ids"):
            domain += [
                "|",
                ("branch_id", "in", context.get("allowed_branch_ids")),
                ("branch_id", "=", False),
            ]

        result = super(PurchaseOrderInherit, self).search_read(
            domain=domain, fields=fields, offset=offset, limit=limit, order=order
        )

        return result

    @api.model
    def read_group(
        self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True
    ):
        domain = domain or []
        context = self.env.context

        if context.get("allowed_branch_ids"):
            domain.extend(
                [
                    "|",
                    ("branch_id", "in", context.get("allowed_branch_ids")),
                    ("branch_id", "=", False),
                ]
            )
        return super(PurchaseOrderInherit, self).read_group(
            domain,
            fields,
            groupby,
            offset=offset,
            limit=limit,
            orderby=orderby,
            lazy=lazy,
        )


class PurchaseTeamAnalysisInherit(models.Model):
    _inherit = "purchase.team.analysis"

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context

        if context.get("allowed_branch_ids"):
            domain += [
                "|",
                ("branch_id", "in", context.get("allowed_branch_ids")),
                ("branch_id", "=", False),
            ]

        result = super(PurchaseTeamAnalysisInherit, self).search_read(
            domain=domain, fields=fields, offset=offset, limit=limit, order=order
        )

        return result

    @api.model
    def read_group(
        self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True
    ):
        domain = domain or []
        context = self.env.context

        if context.get("allowed_branch_ids"):
            domain.extend(
                [
                    "|",
                    ("branch_id", "in", context.get("allowed_branch_ids")),
                    ("branch_id", "=", False),
                ]
            )
        return super(PurchaseTeamAnalysisInherit, self).read_group(
            domain,
            fields,
            groupby,
            offset=offset,
            limit=limit,
            orderby=orderby,
            lazy=lazy,
        )


class PurchaseOrderLineInherit(models.Model):
    _inherit = "purchase.order.line"

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

        result = super(PurchaseOrderLineInherit, self).search_read(
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
        return super(PurchaseOrderLineInherit, self).read_group(
            domain,
            fields,
            groupby,
            offset=offset,
            limit=limit,
            orderby=orderby,
            lazy=lazy,
        )
