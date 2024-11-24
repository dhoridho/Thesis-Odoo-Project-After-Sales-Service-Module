

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError, Warning

class StockCountApprovalMatrix(models.Model):
    _name = "stock.inventory.approval.matrix"
    _description = "Stock Count Approval Matrix"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']

    name = fields.Char(string="Name", required=True, tracking=True)
    company_id = fields.Many2one('res.company', string="Company", required=True, tracking=True, readonly=True, default=lambda self: self.env.company.id)
    branch_id = fields.Many2one('res.branch', string="Branch", related='warehouse_id.branch_id', tracking=True)
    warehouse_id = fields.Many2one('stock.warehouse', string="Warehouse", tracking=True, required=True)
    approval_line_count = fields.Integer(string="Level", compute='approval_line_calc', tracking=True)
    si_approval_matrix_line_ids = fields.One2many('stock.inventory.approval.matrix.line', 'si_approval_matrix', string='Stock Count Approving Matrix')
    
    @api.onchange('company_id')
    def onchange_company_id(self):
        self.branch_id = False

    @api.depends('si_approval_matrix_line_ids')
    def approval_line_calc(self):
        for record in self:
            record.approval_line_count = len(record.si_approval_matrix_line_ids)


    @api.constrains('warehouse_id')
    def check_approver_sequence(self):
        for record in self:
            warhouse_obj = self.env['stock.inventory.approval.matrix'].search([('warehouse_id', '=', record.warehouse_id.id), ('id', '!=', record.id)], limit=1)
            if warhouse_obj:
                raise ValidationError("Warehouse %s exists in %s" %(record.warehouse_id.name, warhouse_obj.name))

class StockCountApprovalMatrixLine(models.Model):
    _name = "stock.inventory.approval.matrix.line"
    _description = "Stock Count Approval Matrix Line"

    @api.model
    def default_get(self, fields):
        res = super(StockCountApprovalMatrixLine, self).default_get(fields)
        if self._context:
            context_keys = self._context.keys()
            next_sequence = 1
            if 'si_approval_matrix_line_ids' in context_keys:
                if len(self._context.get('si_approval_matrix_line_ids')) > 0:
                    next_sequence = len(self._context.get('si_approval_matrix_line_ids')) + 1
            res.update({'sequence': next_sequence})
        return res

    sequence = fields.Integer(string="Sequence")
    user_ids = fields.Many2many('res.users', string="User", required=True)
    minimum_approver = fields.Integer(string="Minimum Approver", default=1, required=True)
    si_approval_matrix = fields.Many2one('stock.inventory.approval.matrix', string="Stock Count Approval Matrix")
    st_inv_id = fields.Many2one('stock.inventory', string="Inventory Adjustments")
    approved_users = fields.Many2many('res.users', 'approved_users_inv_patner_rel', 'inv_id', 'user_id', string='Users')
    state_char = fields.Text(string='Approval Status')
    time_stamp = fields.Datetime(string='TimeStamp')
    feedback = fields.Char(string='Feedback')
    last_approved = fields.Many2one('res.users', string='Last Approved User')
    approved = fields.Boolean('Approved')
    sequence2 = fields.Integer(
        string="No.",
        related="sequence",
        readonly=True,
        store=True
    )

    # @api.constrains('minimum_approver', 'user_ids')
    # def check_approver_sequence(self):
    #     for record in self:
    #         if record.minimum_approver > len(record.user_ids):
    #             raise ValidationError("The number of approvers must be bigger or equal with the quantity of Minimum Approver.")