from odoo import models, fields, _


class Equip3MakePurchaseWizard(models.TransientModel):
    _name = "make.purchase.order.wizard"
    _description = "Purchase Order Wizard"

    partner_id = fields.Many2one("res.partner", _("Vendor"))
    purchase_type = fields.Selection(
        [("draft", _("RFQ")), ("purchase", _("Purchase Order"))],
        default="draft",
        string=_("Type"),
    )

    def action_make_purchase_order(self):
        self.ensure_one()
        if self._context.get("active_model") != "sale.service":
            return
        saleService = self.env["sale.service"].browse(self._context.get("active_ids"))
        picking_type_id = saleService.location_id.warehouse_id.in_type_id.id
        poVals = {
            "partner_id": saleService.partner_id.id,
            "user_id": self.env.user.id,
            "origin": saleService.name,
            "date_order": fields.Datetime.now(),
            "date_planned": fields.Datetime.now(),
            "picking_type_id": picking_type_id,
            "destination_warehouse_id": saleService.location_id.warehouse_id.id,
            "branch_id": saleService.branch_id.id,
        }
        line_vals = []
        for l in saleService.line_material_ids:
            line_vals.append(
                (
                    0,
                    0,
                    {
                        "product_id": l.product_id.id,
                        "name": l.product_id.name,
                        "status": "draft",
                        "product_uom": l.product_uom.id,
                        "product_qty": l.product_qty,
                        "price_unit": l.price_unit,
                        "picking_type_id": picking_type_id,
                        "destination_warehouse_id": saleService.location_id.warehouse_id.id,
                        # 'analytic_tag_ids': order_line.account_tag_ids.ids,
                        "taxes_id": [(6, 0, l.tax_ids.ids)],
                        "is_goods_orders": True,
                        "discount_method": (
                            "fix" if l.disc_method == "fixed" else l.disc_method
                        ),
                        "discount_amount": l.disc_percentage,
                        "discounted_value": l.disc_amount,
                    },
                )
            )
        poVals["order_line"] = line_vals
        created_po = self.env["purchase.order"].create(poVals)
        if self.purchase_type == "purchase":
            created_po.button_confirm()
        saleService.purchase_ids |= created_po
        return {
            "name": _("Purchase Orders/RFQ's"),
            "type": "ir.actions.act_window",
            "res_model": "purchase.order",
            "view_type": "form",
            "view_mode": "tree,form",
            "domain": [("id", "in", saleService.purchase_ids.ids)],
            "target": "current",
        }
