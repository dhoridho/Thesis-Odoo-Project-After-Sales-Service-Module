from odoo import api, fields, models, _


class InternalTransfer(models.Model):
    _inherit = 'internal.transfer'

    base_sync = fields.Boolean("Base Sync", default=False)

    def generate_sequence(self):
        internal_transfer = self.env["internal.transfer"].search(
            [("base_sync", "=", True), ("id", "in", self.ids)]
        )
        for itr in internal_transfer:
            if itr.base_sync:
                itr.name = self.env["ir.sequence"].next_by_code("internal.transfer")
                itr.base_sync = False

        result = {
            "name": "ITR Resequence",
            "view_type": "form",
            "view_mode": "tree,form",
            "res_model": "internal.transfer",
            "type": "ir.actions.act_window",
            "domain": [("id", "in", internal_transfer.ids)],
            "target": "current",
        }
        return result