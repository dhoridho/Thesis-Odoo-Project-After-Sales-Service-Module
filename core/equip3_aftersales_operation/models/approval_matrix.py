from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class Equip3SaleServiceApprovalMatrix(models.Model):
    _name = "sale.service.approval.matrix"
    _description = "Sale Service Approval Matrix"

    name = fields.Char("Name")
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda self: self.env.user.company_id.id,
        required=True,
    )
    branch_id = fields.Many2one(
        comodel_name="res.branch",
        string="Branch",
        default=lambda self: self.env.user.branch_id.id,
        required=True,
    )
    approval_matrix_ids = fields.One2many(
        "sale.service.approval.matrix.line",
        "sale_service_approval_matrix_id",
        string="Approver Name",
    )

    def _reset_sequence(self):
        for rec in self:
            current_sequence = 1
            for line in rec.approval_matrix_ids:
                line.sequence = current_sequence
                current_sequence += 1

    def copy(self, default=None):
        res = super(
            Equip3SaleServiceApprovalMatrix, self.with_context(keep_line_sequence=True)
        ).copy(default)
        return res


class Equip3SaleServiceApprovalMatrixLine(models.Model):
    _name = "sale.service.approval.matrix.line"
    _description = "Sale Service Approval Matrix Line"

    @api.model
    def default_get(self, fields):
        res = super(Equip3SaleServiceApprovalMatrixLine, self).default_get(fields)
        if self._context:
            context_keys = self._context.keys()
            next_sequence = 1
            if "approval_matrix_ids" in context_keys:
                if len(self._context.get("approval_matrix_ids")) > 0:
                    next_sequence = len(self._context.get("approval_matrix_ids")) + 1
            res.update({"sequence": next_sequence})
        return res

    sequence = fields.Integer(string="Sequence")
    sequence2 = fields.Integer(
        string="No.", related="sequence", readonly=True, store=True, tracking=True
    )
    user_ids = fields.Many2many(comodel_name="res.users", string="User", required=True)
    minimum_approver = fields.Integer(
        string="Minimum Approver", default=1, required=True
    )
    sale_service_approval_matrix_id = fields.Many2one(
        "sale.service.approval.matrix", string="Material Approval Matrix"
    )
    approved_users = fields.Many2many(
        "res.users", "approved_users_course_rel", "class_id", "user_ids", string="Users"
    )
    last_approved = fields.Many2one("res.users", string="Users")
    sale_service_id = fields.Many2one("sale.service", string="Sale Service")
    state_char = fields.Text(string="Approval Status")
    feedback = fields.Text("Feedback")
    time_stamp = fields.Datetime(string="TimeStamp")
    last_approved = fields.Many2one("res.users", string="Users")
    approved = fields.Boolean("Approved")
    approver_state = fields.Selection(
        [
            ("draft", "Draft"),
            ("pending", "Pending"),
            ("approved", "Approved"),
            ("refuse", "Refused"),
        ],
        default="",
        string="State",
    )

    def unlink(self):
        approval = self.sale_service_approval_matrix_id
        res = super(Equip3SaleServiceApprovalMatrixLine, self).unlink()
        approval._reset_sequence()
        return res

    @api.model
    def create(self, vals):
        res = super(Equip3SaleServiceApprovalMatrixLine, self).create(vals)
        if not self.env.context.get("keep_line_sequence", False):
            res.sale_service_approval_matrix_id._reset_sequence()
        return res
