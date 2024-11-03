from odoo import models, fields, _


class CalendarWorkingTimes(models.Model):
    _name = "calendar.working.times"
    _description = "Calendar Working Times"

    name = fields.Char(related="shifting_id.name", string="Name")
    resource_calendar_id = fields.Many2one("resource.calendar", ondelete="cascade")
    shifting_id = fields.Many2one("hr.shift.variation", string="Variation Shifting")
    working_date = fields.Date("Working Date")
    work_from = fields.Float(related="shifting_id.work_from", string="Work From")
    work_to = fields.Float(related="shifting_id.work_to", string="Work To")
    break_from = fields.Float(related="shifting_id.break_from", string="Break From")
    break_to = fields.Float(related="shifting_id.break_to", string="Break To")
    tolerance_for_late = fields.Float(
        related="shifting_id.tolerance_for_late", string="Tolerance For Late"
    )
    minimum_hours = fields.Float(
        related="shifting_id.minimum_hours", string="Minimum Hours"
    )
    maximum_break = fields.Float(
        related="shifting_id.maximum_break", string="Maximum Break"
    )
