from odoo import api, fields, models, _


class DevRmaRma(models.Model):
    _inherit = 'dev.rma.rma'

    base_sync = fields.Boolean("Base Sync", default=False)

    def generate_sequence(self):
        dev_rma = self.env["dev.rma.rma"].search(
            [("base_sync", "=", True), ("id", "in", self.ids)]
        )
        for rma in dev_rma:
            if rma.base_sync:
                rma.name = self.env["ir.sequence"].next_by_code("dev.rma.rma")
                rma.base_sync = False

        result = {
            "name": "RMA Resequence",
            "view_type": "form",
            "view_mode": "tree,form",
            "res_model": "dev.rma.rma",
            "type": "ir.actions.act_window",
            "domain": [("id", "in", dev_rma.ids)],
            "target": "current",
        }
        return result