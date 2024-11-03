
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError, Warning
import json

class ApprovalMatrixSaleOrder(models.Model):
    _name = 'approval.matrix.sale.order'
    _description = "Approval Matrix Sale Order"
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
    company_id = fields.Many2one("res.company", string="Company", tracking=True, required=True, readonly=True, default=lambda self: self.env.company.id)
    branch_id = fields.Many2one("res.branch", string="Branch", tracking=True, required=True,)
    
    config = fields.Selection([
        ('total_amt', 'Total Amount'),
        # ('margin_amt', 'Margin Amount'),
        ('pargin_per', 'Margin Percentage'),
        ('discount_amt', 'Discount Amount'),
        #('discount_Pet', 'Discount Percentage')
    ], 'Configuration', store=True, required=True, default="total_amt", tracking=True)
    minimum_amt = fields.Float(string='Minimum Amount', required=True, tracking=True)
    maximum_amt = fields.Float(string='Maximum Amount', required=True, tracking=True)
    approver_matrix_line_ids = fields.One2many('approval.matrix.sale.order.lines', 'approval_matrix', string="Approver Name")
    description = fields.Text(default="Margin configuration will check the margin total from margin in each order line.", readonly=True)
    filter_branch = fields.Char(string="Filter Branch", compute='_compute_filter_branch', store=False)
    currency_id = fields.Many2one('res.currency', 'Currency', required=True,
                                  default=lambda self: self.env.company.currency_id.id)

    
    @api.depends('company_id')
    def _compute_filter_branch(self):
        for rec in self:
            rec.filter_branch = json.dumps(
                [('id', 'in', self.env.branches.ids), ('company_id', '=', self.company_id.id)])


    @api.model
    def default_get(self, fields):
        res = super(ApprovalMatrixSaleOrder, self).default_get(fields)
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        sale_matrix_config =  IrConfigParam.get_param('sale_matrix_config', 'total_amt')
        res['config'] = sale_matrix_config
        return res

    @api.constrains('approver_matrix_line_ids')
    def _check_is_approver_matrix_line_ids_exist(self):
        for record in self:
            if not record.approver_matrix_line_ids:
                raise ValidationError("Can't save sales approval matrix because there's no approver in approver line!")

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
                approval_matrix_id = self.search([('branch_id', '=', record.branch_id.id), ('id', '!=', record.id), ('config', '=', record.config),('currency_id','=',record.currency_id.id),
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
        res = super(ApprovalMatrixSaleOrder, self.with_context(keep_line_sequence=True)).copy(default)
        return res


class ApprovalMatrixSaleOrderLines(models.Model):
    _name = 'approval.matrix.sale.order.lines'
    _description = "Approval Matrix Sale Order Lines"

    @api.model
    def default_get(self, fields):
        res = super(ApprovalMatrixSaleOrderLines, self).default_get(fields)
        if self._context:
            context_keys = self._context.keys()
            next_sequence = 1
            if 'approver_matrix_line_ids' in context_keys:
                if len(self._context.get('approver_matrix_line_ids')) > 0:
                    next_sequence = len(self._context.get('approver_matrix_line_ids')) + 1
            res.update({'sequence': next_sequence})
        return res

    approval_matrix = fields.Many2one('approval.matrix.sale.order', string='Approval Marix')
    order_id = fields.Many2one('sale.order', string="Sale Order")
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
    state_char = fields.Text(string='Approval Status')
    time_stamp = fields.Datetime(string='Timestamp')
    feedback = fields.Char(string='Rejected Reason')
    last_approved = fields.Many2one('res.users', string='Users')
    approved = fields.Boolean('Approved')
    approved_users = fields.Many2many('res.users', 'approved_users_sale_patner_rel', 'order_id', 'user_id', string='Users')
    signature = fields.Binary(related="last_approved.digital_signature", string="Signature", store=True)
    approval_type = fields.Selection([('total_amt', 'Total Amount'),('margin_amt', 'Margin Amount'),('pargin_per', 'Margin Percentage'), ('discount_amt', 'Discount Amount')])
    approver_state = fields.Selection([('draft', 'Draft'), ('pending', 'Pending'), ('approved', 'Approved'),
                                       ('refuse', 'Refused')], default='draft', string="State")
    approver_types = fields.Selection(
        [('by_hierarchy', 'By Hierarchy'),
         ('specific_approver', 'Specific Approver')], default="specific_approver", string="Approver Types")

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
        res = super(ApprovalMatrixSaleOrderLines, self).unlink()
        approval._reset_sequence()
        return res

    @api.model
    def create(self, vals):
        res = super(ApprovalMatrixSaleOrderLines, self).create(vals)
        if not self.env.context.get("keep-line_sequence", False):
            res.approval_matrix._reset_sequence()
        return res
