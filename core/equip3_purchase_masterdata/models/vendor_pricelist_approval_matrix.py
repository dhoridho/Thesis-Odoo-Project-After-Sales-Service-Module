from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import json

class VendorPricelistApprovalMatrix(models.Model):
    _name = "vendor.pricelist.approval.matrix"
    _description = "Vendor Pricelist Approval Matrix"
    
    
    name = fields.Char(string="Name", required=True)
    company_id = fields.Many2one('res.company', string="Company", required=True, readonly=True, default=lambda self: self.env.company.id)
    branch_id = fields.Many2one('res.branch', string="Branch", default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, domain=lambda self: [('id', 'in', self.env.branches.ids)], readonly=False)
    department_id = fields.Many2one('hr.department', 'Department', domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    created_by = fields.Many2one('res.users', "Created By", readonly=True, default=lambda self: self.env.user)
    created_date = fields.Date("Created On", readonly=True, default=fields.Date.today())
    approval_matrix_line_ids = fields.One2many('vendor.pricelist.approval.matrix.line', 'approval_matrix', string='Approving Matrix')
    # minimum_amt = fields.Float(string='Minimum Amount', required=True, tracking=True)
    # maximum_amt = fields.Float(string='Maximum Amount', required=True, tracking=True)
    
    @api.constrains('approval_matrix_line_ids')
    def _check_validation_minimum_approver(self):
        if not self.approval_matrix_line_ids:
            raise ValidationError("Approving Matrix must be filled. Please add the approver.")
        for record in self:
            for approval_matrix_line in record.approval_matrix_line_ids:
                approving_matrix_usrs = approval_matrix_line.user_ids
                approving_matrix_min_approver = approval_matrix_line.minimum_approver

                if approving_matrix_min_approver <= 0 or approving_matrix_min_approver > len(approving_matrix_usrs):
                    raise ValidationError("Minimum approver should be greater than 0 and cannot greater than the total approver")

    @api.constrains('branch_id')
    def _check_existing_record(self):
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
        res = super(VendorPricelistApprovalMatrix, self.with_context(keep_line_sequence=True)).copy(default)
        return res
        

class VendorPricelistApprovalMatrixLine(models.Model):
    _name = "vendor.pricelist.approval.matrix.line"
    _description = "Vendor Pricelist Approval Matrix Line"
    
    @api.model
    def default_get(self, fields):
        res = super(VendorPricelistApprovalMatrixLine, self).default_get(fields)
        if self._context:
            context_keys = self._context.keys()
            next_sequence = 1
            if 'approval_matrix_line_ids' in context_keys:
                if len(self._context.get('approval_matrix_line_ids')) > 0:
                    next_sequence = len(self._context.get('approval_matrix_line_ids')) + 1
            res.update({'sequence': next_sequence})
        return res
    
    sequence = fields.Integer(string="Sequence")
    approval_matrix = fields.Many2one('vendor.pricelist.approval.matrix', string="Approval Matrix")
    company_id = fields.Many2one(comodel_name='res.company', string='Company', related="approval_matrix.company_id", store=True)
    branch_id = fields.Many2one(comodel_name='res.branch', string='Branch', related="approval_matrix.branch_id", store=True)
    user_ids = fields.Many2many('res.users', string="User", required=True)
    minimum_approver = fields.Integer(string="Minimum Approver", default=1, required=True)
    sequence2 = fields.Integer(
        string="No.",
        related="sequence",
        readonly=True,
        store=True
    )
    user_ids_domain = fields.Char(string="User Domain JSON", compute='_compute_user_domain')
    
    @api.depends('user_ids')
    def _compute_user_domain(self):
        domain = [('company_id', '=', self.env.company.id)]
        for rec in self:
            if rec.branch_id:
                domain += [('branch_id', '=', rec.branch_id.id)]
            user_approve_ids = rec.env['res.users'].search(domain)
            rec.user_ids_domain = json.dumps([('id', 'in', user_approve_ids.ids)])
            
    
    def unlink(self):
        approval = self.approval_matrix
        res = super(VendorPricelistApprovalMatrixLine, self).unlink()
        approval._reset_sequence()
        return res
    
    @api.model
    def create(self, vals):
        res = super(VendorPricelistApprovalMatrixLine, self).create(vals)
        if not self.env.context.get("keep-line_sequence", False):
            res.approval_matrix._reset_sequence()
        return res 
