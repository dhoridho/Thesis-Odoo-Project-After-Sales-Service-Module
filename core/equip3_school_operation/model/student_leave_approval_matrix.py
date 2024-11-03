from odoo import _, api, fields, models


class Equip3StudentLeaveApprovalMatrix(models.Model):
    _name = "student.leave.approval.matrix"
    _description = "Student Approval Matrix"

    sequence = fields.Integer("Sequence")
    user_ids = fields.Many2many(
        "res.users",
        "student_leave_user_rel",
        "matrix_id",
        "user_id",
        ondelete="cascade",
        help="Enter related users of the student",
        domain=lambda self: [
            ("groups_id", "!=", self.env.ref("school.group_school_student").id),
            ("groups_id", "!=", self.env.ref("school.group_school_parent").id),
            ("groups_id", "=", self.env.ref("base.group_user").id),
        ],
    )
    student_leave_id = fields.Many2one(
        "studentleave.request", string="Student Leave ID"
    )
    minimum_approver = fields.Integer(default=1)
    approved_user_ids = fields.Many2many(
        "res.users",
        "student_leave_approved_user_rel",
        "matrix_id",
        "user_id",
        string="Approved Users",
        help="Users who have approved the leave request",
    )
    approval_status = fields.Text(string="Approval Status")
    approved_time = fields.Text(string="Approved Time")
    feedback = fields.Text(string="Feedback")
    total_reject_users = fields.Integer("Total Reject Users")
    state = fields.Selection(
        selection=[
            ("waiting", "Waiting"),
            ("confirmed", "Confirmed"),
            ("rejected", "Rejected")
        ],
        string="Status",
        default="waiting"
    )

    @api.model
    def default_get(self, fields):
        res = super(Equip3StudentLeaveApprovalMatrix, self).default_get(fields)
        if self.env.context:
            context_keys = self.env.context.keys()
            next_sequence = 1
            if "approval_matrix_ids" in context_keys:
                if len(self.env.context.get("approval_matrix_ids")) > 0:
                    next_sequence = (
                        len(self.env.context.get("approval_matrix_ids")) + 1
                    )
        res.update({"sequence": next_sequence})

        return res

    def unlink(self):
        rental = self.student_leave_id
        res = super(Equip3StudentLeaveApprovalMatrix, self).unlink()
        rental._reset_sequence()

        return res

    @api.model
    def create(self, vals):
        res = super(Equip3StudentLeaveApprovalMatrix, self).create(vals)
        if not self.env.context.get("keep_line_sequence", False):
            res.student_leave_id._reset_sequence()

        return res


