from odoo import api, fields, models, _


class InvoiceRecurring(models.Model):
    _inherit = "invoice.recurring"

    base_sync = fields.Boolean("Base Sync", default=False)

    def generate_sequence(self):
        recurring_invoices = self.env["invoice.recurring"].search(
            [("base_sync", "=", True), ("id", "in", self.ids)]
        )
        name = "Invoice Recurring"
        
        for recurring in recurring_invoices:
            if recurring.base_sync:
                if recurring.type == "in_invoice":
                    name = "Recurring Bill"
                    sequence_code = "recurring.out.invoice.seq"
                else:
                    name = "Recurring Invoice"
                    sequence_code = "recurring.in.invoice.seq"

                recurring.name = self.env["ir.sequence"].next_by_code(sequence_code)
                recurring.base_sync = False

        result = {
            "name": "%s Resequence" % (name),
            "view_type": "form",
            "view_mode": "tree,form",
            "res_model": "invoice.recurring",
            "type": "ir.actions.act_window",
            "domain": [("id", "in", recurring_invoices.ids)],
            "target": "current",
        }

        return result
