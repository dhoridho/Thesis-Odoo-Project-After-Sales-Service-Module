from odoo import api, fields, models, _


class PurchaseOrderInherit(models.Model):
    _inherit = "purchase.order"

    base_sync = fields.Boolean("Base Sync", default=False)

    def genreate_sequence(self):
        purchase_orders = self.env["purchase.order"].search([
            ("base_sync", "=", True),
            ("id", "in", self.ids)
        ])
        for po in purchase_orders:
            if po.base_sync:
                if not po.dp:
                    if po.is_services_orders:
                        po.name = self.env["ir.sequence"].next_by_code(
                            "purchase.order.seqs.rfq.services"
                        )
                    if po.is_goods_orders:
                        po.name = self.env["ir.sequence"].next_by_code(
                            "purchase.order.seqs.rfq.goods"
                        )
                    else:
                        po.name = self.env["ir.sequence"].next_by_code(
                            "purchase.order.seqs.rfq"
                        )
                else:
                    if po.is_services_orders:
                        po.name = self.env["ir.sequence"].next_by_code(
                            "direct.purchase.sequence.dp.new.services"
                        )
                    if po.is_goods_orders:
                        po.name = self.env["ir.sequence"].next_by_code(
                            "direct.purchase.sequence.dp.new.goods"
                        )
                    else:
                        po.name = self.env["ir.sequence"].next_by_code(
                            "direct.purchase.sequence.dp.new."
                        )
                po.base_sync = False

        result = {
            "name": "Purchase Order Resequence",
            "view_type": "form",
            "view_mode": "tree,form",
            "res_model": "purchase.order",
            "type": "ir.actions.act_window",
            "domain": [("id", "in", purchase_orders.ids)],
            "target": "current",
        }
        return result
