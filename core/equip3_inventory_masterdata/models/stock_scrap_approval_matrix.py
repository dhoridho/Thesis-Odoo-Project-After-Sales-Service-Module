

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError, Warning

class StockScrapApprovalMatrix(models.Model):
    _name = "stock.scrap.approval.matrix"
    _description = "Stock Scrap Approval Matrix"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']

    name = fields.Char(string="Name", required=True, tracking=True)
    company_id = fields.Many2one('res.company', string="Company", required=True, tracking=True, readonly=True, default=lambda self: self.env.company.id)
    warehouse_id = fields.Many2one('stock.warehouse', string="Warehouse", tracking=True, required=True)
    branch_id = fields.Many2one('res.branch', string="Branch", related='warehouse_id.branch_id', tracking=True)
    approval_line_count = fields.Integer(string="Level", compute='approval_line_calc', tracking=True)
    sc_approval_matrix_line_ids = fields.One2many('stock.scrap.approval.matrix.line', 'sc_approval_matrix', string='Stock Scrap Approving Matrix')

    @api.onchange('company_id')
    def onchange_company_id(self):
        self.branch_id = False

    @api.depends('sc_approval_matrix_line_ids')
    def approval_line_calc(self):
        for record in self:
            record.approval_line_count = len(record.sc_approval_matrix_line_ids)


    @api.constrains('warehouse_id')
    def check_approver_sequence(self):
        for record in self:
            warhouse_obj = self.env['stock.scrap.approval.matrix'].search([('warehouse_id', '=', record.warehouse_id.id), ('id', '!=', record.id)], limit=1)
            if warhouse_obj:
                raise ValidationError("Warehouse %s exists in %s" %(record.warehouse_id.name, warhouse_obj.name))

    def unlink(self):
        for record in self:
            waiting_approval = self.env['stock.scrap.request'].search([('approval_matrix_id', '=', record.id)], limit=1)
            if waiting_approval:
                raise Warning(_("Unable to delete this approval matrix settings due to the approval has been used by running product usage."))
        return super(StockScrapApprovalMatrix, self).unlink()

class StockScrapApprovalMatrixLine(models.Model):
    _name = "stock.scrap.approval.matrix.line"
    _description = "Stock Scrap Approval Matrix Line"

    @api.model
    def default_get(self, fields):
        res = super(StockScrapApprovalMatrixLine, self).default_get(fields)
        if self._context:
            context_keys = self._context.keys()
            next_sequence = 1
            if 'sc_approval_matrix_line_ids' in context_keys:
                if len(self._context.get('sc_approval_matrix_line_ids')) > 0:
                    next_sequence = len(self._context.get('sc_approval_matrix_line_ids')) + 1
            res.update({'sequence': next_sequence})
        return res

    sequence = fields.Integer(string="Sequence")
    user_ids = fields.Many2many('res.users', string="User", required=True)
    minimum_approver = fields.Integer(string="Minimum Approver", default=1, required=True)
    sc_approval_matrix = fields.Many2one('stock.scrap.approval.matrix', string="Stock Scrap Approval Matrix")
    approved_users = fields.Many2many('res.users', 'approved_users_scrap_patner_rel', 'scrap_id', 'user_id', string='Users')
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

    @api.constrains('minimum_approver', 'user_ids')
    def check_approver_sequence(self):
        for record in self:
            if record.minimum_approver > len(record.user_ids):
                raise ValidationError("The number of approvers must be bigger or equal with the quantity of Minimum Approver.")
