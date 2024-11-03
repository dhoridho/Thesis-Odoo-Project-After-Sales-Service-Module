from odoo import fields, models


class HrLeaveSG(models.Model):
    _inherit = "hr.leave"

    holiday_status_id = fields.Many2one(
        comodel_name="hr.leave.type", string="Leave Type"
    )


class HrLeaveAllocationSG(models.Model):
    _inherit = "hr.leave.allocation"

    holiday_status_id = fields.Many2one(
        comodel_name="hr.leave.type", string="Leave Type"
    )