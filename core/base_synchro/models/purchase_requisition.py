from odoo import api, fields, models, _


class PurchaseRequisition(models.Model):
    _inherit = "purchase.requisition"

    base_sync = fields.Boolean("Base Sync", default=False)

    def generate_sequence(self):
        purchase_requisition = self.env["purchase.requisition"].search([
            ("base_sync", "=", True),
            ("id", "in", self.ids)
        ])
        for pr in purchase_requisition:
            if pr.base_sync:
                if pr.is_rental_orders:
                    pr.name = self.env['ir.sequence'].next_by_code('purchase.requisition.blanket.order.new.r')
                elif pr.is_goods_orders:
                    pr.name = self.env['ir.sequence'].next_by_code('purchase.requisition.blanket.order.new.g')
                elif pr.is_services_orders:
                    pr.name = self.env['ir.sequence'].next_by_code('purchase.requisition.blanket.order.new.s')
                elif pr.is_assets_orders:
                    pr.name = self.env['ir.sequence'].next_by_code('purchase.requisition.blanket.order.new.a')
                else:
                    pr.name = self.env["ir.sequence"].next_by_code("purchase.requisition.blanket.order.new")
                pr.base_sync = False

        result = {
            "name": "Purchase Requisition Resequence",
            "view_type": "form",
            "view_mode": "tree,form",
            "res_model": "purchase.requisition",
            "type": "ir.actions.act_window",
            "domain": [("id", "in", purchase_requisition.ids)],
            "target": "current",
        }
        return result
