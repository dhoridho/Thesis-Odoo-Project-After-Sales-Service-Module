from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import json

class ApprovalMatrixCustomer(models.Model):
    _name = "approval.matrix.customer"
    _description = "Approval Matrix Customer"


    name = fields.Char(string="Name", required=True)
    company_id = fields.Many2one('res.company', string="Company", required=True, readonly=True, default=lambda self: self.env.company.id)
    branch_id = fields.Many2one('res.branch', string="Branch", required=False, default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, domain=lambda self: [('id', 'in', self.env.branches.ids)], readonly=False)
    approval_matrix_line_ids = fields.One2many('approval.matrix.customer.line', 'approval_matrix', string='Approving Matrix')

    @api.constrains('approval_matrix_line_ids')
    def _check_validation_minimum_approver(self):
        for record in self:
            for approval_matrix_line in record.approval_matrix_line_ids:
                approving_matrix_usrs = approval_matrix_line.user_ids
                approving_matrix_min_approver = approval_matrix_line.minimum_approver

                if approving_matrix_min_approver <= 0 or approving_matrix_min_approver > len(approving_matrix_usrs):
                    raise ValidationError("Minimum approver should be greater than 0 and cannot greater than the total approver")

    @api.constrains('branch_id')
    def _check_existing_record_branch(self):
        for record in self:
            approval_matrix_id = self.search([('branch_id', '=', record.branch_id.id), ('id', '!=', record.id)], limit=1)
            if approval_matrix_id:
                raise ValidationError("There are other approval matrix %s in same branch. Please change branch" % (approval_matrix_id.name))

    def _reset_sequence(self):
        for rec in self:
            current_sequence = 1
            for line in rec.approval_matrix_line_ids:
                line.sequence = current_sequence
                current_sequence += 1
                
    def copy(self, default=None):
        res = super(ApprovalMatrixCustomer, self.with_context(keep_line_sequence=True)).copy(default)
        return res

    @api.model
    def create(self, vals):
        if 'approval_matrix_line_ids' in vals:
            if not vals['approval_matrix_line_ids']:
                raise ValidationError("Approving Matrix must be filled. Please add the approver.")
        return super().create(vals)

    def write(self, vals):
        res = super().write(vals)
        if not self.approval_matrix_line_ids:
            raise ValidationError("Approving Matrix must be filled. Please add the approver.")
        return res
    
class ApprovalMatrixCustomerLine(models.Model):
    _name = "approval.matrix.customer.line"
    _description = "Approval Matrix Customer Line"

    @api.model
    def default_get(self, fields):
        res = super(ApprovalMatrixCustomerLine, self).default_get(fields)
        if self._context:
            context_keys = self._context.keys()
            next_sequence = 1
            if 'approval_matrix_line_ids' in context_keys:
                if len(self._context.get('approval_matrix_line_ids')) > 0:
                    next_sequence = len(self._context.get('approval_matrix_line_ids')) + 1
            res.update({'sequence': next_sequence})
        return res

    sequence = fields.Integer(string="Sequence")
    approval_matrix = fields.Many2one('approval.matrix.customer', string="Approval Matrix")
    company_id = fields.Many2one(comodel_name='res.company', string='Company', related="approval_matrix.company_id", store=True)
    branch_id = fields.Many2one(comodel_name='res.branch', string='Branch', related="approval_matrix.branch_id", store=True)
    user_ids = fields.Many2many('res.users', string="User", required=True)
    minimum_approver = fields.Integer(string="Minimum Approver", default=1, required=True)
    approved_users = fields.Many2many('res.users', 'approved_users_res_patner_customer_rel', 'app_mat_customer_id', 'user_customer_id', string='Users')
    state_char = fields.Text(string='Approval Status')
    time_stamp = fields.Datetime(string='TimeStamp')
    feedback = fields.Char(string='Feedback')
    last_approved = fields.Many2one('res.users', string='Users')
    approved = fields.Boolean('Approved')
    app_matrix_id = fields.Many2one('res.partner', string="Approved Matrix")
    sequence2 = fields.Integer(
        string="No.",
        related="sequence",
        readonly=True,
        store=True
    )
    approver_state = fields.Selection([('draft', 'Draft'), ('pending', 'Pending'), ('approved', 'Approved'),
                                       ('refuse', 'Refused')], default='draft', string="State")
    filter_user_ids = fields.Char(string='Filter User per Branch', compute='_get_filter_user', store=False)

    @api.depends('branch_id')
    def _get_filter_user(self):
        for record in self:
            if record.branch_id:
                record.filter_user_ids = json.dumps([('company_id','=',record.company_id.id),('branch_id','=',record.branch_id.id)])
            else:
                record.filter_user_ids = json.dumps([('company_id','=',record.company_id.id)])

    def unlink(self):
        approval = self.approval_matrix
        res = super(ApprovalMatrixCustomerLine, self).unlink()
        approval._reset_sequence()
        return res

    @api.model
    def create(self, vals):
        res = super(ApprovalMatrixCustomerLine, self).create(vals)
        if not self.env.context.get("keep-line_sequence", False):
            res.approval_matrix._reset_sequence()
        return res 
