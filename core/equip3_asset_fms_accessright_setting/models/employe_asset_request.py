from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import json

class EmployeeAssetRequestInherit(models.Model):
    _inherit = 'employee.asset.request'

    approval_matrix_id = fields.Many2one(comodel_name='approval.matrix.asset.request', string='Approval Matrix')
    approval_line = fields.One2many(comodel_name='approval.matrix.asset.request.line', inverse_name='asset_request_transfer_id', string='Approval Line')
    
    is_need_approval = fields.Boolean(string='Need Approval', compute='_compute_is_need_approval')
    normal_state = fields.Selection(related='state', tracking=False)
    
    @api.depends('branch_id','approval_line','due_date')
    def _compute_is_need_approval(self):
        is_approval_matrix = self.env['ir.config_parameter'].sudo().get_param('equip3_asset_fms_operation.is_approval_matix_asset_employee_request')
        if not is_approval_matrix:
            self.is_need_approval = False
        else:
            for rec in self:
                rec.is_need_approval = False
                
                if self.env.user.has_group('equip3_asset_fms_accessright_setting.group_asset_administrator'):
                    approval_matrix = self.env['approval.matrix.asset.request'].search(['|',('branch_id', '=', rec.branch_id.id),('branch_id', '=', False),('access_type', '=', 'admin')], limit=1)
                    
                elif self.env.user.has_group('equip3_asset_fms_accessright_setting.group_asset_manager'):
                    approval_matrix = self.env['approval.matrix.asset.request'].search(['|',('branch_id', '=', rec.branch_id.id),('branch_id', '=', False),('access_type', '=', 'manager')], limit=1)
                
                elif self.env.user.has_group('equip3_asset_fms_accessright_setting.group_asset_user'):
                    approval_matrix = self.env['approval.matrix.asset.request'].search(['|',('branch_id', '=', rec.branch_id.id),('branch_id', '=', False),('access_type', '=', 'user')], limit=1)


                if approval_matrix and self.env.uid in approval_matrix.user_group_id.users.ids:
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
                    if not rec.approval_line:
                        rec.approval_line = list_approval
                        
                else:
                    rec.write({'is_need_approval': False})
                    
                
        
    def action_approved(self):
        for rec in self:
            approval_matrix = self.approval_matrix_id
            if approval_matrix:
                for line in rec.approval_line:
                    user_approval = line.user_ids.ids
                    if self.env.uid in user_approval and self.env.uid not in rec.approval_line.approved_user_ids.ids:
                        rec.approval_line.search([('user_ids', '=', self.env.uid)]).write({'approved_user_ids': [(4, self.env.uid)], 'approved_status': 'progress'})

                    if len(line.approved_user_ids.ids) == line.minimum_approval:
                        line.write({'approved_status': 'approved'})
                    
                    if all(line.approved_status == 'approved' for line in rec.approval_line):
                        rec.write({'state': 'approved'})




class ApprovalMatrixAssetRequest(models.Model):
    _name = 'approval.matrix.asset.request'
    _description = 'Approval Matrix Asset Request'
    
    name = fields.Char(string='Name', required=True)
    branch_id = fields.Many2one(comodel_name='res.branch', string='Branch',default=lambda self: self.env.branches if len(self.env.branches) == 1 else False,
        domain=lambda self: [('id', 'in', self.env.branches.ids)])
    company_id = fields.Many2one(comodel_name='res.company', string='Company', default=lambda self: self.env.user.company_id)
    access_type = fields.Selection(string='Access Type', selection=[('user', 'User'), ('manager', 'Manager'), ('admin', 'Admin')], required=True)
    user_group_id = fields.Many2one(comodel_name='res.groups', string='User Group', required=True)
    group_id = fields.Many2one(comodel_name='res.groups', string='Group Approve', required=True)
    approval_matrix_maintenance_line = fields.One2many('approval.matrix.asset.request.line', 'asset_approval_id')    
    
    @api.onchange('access_type')
    def onchange_access_type(self):
        if self.access_type == 'user':
            self.user_group_id = self.env.ref('equip3_asset_fms_accessright_setting.group_asset_user').id
            self.group_id = self.env.ref('equip3_asset_fms_accessright_setting.group_asset_manager').id
        elif self.access_type == 'manager':
            self.user_group_id = self.env.ref('equip3_asset_fms_accessright_setting.group_asset_manager').id
            self.group_id = self.env.ref('equip3_asset_fms_accessright_setting.group_asset_administrator').id
        elif self.access_type == 'admin':
            self.user_group_id = self.env.ref('equip3_asset_fms_accessright_setting.group_asset_administrator').id
            self.group_id = self.env.ref('equip3_asset_fms_accessright_setting.group_asset_administrator').id
            
            
class ApprovalMatrixAssetRequestLine(models.Model):
    _name = 'approval.matrix.asset.request.line'
    _description = 'Approval Matrix Asset Request Line'
    
    asset_approval_id = fields.Many2one(comodel_name='approval.matrix.asset.request', string='Maintenance Approval')
    asset_request_transfer_id = fields.Many2one(comodel_name='employee.asset.request', string='Asset Request')
    user_ids = fields.Many2many(comodel_name='res.users', string='Users')
    approved_user_ids = fields.Many2many(comodel_name='res.users', relation='approved_user_ids_rel', string='Approved Users')
    approved_status = fields.Selection([('waiting', 'Waiting'), ('progress', 'Progress'), ('approved', 'Approved')], string='Status', default='waiting')
    minimum_approval = fields.Integer(string='Minimum Approval', default=1)
    user_ids_domain = fields.Char(string='User Domain', compute='_compute_user_ids_domain')
    
    @api.depends('asset_approval_id.group_id')
    def _compute_user_ids_domain(self):
        self.user_ids_domain = json.dumps([])
        for rec in self:
            if rec.asset_approval_id:
                rec.user_ids_domain = json.dumps([('id', 'in', rec.asset_approval_id.group_id.users.ids)])
        
        

    @api.onchange('minimum_approval','user_ids')
    def _check_minimum_approval(self):
        for rec in self:
            
            if rec.user_ids and rec.minimum_approval > len(rec.user_ids) :
                raise ValidationError(_('Minimum Approval must be less than or equal to Users'))
            elif rec.minimum_approval < 1:
                raise ValidationError(_('Minimum Approval must be greater than 0'))