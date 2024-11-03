from odoo import _, api, fields, models


class ResourceCalendarAttendanceInherit(models.Model):
    _inherit = "resource.calendar.attendance"

    tolerance_for_late = fields.Float('Tolerance for Late')
    break_from = fields.Float('Break From')
    break_to = fields.Float('Break To')
    minimum_hours = fields.Float('Minimum Hours')
