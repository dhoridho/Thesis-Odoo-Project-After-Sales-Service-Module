from odoo import models, fields


class User(models.Model):
    _inherit = ["res.users"]

    break_state = fields.Selection(related="employee_id.break_state")
    last_start_break = fields.Datetime(
        related="employee_id.last_attendance_id.start_break"
    )
    last_end_break = fields.Datetime(related="employee_id.last_attendance_id.end_break")

    def __init__(self, pool, cr):
        """Override of __init__ to add access rights.
        Access rights are disabled by default, but allowed
        on some specific fields defined in self.SELF_{READ/WRITE}ABLE_FIELDS.
        """
        attendance_readable_fields = [
            "hours_last_month",
            "hours_last_month_display",
            "attendance_state",
            "last_check_in",
            "last_check_out",
            "break_state",
            "last_start_break",
            "last_end_break",
        ]
        super(User, self).__init__(pool, cr)
        # duplicate list to avoid modifying the original reference
        type(self).SELF_READABLE_FIELDS = (
            type(self).SELF_READABLE_FIELDS + attendance_readable_fields
        )
