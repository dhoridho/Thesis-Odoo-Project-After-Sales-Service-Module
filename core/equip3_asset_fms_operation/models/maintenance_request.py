from odoo import models, fields, api, _
from datetime import datetime,date
from odoo.exceptions import ValidationError, Warning
import pytz
from pytz import timezone, UTC
from odoo import tools
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT


class MaintenanceRequest(models.Model):
    _inherit = 'maintenance.request'

    name = fields.Char('Maintenance Request')
    contact_number = fields.Char("Contact Number")
    facility_area = fields.Many2one ('maintenance.facilities.area', string='Facilities Area', required=True)
    facility = fields.Char('Facility')
    remarks = fields.Text('Remarks')
    reference = fields.Char(string='Reference')
    maintenance_team = fields.Many2one(comodel_name='maintenance.team', string='Maintenance Team')
    work_order_count = fields.Integer(compute='get_orders_count')
    note = fields.Text('Note')
    is_create_work_order = fields.Boolean(related='stage_id.create_work_order', store=True)
    last_wo = fields.Many2one('maintenance.work.order', string='Last Work Order', readonly=True, compute='get_last_wo')
    last_wo_date = fields.Date(string='Last Work Order', readonly=True, compute='get_last_wo')
    last_wo_state = fields.Selection(
        [('draft', 'Draft'),
         ('in_progress', 'In Progress'),
         ('pending', 'Post'),
         ('done', 'Done'),
         ('cancel', 'Cancelled')],
        string="Last Work Order State", readonly=True, compute='get_last_wo')
    maintenance_request_approval_line = fields.One2many(comodel_name='maintenance.request.approval.line', inverse_name='maintenance_id')
    is_need_approval = fields.Boolean(string='Is Triggered', compute='_compute_is_need_approval', store=True)
    extra_state = fields.Selection(string='State', selection=[('new', 'New Request'), ('waiting', 'Waiting for Approval'),('approved', 'Approved'),('progress', 'In Progress'),('done', 'Done'),('reject', 'Rejected'),('cancel', 'Cancelled'),], default='new', help='additional state with selection', copy=False)
    approval_matrix_id = fields.Many2one(comodel_name='approval.matrix.maintenance.request', string='Approval Matrix')
    is_user_approve = fields.Boolean(string='Is User Approve', compute='_compute_is_user_approve')
    analytic_group_ids = fields.Many2many(comodel_name='account.analytic.tag', string='Analytic Group')


    def button_confirm(self):
        if self.is_need_approval:
            next_stage = self.env['maintenance.stage'].search([('sequence', '>', self.stage_id.sequence)], limit=1)
            self.write({'extra_state': 'waiting', 'stage_id': next_stage.id})
        else:
            next_stage = self.env['maintenance.stage'].search([('name', '=', 'In Progress')], limit=1)
            self.write({'extra_state': 'progress', 'stage_id': next_stage.id})


    @api.depends('maintenance_request_approval_line','is_need_approval')
    def _compute_is_need_approval(self):
        for rec in self:
            rec.is_need_approval = False

            fms_accessright_installed = self.env['ir.module.module'].search([('name', '=', 'equip3_asset_fms_accessright_setting'), ('state', '=', 'installed')])
            if fms_accessright_installed:
                
                approval_matrix = False

                if self.env.user.has_group('equip3_asset_fms_accessright_setting.group_asset_administrator'):
                    approval_matrix = rec.env['approval.matrix.maintenance.request'].search([('access_type', '=', 'admin')], limit=1)

                elif self.env.user.has_group('equip3_asset_fms_accessright_setting.group_asset_manager'):
                    approval_matrix = rec.env['approval.matrix.maintenance.request'].search([('access_type', '=', 'manager')], limit=1)

                elif self.env.user.has_group('equip3_asset_fms_accessright_setting.group_asset_user'):
                    approval_matrix = rec.env['approval.matrix.maintenance.request'].search([('access_type', '=', 'user')], limit=1)

                if approval_matrix:
                    rec.write({'is_need_approval': True, 'approval_matrix_id': approval_matrix.id})

                    list_approval = [(5, 0, 0)]
                    for line in approval_matrix.approval_matrix_maintenance_line:
                        if not line:
                            raise ValidationError(_('Please fill approve user in approval matrix.'))
                        list_approval.append((0, 0, {
                            'user_ids': [(6, 0, line.user_ids.ids)],
                            'minimum_approval': line.minimum_approval,
                            'approved_status': 'waiting',
                        }))
                    if not rec.maintenance_request_approval_line:
                        rec.maintenance_request_approval_line = list_approval
                else:
                    rec.write({'is_need_approval': False})

    def _compute_is_user_approve(self):
        self.is_user_approve = False
        if self.maintenance_request_approval_line:
            for line in self.maintenance_request_approval_line:
                if self.env.uid in line.user_ids.ids and self.env.uid not in line.approved_user_ids.ids:
                    self.is_user_approve = True
                else:
                    self.is_user_approve = False


    def button_approve(self):
        for rec in self:
            fms_accessright_installed = self.env['ir.module.module'].search([('name', '=', 'equip3_asset_fms_accessright_setting'), ('state', '=', 'installed')])
            if fms_accessright_installed:

                approval_matrix = rec.env['approval.matrix.maintenance.request'].search([('access_type', '=', 'user')], limit=1)
                if approval_matrix:
                    for line in rec.maintenance_request_approval_line:
                        user_approval = line.user_ids.ids
                        approved_user = line.approved_user_ids.ids
                        if self.env.uid in user_approval and self.env.uid not in approved_user:
                            rec.maintenance_request_approval_line.search([('user_ids', '=', self.env.uid)]).write({'approved_user_ids': [(4, self.env.uid)], 'approved_status': 'progress'})

                        if len(line.approved_user_ids.ids) == line.minimum_approval:
                            line.write({'approved_status': 'approved'})

                        if all(line.approved_status == 'approved' for line in rec.maintenance_request_approval_line):
                            next_stage = self.env['maintenance.stage'].search([('sequence', '>', self.stage_id.sequence)], limit=1)
                            rec.write({'extra_state': 'approved', 'stage_id': next_stage.id})

    def button_reject(self):
        next_stage = self.env['maintenance.stage'].search([('sequence', '>', self.stage_id.sequence + 3)], limit=1)
        self.write({'extra_state': 'reject', 'stage_id': next_stage.id})

    def button_progress(self):
        next_stage = self.env['maintenance.stage'].search([('sequence', '>', self.stage_id.sequence)], limit=1)
        self.write({'extra_state': 'progress', 'stage_id': next_stage.id})

    def button_done(self):
        if self.extra_state == 'approved':
            next_stage = self.env['maintenance.stage'].search([('sequence', '>', self.stage_id.sequence + 1)], limit=1)
            self.write({'extra_state': 'done', 'stage_id': next_stage.id})
        else:
            next_stage = self.env['maintenance.stage'].search([('name', '=', 'Done')], limit=1)
            self.write({'extra_state': 'done', 'stage_id': next_stage.id})

    def archive_equipment_request(self):
        res = super(MaintenanceRequest, self).archive_equipment_request()
        next_stage = self.env['maintenance.stage'].search([('name', '=', 'Cancelled')], limit=1)
        self.write({'extra_state': 'cancel','maintenance_request_approval_line': [(5, 0, 0)], 'stage_id': next_stage.id})
        return res

    def reset_equipment_request(self):
        res = super(MaintenanceRequest, self).reset_equipment_request()
        self.write({'extra_state': 'new'})
        return res



    def get_last_wo(self):
        for rec in self:
            last_wo = self.env['maintenance.work.order'].search([('maintainence_request_id','=',rec.id)],order='id desc',limit=1)
            if last_wo:
                rec.last_wo = last_wo.id
                rec.last_wo_date = last_wo.startdate
                rec.last_wo_state = last_wo.state_id
            else:
                rec.last_wo = False
                rec.last_wo_date = False
                rec.last_wo_state = False

    @api.onchange('facility_area')
    def onchange_facility_area(self):
        for rec in self:
            return {'domain': {'equipment_id': [('fac_area', '=', rec.facility_area.id)]}}

    def get_orders_count(self):
        for rec in self:
            order_count = self.env['maintenance.work.order'].search([('maintainence_request_id','=',rec.id)]).ids
            rec.work_order_count = len(order_count)

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('maintainance.request.sequence') or 'New'
        return super(MaintenanceRequest, self).create(vals)

    def create_work_order(self):
        view_id = self.env.ref('equip3_asset_fms_operation.create_work_order_views').id
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Work Order'),
            'res_model': 'work.order.wizard',
            'target': 'new',
            'view_mode': 'form',
            'views': [[view_id, 'form']],
            'context': {
                'default_asset_id': self.equipment_id.id,
                'default_facility_area':self.facility_area.id,
                'default_description':self.remarks,
                'request_note':self.note,
                'default_ref':self.name,
            }
        }

    def create_work_order_new(self):
        # this button is used to create work order from maintenance request from the above function
        # the reason why we have created this function is because we have to invisible the button in the view based on asset group
        view_id = self.env.ref('equip3_asset_fms_operation.create_work_order_views').id
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Work Order'),
            'res_model': 'work.order.wizard',
            'target': 'new',
            'view_mode': 'form',
            'views': [[view_id, 'form']],
            'context': {
                'default_asset_id': self.equipment_id.id,
                'default_facility_area':self.facility_area.id,
                'default_description':self.remarks,
                'request_note':self.note,
                'default_ref':self.name,
            }
        }

    def button_cancel(self):
        # this button is used to create work order from maintenance request from the above function
        # the reason why we have created this function is because we have to invisible the button in the view based on asset group
        self.archive_equipment_request()

    def action_view_work_order(self):
        work_orders = self.env['maintenance.work.order'].search([('maintainence_request_id','=',self.id)]).ids
        action = {
            'name': _('Maintenance Work Orders'),
            'type': 'ir.actions.act_window',
            'res_model': 'maintenance.work.order',
            'target': 'current',
        }
        if len(work_orders) == 1:
            wk_order = work_orders[0]
            action['res_id'] = wk_order
            action['view_mode'] = 'form'
            form_view = [(self.env.ref('equip3_asset_fms_operation.maintenance_work_order_view_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state, view) for state, view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
        else:
            action['view_mode'] = 'tree,form'
            action['domain'] = [('id', 'in', work_orders)]
        return action

    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Import Template for Maintenance Request '),
            'template': '/equip3_asset_fms_operation/static/xls/request_template.xls'
        }]

    def get_selection_label(self, field_name, field_value):
        field = self._fields.get(field_name)
        if field and field.type == 'selection':
            selection_dict = dict(self._fields[field_name].selection)
            label = selection_dict.get(field_value)
        return label

    def unlink(self):
        for record in self:
            if record.extra_state in ('progress', 'done'):
                state_label = record.get_selection_label('extra_state', record.extra_state)
                if state_label:
                    raise ValidationError(f"You can not delete maintenance requests in '{state_label}' stage")
        return super(MaintenanceRequest, self).unlink()

class MaintenanceRequestApprovalLine(models.Model):
    _name = 'maintenance.request.approval.line'
    _description = 'Maintenance Request Approval Line'

    maintenance_id = fields.Many2one(comodel_name='maintenance.request', string='Maintenance Request')
    user_ids = fields.Many2many(comodel_name='res.users', string='Users')
    approved_user_ids = fields.Many2many(comodel_name='res.users', relation='maintenance_request_approval_line_approved_user_rel', string='Approved Users')
    approved_status = fields.Selection(string='Approved Status', selection=[('waiting', 'Waiting'), ('progress', 'In Progress'), ('approved', 'Approved')])
    minimum_approval = fields.Integer(string='Minimum Approval')

class ApprovalMwoLine(models.Model):
    _name = 'approval.mwo.line'
    _description = 'Approval Mwo Line'


    maintenance_id = fields.Many2one('maintenance.work.order')
    maintenance_id2 = fields.Many2one('maintenance.work.order')
    maintenance_id3 = fields.Many2one('maintenance.work.order')
    maintenance_id4 = fields.Many2one('maintenance.work.order')
    sequence = fields.Integer(string="Sequence")
    approval_matrix_mwo_id = fields.Many2one('approval.matrix.mwo')
    user_ids = fields.Many2many(comodel_name='res.users', string='User', required=True)
    min_approvers = fields.Integer(string='Minimum Approvers', required=True, default=1)
    approved = fields.Boolean(string="approved")
    last_approved = fields.Many2one('res.users', string='Users')
    approved_users = fields.Many2many('res.users', 'approved_users_mwo_rel', 'maintenance_work_id', 'user_id', string='Users')

MaintenanceRequest()

class MaintenanceWorkOrder(models.Model):
    _inherit = 'maintenance.work.order'

    maintainence_request_id = fields.Many2one('maintenance.request')
    # approvalmatrix = fields.Many2one('approval.matrix.mwo', string='Approval Matrix', required=False, readonly=True, compute='_compute_approvalmatrix')
    is_waiting_for_other_approvers = fields.Boolean(string='Waiting other approvers')
    approvers_id = fields.Many2many('res.users', string='Approvers')
    is_consume_material_checked = fields.Boolean(string="Is Consume Material Checked", default=False)

    is_approval_matrix = fields.Boolean(string='Is Approval Matrix', compute='_compute_isapprovalmatrix')
    approvalmatrix = fields.Many2one('approval.matrix.mwo', string='Approval Matrix',required=False, readonly=True, compute='_compute_isapprovalmatrix')
    approval_matrix_line_ids = fields.One2many('approval.mwo.line','maintenance_id', compute="_compute_approval_matrix_line_approve", store=True, string="Approval Matrix")
    approval_matrix_line_id = fields.Many2one('approval.matrix.mwo.line', string='MWO Approval Matrix Line', compute='_get_approve_button_mwo', store=False)
    is_approve_button = fields.Boolean('Is Approve Button', compute='_get_approve_button_mwo', store=False, default=False)

    approvalmatrix2 = fields.Many2one('approval.matrix.mwo', string='Approval Matrix 2',required=False, readonly=True, compute='_compute_isapprovalmatrix')
    approval_matrix_line_ids_done = fields.One2many('approval.mwo.line','maintenance_id2', compute="_compute_approval_matrix_line_done", store=True, string="Approval Matrix")
    approval_matrix_line_id_done = fields.Many2one('approval.matrix.mwo.line', string='MWO Approval Matrix Line Done', compute='_get_approve_button_mwo_done', store=False)
    is_approve_button_done = fields.Boolean('Is Approve Button Done', compute='_get_approve_button_mwo_done', store=False, default=False)

    approvalmatrix3 = fields.Many2one('approval.matrix.mwo', string='Approval Matrix 3',required=False, readonly=True, compute='_compute_isapprovalmatrix')
    approval_matrix_line_ids_post = fields.One2many('approval.mwo.line','maintenance_id3', compute="_compute_approval_matrix_line_post", store=True, string="Approval Matrix")
    approval_matrix_line_id_post = fields.Many2one('approval.matrix.mwo.line', string='MWO Approval Matrix Line Post', compute='_get_approve_button_mwo_post', store=False)
    is_approve_button_post = fields.Boolean('Is Approve Button Post', compute='_get_approve_button_mwo_post', store=False, default=False)
    in_progress_to_post = fields.Boolean('In Progress to Post')

    approvalmatrix4 = fields.Many2one('approval.matrix.mwo', string='Approval Matrix 4',required=False, readonly=True, compute='_compute_isapprovalmatrix')
    approval_matrix_line_ids_cancel = fields.One2many('approval.mwo.line','maintenance_id4', compute="_compute_approval_matrix_line_cancel", store=True, string="Approval Matrix")
    approval_matrix_line_id_cancel = fields.Many2one('approval.matrix.mwo.line', string='MWO Approval Matrix Line cancel', compute='_get_approve_button_mwo_cancel', store=False)
    is_approve_button_cancel = fields.Boolean('Is Approve Button Post', compute='_get_approve_button_mwo_cancel', store=False, default=False)

    @api.depends('branch_id')
    def _compute_isapprovalmatrix(self):
        self.approvalmatrix = self.env['approval.matrix.mwo'].search([('state','=','in_progress'),('branch_id', '=', self.branch_id.id)])
        self.approvalmatrix2 = self.env['approval.matrix.mwo'].search([('state','=','done'),('branch_id', '=', self.branch_id.id)])
        self.approvalmatrix3 = self.env['approval.matrix.mwo'].search([('state','=','pending'),('branch_id', '=', self.branch_id.id)])
        self.approvalmatrix4 = self.env['approval.matrix.mwo'].search([('state','=','cancel'),('branch_id', '=', self.branch_id.id)])
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        is_there = IrConfigParam.search([('key', '=', 'equip3_asset_fms_operation.is_approval_matix_mwo')])
        approval =  IrConfigParam.get_param('equip3_asset_fms_operation.is_approval_matix_mwo')
        for record in self:
            if is_there:
                record.is_approval_matrix = approval
            else:
                record.is_approval_matrix = False

    @api.depends('approvalmatrix')
    def _compute_approval_matrix_line_approve(self):
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        is_there = IrConfigParam.search([('key', '=', 'equip3_asset_fms_operation.is_approval_matix_mwo')])
        if is_there:
            data = [(5, 0, 0)]
            for record in self:
                counter = 1
                record.approval_matrix_line_ids = []
                for line in record.approvalmatrix.approval_matrix_mwo_ids:
                    data.append((0, 0, {
                        'sequence' : counter,
                        'user_ids': [(6, 0, line.user_ids.ids)],
                        'min_approvers' : line.min_approvers,
                    }))
                    counter += 1
                record.approval_matrix_line_ids = data
        else:
            self.approval_matrix_line_ids = False

    @api.depends('approvalmatrix2')
    def _compute_approval_matrix_line_done(self):
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        is_there = IrConfigParam.search([('key', '=', 'equip3_asset_fms_operation.is_approval_matix_mwo')])
        if is_there:
            data_done = [(5, 0, 0)]
            for record in self:
                counter = 1
                record.approval_matrix_line_ids_done = []
                for line in record.approvalmatrix2.approval_matrix_mwo_ids:
                    data_done.append((0, 0, {
                        'sequence' : counter,
                        'user_ids': [(6, 0, line.user_ids.ids)],
                        'min_approvers' : line.min_approvers,
                    }))
                    counter += 1
                record.approval_matrix_line_ids_done = data_done
        else:
            self.approval_matrix_line_ids_done = False

    @api.depends('approvalmatrix3')
    def _compute_approval_matrix_line_post(self):
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        is_there = IrConfigParam.search([('key', '=', 'equip3_asset_fms_operation.is_approval_matix_mwo')])
        if is_there:
            data_post = [(5, 0, 0)]
            for record in self:
                counter = 1
                record.approval_matrix_line_ids_post = []
                for line in record.approvalmatrix3.approval_matrix_mwo_ids:
                    data_post.append((0, 0, {
                        'sequence' : counter,
                        'user_ids': [(6, 0, line.user_ids.ids)],
                        'min_approvers' : line.min_approvers,
                    }))
                    counter += 1
                record.approval_matrix_line_ids_post = data_post
        else:
            self.approval_matrix_line_ids_post = False

    @api.depends('approvalmatrix4')
    def _compute_approval_matrix_line_cancel(self):
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        is_there = IrConfigParam.search([('key', '=', 'equip3_asset_fms_operation.is_approval_matix_mwo')])
        if is_there:
            data_post = [(5, 0, 0)]
            for record in self:
                counter = 1
                record.approval_matrix_line_ids_cancel = []
                for line in record.approvalmatrix4.approval_matrix_mwo_ids:
                    data_post.append((0, 0, {
                        'sequence' : counter,
                        'user_ids': [(6, 0, line.user_ids.ids)],
                        'min_approvers' : line.min_approvers,
                    }))
                    counter += 1
                record.approval_matrix_line_ids_cancel = data_post
        else:
            self.approval_matrix_line_ids_cancel = False

    def _get_approve_button_mwo(self):
        for record in self:
            matrix_line_mwo = sorted(record.approval_matrix_line_ids.filtered(lambda r: not r.approved), key=lambda r: r.sequence)
            if len(matrix_line_mwo) == 0:
                record.is_approve_button = False
                record.approval_matrix_line_id = False
            elif len(matrix_line_mwo) > 0:
                matrix_line = matrix_line_mwo[0]
                if self.env.user.id in matrix_line.user_ids.ids and self.env.user.id != matrix_line.last_approved.id:
                    record.is_approve_button = True
                    record.approval_matrix_line_id = matrix_line.id
                else:
                    record.is_approve_button = False
                    record.approval_matrix_line_id = False
            else:
                record.is_approve_button = False
                record.approval_matrix_line_id = False

    def _get_approve_button_mwo_done(self):
        for record in self:
            matrix_line_mwo = sorted(record.approval_matrix_line_ids_done.filtered(lambda r: not r.approved), key=lambda r: r.sequence)
            if len(matrix_line_mwo) == 0:
                record.is_approve_button_done = False
                record.approval_matrix_line_id_done = False
            elif len(matrix_line_mwo) > 0:
                matrix_line = matrix_line_mwo[0]
                if self.env.user.id in matrix_line.user_ids.ids and self.env.user.id != matrix_line.last_approved.id:
                    record.is_approve_button_done = True
                    record.approval_matrix_line_id_done = matrix_line.id
                else:
                    record.is_approve_button_done = False
                    record.approval_matrix_line_id_done = False
            else:
                record.is_approve_button_done = False
                record.approval_matrix_line_id_done = False

    def _get_approve_button_mwo_post(self):
        for record in self:
            matrix_line_mwo = sorted(record.approval_matrix_line_ids_post.filtered(lambda r: not r.approved), key=lambda r: r.sequence)
            if len(matrix_line_mwo) == 0:
                record.is_approve_button_post = False
                record.approval_matrix_line_id_post = False
            elif len(matrix_line_mwo) > 0:
                matrix_line = matrix_line_mwo[0]
                if self.env.user.id in matrix_line.user_ids.ids and self.env.user.id != matrix_line.last_approved.id:
                    record.is_approve_button_post = True
                    record.approval_matrix_line_id_post = matrix_line.id
                else:
                    record.is_approve_button_post = False
                    record.approval_matrix_line_id_post = False
            else:
                record.is_approve_button_post = False
                record.approval_matrix_line_id_post = False

    def _get_approve_button_mwo_cancel(self):
        for record in self:
            matrix_line_mwo = sorted(record.approval_matrix_line_ids_cancel.filtered(lambda r: not r.approved), key=lambda r: r.sequence)
            if len(matrix_line_mwo) == 0:
                record.is_approve_button_cancel = False
                record.approval_matrix_line_id_cancel = False
            elif len(matrix_line_mwo) > 0:
                matrix_line = matrix_line_mwo[0]
                if self.env.user.id in matrix_line.user_ids.ids and self.env.user.id != matrix_line.last_approved.id:
                    record.is_approve_button_cancel = True
                    record.approval_matrix_line_id_cancel = matrix_line.id
                else:
                    record.is_approve_button_cancel = False
                    record.approval_matrix_line_id_cancel = False
            else:
                record.is_approve_button_cancel = False
                record.approval_matrix_line_id_cancel = False

    def mwo_request_for_approval(self):
        for rec in self:
            self.write({'state_id' : 'to_approve'})

    def mwo_approving(self):
        for record in self:
            user = self.env.user
            if record.is_approve_button and record.approval_matrix_line_id:
                approval_matrix_line_id = sorted(record.approval_matrix_line_ids.filtered(lambda r: not r.approved), key=lambda r:r.sequence) # ini bayangan
                if user.id in approval_matrix_line_id[0].user_ids.ids and user.id not in approval_matrix_line_id[0].approved_users.ids:
                    name = ''
                    utc_datetime = datetime.now()
                    local_timezone = pytz.timezone(self.env.user.tz)
                    local_datetime = utc_datetime.replace(tzinfo=pytz.utc)
                    local_datetime = local_datetime.astimezone(local_timezone).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                    if name != '':
                        name += "\n • %s: Approved - %s" % (self.env.user.name, local_datetime)
                    else:
                        name += "• %s: Approved - %s" % (self.env.user.name, local_datetime)

                    approval_matrix_line_id[0].write({
                        'last_approved': self.env.user.id,
                        'approved_users': [(4, user.id)]})
                    if approval_matrix_line_id[0].min_approvers == len(approval_matrix_line_id[0].approved_users.ids):
                        approval_matrix_line_id[0].write({'approved': True})
            if len(record.approval_matrix_line_ids) == len(record.approval_matrix_line_ids.filtered(lambda r:r.approved)):
                record.write({'state_id': 'in_progress'})
                self.env['time.progress'].create(
                self._prepare_timeline_vals(self.time_in_progress, datetime.now()))
                record.approval_matrix_line_ids.write({'approved': False})

    def mwo_approving_done(self):
        for record in self:
            user = self.env.user
            if record.is_approve_button_done and record.approval_matrix_line_id_done:
                approval_matrix_line_id = sorted(record.approval_matrix_line_ids_done.filtered(lambda r: not r.approved), key=lambda r:r.sequence)
                if user.id in approval_matrix_line_id[0].user_ids.ids and user.id not in approval_matrix_line_id[0].approved_users.ids:
                    name = ''
                    utc_datetime = datetime.now()
                    local_timezone = pytz.timezone(self.env.user.tz)
                    local_datetime = utc_datetime.replace(tzinfo=pytz.utc)
                    local_datetime = local_datetime.astimezone(local_timezone).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                    if name != '':
                        name += "\n • %s: Approved - %s" % (self.env.user.name, local_datetime)
                    else:
                        name += "• %s: Approved - %s" % (self.env.user.name, local_datetime)

                    approval_matrix_line_id[0].write({
                        'last_approved': self.env.user.id,
                        'approved_users': [(4, user.id)]})
                    if approval_matrix_line_id[0].min_approvers == len(approval_matrix_line_id[0].approved_users.ids):
                        approval_matrix_line_id[0].write({'approved': True})
            if len(record.approval_matrix_line_ids_done) == len(record.approval_matrix_line_ids_done.filtered(lambda r:r.approved)):
                previous_state = self.state_id
                self.write({'state_id': 'done'})
                time_ids = self.time_ids.filtered(lambda r:not r.date_end)
                if time_ids:
                    time_ids.write({'date_end': datetime.now()})
                time_post_ids = self.time_post_ids.filtered(lambda r:not r.date_end)
                if time_post_ids:
                    time_post_ids.write({'date_end': datetime.now()})

                if self.maintenance_materials_list_ids:
                    if (self.repair_count > 0) or (self.delivery_order_count > 0):
                        previous_state = self.state_id
                        self.write({'state_id': 'done'})
                        if self.is_approval_matrix_defined():
                            self._is_unauthorized_user()
                            self._is_enough_approvers(previous_state)

                        self.update_equipment_state()

                        stock_pickings = self.env['stock.picking'].search([('mwo_id', 'in', self.ids)])
                        for stock_picking in stock_pickings:
                            stock_picking.button_validate()
                    # else:
                    #     raise ValidationError("You need to choose either consume materials or create repair order.")
                else:


                    self.update_equipment_state()

                    stock_pickings = self.env['stock.picking'].search([('mwo_id', 'in', self.ids)])
                    for stock_picking in stock_pickings:
                        stock_picking.button_validate()

    def mwo_approving_post(self):
        for record in self:
            user = self.env.user
            if record.is_approve_button_post and record.approval_matrix_line_id_post:
                approval_matrix_line_id = sorted(record.approval_matrix_line_ids_post.filtered(lambda r: not r.approved), key=lambda r:r.sequence)
                if user.id in approval_matrix_line_id[0].user_ids.ids and user.id not in approval_matrix_line_id[0].approved_users.ids:
                    name = ''
                    utc_datetime = datetime.now()
                    local_timezone = pytz.timezone(self.env.user.tz)
                    local_datetime = utc_datetime.replace(tzinfo=pytz.utc)
                    local_datetime = local_datetime.astimezone(local_timezone).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                    if name != '':
                        name += "\n • %s: Approved - %s" % (self.env.user.name, local_datetime)
                    else:
                        name += "• %s: Approved - %s" % (self.env.user.name, local_datetime)

                    approval_matrix_line_id[0].write({
                        'last_approved': self.env.user.id,
                        'approved_users': [(4, user.id)]})
                    if approval_matrix_line_id[0].min_approvers == len(approval_matrix_line_id[0].approved_users.ids):
                        approval_matrix_line_id[0].write({'approved': True})
            if len(record.approval_matrix_line_ids_post) == len(record.approval_matrix_line_ids_post.filtered(lambda r:r.approved)):
                record.write({'state_id': 'pending'})
                time_ids = self.time_ids.filtered(lambda r:not r.date_end)
                if time_ids:
                    time_ids.write({'date_end': datetime.now()})
                self.env['time.post'].create(
                    self._prepare_timeline_vals(self.time_post, datetime.now())
                )

                self.update_equipment_state()
                record.approval_matrix_line_ids_post.write({'approved': False})

    def mwo_approving_cancel(self):
        for record in self:
            user = self.env.user
            if record.is_approve_button_cancel and record.approval_matrix_line_id_cancel:
                approval_matrix_line_id = sorted(record.approval_matrix_line_ids_cancel.filtered(lambda r: not r.approved), key=lambda r:r.sequence)
                if user.id in approval_matrix_line_id[0].user_ids.ids and user.id not in approval_matrix_line_id[0].approved_users.ids:
                    name = ''
                    utc_datetime = datetime.now()
                    local_timezone = pytz.timezone(self.env.user.tz)
                    local_datetime = utc_datetime.replace(tzinfo=pytz.utc)
                    local_datetime = local_datetime.astimezone(local_timezone).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                    if name != '':
                        name += "\n • %s: Approved - %s" % (self.env.user.name, local_datetime)
                    else:
                        name += "• %s: Approved - %s" % (self.env.user.name, local_datetime)

                    approval_matrix_line_id[0].write({
                        'last_approved': self.env.user.id,
                        'approved_users': [(4, user.id)]})
                    if approval_matrix_line_id[0].min_approvers == len(approval_matrix_line_id[0].approved_users.ids):
                        approval_matrix_line_id[0].write({'approved': True})
            if len(record.approval_matrix_line_ids_cancel) == len(record.approval_matrix_line_ids_cancel.filtered(lambda r:r.approved)):
                record.write({'state_id': 'cancel'})
                time_ids = self.time_ids.filtered(lambda r:not r.date_end)
                if time_ids:
                    time_ids.write({'date_end': datetime.now()})
                self.env['time.post'].create(
                    self._prepare_timeline_vals(self.time_post, datetime.now())
                )

                self.update_equipment_state()
                record.approval_matrix_line_ids_cancel.write({'approved': False})

    def is_approval_matrix_defined(self):
        is_approval_matrix = self.env['ir.config_parameter'].sudo().get_param('equip3_asset_fms_operation.is_approval_matix_mwo')
        if is_approval_matrix == 'True':
            return True
        else:
            return False

    def consume_materials(self):
        location_id = []
        materials = self.maintenance_materials_list_ids
        for material in materials:
            if material.product_id.type == 'product':
                material_stock = self.env['stock.quant'].search(
                    [('product_id', '=', material.product_id.id), ('location_id', '=', material.location_id.id)])
                for material_stock in material_stock:
                    if material_stock.available_quantity < material.product_uom_qty:
                        raise Warning(
                            _('The materials you requested are not enough. You can filled in a Materials Request for an extra quantity'))
            if material.product_id.type in ['product', 'consu']:
                if location_id == []:
                    loc_vals = {'location_id': material.location_id.id,
                                'location_dest_id': material.location_dest_id.id}
                    location_id.append(loc_vals)
                else:
                    for loc in location_id:
                        if loc['location_id'] == material.location_id.id and loc[
                            'location_dest_id'] == material.location_dest_id.id:
                            break
                        else:
                            loc_vals = {'location_id': material.location_id.id,
                                        'location_dest_id': material.location_dest_id.id}
                            location_id.append(loc_vals)

        unique_location = [i for n, i in enumerate(location_id) if i not in location_id[n + 1:]]
        for loc in unique_location:
            # for loc in location_id:
            material_ids = []
            for material in materials:
                if material.product_id.type in ['product', 'consu']:
                    if loc['location_id'] == material.location_id.id and loc[
                        'location_dest_id'] == material.location_dest_id.id:
                        material_ids.append(material.id)
            stock_picking = self.env['stock.picking'].create({
                'mwo_id': self.id,
                # 'picking_type_id': self.env.ref('stock.picking_type_out').id,
                'picking_type_id': self.env['stock.picking.type'].search(
                    [('code', '=', 'outgoing'), ('default_location_src_id', '=', loc['location_id'])], limit=1).id,
                'location_id': loc['location_id'],
                'location_dest_id': loc['location_dest_id'],
                'analytic_account_group_ids': [(6, 0, self.analytic_group_id.ids)],
                'origin': self.name,
                'company_id': self.company_id.id,
                'branch_id': self.branch_id.id,
                'scheduled_date': fields.Datetime.now(),
            })
            for material in material_ids:
                self.env['stock.move'].create({
                    'picking_id': stock_picking.id,
                    'name': materials.browse(material).product_id.name,
                    'product_id': materials.browse(material).product_id.id,
                    'product_uom_qty': materials.browse(material).product_uom_qty,
                    'product_uom': materials.browse(material).uom_id.id,
                    'location_id': materials.browse(material).location_id.id,
                    'location_dest_id': materials.browse(material).location_dest_id.id,
                    'analytic_account_group_ids': [(6, 0, self.analytic_group_id.ids)],
                    'date': fields.Datetime.now(),
                    'quantity_done': materials.browse(material).product_uom_qty,
                })

            stock_picking.action_assign()
        self.is_consume_material_checked = True
        
    def _create_do_from_mwo(self):
        production_location = self.env['stock.location'].search([('usage', '=', 'production')], limit=1)
        
        for record in self.maintenance_materials_list_ids.sorted(key=lambda r: r.location_id.id):
            stock_move = self.env['stock.move'].create({
                'mwo_id': self.id,
                'name': record.product_id.name,
                'product_id': record.product_id.id,
                'product_uom_qty': record.product_uom_qty,
                'product_uom': record.uom_id.id,
                'picking_type_id': self.env['stock.picking.type'].search(
                    [('code', '=', 'outgoing'), ('default_location_src_id', '=', record.location_id.id)], limit=1).id,
                'location_id': record.location_id.id,
                'location_dest_id': production_location.id,
                'analytic_account_group_ids': [(6, 0, self.analytic_group_id.ids)],
                'date': fields.Datetime.now(),
                'quantity_done': record.product_uom_qty,
                'branch_id': self.branch_id.id
            })
            stock_move._action_confirm()
            stock_move._action_done()

            
    def state_confirm(self):
        # self.check_equipment_state()
        location_id = []
        materials = self.maintenance_materials_list_ids
        is_available = True
        for material in materials:
            if material.product_id.type == 'product':
                material_stock = self.env['stock.quant'].search([('product_id', '=', material.product_id.id), ('location_id', '=', material.location_id.id)])
                for material_stock in material_stock:
                    if material_stock.available_quantity < material.product_uom_qty:
                        is_available = False
                        self.is_material_not_available = True
        if not is_available:
            wizard = self.env['warning.wizard'].create({})
            return wizard.show_message(
                "The materials you requested are not enough. You can filled in a Materials Request for an extra quantity.")
        
        # else:
        #     self.is_material_not_available = False
        #     for material in materials:
        #         if material.product_id.type in ['product', 'consu']:
        #             if location_id == []:
        #                 loc_vals = {'location_id': material.location_id.id, 'location_dest_id': material.location_dest_id.id}
        #                 location_id.append(loc_vals)
        #             else:
        #                 for loc in location_id:
        #                     if loc['location_id'] == material.location_id.id and loc['location_dest_id'] == material.location_dest_id.id:
        #                         break
        #                     else:
        #                         loc_vals = {'location_id': material.location_id.id, 'location_dest_id': material.location_dest_id.id}
        #                         location_id.append(loc_vals)
        #
        # unique_location = [i for n, i in enumerate(location_id) if i not in location_id[n + 1:]]
        # for loc in unique_location:
        # # for loc in location_id:
        #     material_ids = []
        #     for material in materials:
        #         if material.product_id.type in ['product', 'consu']:
        #             if loc['location_id'] == material.location_id.id and loc['location_dest_id'] == material.location_dest_id.id:
        #                 material_ids.append(material.id)
        #     stock_picking = self.env['stock.picking'].create({
        #         'mwo_id': self.id,
        #         # 'picking_type_id': self.env.ref('stock.picking_type_out').id,
        #         'picking_type_id': self.env['stock.picking.type'].search([('code', '=', 'outgoing'),('default_location_src_id', '=', loc['location_id'])], limit=1).id,
        #         'location_id': loc['location_id'],
        #         'location_dest_id': loc['location_dest_id'],
        #         'analytic_account_group_ids': [(6, 0, self.analytic_group_id.ids)],
        #         'origin': self.name,
        #         'company_id': self.company_id.id,
        #         'branch_id': self.branch_id.id,
        #         'scheduled_date': fields.Datetime.now(),
        #     })
        #     for material in material_ids:
                # self.env['stock.move'].create({
                #     'picking_id': stock_picking.id,
                #     'name': materials.browse(material).product_id.name,
                #     'product_id': materials.browse(material).product_id.id,
                #     'product_uom_qty': materials.browse(material).product_uom_qty,
                #     'product_uom': materials.browse(material).uom_id.id,
                #     'location_id': materials.browse(material).location_id.id,
                #     'location_dest_id': materials.browse(material).location_dest_id.id,
                #     'analytic_account_group_ids': [(6, 0, self.analytic_group_id.ids)],
                #     'date': fields.Datetime.now(),
                #     'quantity_done': materials.browse(material).product_uom_qty,
                # })
        #
        #     stock_picking.action_assign()

        previous_state = self.state_id
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        is_there = IrConfigParam.search([('key', '=', 'equip3_asset_fms_operation.is_approval_matix_mwo')])
        if is_there and self.approvalmatrix :
            self.write({'state_id': 'to_approve'})
        else:
            self.write({'state_id': 'in_progress'})
            self.env['time.progress'].create(
            self._prepare_timeline_vals(self.time_in_progress, datetime.now())
        )
        if self.is_approval_matrix_defined():
            self._is_unauthorized_user()
            self._is_enough_approvers(previous_state)

        self.update_equipment_state()


    def state_pending(self):
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        is_there = IrConfigParam.search([('key', '=', 'equip3_asset_fms_operation.is_approval_matix_mwo')])
        if self.approvalmatrix3 and is_there:
            self.write({'state_id': 'to_approve_post'})
            self.write({'in_progress_to_post' : True})
        else:
            previous_state = self.state_id
            self.write({'state_id': 'pending'})
            self.write({'in_progress_to_post' : True})
            if self.is_approval_matrix_defined():
                self._is_unauthorized_user()
                self._is_enough_approvers(previous_state)
            time_ids = self.time_ids.filtered(lambda r:not r.date_end)
            if time_ids:
                time_ids.write({'date_end': datetime.now()})
                self.env['time.post'].create(
                    self._prepare_timeline_vals(self.time_post, datetime.now())
            )

            self.update_equipment_state()

    def action_start_again(self):
        previous_state = self.state_id
        self.write({'state_id': 'in_progress'})
        self.env['time.progress'].create(
            self._prepare_timeline_vals(self.time_in_progress, datetime.now())
        )
        time_post_ids = self.time_post_ids.filtered(lambda r:not r.date_end)
        if time_post_ids:
            time_post_ids.write({'date_end': datetime.now()})

        self.update_equipment_state()
        if self.approval_matrix_line_ids_post:
            self.approval_matrix_line_ids_post.write({'last_approved' : False})
            self.approval_matrix_line_ids_post.approved_users = [(5,0,0)]

    def state_cancel(self):
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        is_there = IrConfigParam.search([('key', '=', 'equip3_asset_fms_operation.is_approval_matix_mwo')])
        if self.approvalmatrix4 and is_there:
            self.write({'state_id': 'to_approve_cancel'})
        else:
            previous_state = self.state_id
            self.write({'state_id': 'cancel'})
            if self.is_approval_matrix_defined():
                self._is_unauthorized_user()
                self._is_enough_approvers(previous_state)
            time_ids = self.time_ids.filtered(lambda r:not r.date_end)
            if time_ids:
                time_ids.write({'date_end': datetime.now()})
            time_post_ids = self.time_post_ids.filtered(lambda r:not r.date_end)
            if time_post_ids:
                time_post_ids.write({'date_end': datetime.now()})

            self.update_equipment_state()

    def state_done(self):
        if not all(state == 'done' for state in self.repair_ids.mapped('state_id')):
            raise ValidationError(_('You have Repair Order in progress'))
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        is_there = IrConfigParam.search([('key', '=', 'equip3_asset_fms_operation.is_approval_matix_mwo')])
        if self.approvalmatrix2 and is_there:
            self.write({'state_id': 'to_approve_done'})
        else:
            self._check_asset_budget_amount_mwo()
            previous_state = self.state_id
            self.write({'state_id': 'done'})
            time_ids = self.time_ids.filtered(lambda r:not r.date_end)
            if time_ids:
                time_ids.write({'date_end': datetime.now()})
            time_post_ids = self.time_post_ids.filtered(lambda r:not r.date_end)
            if time_post_ids:
                time_post_ids.write({'date_end': datetime.now()})

            if self.maintenance_materials_list_ids:
                if (self.repair_count > 0) or (self.delivery_order_count > 0):
                    previous_state = self.state_id
                    self.write({'state_id': 'done'})
                    if self.is_approval_matrix_defined():
                        self._is_unauthorized_user()
                        self._is_enough_approvers(previous_state)

                    self.update_equipment_state()

                    # stock_pickings = self.env['stock.picking'].search([('mwo_id', 'in', self.ids)])
                    # for stock_picking in stock_pickings:
                    #     if stock_picking.state != 'done':
                    #         stock_picking.button_validate()
                # else:
                #     raise ValidationError("You need to choose either consume materials or create repair order.")
            else:

                self.update_equipment_state()

                # stock_pickings = self.env['stock.picking'].search([('mwo_id', 'in', self.ids)])
                # for stock_picking in stock_pickings:
                #     if stock_picking.state != 'done':
                #         stock_picking.button_validate()
        self._create_do_from_mwo()
        
        return True
                        
    def mwo_reject_in_progress(self):
        for rec in self:
            rec.write({'state_id': 'draft'})

    def mwo_reject_post(self):
        for rec in self:
            rec.write({'state_id': 'in_progress'})

    def mwo_reject_done(self):
        for rec in self:
            if rec.in_progress_to_post:
                rec.write({'state_id': 'pending'})
            else:
                rec.write({'state_id': 'in_progress'})

    def mwo_reject_cancel(self):
        for rec in self:
            rec.write({'state_id': 'in_progress'})

    # @api.depends('branch_id')
    # def _compute_approvalmatrix(self):
    #     self.approvalmatrix = self.env['approval.matrix.mwo'].search([('branch_id', '=', self.branch_id.id)], limit=1)

    def _is_unauthorized_user(self):
       for rec in self.approvalmatrix.filtered(lambda x: x.state == self.state_id):
            if  self.env.user not in rec.approval_matrix_mwo_ids.mapped('user_ids'):
                raise ValidationError('You are not allowed to do this action')

    def _is_enough_approvers(self, previous_state):
        self.approvers_id = [(4, self.env.user.id)]
        self.activity_search(['mail.mail_activity_data_todo']).unlink()
        line = self.approvalmatrix.filtered(lambda x: x.state == self.state_id)
        for rec in line.approval_matrix_mwo_ids:
            if len(self.approvers_id) < rec.min_approvers: # belum cukup
                for user in line.mapped('user_id'):
                    if user in self.approvers_id:
                        continue
                    self.activity_schedule(act_type_xmlid='mail.mail_activity_data_todo', user_id=user.id)
                    self.state_id = previous_state
            else:
                self.approvers_id = [(5)]

MaintenanceWorkOrder()

class MaintenanceStage(models.Model):
    _inherit = 'maintenance.stage'

    create_work_order = fields.Boolean('Create Work Order', default=True)
