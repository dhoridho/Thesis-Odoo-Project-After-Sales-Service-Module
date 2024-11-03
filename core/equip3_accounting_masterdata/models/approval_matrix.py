from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class ApprovalMatrixAccounting(models.Model):
    _name = "approval.matrix.accounting"
    _description = 'Approval Matrix Accounting'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']

    @api.model
    def _default_branch(self):
        default_branch_id = self.env.context.get('default_branch_id',False)
        if default_branch_id:
            return default_branch_id
        return self.env.company_branches[0].id if len(self.env.company_branches) == 1 else self.env.user.branch_id.id

    @api.model
    def _domain_branch(self):
        return [('id', 'in', self.env.branches.ids), ('company_id','=', self.env.company.id)]
        
    approval_matrix_type = fields.Selection([
        ('invoice', 'Invoice'),
        ('bill', 'Bill'),
        ('other_income', 'Other Income'),
        ('other_expense', 'Other Expense'),
        ('payment_voucher', 'Payment Voucher'),
        ('credit_note', 'Credit Note'),
        ('refund_approval_matrix', 'Refund Approval Note'),
        ('customer_deposit_approval_matrix', 'Customer Deposit'),
        ('vendor_deposit_approval_matrix', 'Vendor Deposit'),
        ('customer_multi_receipt_approval_matrix', 'Customer Multi Receipt'),
        ('vendor_multi_receipt_approval_matrix', 'Vendor Multi Receipt'),
        ('receipt_giro_approval_matrix', 'Receipt Giro'),
        ('payment_giro_approval_matrix', 'Payment Giro'),
        ('receipt_approval_matrix', 'Receipt'),
        ('payment_approval_matrix', 'Payment'),
        ('inter_bank_cash_approval_matrix', 'Inter Bank/Cash'),
        ('purchase_currency_approval_matrix', 'Purchase Currency'),
        ('budget', 'Budget'),
        ('budget_change_request_approval','Budget Change Request '),
        ('purchase_budget', 'Purchase Budget'),
        ('purchase_budget_change_request_approval','Purchase Budget Change Request Approval Matrix'),
        ('cash_advance_approval_matrix','Cash Advance')
    ], string='Approval Matrix Type', tracking=True)
    change_amount = fields.Float(string="Change Amount")
    name = fields.Char(string='Name', required=True, tracking=True)
    min_amount = fields.Float(string='Minimum Amount', tracking=True)
    max_amount = fields.Float(string='Maximum Amount', tracking=True)
    company_id = fields.Many2one('res.company', string="Company", required=True, readonly=True,
                                 default=lambda self: self.env.company.id, tracking=True)
    # branch_id = fields.Many2one('res.branch', string='Branch', tracking=True,
    #                             default=lambda self: self.env.user.branch_id.id)
    branch_id = fields.Many2one('res.branch', check_company=True, domain=_domain_branch, default = _default_branch, readonly=False, required=True, string='Branch')
    filter_branch_ids = fields.Many2many('res.branch', string="Branch", compute='_compute_branch_ids')
    approval_matrix_line_ids = fields.One2many('approval.matrix.accounting.lines', 'approval_matrix_id',
                                               string='Approval Matrix Lines', required=True)

    @api.onchange('name')
    def _onchange_name(self):
        self._compute_branch_ids()

    @api.constrains('branch_id', 'min_amount', 'max_amount', 'approval_matrix_type')
    def _check_existing_record(self):
        for record in self:
            if record.min_amount > record.max_amount:
                raise ValidationError("The minimum amount cannot bigger than maximum amount.")    

            if record.branch_id:
                approval_matrix_id = self.search([('branch_id', '=', record.branch_id.id), ('id', '!=', record.id),
                                                  ('approval_matrix_type', '=', record.approval_matrix_type),
                                                  '|', '|',
                                                  '&', ('min_amount', '<=', record.min_amount),
                                                  ('max_amount', '>=', record.min_amount),
                                                  '&', ('min_amount', '<=', record.max_amount),
                                                  ('max_amount', '>=', record.max_amount),
                                                  '&', ('min_amount', '>=', record.min_amount),
                                                  ('max_amount', '<=', record.max_amount)], limit=1)
                if approval_matrix_id and (record.approval_matrix_type != 'budget' and record.approval_matrix_type != 'budget_change_request_approval' and record.approval_matrix_type != 'purchase_budget' and record.approval_matrix_type != 'purchase_budget_change_request_approval'):
                    raise ValidationError(
                        "The minimum and maximum range of this approval matrix is intersects with other approval matrix [%s] in same branch. Please change the minimum and maximum range" % (
                            approval_matrix_id.name))    

    @api.constrains('branch_id','company_id','approval_matrix_type')
    def _check_branch_company_record(self):
        for record in self:
            if record.branch_id:
                approve = self.search([('id', '!=', record.id),
                                       ('approval_matrix_type', '=', record.approval_matrix_type),
                                       ('branch_id', '=', record.branch_id.id),
                                       ('company_id', '=', record.company_id.id)], limit=1)
                if approve and (record.approval_matrix_type == 'budget' or record.approval_matrix_type == 'purchase_budget'):
                    raise ValidationError(
                        "Company and branch approval matrix is the same as with other approval matrix [%s]. Please change the company or branch" % (
                            approve.name))

    @api.constrains('change_amount','approval_matrix_type')
    def _check_existing(self):
        for record in self:
            if record.change_amount:
                approval_id = self.search([('id', '!=', record.id),
                                           ('branch_id', '=', record.branch_id.id),
                                           ('change_amount', '=', record.change_amount),
                                           ('company_id', '=', record.company_id.id),
                                           ('approval_matrix_type', '=', record.approval_matrix_type)], limit=1)
                if approval_id :
                    raise ValidationError(
                        "The change amount of the approval matrix is intersect with other approval matrix  [%s] in the same branch. Please change the change amount." % (
                            approval_id.name)) 

    @api.constrains('approval_matrix_line_ids')
    def _check_null(self):
        if not self.approval_matrix_line_ids :
            raise ValidationError(_("Please fill the Approving Matrix Line!"))

    def _reset_sequence(self):
        for rec in self:
            current_sequence = 1
            for line in rec.approval_matrix_line_ids:
                line.sequence = current_sequence
                current_sequence += 1

    def copy(self, default=None):
        res = super(ApprovalMatrixAccounting, self.with_context(keep_line_sequence=True)).copy(default)
        return res

    def _compute_branch_ids(self):
        user = self.env.user
        branch_ids = user.branch_ids + user.branch_id
        for rec in self:
            rec.filter_branch_ids = [(6, 0, branch_ids.ids)]


class ApprovalMatrixAccountingLines(models.Model):
    _name = "approval.matrix.accounting.lines"
    _description = 'Approval Matrix Accounting Lines'

    @api.model
    def default_get(self, fields):
        res = super(ApprovalMatrixAccountingLines, self).default_get(fields)
        if self._context:
            context_keys = self._context.keys()
            next_sequence = 1
            if 'approval_matrix_line_ids' in context_keys:
                if len(self._context.get('approval_matrix_line_ids')) > 0:
                    next_sequence = len(self._context.get('approval_matrix_line_ids')) + 1
            res.update({'sequence': next_sequence})
        return res

    sequence = fields.Integer(string="Sequence")
    user_ids = fields.Many2many('res.users', string="User", required=True)
    minimum_approver = fields.Integer(string="Minimum Approver", default=1, required=True)
    approval_matrix_id = fields.Many2one('approval.matrix.accounting', string="Approval Matrix", ondelete="cascade")
    approved_users = fields.Many2many('res.users', 'approved_users_accounting_res_patner_rel', 'app_mat_id', 'user_id', string='Users')
    state_char = fields.Text(string='Approval Status')
    time_stamp = fields.Datetime(string='TimeStamp')
    feedback = fields.Char(string='Feedback')
    last_approved = fields.Many2one('res.users', string='Users')
    approved = fields.Boolean('Approved')
    sequence2 = fields.Integer(string="No.", related="sequence", readonly=True, store=True, tracking=True)
    approver_state = fields.Selection([('draft', 'Draft'), ('pending', 'Pending'), ('approved', 'Approved'),
                                       ('refuse', 'Refused')], default='', string="State")

    def _valid_field_parameter(self, field, name):
        return name == "tracking" or super()._valid_field_parameter(field, name)

    @api.constrains('minimum_approver', 'user_ids')
    def _check_minimum_users(self):
        for record in self:
            if record.minimum_approver > len(record.user_ids):
                raise ValidationError("The minimum approver is exceed the amount of the user assigned.")

    def unlink(self):
        approval = self.approval_matrix_id
        res = super(ApprovalMatrixAccountingLines, self).unlink()
        approval._reset_sequence()
        return res

    @api.model
    def create(self, vals):
        res = super(ApprovalMatrixAccountingLines, self).create(vals)
        if not self.env.context.get("keep-line_sequence", False):
            res.approval_matrix_id._reset_sequence()
        return res
