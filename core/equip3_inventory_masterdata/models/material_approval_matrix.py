

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError, Warning

class MaterialApprovalMatrix(models.Model):
    _name = "mr.approval.matrix"
    _description = "Material Approval Matrix"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']

    name = fields.Char(string="Name", required=True, tracking=True)
    company_id = fields.Many2one('res.company', string="Company", required=True, tracking=True, readonly=True, default=lambda self: self.env.company.id)
    branch_id = fields.Many2one('res.branch', string="Branch", domain="[('company_id', '=', company_id)]", tracking=True)
    warehouse_id = fields.Many2one('stock.warehouse', string="Warehouse", tracking=True, required=True)
    approval_line_count = fields.Integer(string="Level", compute='approval_line_calc', tracking=True)
    mr_approval_matrix_line_ids = fields.One2many('mr.approval.matrix.line', 'mr_approval_matrix', string='Material Approving Matrix')
    location_child_ids = fields.Many2many('stock.location', 'locattion_matrix_rel', 'location_id', string="Details")

    @api.onchange('company_id')
    def onchange_company_id(self):
        self.branch_id = False

    @api.onchange('warehouse_id')
    def onchange_warehouse(self):
        location_ids = []
        if self.warehouse_id:
            location_obj = self.env['stock.location']
            store_location_id = self.warehouse_id.view_location_id.id
            addtional_ids = location_obj.search([('location_id', 'child_of', store_location_id), ('usage', '=', 'internal')])
            for location in addtional_ids:
                if location.location_id.id not in addtional_ids.ids:
                    location_ids.append(location.id)
            child_location_ids = self.env['stock.location'].search([('id', 'child_of', location_ids), ('id', 'not in', location_ids)]).ids
            final_location = child_location_ids + location_ids
            self.location_child_ids = [(6, 0, final_location)]
        else:
            self.location_child_ids = [(6, 0, [])]

    @api.depends('mr_approval_matrix_line_ids')
    def approval_line_calc(self):
        for record in self:
            record.approval_line_count = len(record.mr_approval_matrix_line_ids)


    @api.constrains('location_child_ids')
    def check_approver_sequence(self):
        for record in self:
            for location in record.location_child_ids:
                location_obj = self.env['mr.approval.matrix'].search([('location_child_ids', 'in', location.ids), ('id', '!=', record.id)], limit=1)
                if location_obj:
                    raise ValidationError("Location exists %s in Material Request %s" %(location.display_name, location_obj.name))

    def unlink(self):
        for record in self:
            running_material_request = self.env['material.request'].search([('mr_approval_matrix_id', '=', record.id)], limit=1)
            if running_material_request:
                raise Warning(_("Unable to delete this approval matrix settings due to the approval has been used by running material request."))
        return super(MaterialApprovalMatrix, self).unlink()

class MaterialApprovalMatrixLine(models.Model):
    _name = "mr.approval.matrix.line"
    _description = "Material Approval Matrix Line"

    @api.model
    def default_get(self, fields):
        res = super(MaterialApprovalMatrixLine, self).default_get(fields)
        if self._context:
            context_keys = self._context.keys()
            next_sequence = 1
            if 'mr_approval_matrix_line_ids' in context_keys:
                if len(self._context.get('mr_approval_matrix_line_ids')) > 0:
                    next_sequence = len(self._context.get('mr_approval_matrix_line_ids')) + 1
            res.update({'sequence': next_sequence})
        return res

    sequence = fields.Integer(string="Sequence")
    user_ids = fields.Many2many('res.users', string="User", required=True)
    minimum_approver = fields.Integer(string="Minimum Approver", default=1, required=True)
    mr_approval_matrix = fields.Many2one('mr.approval.matrix', string="Material Approval Matrix")
    approved_users = fields.Many2many('res.users', 'approved_users_material_patner_rel', 'mr_id', 'user_id', string='Users')
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
