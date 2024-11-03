from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ReceivingNotesApprovalMatrix(models.Model):
    _name = 'rn.approval.matrix'
    _description = "Receiving Notes Approval Matrix"
    _rec_name = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Name", required=True, tracking=True)
    company_id = fields.Many2one(
        'res.company', 'Company', tracking=True, default=lambda self: self.env.company)
    branch_id = fields.Many2one(
        'res.branch', 'Branch', tracking=True,  default=lambda self: self.env.branch)
    warehouse_id = fields.Many2one(
        'stock.warehouse', 'Warehouse', tracking=True, required='1')
    create_date = fields.Datetime('Create On', tracking=True, readonly='1')
    create_uid = fields.Many2one(
        'res.users', 'Created by', tracking=True, readonly='1')
    rn_approval_matrix_line_ids = fields.One2many(
        'rn.approval_matrix_line', 'rn_approval_matrix_id1', string='Approver Line')
    rn_approval_matrix_details_id = fields.One2many(
        'rn.approval_matrix_detail', 'rn_approval_matrix_id2', string='Details')
    location_child_ids = fields.Many2many(
        'stock.location', 'locattion_matrix_rel_id', 'loc_id', string="Locations")
    level = fields.Integer('Level', compute='compute_level')

    def compute_level(self):
        for record in self:
            record.level = len(record.rn_approval_matrix_line_ids)

    @api.constrains('warehouse_id')
    def check_if_location_exists(self):
        current_model = self.env['rn.approval.matrix'].search(
            [('warehouse_id', '=', self.warehouse_id.id)], limit=1)
        if current_model and current_model.id != self.id:
            raise ValidationError("%s exists in %s" % (
                self.warehouse_id.name, current_model.name))

    @api.onchange('warehouse_id')
    def onchange_warehouse(self):
        location_ids = []
        if self.warehouse_id:
            location_obj = self.env['stock.location']
            store_location_id = self.warehouse_id.view_location_id.id
            addtional_ids = location_obj.search(
                [('location_id', 'child_of', store_location_id), ('usage', '=', 'internal')])
            for location in addtional_ids:
                if location.location_id.id not in addtional_ids.ids:
                    location_ids.append(location.id)
            child_location_ids = self.env['stock.location'].search(
                [('id', 'child_of', location_ids), ('id', 'not in', location_ids)]).ids
            final_location = child_location_ids + location_ids
            self.location_child_ids = [(6, 0, final_location)]
        else:
            self.location_child_ids = [(6, 0, [])]


class RnApprovalMatrixLine(models.Model):
    _name = 'rn.approval_matrix_line'
    _description = "Receiving Notes Approval line"

    @api.model
    def default_get(self, fields):
        res = super(RnApprovalMatrixLine, self).default_get(fields)
        if self._context:
            context_keys = self._context.keys()
            next_sequence = 1
            if 'rn_approval_matrix_line_ids' in context_keys:
                if len(self._context.get('rn_approval_matrix_line_ids')) > 0:
                    next_sequence = len(self._context.get(
                        'rn_approval_matrix_line_ids')) + 1
            res.update({'sequence': next_sequence})
        return res

    sequence = fields.Integer('Sequence')
    sequence1 = fields.Integer(
        string="No.",
        related="sequence",
        readonly=True,
        store=True
    )
    approver = fields.Many2many('res.users', string='Approver', required=True)
    minimal_approver = fields.Integer('Minimum Approver', default=1)
    approval_status = fields.Text(string='Approval Status')
    feedback = fields.Char(string='Feedback')
    time_stamp = fields.Datetime(string='TimeStamp')
    last_approved = fields.Many2one('res.users', string='Last Approved User')
    approved = fields.Boolean('Approved')
    rn_approval_matrix_id1 = fields.Many2one('rn.approval.matrix')
    picking_id = fields.Many2one('stock.picking', string='picking')
    approved_users = fields.Many2many(
        'res.users', 'approved_users_receiving_partner_rel', 'rn_id', 'user_id', string='Users')
    state = fields.Text(string='State', compute='compute_state', store=True)

    def get_selection_label(self, object, field_name, field_value):
        return _(dict(self.env[object].fields_get(allfields=[field_name])[field_name]['selection'])[field_value])

    # @api.onchange('approver')
    # def onchange_approver(self):
    #     if self.approver and len(self.approver.ids) > 0:
    #         self.minimal_approver = 1
    #     elif not self.approver and len(self.approver.ids) <= 0:
    #         self.minimal_approver = 0

    @api.constrains('minimal_approver', 'approver')
    def min_approver_validation(self):
        for record in self:
            if len(record.approver) < record.minimal_approver:
                raise ValidationError(
                    "The number of approvers must be bigger or equal with the quantity of Minimum Approver.")

    @api.depends('picking_id.state')
    def compute_state(self):
        if self:
            for record in self:
                if record.picking_id:
                    state = self.get_selection_label(
                        'stock.picking', 'state', record.picking_id.state)
                    record.state = state
                else:
                    record.state = ''


class RnApprovalMatrixDetailsTa(models.Model):
    _name = 'rn.approval_matrix_detail'
    _description = 'RN Approval Matrix Detail'

    location_name = fields.Many2many('stock.location', 'location_rn_approval_detail_id',
                                     'loc_id', 'rn_appr_detail_id', string='Location Name', readonly='1')
    usage = fields.Selection([
        ('supplier', 'Vendor Location'),
        ('view', 'View'),
        ('internal', 'Internal Location'),
        ('customer', 'Customer Location'),
        ('inventory', 'Inventory Loss'),
        ('production', 'Production'),
        ('transit', 'Transit Location')], string='Location Type', readonly='1')
    company_id = fields.Many2one('res.company', 'Company', readonly='1')
    rn_approval_matrix_id2 = fields.Many2one('rn.approval.matrix')
