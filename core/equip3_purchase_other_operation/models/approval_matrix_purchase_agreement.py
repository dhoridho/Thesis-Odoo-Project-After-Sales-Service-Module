
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError, Warning

class ApprovalMatrixPurchaseAgreement(models.Model):
    _name = "purchase.agreement.approval.matrix"
    _description = "Approval Matrix Purchase Agreement"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    
    name = fields.Char(string="Name", required=True, tracking=True)
    company_id = fields.Many2one('res.company', string="Company", required=True, tracking=True, readonly=True, default=lambda self: self.env.company.id)
    branch_id = fields.Many2one('res.branch', string="Branch", required=True, default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, domain=lambda self: [('id', 'in', self.env.branches.ids)], tracking=True, readonly=False)
    minimum_amt = fields.Float(string="Minimum Amount", tracking=True)
    maximum_amt = fields.Float(string="Maximum Amount", tracking=True)
    approval_matrix_purchase_agreement_line_ids = fields.One2many('approval.matrix.purchase.agreement.line', 'approval_matrix_purchase_agreement', string='Approving Matrix Purchase Agreement', tracking=True)
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
            
    @api.onchange('name')
    def _onchange_name(self):
        self._compute_is_good_services_order()

    @api.constrains('approval_matrix_purchase_agreement_line_ids')
    def _check_validation_minimum_approver(self):
        for record in self:
            for approval_matrix_line in record.approval_matrix_purchase_agreement_line_ids:
                approving_matrix_usrs = approval_matrix_line.user_ids
                approving_matrix_min_approver = approval_matrix_line.minimum_approver

                if approving_matrix_min_approver <= 0 or approving_matrix_min_approver > len(approving_matrix_usrs):
                    raise ValidationError("Minimum approver should be greater than 0 and cannot greater than the total approver")

    @api.constrains('branch_id')
    def _check_existing_record(self):
        for record in self:
            if record.is_good_services_order:
                approval_matrix_id = self.search([('branch_id', '=', record.branch_id.id), ('id', '!=', record.id), ('order_type', '=', record.order_type)], limit=1)
                if approval_matrix_id:
                    raise ValidationError("Approval Matrix with Same Branch and Order Type Already Created!")
            else:
                approval_matrix_id = self.search([('branch_id', '=', record.branch_id.id), ('id', '!=', record.id)], limit=1)
                if approval_matrix_id:
                    raise ValidationError("Approval Matrix with Same Branch Already Created!")
    
    def _reset_sequence(self):
        for rec in self:
            current_sequence = 1
            for line in rec.approval_matrix_purchase_agreement_line_ids:
                line.sequence = current_sequence
                current_sequence += 1

class ApprovalMatrixPurchaseAgreementLine(models.Model):
    _name = "approval.matrix.purchase.agreement.line"
    _description = "Approval Matrix Purchase Agreement Line"
    
    @api.model
    def default_get(self, fields):
        res = super(ApprovalMatrixPurchaseAgreementLine, self).default_get(fields)
        if self._context:
            context_keys = self._context.keys()
            next_sequence = 1
            if 'approval_matrix_purchase_agreement_line_ids' in context_keys:
                if len(self._context.get('approval_matrix_purchase_agreement_line_ids')) > 0:
                    next_sequence = len(self._context.get('approval_matrix_purchase_agreement_line_ids')) + 1
            res.update({'sequence': next_sequence})
        return res
    
    sequence = fields.Integer(string="Sequence")
    user_ids = fields.Many2many('res.users', string="User", required=True)
    minimum_approver = fields.Integer(string="Minimum Approver", default=1, required=True)
    approval_matrix_purchase_agreement = fields.Many2one('purchase.agreement.approval.matrix', string="Approval Matrix")
    
    sequence2 = fields.Integer(
        string="No.",
        related="sequence",
        readonly=True,
        store=True,
    )
    
    def unlink(self):
        approval = self.approval_matrix_purchase_order
        res = super(ApprovalMatrixPurchaseAgreementLine, self).unlink()
        approval._reset_sequence()
        return res
    
    @api.model
    def create(self, vals):
        res = super(ApprovalMatrixPurchaseAgreementLine, self).create(vals)
        if not self.env.context.get("keep-line_sequence", False):
            res.approval_matrix_purchase_agreement._reset_sequence()
        return res
