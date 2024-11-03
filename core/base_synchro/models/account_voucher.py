from odoo import api, fields, models, _


class AccountVoucher(models.Model):
    _inherit = "account.voucher"

    base_sync = fields.Boolean("Base Sync", default=False)

    def generate_sequence(self):
        account_vouchers = self.env["account.voucher"].search(
            [("base_sync", "=", True), ("id", "in", self.ids)]
        )
        name = "Account Voucher"

        for voucher in account_vouchers:
            if voucher.base_sync:
                if voucher.voucher_type == "purchase":
                    name = "Other Expense"
                    sequence_code = "seq.account.voucher.oex"
                else:
                    name = "Other Income"
                    sequence_code = "seq.account.voucher.oin"

                voucher.number = self.env["ir.sequence"].next_by_code(sequence_code)
                voucher.base_sync = False

        result = {
            "name": "%s Resequence" % (name),
            "view_type": "form",
            "view_mode": "tree,form",
            "res_model": "account.voucher",
            "type": "ir.actions.act_window",
            "domain": [("id", "in", account_vouchers.ids)],
            "target": "current",
        }

        return result
