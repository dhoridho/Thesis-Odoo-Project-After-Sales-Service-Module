from odoo import api, fields, models, _
from odoo.exceptions import UserError


class EmployeeAssetRequest(models.Model):
    _name = 'employee.asset.request'
    _inherit = ['mail.thread','mail.activity.mixin']
    _description = 'Asset Employee Request'

    name = fields.Char(string='Sequence Asset Request', required=True, default=lambda self: _('New'), copy=False)
    branch_id = fields.Many2one('res.branch', string='Branch',default=lambda self: self.env.branches if len(self.env.branches) == 1 else False,
                    domain=lambda self: [('id', 'in', self.env.branches.ids)])
    due_date = fields.Date(string='Due Date', required=True)
    description = fields.Text(string='Description')
    assets_line = fields.One2many('employee.asset.request.line', 'employee_asset_request_id', string='Assets')
    state = fields.Selection([('draft', 'Draft'), ('waiting_approval', 'Waiting for Approval'), ('approved', 'Approved'), ('transfer', 'In Progress'), ('expired', 'Expired'), ('cancelled', 'Cancelled')], string='State', default='draft', tracking=True)
    employee_asset_transfer_count = fields.Integer(string='# of Employee Asset Transfer', compute='_compute_employee_asset_transfer_count')
    
    def _compute_employee_asset_transfer_count(self):
        for request in self:
            employee_asset_transfer = self.env['employee.asset.transfer'].sudo().search_count([('employee_asset_request_id', '=', request.id)])
            if employee_asset_transfer:
                request.employee_asset_transfer_count = employee_asset_transfer
            else:
                request.employee_asset_transfer_count = 0
                
    def action_view_employee_asset_transfer(self):
        employee_asset_transfer = self.env['employee.asset.transfer'].search([('employee_asset_request_id', '=', self.id)])
        if employee_asset_transfer:
            action = self.env.ref('equip3_asset_fms_operation.employee_asset_transfer_action').read()[0]
            action['views'] = [(self.env.ref('equip3_asset_fms_operation.employee_asset_transfer_view_form').id, 'form')]
            action['res_id'] = employee_asset_transfer.id
            return action
        else:
            return False
    
    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('asset.employee.request') or _('New')
        duedate = vals.get('due_date')
        result = super(EmployeeAssetRequest, self).create(vals)
        result.check_due_date(duedate)
        return result
    
    def write(self, vals):
        if vals.get('due_date'):
            self.check_due_date(vals.get('due_date'))
        result = super(EmployeeAssetRequest, self).write(vals)
        return result
    
    def check_due_date(self, date):
        if date:
            date = fields.Date.from_string(date)
            if date <= fields.Date.today():
                raise UserError(_('Due Date must be greater than today.'))
            else:
                return True

    def scheduled_employee_asset_req(self):
        employee_asset_req = self.env['employee.asset.request'].search([('state', 'in', ['waiting_approval'])])
        for line in employee_asset_req:
            if line.due_date <= fields.Date.today():
                line.state = 'expired'
        return True
    
    def action_cancel(self):
        self.state = 'cancelled'
        
    def action_waiting_approval(self):
        self.state = 'waiting_approval'
    
    def action_approved(self):
        self.state = 'approved'
    
    def action_transfer(self):
        try:
            employee_Asset_transfer = self.env['employee.asset.transfer']
            val = {
                'employee_asset_request_id': self.id,
                'branch_id': self.branch_id.id,
                'due_date': self.due_date,
                'description': self.description,
                'assets_line': [(0, 0, {'asset_id': line.asset_id.id, 'asset_category_id': line.asset_category_id.id, 'employee_id': line.employee_id.id, 'notes': line.notes}) for line in self.assets_line],
            }
            employee_Asset_transfer.create(val)
            self.state = 'transfer'
        except Exception as e:
            raise UserError(_('Error: ' + str(e)))
        
    def action_expired(self):
        self.state = 'expired'
        
class EmployeeAssetRequestLine(models.Model):
    _name = 'employee.asset.request.line'
    _description = 'Employee Asset Request Line'
    
    employee_asset_request_id = fields.Many2one('employee.asset.request', string='Employee Asset Request')
    asset_id = fields.Many2one('maintenance.equipment', string='Asset')
    employee_id = fields.Many2one('res.users', string='Employee', required=True)
    notes = fields.Text(string='Notes')
    asset_category_id = fields.Many2one(comodel_name='maintenance.equipment.category', string='Category', required=True)
    
    @api.onchange('asset_id')
    def onchange_asset_id(self):
        if self.asset_id:
            self.asset_category_id = self.asset_id.category_id.id