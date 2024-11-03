from odoo import api, fields, models, _


class PurchaseRequest(models.Model):
    _inherit = "purchase.request"

    base_sync = fields.Boolean("Base Sync", default=False)

    def generate_sequence(self):
        purchase_requests = self.env["purchase.request"].search([
            ("base_sync", "=", True),
            ("id", "in", self.ids)
        ])
        for pr in purchase_requests:
            if pr.base_sync:
                if self.env.context.get('default_is_rental_orders') or pr.is_rental_orders:
                    pr.name = self.env['ir.sequence'].next_by_code('purchase.request.seqs.r')
                elif self.env.context.get('assets_orders') or pr.is_assets_orders:
                    pr.name = self.env['ir.sequence'].next_by_code('purchase.request.seqs.a')
                else:
                    pr.name = self.env["ir.sequence"].next_by_code("purchase.req.seqs")
                pr.base_sync = False

        result = {
            "name": "Purchase Request Resequence",
            "view_type": "form",
            "view_mode": "tree,form",
            "res_model": "purchase.request",
            "type": "ir.actions.act_window",
            "domain": [("id", "in", purchase_requests.ids)],
            "target": "current",
        }
        return result
