from odoo import models, fields, api, _
from datetime import datetime
from odoo.exceptions import ValidationError
from odoo.exceptions import UserError
from lxml import etree

class InterAssetTransfer(models.Model):
    _name = 'inter.asset.transfer'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Internal Asset Transfer'

    @api.returns('self')
    def _default_stage(self):
        return self.env['inter.asset.transfer.stage'].search([], limit=1)

    name = fields.Char(string='Name')
    source = fields.Many2one(comodel_name='maintenance.facilities.area', string='Source Location')
    schedule = fields.Date(string='Start Date',default=datetime.today().date())
    description = fields.Text(string='Description')
    destloc = fields.Many2one(comodel_name='maintenance.facilities.area', string='Destination Location')
    branch_id = fields.Many2one('res.branch', string="Branch", required=True,default=lambda self: self.env.branches if len(self.env.branches) == 1 else False,
                    domain=lambda self: [('id', 'in', self.env.branches.ids)])
    approvalmatrix = fields.Many2one('approval.matrix.asset.transfer', string='Approval Matrix', compute='_compute_approvalmatrix', required=False, readonly=True)
    is_waiting_for_other_approvers = fields.Boolean(string='Waiting other approvers')
    approvers_id = fields.Many2many('res.users', string='Approvers')
    created = fields.Char(string='Create By')
    created_date = fields.Date(string='Create Date', readonly=True, default=datetime.today().date())
    asset_ids = fields.One2many(comodel_name='inter.asset', inverse_name='asset_line', string='Asset')
    user_id = fields.Many2one('res.users', 'Created By', required=True, readonly=True, default=lambda self: self.env.user)
    company_id = fields.Many2one("res.company", "Company", default=lambda self: self.env.user.company_id)
    partner_id = fields.Many2one('res.partner', string='Customer')
    stage_id = fields.Many2one('inter.asset.transfer.stage', string='Stage', ondelete='restrict', tracking=True,
                               group_expand='_read_group_stage_ids', default=_default_stage, copy=False)
    state = fields.Selection(
        [('draft', 'Draft'),
         ('waiting_approval', 'Waiting for Approval'),
         ('approved', 'Approved'),
         ('in_progress', 'In Progress'),
         ('done', 'Done'),
         ('cancel', 'Cancelled')], string="State", default='draft')

    total_asset_value = fields.Float(string='Total Asset Value', compute='_compute_total_asset_value')
    is_approvalmatrix = fields.Boolean(string='Is Approval Matrix', compute='_compute_is_approvalmatrix', store=True)
    state_a = fields.Selection(related='state')
    state_b = fields.Selection(related='state')

    @api.depends('branch_id')
    def _compute_is_approvalmatrix(self):
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        is_there = IrConfigParam.search([('key', '=', 'equip3_asset_fms_operation.is_approval_matix_asset_transfer')])
        approval =  IrConfigParam.get_param('equip3_asset_fms_operation.is_approval_matix_asset_transfer')
        for record in self:
            if is_there:
                record.is_approvalmatrix = approval
            else:
                record.is_approvalmatrix = False

    def is_approval_matrix_defined(self):
        is_approval_matrix = self.env['ir.config_parameter'].sudo().get_param('equip3_asset_fms_operation.is_approval_matix_asset_transfer')
        if is_approval_matrix == 'True':
            return True
        else:
            return False

    @api.depends('asset_ids.asset_value')
    def _compute_total_asset_value(self):
        for record in self:
            record.total_asset_value = sum(record.asset_ids.mapped('asset_value'))

    def action_done(self):
        previous_state = self.state
        for record in self:
            for line in record.asset_ids:
                line.asset_id.fac_area = line.dest.id
            record.write({'state': 'done'})
        if self.is_approval_matrix_defined():
            self._is_unauthorized_user()
            self._is_enough_approvers(previous_state)

    def action_waiting_approval(self):
        previous_state = self.state
        for record in self:
            record.write({'state': 'waiting_approval'})
        if self.is_approval_matrix_defined():
            self._is_unauthorized_user()
            self._is_enough_approvers(previous_state)

    def action_approve(self):
        previous_state = self.state
        for record in self:
            record.write({'state': 'approved'})
        if self.is_approval_matrix_defined():
            self._is_unauthorized_user()
            self._is_enough_approvers(previous_state)

    def action_cancel(self):
        previous_state = self.state
        for record in self:
            record.write({'state': 'cancel'})
        if self.is_approval_matrix_defined():
            self._is_unauthorized_user()
            self._is_enough_approvers(previous_state)

    def action_confirm(self):
        previous_state = self.state
        for record in self:
            record.write({'state': 'in_progress'})
        if self.is_approval_matrix_defined():
            self._is_unauthorized_user()
            self._is_enough_approvers(previous_state)

    def write(self, vals):
        if vals.get('stage_id'):
            stage_id = self.env['inter.asset.transfer.stage'].browse(vals.get('stage_id'))
            if not stage_id.custom_user_ids:
                return super(InterAssetTransfer, self).write(vals)
            if self.env.user.id in stage_id.custom_user_ids.ids:
                return super(InterAssetTransfer, self).write(vals)
            else:
                raise UserError(_("You can not move internal asset transfer to this stage. Please contact your manager."))
            return super(InterAssetTransfer, self).write(vals)
        return super(InterAssetTransfer, self).write(vals)

    @api.depends('source', 'branch_id', 'total_asset_value')
    def _compute_approvalmatrix(self):
        for rec in self:
            rec.approvalmatrix = self.env['approval.matrix.asset.transfer'].search([('fac_area', '=', rec.source.id), ('branch_id', '=', rec.branch_id.id), ('min_amount', '<=', self.total_asset_value), ('max_amount', '>=', self.total_asset_value)], limit=1)


    @api.constrains('source', 'destloc')
    def _check_source(self):
        for record in self :
            same = record.source == record.destloc
            if same:
                raise ValidationError("Source Location must be diferent with Destination Location")

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code(
                'inter.asset.transfer.sequence') or 'New'
        return super(InterAssetTransfer, self).create(vals)

    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Import Template for Internal Asset Transfer '),
            'template': '/equip3_asset_fms_operation/static/xls/internal_asset_transfer_template.xls'
        }]

    def _is_unauthorized_user(self):
        users = self.approvalmatrix.approval_matrix_asset_transfer_ids.filtered(lambda x: x.state_id == self.state).mapped('user_id')
        if self.env.user not in users:
            raise ValidationError('You are not allowed to do this action.')

    def _is_enough_approvers(self, previous_state):
        self.approvers_id = [(4, self.env.user.id)]
        self.activity_search(['mail.mail_activity_data_todo']).unlink()
        line = self.approvalmatrix.approval_matrix_asset_transfer_ids.filtered(lambda x: x.state_id == self.state)
        if len(self.approvers_id) < line.min_approvers: # belum cukup
            for user in line.mapped('user_id'):
                if user in self.approvers_id:
                    continue
                self.activity_schedule(act_type_xmlid='mail.mail_activity_data_todo', user_id=user.id)
                self.state = previous_state
        else:
            self.approvers_id = [(5)]

class InterAsset(models.Model):
    _name = 'inter.asset'
    _description = 'Inter Asset'

    no_asset_sequence = fields.Integer(string='NO', default=1)
    asset_id = fields.Many2one(comodel_name='maintenance.equipment', string='Asset')
    asset_line = fields.Many2one(comodel_name='inter.asset.transfer', string='Asset')
    #qty = fields.Integer(string='Qty')
    receive = fields.Char(string='Received Quantity')
    source = fields.Many2one(comodel_name='maintenance.facilities.area', string='Source Location', related='asset_line.source')
    dest = fields.Many2one(comodel_name='maintenance.facilities.area', string='Destination Location', related='asset_line.destloc')
    asset_value = fields.Float(string='Asset Value', compute='_compute_asset_value')

    @api.depends('asset_id')
    def _compute_asset_value(self):
        for record in self:
            record.asset_value = record.asset_id.asset_value

    @api.model
    def default_get(self, fields):
        res = super(InterAsset, self).default_get(fields)
        if self._context:
            context_keys = self._context.keys()
            next_sequence = 1
            if 'asset_ids' in context_keys:
               if len(self._context.get('asset_ids')) > 0:
                    next_sequence = len(self._context.get('asset_ids')) + 1
            res.update({'no_asset_sequence': next_sequence})
        return res

class InterAssetTransferStage(models.Model):
    _name = 'inter.asset.transfer.stage'
    _description = 'Inter Asset Transfer Stage'
    _order = 'sequence, id'

    name = fields.Char('Name', required=True, translate=True)
    sequence = fields.Integer('Sequence', default=20)
    fold = fields.Boolean('Folded in Maintenance Pipe')
    done = fields.Boolean('InterAsset Done')
    custom_user_ids = fields.Many2many('res.users', string='Allow Users', help="Selected users can move maintenance Internal Asset Transfer into this stage.")
    custom_mail_template_id = fields.Many2one('mail.template', string='Email Template', domain=[('model', '=', 'inter.asset.transfer')])
