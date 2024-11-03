from odoo import api, fields, models, _


class HrPayslipRunInheirt(models.Model):
    _inherit = "hr.payslip.run"

    base_sync = fields.Boolean("Base Sync", default=False)


class HrPayslipInheirt(models.Model):
    _inherit = "hr.payslip"

    base_sync = fields.Boolean("Base Sync", default=False)

    def generate_sequence(self):
        paylips = self.env["hr.payslip"].search(
            [("base_sync", "=", True), ("id", "in", self.ids)]
        )
        for payslip in paylips:
            if payslip.base_sync:
                payslip.number = self.env["ir.sequence"].next_by_code("salary.slip")
                payslip.base_sync = False

        result = {
            "name": "Payroll Resequence",
            "view_type": "form",
            "view_mode": "tree,form",
            "res_model": "hr.payslip",
            "type": "ir.actions.act_window",
            "domain": [("id", "in", paylips.ids)],
            "target": "current",
        }
        return result

