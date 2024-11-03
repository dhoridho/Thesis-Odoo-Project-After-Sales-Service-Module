from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class ApprovalMatrixMaintenanceReuest(models.Model):
    _name = 'approval.matrix.maintenance.request'
    _description = 'Approval Matrix Maintenance Request'
    
    name = fields.Char(string='Name', required=True)
    company_id = fields.Many2one(comodel_name='res.company', string='Company', default=lambda self: self.env.user.company_id)
    branch_id = fields.Many2one(comodel_name='res.branch', string='Branch', required=True,default=lambda self: self.env.branches if len(self.env.branches) == 1 else False,
                    domain=lambda self: [('id', 'in', self.env.branches.ids)])
    access_type = fields.Selection(string='Access', selection=[('user', 'User'), ('manager', 'Manager'),('admin', 'Admin')], required=True, default='user')
    group_id = fields.Many2one(comodel_name='res.groups', string='Current Group', required=True)
    approval_group_id = fields.Many2one(comodel_name='res.groups', string='Approval Group', required=True)
    approval_matrix_maintenance_line = fields.One2many('approval.matrix.maintenance.request.line', 'maintenance_approval_id')
    
    @api.onchange('access_type')
    def onchange_access_type(self):
        fms_accessright = self.env['ir.module.module'].search([('name', '=', 'equip3_asset_fms_accessright_setting'), ('state', '=', 'installed')])
        if fms_accessright:
            if self.access_type == 'user':
                self.group_id = self.env.ref('equip3_asset_fms_accessright_setting.group_asset_user').id
                self.approval_group_id = self.env.ref('equip3_asset_fms_accessright_setting.group_asset_manager').id
            elif self.access_type == 'manager':
                self.group_id = self.env.ref('equip3_asset_fms_accessright_setting.group_asset_manager').id
                self.approval_group_id = self.env.ref('equip3_asset_fms_accessright_setting.group_asset_manager').id
            elif self.access_type == 'Admin':
                self.group_id = self.env.ref('equip3_asset_fms_accessright_setting.group_asset_administrator').id
                self.approval_group_id = self.env.ref('equip3_asset_fms_accessright_setting.group_asset_administrator').id
    
    
    
    
class ApprovalMatrixMaintenanceReuestLine(models.Model):
    _name = 'approval.matrix.maintenance.request.line'
    _description = 'Approval Matrix Maintenance Request Line'
    
    maintenance_approval_id = fields.Many2one(comodel_name='approval.matrix.maintenance.request', string='Maintenance Approval')
    user_ids = fields.Many2many(comodel_name='res.users', string='Users')
    minimum_approval = fields.Integer(string='Minimum Approval', default=1)


    @api.onchange('minimum_approval','user_ids')
    def _check_minimum_approval(self):
        for rec in self:
            
            if rec.user_ids and rec.minimum_approval > len(rec.user_ids) :
                raise ValidationError(_('Minimum Approval must be less than or equal to Users'))
            elif rec.minimum_approval < 1:
                raise ValidationError(_('Minimum Approval must be greater than 0'))