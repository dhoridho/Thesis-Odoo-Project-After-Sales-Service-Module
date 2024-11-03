
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError, Warning

class CashAdvanceApprovalMatrix(models.Model):
    _name = "cash.advance.approval.matrix"
    _description = "Cash Advance Approval Matrix"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    
    @api.model
    def _get_branch_domain(self):
        return [("id", "in", self.env.user.branch_ids.ids)]
    
    name = fields.Char(string="Name", required=True, tracking=True)
    company_id = fields.Many2one('res.company', string="Company", required=True, tracking=True, readonly=True, default=lambda self: self.env.company.id)
    branch_id = fields.Many2one('res.branch', string="Branch", required=True, domain="[('company_id', '=', company_id)]", tracking=True)
    cash_advance_approval_matrix_line_ids = fields.One2many('cash.advance.approval.matrix.line', 'cash_advance_approval_matrix_id', string='Cash Advance Approving Matrix')
    is_cash_advance_approval = fields.Boolean(string="Cash Advance Approval", compute="_compute_is_assets_approval")
    
    def _compute_is_assets_approval(self):
        for record in self:
            is_cash_advance_approving_matrix = self.env['ir.config_parameter'].sudo().get_param('is_cash_advance_approving_matrix', False)
            record.is_cash_advance_approval = is_cash_advance_approving_matrix
    
    def _reset_sequence(self):
        for rec in self:
            current_sequence = 1
            for line in rec.cash_advance_approval_matrix_line_ids:
                line.sequence = current_sequence
                current_sequence += 1
                
    @api.constrains('branch_id', 'company_id')
    def _check_existing_record(self):
        for record in self:
            if record.branch_id and record.is_cash_advance_approval:
                approval_matrix_id = self.search([('branch_id', '=', record.branch_id.id), ('id', '!=', record.id), ('company_id', '=', record.company_id.id)], limit=1)
                if approval_matrix_id:
                    raise ValidationError("There are the other approval matrix %s in same Branch. Please change branch and Company." % (approval_matrix_id.name))
    

class CashAdvanceApprovalMatrixLine(models.Model):
    _name = "cash.advance.approval.matrix.line"
    _description = "Cash Advance Approval Matrix Line"
    
    @api.model
    def default_get(self, fields):
        res = super(CashAdvanceApprovalMatrixLine, self).default_get(fields)
        if self._context:
            context_keys = self._context.keys()
            next_sequence = 1
            if 'cash_advance_approval_matrix_line_ids' in context_keys:
                if len(self._context.get('cash_advance_approval_matrix_line_ids')) > 0:
                    next_sequence = len(self._context.get('cash_advance_approval_matrix_line_ids')) + 1
            res.update({'sequence': next_sequence})
        return res
    
    sequence = fields.Integer(string="Sequence")
    user_ids = fields.Many2many('res.users', string="User", required=True)
    minimum_approver = fields.Integer(string="Minimum Approver", default=1, required=True)
    cash_advance_approval_matrix_id = fields.Many2one('cash.advance.approval.matrix', string="Approval Matrix")
    sequence2 = fields.Integer(string="No.", related="sequence", readonly=True, store=True, tracking=True)
    approved_users = fields.Many2many('res.users', 'cash_advance_approved_users_patner_rel', 'order_id', 'user_id', string='Users')
    state_char = fields.Text(string='Approval Status')
    time_stamp = fields.Datetime(string='TimeStamp')
    feedback = fields.Char(string='Feedback')
    last_approved = fields.Many2one('res.users', string='Users')
    approved = fields.Boolean('Approved')
    cash_advance_id = fields.Many2one('vendor.deposit', string="Cash Advance Approval")

    def _valid_field_parameter(self, field, name):
        return name == "tracking" or super()._valid_field_parameter(field, name)
    
    def unlink(self):
        approval = self.cash_advance_approval_matrix_id
        res = super(CashAdvanceApprovalMatrixLine, self).unlink()
        approval._reset_sequence()
        return res

    @api.model
    def create(self, vals):
        res = super(CashAdvanceApprovalMatrixLine, self).create(vals)
        if not self.env.context.get("keep-line_sequence", False):
            res.cash_advance_approval_matrix_id._reset_sequence()
        return res
    
    