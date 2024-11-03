from odoo import fields, models, _, api
from odoo.exceptions import ValidationError


class ResusersInherit(models.Model):
    _inherit = "res.users"

    rental_approval_matrix_id = fields.Many2one(
        comodel_name="rental.approval.matrix", string="Rental Approval Matrix"
    )


class RentalApprovalMatrix(models.Model):
    _name = "rental.approval.matrix"
    _description = "Rental Approval Matrix"

    sequence = fields.Integer(string="No.", readonly=True)
    user_ids = fields.Many2many(
        comodel_name="res.users",
        string="User",
        required=True,
    )
    minimum_approver = fields.Integer(string="Minimum Approver")
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
    approved_user_ids = fields.One2many(
        comodel_name="res.users",
        inverse_name="rental_approval_matrix_id",
        string="Approved User",
    )
    rental_order_id = fields.Many2one(
        comodel_name="rental.order", string="Rental Order"
    )

    @api.model
    def default_get(self, fields):
        res = super(RentalApprovalMatrix, self).default_get(fields)
        if self.env.context:
            context_keys = self.env.context.keys()
            next_sequence = 1
            if "rental_approval_line_ids" in context_keys:
                if len(self.env.context.get("rental_approval_line_ids")) > 0:
                    next_sequence = (
                        len(self.env.context.get("rental_approval_line_ids")) + 1
                    )
        res.update({"sequence": next_sequence})

        return res

    def unlink(self):
        rental = self.rental_order_id
        res = super(RentalApprovalMatrix, self).unlink()
        rental._reset_sequence()

        return res

    @api.model
    def create(self, vals):
        res = super(RentalApprovalMatrix, self).create(vals)
        if not self.env.context.get("keep_line_sequence", False):
            res.rental_order_id._reset_sequence()

        return res


class RentalOrderApprovalMatrix(models.Model):
    _name = "rental.order.approval.matrix"
    _description = "Rental Order Approval Matrix"

    @api.model
    def _default_branch(self):
        default_branch_id = self.env.context.get("default_branch_id", False)
        if default_branch_id:
            return default_branch_id
        return (
            self.env.company_branches[0].id
            if len(self.env.company_branches) == 1
            else False
        )

    @api.model
    def _domain_branch(self):
        return [
            ("id", "in", self.env.branches.ids),
            ("company_id", "=", self.env.company.id),
        ]

    @api.model
    def _default_user_id(self):
        return self.env.user.id

    name = fields.Char(string="Name", required=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        required=True,
        readonly=True,
        default=lambda self: self.env.user.company_id,
    )
    branch_id = fields.Many2one(
        comodel_name="res.branch",
        string="Branch",
        default=_default_branch,
        domain=_domain_branch,
    )
    created_date = fields.Datetime(
        string="Created on", readonly=True, default=fields.Datetime.now
    )
    created_uid = fields.Many2one(
        comodel_name="res.users",
        string="Created by",
        readonly=True,
        default=_default_user_id,
    )
    approval_matrix_line_ids = fields.One2many(
        comodel_name="rental.order.approval.matrix.line",
        inverse_name="approval_matrix_id",
    )

    @api.constrains("branch_id")
    def check_branch(self):
        for record in self:
            is_branch_exist = (
                self.env["rental.order.approval.matrix"]
                .search([("branch_id", "=", record.branch_id.id)])
                .filtered(lambda r: r.id != record.id)
            )
            # raise ValidationError(is_branch_exist)
            if is_branch_exist:
                raise ValidationError(
                    _(
                        "The rental order approval matrix for this branch already exist, "
                        + "please change the branch.\nExisted approval: %s"
                        % record.branch_id.name
                    )
                )

    def _reset_sequence(self):
        for rec in self:
            current_sequence = 1
            for line in rec.approval_matrix_line_ids:
                line.sequence = current_sequence
                current_sequence += 1

    def copy(self, default=None):
        res = super(
            RentalOrderApprovalMatrix, self.with_context(keep_line_sequence=True)
        ).copy(default)

        return res


class RentalOrderApprovalMatrixLine(models.Model):
    _name = "rental.order.approval.matrix.line"
    _description = "Rental Order Approval Matrix Line"

    @api.model
    def default_get(self, fields):
        res = super(RentalOrderApprovalMatrixLine, self).default_get(fields)
        if self.env.context:
            context_keys = self.env.context.keys()
            next_sequence = 1
            if "approval_matrix_line_ids" in context_keys:
                if len(self.env.context.get("approval_matrix_line_ids")) > 0:
                    next_sequence = (
                        len(self.env.context.get("approval_matrix_line_ids")) + 1
                    )
        res.update({"sequence": next_sequence})

        return res

    sequence = fields.Integer(string="No.", readonly=True)
    user_ids = fields.Many2many(comodel_name="res.users", string="User", required=True)
    minimum_approver = fields.Integer(string="Minimum Approver")
    approval_matrix_id = fields.Many2one(
        comodel_name="rental.order.approval.matrix", string="Approval Matrix"
    )

    @api.constrains("minimum_approver")
    def check_minimum_approver(self):
        for record in self:
            if record.user_ids and record.minimum_approver:
                if record.minimum_approver > len(record.user_ids):
                    raise ValidationError(
                        _(
                            "The minimum approver is exceed the amount of the user assigned."
                        )
                    )
                elif record.minimum_approver < 0:
                    raise ValidationError(
                        _("Minimum approver in approver line must be possitive.")
                    )
            else:
                raise ValidationError(
                    _("Minimum approver in approver line must be possitive.")
                )

    def unlink(self):
        approval = self.approval_matrix_id
        res = super(RentalOrderApprovalMatrixLine, self).unlink()
        approval._reset_sequence()

        return res

    @api.model
    def create(self, vals):
        res = super(RentalOrderApprovalMatrixLine, self).create(vals)
        if not self.env.context.get("keep_line_sequence", False):
            res.approval_matrix_id._reset_sequence()

        return res
