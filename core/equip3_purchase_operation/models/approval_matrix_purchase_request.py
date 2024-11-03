

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError, Warning

class ApprovalMatrixPurchaseRequest(models.Model):
    _name = "approval.matrix.purchase.request"
    _description = "Approval Matrix Purchase Reqest"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']


    name = fields.Char(string="Name", required=True, tracking=True)
    company_id = fields.Many2one('res.company', string="Company", required=True, tracking=True, readonly=True, default=lambda self: self.env.company.id)
    branch_id = fields.Many2one('res.branch', string="Branch", required=True, default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, domain=lambda self: [('id', 'in', self.env.branches.ids)], tracking=True)
    department_id = fields.Many2one('hr.department', string="Department", tracking=True)
    minimum_amt = fields.Float(string="Minimum Amount", tracking=True, required=True)
    maximum_amt = fields.Float(string="Maximum Amount", tracking=True, required=True)
    is_purchase_request_department = fields.Boolean(string="PR Department", compute='_compute_pr_department')
    
    def _compute_pr_department(self):
        is_pr_department = self.env['ir.config_parameter'].sudo().get_param('is_pr_department', False)
        # is_pr_department = self.env.company.is_pr_department
        for record in self:
            record.is_purchase_request_department = False
            if is_pr_department:
                record.is_purchase_request_department = True

    approval_matrix_purchase_request_line_ids = fields.One2many('approval.matrix.purchase.request.line', 'approval_matrix_purchase_request', string='Approving Matrix Purchase Request')
    order_type = fields.Selection([
                ("goods_order","Goods Order"),
                ("services_order","Services Order")
                ], string='Order Type', default="goods_order")
    is_good_services_order = fields.Boolean(string="Orders", compute="_compute_is_good_services_order")
    
    def _compute_is_good_services_order(self):
        for record in self:
            is_good_services_order = self.env['ir.config_parameter'].sudo().get_param('is_good_services_order', False)
            # is_good_services_order = self.env.company.is_good_services_order
            record.is_good_services_order = is_good_services_order

    # @api.constrains('approval_matrix_purchase_request_line_ids')
    # def _check_validation_minimum_approver(self):
    #     for record in self:
    #         for approval_matrix_line in record.approval_matrix_purchase_request_line_ids:
    #             approving_matrix_usrs = approval_matrix_line.user_ids
    #             approving_matrix_min_approver = approval_matrix_line.minimum_approver

    #             if approving_matrix_min_approver <= 0 or approving_matrix_min_approver > len(approving_matrix_usrs):
    #                 raise ValidationError("Minimum approver should be greater than 0 and cannot greater than the total approver")

    @api.constrains('branch_id', 'department_id')
    def _check_existing_record(self):
        for record in self:
            if record.is_good_services_order and record.is_purchase_request_department:
                approval_matrix_id = self.search([('branch_id', '=', record.branch_id.id), ('id', '!=', record.id), ('order_type', '=', record.order_type), ('department_id', '=', record.department_id.id)], limit=1)
                if approval_matrix_id:
                    raise ValidationError("There are the other approval matrix %s in same Branch, Order Type and Department. Please change branch , order type or Department." % (approval_matrix_id.name))
            elif record.is_good_services_order:
                approval_matrix_id = self.search([('branch_id', '=', record.branch_id.id), ('id', '!=', record.id), ('order_type', '=', record.order_type)], limit=1)
                if approval_matrix_id:
                    raise ValidationError("There are the other approval matrix %s in same Branch, Order Type. Please change branch or order type." % (approval_matrix_id.name))
            elif record.is_purchase_request_department:
                approval_matrix_id = self.search([('branch_id', '=', record.branch_id.id), ('id', '!=', record.id), ('department_id', '=', record.department_id.id)], limit=1)
                if approval_matrix_id:
                    raise ValidationError("There are other approval matrix %s in same branch. Please change branch or Department" % (approval_matrix_id.name))
            else:
                approval_matrix_id = self.search([('branch_id', '=', record.branch_id.id), ('id', '!=', record.id)], limit=1)
                if approval_matrix_id:
                    raise ValidationError("There are other approval matrix %s in same branch. Please change branch" % (approval_matrix_id.name))
 
    def _reset_sequence(self):
        for rec in self:
            current_sequence = 1
            for line in rec.approval_matrix_purchase_request_line_ids:
                line.sequence = current_sequence
                current_sequence += 1

    @api.onchange('company_id')
    def onchange_company_id(self):
        self._compute_is_good_services_order()
        self._compute_pr_department()

    @api.onchange('company_id')
    def default_branch(self):
        user = self.env['res.users'].browse(self.env.uid)
        if user.has_group('branch.group_multi_branch'):
            branch_id = self.env['res.branch'].search([('id', 'in', self.env.context['allowed_branch_ids'])])
        else:
            branch_id = self.env['res.branch'].search([
                ('id','=',self.branch_id.id),
                '|',
                ('company_id','=',False),
                ('company_id','=',self.env.company.id),
            ])
        self.branch_id = self.env.branch.id if len(self.env.branches) == 1 else False


class ApprovalMatrixPurchaseRequestLine(models.Model):
    _name = "approval.matrix.purchase.request.line"
    _description = "Approval Matrix Purchase Request Line"

    @api.model
    def default_get(self, fields):
        res = super(ApprovalMatrixPurchaseRequestLine, self).default_get(fields)
        if self._context:
            context_keys = self._context.keys()
            next_sequence = 1
            if 'approval_matrix_purchase_request_line_ids' in context_keys:
                if len(self._context.get('approval_matrix_purchase_request_line_ids')) > 0:
                    next_sequence = len(self._context.get('approval_matrix_purchase_request_line_ids')) + 1
            res.update({'sequence': next_sequence})
        return res

    sequence = fields.Integer(string="Sequence")
    user_ids = fields.Many2many('res.users', string="User", required=True)
    minimum_approver = fields.Integer(string="Minimum Approver", default=1, required=True)
    approval_matrix_purchase_request = fields.Many2one('approval.matrix.purchase.request', string="Approval Matrix")
    request_id = fields.Many2one('purchase.request', string="Purchase Request")
    approved_users = fields.Many2many('res.users', 'approved_users_purchase_request_patner_rel', 'request_id', 'user_id', string='Users')
    state_char = fields.Text(string='Approval Status')
    time_stamp = fields.Datetime(string='TimeStamp')
    feedback = fields.Char(string='Feedback')
    last_approved = fields.Many2one('res.users', string='Users')
    approved = fields.Boolean('Approved')
    sequence2 = fields.Integer(
        string="No.",
        related="sequence",
        readonly=True,
        store=True
    )
    approver_state = fields.Selection([('draft', 'Draft'), ('pending', 'Pending'), ('approved', 'Approved'),
                                       ('refuse', 'Refused')], default='draft', string="State")

    def unlink(self):
        approval = self.approval_matrix_purchase_request
        res = super(ApprovalMatrixPurchaseRequestLine, self).unlink()
        approval._reset_sequence()
        return res

    @api.model
    def create(self, vals):
        res = super(ApprovalMatrixPurchaseRequestLine, self).create(vals)
        if not self.env.context.get("keep-line_sequence", False):
            res.approval_matrix_purchase_request._reset_sequence()
        return res
