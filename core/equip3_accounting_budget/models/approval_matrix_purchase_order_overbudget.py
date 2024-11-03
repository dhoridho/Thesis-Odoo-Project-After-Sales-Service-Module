from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class ApprovalMatrixPurchaseOrderOverbudget(models.Model):
    _name = "approval.matrix.purchase.order.overbudget"
    _description = "Approval Matrix Purchase Order Overbudget"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']


    name = fields.Char(string="Name", required=True)
    company_id = fields.Many2one('res.company', string="Company", required=True, readonly=True, default=lambda self: self.env.company.id)
    branch_id = fields.Many2one('res.branch', string="Branch", required=True, default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, domain=lambda self: [('id', 'in', self.env.branches.ids)])
    min_difference_amount = fields.Float(string="Min Difference Amount", required=True)
    max_difference_amount = fields.Float(string="Max Difference Amount", required=True)
    approval_matrix_purchase_order_overbudget_line_ids = fields.One2many('approval.matrix.purchase.order.overbudget.line', 'approval_matrix_purchase_order_overbudget_id', string='Approving Matrix Purchase Order Overbudget Lines')


    @api.constrains('approval_matrix_purchase_order_overbudget_line_ids')
    def _check_validation_minimum_approver(self):
        for record in self:
            for approval_matrix_line in record.approval_matrix_purchase_order_overbudget_line_ids:
                approving_matrix_usrs = approval_matrix_line.user_ids
                approving_matrix_min_approver = approval_matrix_line.minimum_approver

                if approving_matrix_min_approver <= 0 or approving_matrix_min_approver > len(approving_matrix_usrs):
                    raise ValidationError("Minimum approver should be greater than 0 and cannot greater than the total approver")

    @api.constrains('branch_id', 'min_difference_amount', 'max_difference_amount')
    def _check_existing_record(self):
        for record in self:
            if record.min_difference_amount > record.max_difference_amount:
                raise ValidationError("Min Difference Amount can not be greater than Max Difference Amount!")

            if record.branch_id:
                approval_matrix_id = self.search([('branch_id', '=', record.branch_id.id), ('id', '!=', record.id),
                                                  '|', '|',
                                                  '&', ('min_difference_amount', '<=', record.min_difference_amount),
                                                  ('max_difference_amount', '>=', record.max_difference_amount),
                                                  '&', ('min_difference_amount', '<=', record.min_difference_amount),
                                                  ('max_difference_amount', '>=', record.max_difference_amount),
                                                  '&', ('min_difference_amount', '>=', record.min_difference_amount),
                                                  ('max_difference_amount', '<=', record.max_difference_amount)], limit=1)
                if approval_matrix_id:
                    raise ValidationError(
                        "The minimum and maximum range of this approval matrix is intersects with other approval matrix [%s] in same branch. Please change the minimum and maximum range" % (
                            approval_matrix_id.name))    
 
    def _reset_sequence(self):
        for rec in self:
            current_sequence = 1
            for line in rec.approval_matrix_purchase_order_overbudget_line_ids:
                line.sequence = current_sequence
                current_sequence += 1


class ApprovalMatrixPurchaseOrderOverbudgetLine(models.Model):
    _name = "approval.matrix.purchase.order.overbudget.line"
    _description = "Approval Matrix Purchase Order Overbudget Line"

    @api.model
    def default_get(self, fields):
        res = super(ApprovalMatrixPurchaseOrderOverbudgetLine, self).default_get(fields)
        if self._context:
            context_keys = self._context.keys()
            next_sequence = 1
            if 'approval_matrix_purchase_order_overbudget_line_ids' in context_keys:
                if len(self._context.get('approval_matrix_purchase_order_overbudget_line_ids')) > 0:
                    next_sequence = len(self._context.get('approval_matrix_purchase_order_overbudget_line_ids')) + 1
            res.update({'sequence': next_sequence})
        return res

    sequence = fields.Integer(string="Sequence")
    sequence2 = fields.Integer(string="No.", related="sequence", readonly=True, store=True, tracking=True)
    user_ids = fields.Many2many('res.users', string="User", required=True)
    minimum_approver = fields.Integer(string="Minimum Approver", default=1, required=True)
    approval_matrix_purchase_order_overbudget_id = fields.Many2one('approval.matrix.purchase.order.overbudget', string="Approval Matrix")
    order_id = fields.Many2one('purchase.order', string="Purchase Order")
    approved_users = fields.Many2many('res.users', 'approved_users_purchase_order_overbudget_patner_rel', 'order_id', 'user_id', string='Users')
    state_char = fields.Text(string='Approval Status')
    time_stamp = fields.Datetime(string='TimeStamp')
    feedback = fields.Char(string='Feedback')
    last_approved = fields.Many2one('res.users', string='Users')
    approved = fields.Boolean('Approved')
    approver_state = fields.Selection([('draft', 'Draft'), ('pending', 'Pending'), ('approved', 'Approved'),
                                       ('refuse', 'Refused')], default='draft', string="State")

    def unlink(self):
        approval = self.approval_matrix_purchase_order_overbudget_id
        res = super(ApprovalMatrixPurchaseOrderOverbudgetLine, self).unlink()
        approval._reset_sequence()
        return res

    @api.model
    def create(self, vals):
        res = super(ApprovalMatrixPurchaseOrderOverbudgetLine, self).create(vals)
        if not self.env.context.get("keep-line_sequence", False):
            res.approval_matrix_purchase_order_overbudget_id._reset_sequence()
        return res