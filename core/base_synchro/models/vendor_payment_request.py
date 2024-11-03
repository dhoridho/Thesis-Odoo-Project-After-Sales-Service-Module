from odoo import api, fields, models, _


class VendorPaymentRequestInherit(models.Model):
    _inherit = "vendor.payment.request"

    base_sync = fields.Boolean("Base Sync", default=False)

    def generate_sequence(self):
        vendor_payment_requests = self.env["vendor.payment.request"].search(
            [("base_sync", "=", True), ("id", "in", self.ids)]
        )
        for vendor in vendor_payment_requests:
            if vendor.base_sync:
                vendor.name = self.env["ir.sequence"].next_by_code("vendor.payment.id.sequence")
                vendor.base_sync = False

        result = {
            "name": "Vendor Payment Request Resequence",
            "view_type": "form",
            "view_mode": "tree,form",
            "res_model": "vendor.payment.request",
            "type": "ir.actions.act_window",
            "domain": [("id", "in", vendor_payment_requests.ids)],
            "target": "current",
        }
        return result