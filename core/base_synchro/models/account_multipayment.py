from odoo import api, fields, models, _


class AccountMultiPaymentInherit(models.Model):
    _inherit = "account.multipayment"

    base_sync = fields.Boolean("Base Sync", default=False)

    def generate_sequence(self):
        account_multipayments = self.env["account.multipayment"].search(
            [("base_sync", "=", True), ("id", "in", self.ids)]
        )
        name = "Account Multipayment"
        for payment in account_multipayments:
            if payment.base_sync:
                if payment.partner_type == "customer":
                    if payment.payment_type == "payment":
                        name = "Customer Multi Receipt"
                        sequence_code = "customer.account.multipayment"
                    else:
                        name = "Receipt Giro"
                        sequence_code = "receipt.giro"
                else:
                    if payment.payment_type == "giro":
                        name = "Payment Giro"
                        sequence_code = "payment.giro"
                    else:
                        name = "Vendor Multi Payment"
                        sequence_code = "vendor.account.multipayment"
                payment.name = self.env["ir.sequence"].next_by_code(sequence_code)
                payment.base_sync = False

        result = {
            "name": "%s Resequence" % (name),
            "view_type": "form",
            "view_mode": "tree,form",
            "res_model": "account.multipayment",
            "type": "ir.actions.act_window",
            "domain": [("id", "in", account_multipayments.ids)],
            "target": "current",
        }
        return result
