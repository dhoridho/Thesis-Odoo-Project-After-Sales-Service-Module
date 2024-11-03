from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class HrShiftVariation(models.Model):
    _name = "hr.shift.variation"
    _description = "HR Shift Variations"

    name = fields.Char("Shift Name", required=True)
    shift_code = fields.Char("Shift Code")
    day_type = fields.Selection(
        [("work_day", "Work Day"), ("day_off", "Day Off")],
        string="Day Type",
        default="work_day",
    )
    work_from = fields.Float("Work From", default=0)
    work_to = fields.Float("Work To", default=0)
    tolerance_for_late = fields.Float("Tolerance for Late", default=0)
    break_from = fields.Float("Allowed Start Break", default=0)
    break_to = fields.Float("Allowed End Break", default=0)
    minimum_hours = fields.Float(string="Minimum Hours", default=0)
    maximum_break = fields.Float(string="Maximum Break")
