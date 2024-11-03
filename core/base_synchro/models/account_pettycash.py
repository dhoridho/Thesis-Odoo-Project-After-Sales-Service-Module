from odoo import api, fields, models, _


class AccountPettyCashInherit(models.Model):
    _inherit = "account.pettycash"

    base_sync = fields.Boolean("Base Sync", default=False)

    def generate_sequence(self):
        pettycashes = self.env["account.pettycash"].search(
            [("base_sync", "=", True), ("id", "in", self.ids)]
        )
        for pettycash in pettycashes:
            if pettycash.base_sync:
                pettycash.number = self.env["ir.sequence"].next_by_code(
                    "account.pettycash.sequence"
                )
                pettycash.base_sync = False

        result = {
            "name": "Account Pettycash Resequence",
            "view_type": "form",
            "view_mode": "tree,form",
            "res_model": "account.pettycash",
            "type": "ir.actions.act_window",
            "domain": [("id", "in", pettycashes.ids)],
            "target": "current",
        }
        return result


class AccountPettyCashVoucherInherit(models.Model):
    _inherit = "account.pettycash.voucher.wizard"

    base_sync = fields.Boolean("Base Sync", default=False)

    def generate_sequence(self):
        pettycash_vouchers = self.env["account.pettycash.voucher.wizard"].search(
            [("base_sync", "=", True), ("id", "in", self.ids)]
        )
        for pettycash in pettycash_vouchers:
            if pettycash.base_sync:
                if pettycash.date:
                    seq_date = fields.Datetime.context_timestamp(self, fields.Datetime.to_datetime(pettycash.date))
                    pettycash.name = self.env["ir.sequence"].next_by_code(
                        'account.pettycash.voucher.wizard.seq', sequence_date=seq_date) or _('New')
                    pettycash.base_sync = False

        result = {
            "name": "Account Pettycash Voucher Resequence",
            "view_type": "form",
            "view_mode": "tree,form",
            "res_model": "account.pettycash.voucher.wizard",
            "type": "ir.actions.act_window",
            "domain": [("id", "in", pettycash_vouchers.ids)],
            "target": "current",
        }
        return result
