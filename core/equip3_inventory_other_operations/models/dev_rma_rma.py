from odoo import models


class DevRmaLine(models.Model):
    _inherit = "dev.rma.line"

    def create_repair_order(self):
        res = super(DevRmaLine, self).create_repair_order()
        is_create_delivery_order = False if self.rma_id.sale_id else True
        res.write({"state": "availability", "is_create_delivery_order": is_create_delivery_order})
        return res