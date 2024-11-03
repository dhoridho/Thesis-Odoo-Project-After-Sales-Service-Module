from odoo import api, fields, models, _


class AccountInternalTransferInherit(models.Model):
    _inherit = "account.internal.transfer"

    base_sync = fields.Boolean("Base Sync", default=False)

    def generate_sequence(self):
        internal_transfers = self.env["account.internal.transfer"].search(
            [("base_sync", "=", True), ("id", "in", self.ids)]
        )
        for transfer in internal_transfers:
            if transfer.base_sync:
                transfer.name = self.env["ir.sequence"].next_by_code("account.internal.transfer")
                transfer.base_sync = False

        result = {
            "name": "Account Internal Transfer Resequence",
            "view_type": "form",
            "view_mode": "tree,form",
            "res_model": "account.internal.transfer",
            "type": "ir.actions.act_window",
            "domain": [("id", "in", internal_transfers.ids)],
            "target": "current",
        }
        return result