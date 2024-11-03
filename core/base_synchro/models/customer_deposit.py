from odoo import api, fields, models, _
from datetime import datetime


class CustomerDepositInherit(models.Model):
    """
    Note:
    To make this object recognized, equip3_accounting_deposit module should be added to the dependency
    """

    _inherit = "customer.deposit"

    base_sync = fields.Boolean("Base Sync", default=False)

    def generate_sequence(self):
        customer_deposits = self.env["customer.deposit"].search(
            [("base_sync", "=", True), ("id", "in", self.ids)]
        )
        for deposit in customer_deposits:
            if deposit.base_sync:
                deposit.name = self.env["ir.sequence"].next_by_code("customer.deposit")
                deposit.base_sync = False

        result = {
            "name": "Customer Deposit Resequence",
            "view_type": "form",
            "view_mode": "tree,form",
            "res_model": "customer.deposit",
            "type": "ir.actions.act_window",
            "domain": [("id", "in", customer_deposits.ids)],
            "target": "current",
        }
        return result

class VendorDepositInherit(models.Model):
    _inherit = "vendor.deposit"

    base_sync = fields.Boolean("Base Sync", default=False)

    def generate_sequence(self):
        vendor_deposits = self.env["vendor.deposit"].search(
            [("base_sync", "=", True), ("id", "in", self.ids)]
        )
        for deposit in vendor_deposits:
            if deposit.base_sync:
                if deposit.is_cash_advance:
                    now = datetime.now()
                    sequence = self.env["ir.sequence"].next_by_code('hr.cash.advance')
                    split_sequence = str(sequence).split('/')
                    sequence_number = f"ADV/{split_sequence[0]}/{now.month}/{now.day}/{split_sequence[1]}"
                else:
                    sequence_number = self.env["ir.sequence"].next_by_code('vendor.deposit')

                deposit.name = sequence_number
                deposit.base_sync = False

        result = {
            "name": "Vendor Deposit Resequence",
            "view_type": "form",
            "view_mode": "tree,form",
            "res_model": "vendor.deposit",
            "type": "ir.actions.act_window",
            "domain": [("id", "in", vendor_deposits.ids)],
            "target": "current",
        }
        return result

