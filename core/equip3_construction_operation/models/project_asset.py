# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError

class EmployeeAssetRequest(models.Model):
    _inherit = 'employee.asset.request'

    project_id = fields.Many2one('project.project', string='Project', required=True,domain = lambda self:[('company_id','=',self.env.company.id)])
    is_project = fields.Boolean('Is Project')
    company_id = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.company.id)
    department_type = fields.Selection(related='project_id.department_type', string='Type of Department')
    cons_asset_ids = fields.Many2many('maintenance.equipment', string='asset list')
    budgeting_method = fields.Selection([
        ('product_budget', 'Based on Product Budget'),
        ('gop_budget', 'Based on Group of Product Budget'),
        ('budget_type', 'Based on Budget Type'),
        ('total_budget', 'Based on Total Budget')], string='Budgeting Method', related='project_id.budgeting_method', store = True)
    budgeting_period = fields.Selection([
        ('project', 'Project Length Budgeting'),
        ('monthly', 'Monthly Budgeting'),
        ('custom', 'Custom Time Budgeting'),], string='Budgeting Period', related='project_id.budgeting_period', store = True)

    @api.onchange('project_id')
    def _onchange_project_id_branch(self):
        for rec in self:
            project = rec.project_id
            if project:
                rec.branch_id = project.branch_id.id
            else:
                rec.branch_id = False
    
    @api.onchange('department_type')
    def _onchange_department_type(self):
        for rec in self:
            if rec.department_type == 'project':
                return {
                    'domain': {'project_id': [('department_type', '=', 'project'), ('primary_states', '=', 'progress'), ('company_id', '=', rec.company_id.id)]}
                }
            elif rec.department_type == 'department':
                return {
                    'domain': {'project_id': [('department_type', '=', 'department'), ('primary_states', '=', 'progress'), ('company_id', '=', rec.company_id.id)]}
                }
    

    def action_transfer(self):
        try:
            employee_Asset_transfer = self.env['employee.asset.transfer']
            val = {
                'employee_asset_request_id': self.id,
                'to_project_id': self.project_id.id,
                'branch_id': self.branch_id.id,
                'due_date': self.due_date,
                'description': self.description,
                'assets_line': [(0, 0, {'asset_id': line.asset_id.id, 'asset_category_id': line.asset_category_id.id, 'employee_id': line.employee_id.id, 'notes': line.notes}) for line in self.assets_line],
            }
            employee_Asset_transfer.create(val)
            self.state = 'transfer'
        except Exception as e:
            raise UserError(_('Error: ' + str(e)))
        

class EmployeeAssetRequestLine(models.Model):
    _inherit = 'employee.asset.request.line'
        
    cons_asset_line_ids = fields.Many2many('maintenance.equipment', string='asset list')
    project_id = fields.Many2one(related="employee_asset_request_id.project_id", string='Project')
    asset_id = fields.Many2one('maintenance.equipment', string='Asset')

    @api.onchange('project_id', 'asset_id')
    def _onchange_asset_id(self):
        for rec in self:
            if rec.project_id:
                internal_asset = []
                if rec.project_id.cost_sheet:
                    for asset in rec.project_id.cost_sheet.internal_asset_ids.asset_id:
                        internal_asset.append(asset.id)
                return {
                    'domain': {'asset_id': [('id', 'in', internal_asset)]}
                }

class EmployeeAssetTransfer(models.Model):
    _inherit = 'employee.asset.transfer'

    from_project_id = fields.Many2one('project.project', string='From Project', domain="[('primary_states','=', 'progress')]")
    to_project_id = fields.Many2one('project.project', string='To Project', required=True,domain = lambda self:[('company_id','=',self.env.company.id),('primary_states','=', 'progress')])
    is_project = fields.Boolean('Is Project')

    #  inherit action_done function ----------
    def action_done(self):
        res = super(EmployeeAssetTransfer, self).action_done()
        if self.assets_line:
            for rec in self.assets_line:
                rec_asset_id = rec.asset_id
                rec_asset_id.project_id = self.to_project_id.id
        return res

class EmployeeAssetReturn(models.Model):
    _inherit = 'employee.asset.return'

    project_id = fields.Many2one('project.project', string='Project', required=True,domain = lambda self:[('company_id','=',self.env.company.id),('primary_states','=', 'progress')])
    is_project = fields.Boolean('Is Project')
    company_id = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.company.id)
    department_type = fields.Selection(related='project_id.department_type', string='Type of Department')

    @api.onchange('project_id')
    def _onchange_project_id_branch(self):
        for rec in self:
            project = rec.project_id
            if project:
                rec.branch_id = project.branch_id.id
            else:
                rec.branch_id = False

    @api.onchange('department_type')
    def _onchange_department_type(self):
        for rec in self:
            if rec.department_type == 'project':
                return {
                    'domain': {'project_id': [('department_type', '=', 'project'), ('primary_states', '=', 'progress'), ('company_id', '=', rec.company_id.id)]}
                }
            elif rec.department_type == 'department':
                return {
                    'domain': {'project_id': [('department_type', '=', 'department'), ('primary_states', '=', 'progress'), ('company_id', '=', rec.company_id.id)]}
                }
    

    #  inherit action_done function ----------
    def action_done(self):
        res = super(EmployeeAssetReturn, self).action_done()
        if self.assets_line:
            for rec in self.assets_line:
                rec_asset_id = rec.asset_id
                rec_asset_id.project_id = False
        return res

class EmployeeAssetTransferLine(models.Model):
    _inherit = 'employee.asset.transfer.line'

    from_project_id = fields.Many2one('project.project', string='From Project', related='asset_id.project_id', domain="[('primary_states','=', 'progress')]")
    to_project_id = fields.Many2one('project.project', string='To Project', related='employee_asset_transfer_id.to_project_id', domain="[('primary_states','=', 'progress')]")

    # @api.onchange('asset_id')
    # def _onChange_transfer_assest(self):
    #     if self.employee_asset_transfer_id.from_project_id:
    #         asset = self.env['maintenance.equipment'].sudo().search(
    #             [('project_id', '=', self.employee_asset_transfer_id.from_project_id.id)])
    #         return {'domain': {'asset_id': [('id', 'in', asset.ids)]}}

    @api.onchange('to_project_id', 'asset_id')
    def _onchange_asset_id(self):
        for rec in self:
            if rec.to_project_id:
                internal_asset = []
                if rec.to_project_id.cost_sheet:
                    for asset in rec.to_project_id.cost_sheet.internal_asset_ids.asset_id:
                        internal_asset.append(asset.id)
                return {
                    'domain': {'asset_id': [('id', 'in', internal_asset)]}
                }

class EmployeeAssetReturnLine(models.Model):
    _inherit = 'employee.asset.return.line'

    @api.onchange('asset_id')
    def _onChange_assest(self):
        if self.employee_asset_return_id.project_id:
            asset = self.env['maintenance.equipment'].sudo().search(
                [('project_id', '=', self.employee_asset_return_id.project_id.id)])
            return {'domain': {'asset_id': [('id', 'in', asset.ids)]}}
