from odoo import api, fields, models, _
from odoo.exceptions import UserError



class AssetEmployeeManagement(models.Model):
    _name = 'asset.employee.management'
    _inherit = ['mail.thread','mail.activity.mixin']
    _description = 'Asset Employee Management'

    name = fields.Char(string='Sequence Asset Request', required=True, default=lambda self: _('New'), copy=False)
    branch_id = fields.Many2one('res.branch', string='Branch')
    due_date = fields.Date(string='Due Date', required=True)
    description = fields.Text(string='Description')
    assets_line = fields.One2many('asset.employee.management.line', 'asset_employee_management_id', string='Assets')
    state = fields.Selection([('draft', 'Draft'), ('waiting_approval', 'Waiting for Approval'), ('approved', 'Approved'), ('expired', 'Expired'), ('cancelled', 'Cancelled')], string='State', default='draft', tracking=True)
    
    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('asset.employee.management') or _('New')
        duedate = vals.get('due_date')
        result = super(AssetEmployeeManagement, self).create(vals)
        result.check_due_date(duedate)
        return result
    
    def write(self, vals):
        if vals.get('due_date'):
            self.check_due_date(vals.get('due_date'))
        result = super(AssetEmployeeManagement, self).write(vals)
        return result
    
    def check_due_date(self, date):
        if date:
            date = fields.Date.from_string(date)
            if date <= fields.Date.today():
                raise UserError(_('Due Date must be greater than today.'))
            else:
                return True
            
    def scheduled_asset_employee_management(self):
        asset_employee_management_ids = self.env['asset.employee.management'].search([('state', 'not in', ['expired', 'cancelled'])])
        for asset_employee_management in asset_employee_management_ids:
            if asset_employee_management.due_date <= fields.Date.today():
                asset_employee_management.state = 'expired'
        return True
    
    def action_cancel(self):
        self.state = 'cancelled'
        
    def action_waiting_approval(self):
        self.state = 'waiting_approval'
    
    def action_approved(self):
        asset_employee_management_line = self.assets_line
        if asset_employee_management_line:
            try:
                for line in asset_employee_management_line:
                    line.asset_id.owner = line.employee_id.partner_id.id
                self.state = 'approved'
            except Exception as e:
                raise UserError(_('Error: ' + str(e)))
        else:
            raise UserError(_('Please add asset line before approve.'))
        
    def action_expired(self):
        self.state = 'expired'
    
class AssetEmployeeManagementLine(models.Model):
    _name = 'asset.employee.management.line'
    _description = 'Asset Employee Management Line'

    asset_employee_management_id = fields.Many2one('asset.employee.management', string='Asset Employee Management')
    asset_id = fields.Many2one('maintenance.equipment', string='Asset', required=True)
    employee_id = fields.Many2one('res.users', string='Employee', required=True)
    notes = fields.Text(string='Notes')

class MaintenanceEquipment(models.Model):
    _inherit = 'maintenance.equipment'

    assignment_history_count = fields.Integer(string='Assignment History Count', compute='_compute_assignment_history_count')
    is_sale_dispose = fields.Boolean(string='Is Sale Dispose', compute='_compute_is_sale_dispose')
    
    def _compute_is_sale_dispose(self):
        self.is_sale_dispose = False
        is_sale_dispose = self.env['ir.config_parameter'].sudo().get_param('equip3_asset_fms_operation.is_disposable_asset')
        if is_sale_dispose == 'True':
            self.is_sale_dispose = True
        else:
            self.is_sale_dispose = False
    
    def _compute_assignment_history_count(self):
        for equipment in self:
            equipment.assignment_history_count = self.env['asset.employee.management.line'].search_count([('asset_id', '=', equipment.id)])
            
    def action_assignment_history(self):
        asset_employee_management_id = []
        asset_employee_management_line_id = self.env['asset.employee.management.line'].search([('asset_id', '=', self.id)])
        for line in asset_employee_management_line_id:
            asset_employee_management_id.append(line.asset_employee_management_id.id)
        action = {
            'name': _('Assignment History'),
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'asset.employee.management',
            'domain': [('id', 'in', asset_employee_management_id)],
        }
        return action

    