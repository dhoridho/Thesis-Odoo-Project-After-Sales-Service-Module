from odoo import api, fields, models, _

class HrExpenseSheetInherit(models.Model):
    _inherit = "hr.expense.sheet"

    base_sync = fields.Boolean("Base Sync", default=False)

    def generate_sequence(self):
        expenses = self.env["hr.expense.sheet"].search(
            [("base_sync", "=", True), ("id", "in", self.ids)]
        )
        for expense in expenses:
            if expense.base_sync:
                expense.seq_name = self.env["ir.sequence"].next_by_code("hr.expense.sheet")
                expense.base_sync = False

        result = {
            "name": "HR Expense Resequence",
            "view_type": "form",
            "view_mode": "tree,form",
            "res_model": "hr.expense.sheet",
            "type": "ir.actions.act_window",
            "domain": [("id", "in", expenses.ids)],
            "target": "current",
        }
        return result