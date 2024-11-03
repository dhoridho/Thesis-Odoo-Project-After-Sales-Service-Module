from odoo import models, fields, api, _
from datetime import datetime, date, timedelta
from odoo.exceptions import ValidationError


class DeliveryOrderApprovalMatrix(models.Model):
    _name = 'do.approval.matrix'
    _description = "Delivery Order Approval Matrix"
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
    do_approval_matrix_line_ids = fields.One2many(
        'do.approval_matrix_line', 'do_approval_matrix_id1', string='Approver Line')
    do_approval_matrix_details_id = fields.One2many(
        'do.approval_matrix_detail', 'do_approval_matrix_id2', string='Details')
    location_child_ids = fields.Many2many(
        'stock.location', 'location_matrix_rel_id', 'loc_id', string="Locations")
    level = fields.Integer('Level', compute='compute_level')

    def compute_level(self):
        for record in self:
            record.level = len(record.do_approval_matrix_line_ids)

    @api.constrains('warehouse_id')
    def check_if_location_exists(self):
        current_model = self.env['do.approval.matrix'].search(
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


class DOApprovalMatrixLine(models.Model):
    _name = 'do.approval_matrix_line'
    _description = "Delivery Order Approval line"

    @api.model
    def default_get(self, fields):
        res = super(DOApprovalMatrixLine, self).default_get(fields)
        if self._context:
            context_keys = self._context.keys()
            next_sequence = 1
            if 'do_approval_matrix_line_ids' in context_keys:
                if len(self._context.get('do_approval_matrix_line_ids')) > 0:
                    next_sequence = len(self._context.get(
                        'do_approval_matrix_line_ids')) + 1
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
    do_approval_matrix_id1 = fields.Many2one('do.approval.matrix')
    picking_id = fields.Many2one('stock.picking', string='picking')
    approved_users = fields.Many2many(
        'res.users', 'approved_users_delivery_partner_rel', 'do_id', 'user_id', string='Users')

    @api.constrains('minimal_approver', 'approver')
    def min_approver_validation(self):
        for record in self:
            if len(record.approver) < record.minimal_approver:
                raise ValidationError(
                    "The number of approvers must be bigger or equal with the quantity of Minimum Approver.")


class DOApprovalMatrixDetailsTa(models.Model):
    _name = 'do.approval_matrix_detail'
    _description = 'DO Approval Matrix Detail'

    location_name = fields.Many2many('stock.location', 'location_do_approval_detail_id',
                                     'loc_id', 'do_appr_detail_id', string='Location Name', readonly='1')
    usage = fields.Selection([
        ('supplier', 'Vendor Location'),
        ('view', 'View'),
        ('internal', 'Internal Location'),
        ('customer', 'Customer Location'),
        ('inventory', 'Inventory Loss'),
        ('production', 'Production'),
        ('transit', 'Transit Location')], string='Location Type', readonly='1')
    company_id = fields.Many2one('res.company', 'Company', readonly='1')
    do_approval_matrix_id2 = fields.Many2one('do.approval.matrix')
