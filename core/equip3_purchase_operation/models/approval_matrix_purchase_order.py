
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError, Warning

class ApprovalMatrixPurchaseOrder(models.Model):
    _name = "approval.matrix.purchase.order"
    _description = "Approval Matrix Purchase Order"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']

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

    name = fields.Char(string="Name", required=True, tracking=True)
    company_id = fields.Many2one('res.company', string="Company", required=True, tracking=True, readonly=True, default=lambda self: self.env.company.id)
    branch_id = fields.Many2one('res.branch', string="Branch", required=True, default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, domain=lambda self: [('id', 'in', self.env.branches.ids)], tracking=True)
    minimum_amt = fields.Float(string="Minimum Amount", tracking=True, required=True)
    maximum_amt = fields.Float(string="Maximum Amount", tracking=True, required=True)
    approval_matrix_purchase_order_line_ids = fields.One2many('approval.matrix.purchase.order.line', 'approval_matrix_purchase_order', string='Approving Matrix Purchase Order')
    order_type = fields.Selection([
                ("goods_order","Goods Order"),
                ("services_order","Services Order")
                ], string='Order Type', default="goods_order")
    is_good_services_order = fields.Boolean(string="Orders", compute="_compute_is_good_services_order")
    currency_id = fields.Many2one('res.currency', 'Currency', required=True,
                                  default=lambda self: self.env.company.currency_id.id)


    def _compute_is_good_services_order(self):
        for record in self:
            is_good_services_order = self.env['ir.config_parameter'].sudo().get_param('is_good_services_order', False)
            # is_good_services_order = self.env.company.is_good_services_order
            record.is_good_services_order = is_good_services_order

    def get_domain_approval(self, res_domain):
        domain = (
            ('branch_id', '=', self.branch_id.id), ('id', '!=', self.id), ('currency_id','=',self.currency_id.id),
            '|', '|',
            '&', ('minimum_amt', '<=', self.minimum_amt), ('maximum_amt', '>=', self.minimum_amt),
            '&', ('minimum_amt', '<=', self.maximum_amt), ('maximum_amt', '>=', self.maximum_amt),
            '&', ('minimum_amt', '>=', self.minimum_amt), ('maximum_amt', '<=', self.maximum_amt)
        )
        if res_domain:
            domain = (res_domain,) + domain
        return domain
            
    @api.constrains('branch_id', 'minimum_amt', 'maximum_amt', 'order_type')
    def _check_existing_record(self):
        for record in self:
            if record.branch_id and record.is_good_services_order:
                approval_matrix_id = self.search([dom for dom in record.get_domain_approval(('order_type', '=', record.order_type))], limit = 1)
                if approval_matrix_id:
                    raise ValidationError("There are the other approval matrix %s in same Branch, Order Type and minimum / maximum Amount. Please change branch , order type or minimum and maximum amount." % (approval_matrix_id.name))
            else:
                approval_matrix_id = self.search([dom for dom in record.get_domain_approval(False)], limit = 1)
                if approval_matrix_id:
                    raise ValidationError("The minimum and maximum range of this approval matrix is intersects with other approval matrix %s in same branch. Please change the minimum and maximum range" % (approval_matrix_id.name))

    def _reset_sequence(self):
        for rec in self:
            current_sequence = 1
            for line in rec.approval_matrix_purchase_order_line_ids:
                line.sequence = current_sequence
                current_sequence += 1

    @api.onchange('company_id')
    def onchange_company_id(self):
        self._compute_is_good_services_order()


class ApprovalMatrixPurchaseOrderLine(models.Model):
    _name = "approval.matrix.purchase.order.line"
    _description = "Approval Matrix Purchase Order Line"

    @api.model
    def default_get(self, fields):
        res = super(ApprovalMatrixPurchaseOrderLine, self).default_get(fields)
        if self._context:
            context_keys = self._context.keys()
            next_sequence = 1
            if 'approval_matrix_purchase_order_line_ids' in context_keys:
                if len(self._context.get('approval_matrix_purchase_order_line_ids')) > 0:
                    next_sequence = len(self._context.get('approval_matrix_purchase_order_line_ids')) + 1
            res.update({'sequence': next_sequence})
        return res

    sequence = fields.Integer(string="Sequence")
    user_ids = fields.Many2many('res.users', string="User", required=True)
    minimum_approver = fields.Integer(string="Minimum Approver", default=1, required=True)
    approval_matrix_purchase_order = fields.Many2one('approval.matrix.purchase.order', string="Approval Matrix")

    sequence2 = fields.Integer(
        string="No.",
        related="sequence",
        readonly=True,
        store=True
    )
    approved_users = fields.Many2many('res.users', 'approved_users_purchase_patner_rel', 'order_id', 'user_id', string='Users')
    state_char = fields.Text(string='Approval Status')
    time_stamp = fields.Datetime(string='TimeStamp')
    feedback = fields.Char(string='Feedback')
    last_approved = fields.Many2one('res.users', string='Users')
    approved = fields.Boolean('Approved')
    order_id = fields.Many2one('purchase.order', string="Purchase Order")
    approver_state = fields.Selection([('draft', 'Draft'), ('pending', 'Pending'), ('approved', 'Approved'),
                                       ('refuse', 'Refused')], default='draft', string="State")

    def unlink(self):
        approval = self.approval_matrix_purchase_order
        res = super(ApprovalMatrixPurchaseOrderLine, self).unlink()
        approval._reset_sequence()
        return res

    @api.model
    def create(self, vals):
        res = super(ApprovalMatrixPurchaseOrderLine, self).create(vals)
        if not self.env.context.get("keep-line_sequence", False):
            res.approval_matrix_purchase_order._reset_sequence()
        return res
