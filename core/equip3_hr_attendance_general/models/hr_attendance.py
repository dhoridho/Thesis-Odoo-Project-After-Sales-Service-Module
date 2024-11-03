from odoo import api, fields, models, _

class HrAttendanceInherit(models.Model):
    _inherit = "hr.attendance"

    start_break = fields.Datetime(string="Start Break")
    end_break = fields.Datetime(string="End Break")