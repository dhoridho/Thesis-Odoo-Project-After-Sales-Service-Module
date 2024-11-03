from odoo import models, api, fields, _
from odoo.exceptions import ValidationError


class saleOrderLine(models.Model):
    _inherit = "sale.order.line"

    toservice = fields.Boolean("Service")


class saleOrder(models.Model):
    _inherit = "sale.order"

    sale_service_id = fields.Many2one("sale.service", _("Related Service"))

    def _prepare_sale_service(self):
        """
        -nama customer
        -nama product
        -create on
        -source document = nomor sales order
        -product
        -description
        -quantity
        -unit of measure
        """
        self.ensure_one()
        return {
            "partner_id": self.partner_id.id,
            "reference": self.name,
            "line_ids": [
                (
                    0,
                    0,
                    {
                        "product_id": l.product_id.id,
                        "name": l.name,
                        "product_qty": l.product_uom_qty,
                        "product_uom": l.product_uom.id,
                        "chargable": False,
                        "price_unit": 0.0,
                    },
                )
                for l in self.order_line.filtered(lambda l: l.toservice)
            ],
        }

    def action_confirm(self):
        res = super(saleOrder, self).action_confirm()
        for rec in self:
            if not any([l.toservice for l in rec.order_line]):
                continue
            rec.sale_service_id = self.env["sale.service"].create(
                rec._prepare_sale_service()
            )

        return res
