from odoo import fields, models


class HrLeaveConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    module_sg_holiday_extended = fields.Boolean(
        "Leave Structure Functionality",
        help="This allows you to create leave structures for employee")
    module_sg_allocate_leave = fields.Boolean(
        "Leave Allocation for Employee",
        help="This allows you to create bulk leave allocation for selected \
        employee's for selected leave types by wizard")
    module_sg_leave_constraints = fields.Boolean(
        "Leave Constraints",
        help="This will helps to add constraints for leave.")
    module_sg_leave_extended = fields.Boolean(
        "Leave Allocation using Interval functionality",
        help="This will help to allocate leave using interval unit \
        functionality")
    module_sg_expire_leave = fields.Boolean(
        "Expire carry forward allocated leave using leave expire scheduler.",
        help="This will help to expire carry forward allocated leave using \
        scheduler.")
