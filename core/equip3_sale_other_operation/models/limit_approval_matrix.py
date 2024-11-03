
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError, Warning
import json

class LimitApprovalMatrix(models.Model):
    _name = 'limit.approval.matrix'
    _description = "Limit Approval Matrix"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']


    @api.model
    def _default_branch(self):
        default_branch_id = self.env.context.get('default_branch_id',False)
        if default_branch_id:
            return default_branch_id
        return self.env.company_branches[0].id if len(self.env.company_branches) == 1 else False


    # @api.model
    # def _domain_branch(self):
    #     return [('id', 'in', self.env.branches.ids), ('company_id','=', self.env.company.id)]

    name = fields.Char(string='Name', tracking=True, required=True)
    company_id = fields.Many2one('res.company', string="Company", required=True, default=lambda self: self.env.company, store=True, tracking=True)
    branch_id = fields.Many2one("res.branch", string="Branch", default=_default_branch, tracking=True, required=True,)
    config = fields.Selection([
        ('credit_limit', 'Credit Limit'),
        ('credit_limit_brand','Credit Limit Brand'),
        ('open_invoice_limit', 'Numbers of Open Invoices Limit'),
        ('max_invoice_overdue_days', 'Maximal Invoice Overdue Days'),
        ('over_limit', 'Over Limit')
        ], 'Configuration', store=True, required=True, default="credit_limit", tracking=True)
    minimum_amt = fields.Float(string='Minimum Amount', required=True, tracking=True)
    maximum_amt = fields.Float(string='Maximum Amount', required=True, tracking=True)
    minimal_days = fields.Float(string='Minimal Days', required=True, tracking=True)
    maximal_days = fields.Float(string='Maximal Days', required=True, tracking=True)
    approver_matrix_line_ids = fields.One2many('limit.approval.matrix.lines', 'approval_matrix', string="Approver Name")
    filter_branch = fields.Char(string="Filter Branch", compute='_compute_filter_branch', store=False)

    @api.model
    def create(self, vals):
        if vals.get('config'):
            if vals.get('config') == 'max_invoice_overdue_days':
                vals['minimum_amt'] = vals['minimal_days']
                vals['maximum_amt'] = vals['maximal_days']
            else:
                vals['minimal_days'] = vals['minimum_amt']
                vals['maximal_days'] = vals['maximum_amt']
        res = super().create(vals)
        return res

    @api.depends('company_id')
    def _compute_filter_branch(self):
        for rec in self:
            rec.filter_branch = json.dumps(
                [('id', 'in', self.env.branches.ids), ('company_id', '=', self.company_id.id)])

    @api.constrains('approver_matrix_line_ids')
    def _check_is_approver_matrix_line_ids_exist(self):
        for record in self:
            if not record.approver_matrix_line_ids:
                raise ValidationError("Can't save customers limit approver matrix because there's no approver in approver line!")

    @api.constrains('minimum_amt', 'maximum_amt')
    def _check_greater_lower_amt(self):
        for record in self:
            if record.minimum_amt and record.maximum_amt:
                if record.minimum_amt > record.maximum_amt:
                    raise ValidationError("The minimum amount should be lower than maximum amount")

    @api.constrains('branch_id', 'minimum_amt', 'maximum_amt')
    def _check_existing_record(self):
        for record in self:
            if record.branch_id:
                approval_matrix_id = self.search([('branch_id', '=', record.branch_id.id), ('id', '!=', record.id), ('config', '=', record.config),
                                                '|', '|',
                                                '&', ('minimum_amt', '<=', record.minimum_amt), ('maximum_amt', '>=', record.minimum_amt),
                                                '&', ('minimum_amt', '<=', record.maximum_amt), ('maximum_amt', '>=', record.maximum_amt),
                                                '&', ('minimum_amt', '>=', record.minimum_amt), ('maximum_amt', '<=', record.maximum_amt)], limit=1)
                if approval_matrix_id:
                    raise ValidationError("The minimum and maximum range of this approval matrix is intersects with other approval matrix [%s] in same branch. Please change the minimum and maximum range" % (approval_matrix_id.name))

    def _reset_sequence(self):
        for rec in self:
            current_sequence = 1
            for line in rec.approver_matrix_line_ids:
                line.sequence = current_sequence
                current_sequence += 1

    def copy(self, default=None):
        res = super(LimitApprovalMatrix, self.with_context(keep_line_sequence=True)).copy(default)
        return res


class LimitApprovalMatrixLines(models.Model):
    _name = 'limit.approval.matrix.lines'
    _description = "Limit Approval Matrix Lines"

    @api.model
    def default_get(self, fields):
        res = super(LimitApprovalMatrixLines, self).default_get(fields)
        if self._context:
            context_keys = self._context.keys()
            next_sequence = 1
            if 'approver_matrix_line_ids' in context_keys:
                if len(self._context.get('approver_matrix_line_ids')) > 0:
                    next_sequence = len(self._context.get('approver_matrix_line_ids')) + 1
            res.update({'sequence': next_sequence})
        return res


    approval_matrix = fields.Many2one('limit.approval.matrix', string='Approval Marix')
    def _domain_user_ids(self):
        current_company_id = self.env.company.id
        available_users=self.env['res.users'].search([('share', '=', False)]).filtered(lambda u,current_company_id=current_company_id:current_company_id in u.company_ids.ids)
        return [('id','in',available_users.ids)]
    user_name_ids = fields.Many2many('res.users', string="Users", required=True, domain=_domain_user_ids)
    sequence = fields.Integer(required=True, index=True, help='Use to arrange calculation sequence')
    sequence2 = fields.Integer(
        string="No.",
        related="sequence",
        readonly=True,
        store=True
    )
    minimum_approver = fields.Integer(string="Minimum Approver", required=True, default=1)
    order_id = fields.Many2one('sale.order', string="Sale Order")
    minimum_approver = fields.Integer(string="Minimum Approver", required=True, default=1)
    state_char = fields.Text(string='Approval Status')
    time_stamp = fields.Datetime(string='Timestamp')
    feedback = fields.Char(string='Rejected Reason')
    last_approved = fields.Many2one('res.users', string='Users')
    approved = fields.Boolean('Approved')
    approved_users = fields.Many2many('res.users', 'approved_users_limit_patner_rel', 'limit_id', 'user_id', string='Users')
    approval_type = fields.Selection([('credit_limit','Credit Limit'), ('open_invoice_limit', 'Number Open Invoice Limit'), ('max_invoice_overdue_days','Max Invoice Overdue (Days)'),('over_limit','Over Credit Limit')])
    company_id = fields.Many2one(comodel_name='res.company', string='Company', related="approval_matrix.company_id", store=True)
    approver_state = fields.Selection([('draft', 'Draft'), ('pending', 'Pending'), ('approved', 'Approved'),
                                       ('refuse', 'Rejected')], default='draft', string="State")

    @api.constrains('minimum_approver')
    def _check_is_positive_minimum_approver(self):
        for record in self:
            if record.minimum_approver < 1:
                raise ValidationError("Minimum approver in approver line must be positive")
    
    @api.constrains('user_name_ids', 'minimum_approver')
    def _check_is_user_ids_lower_than_minimum_approver(self):
        for record in self:
            if record.user_name_ids:
                if len(record.user_name_ids) < record.minimum_approver:
                    raise ValidationError("Minimum approver cannot exceed the number of users")

    def unlink(self):
        approval = self.approval_matrix
        res = super(LimitApprovalMatrixLines, self).unlink()
        approval._reset_sequence()
        return res

    @api.model
    def create(self, vals):
        res = super(LimitApprovalMatrixLines, self).create(vals)
        if not self.env.context.get("keep-line_sequence", False):
            res.approval_matrix._reset_sequence()
        return res 


