from odoo import api, fields, models, _


class ReceiptVoucherInherit(models.Model):
    _inherit = "receipt.voucher"

    base_sync = fields.Boolean("Base Sync", default=False)

    def generate_sequence(self):
        receipt_vouchers = self.env["receipt.voucher"].search(
            [("base_sync", "=", True), ("id", "in", self.ids)]
        )
        for voucher in receipt_vouchers:
            if voucher.base_sync:
                voucher.name = self.env["ir.sequence"].next_by_code("receipt.voucher.code")
                voucher.base_sync = False

        result = {
            "name": "Receipt Voucher Resequence",
            "view_type": "form",
            "view_mode": "tree,form",
            "res_model": "receipt.voucher",
            "type": "ir.actions.act_window",
            "domain": [("id", "in", receipt_vouchers.ids)],
            "target": "current",
        }
        return result