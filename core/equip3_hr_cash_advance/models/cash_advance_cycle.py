from odoo import _, api, fields, models


class HrCashAdvanceCycle(models.Model):
    _name = "hr.cash.advance.cycle"
    _description = "Hr Cash Advance Cycle"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    hr_year_id = fields.Many2one(
        comodel_name="hr.years", string="Hr Year", domain="[('status', '=', 'open')]"
    )
    limit_type = fields.Selection(
        [
            ("monthly", "Monthly"),
            ("yearly", "Yearly"),
        ],
        string="Limit Type",
        copy=False,
        index=True,
        default="monthly",
    )
    cash_advance_cycle_line_ids = fields.One2many(
        comodel_name="hr.cash.advance.cycle.line",
        inverse_name="cash_advance_cycle_id",
        string="Cash Adcance Cycle Line",
    )
    is_confirm = fields.Boolean("Is Confirmed", default=False)

    def name_get(self):
        return [(record.id, "%s" % (record.hr_year_id.name)) for record in self]

    def cash_advance_confirm(self):
        expense_line = []
        for rec in self:
            if rec.hr_year_id:
                rec.is_confirm = True
                rec.cash_advance_cycle_line_ids.unlink()
                for hr_rec_line in rec.hr_year_id.year_ids:
                    expense_line.append(
                        (
                            0,
                            0,
                            {
                                "cash_advance_cycle_id": self.id,
                                "code": hr_rec_line.code,
                                "cycle_start": hr_rec_line.start_period,
                                "cycle_end": hr_rec_line.end_period,
                            },
                        )
                    )
                rec.cash_advance_cycle_line_ids = expense_line


class HrCashAdvanceCycleLine(models.Model):
    _name = "hr.cash.advance.cycle.line"
    _description = "HR Cash Advance Cycle Line"

    cash_advance_cycle_id = fields.Many2one(
        comodel_name="hr.cash.advance.cycle", string="Cash Advance Cycle"
    )
    code = fields.Char("Cycle Code")
    cycle_start = fields.Date("Cycle Start")
    cycle_end = fields.Date("Cycle End")

    def name_get(self):
        result = []
        for rec in self:
            result.append((rec.id, rec.code))
        return result