from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from dateutil.relativedelta import relativedelta
import json



class EmployeeAssetTransfer(models.Model):
    _name = 'employee.asset.transfer'
    _inherit = ['mail.thread','mail.activity.mixin']
    _description = 'Asset Employee Transfer'

    name = fields.Char(string='Sequence Asset Transfer', required=True, default=lambda self: _('New'), copy=False)
    branch_id = fields.Many2one('res.branch', string='Branch',default=lambda self: self.env.branches if len(self.env.branches) == 1 else False,
                    domain=lambda self: [('id', 'in', self.env.branches.ids)])
    due_date = fields.Date(string='Due Date', required=True)
    description = fields.Text(string='Description')
    assets_line = fields.One2many('employee.asset.transfer.line', 'employee_asset_transfer_id', string='Assets')
    state = fields.Selection([('draft', 'Draft'), ('waiting', 'Waiting'), ('done', 'Done'), ('expired', 'Expired'), ('cancelled', 'Cancelled')], string='State', default='draft', tracking=True)
    employee_asset_request_id = fields.Many2one('employee.asset.request', string='Reference')
    employee_asset_return_count = fields.Integer(string='# of Employee Asset Return', compute='_compute_employee_asset_return_count')
    
    def _compute_employee_asset_return_count(self):
        for line in self:
            employee_asset_return = self.env['employee.asset.return'].search_count([('employee_asset_transfer_id', '=', line.id)])
            if employee_asset_return:
                line.employee_asset_return_count = employee_asset_return
            else:
                line.employee_asset_return_count = 0
    
    def action_view_employee_asset_return(self):
        employee_asset_return = self.env['employee.asset.return'].search([('employee_asset_transfer_id', '=', self.id)])
        if employee_asset_return:
            action = self.env.ref('equip3_asset_fms_operation.employee_asset_return_action').read()[0]
            action['views'] = [(self.env.ref('equip3_asset_fms_operation.employee_asset_return_view_form').id, 'form')]
            action['res_id'] = employee_asset_return.id
            return action
        else:
            raise UserError(_('No Employee Asset Return found for this Employee Asset Transfer.'))

    
    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('asset.employee.transfer') or _('New')
        duedate = vals.get('due_date')
        result = super(EmployeeAssetTransfer, self).create(vals)
        result.check_due_date(duedate)
        return result
    
    def write(self, vals):
        if vals.get('due_date'):
            self.check_due_date(vals.get('due_date'))
        result = super(EmployeeAssetTransfer, self).write(vals)
        return result
    
    def check_due_date(self, date):
        if date:
            date = fields.Date.from_string(date)
            if date <= fields.Date.today():
                raise UserError(_('Due Date must be greater than today.'))
            else:
                return True

    def scheduled_employee_asset_transfer(self):
        employee_asset_transfer = self.env['employee.asset.transfer'].search([('state', 'in', ['waiting', 'done'])])
        for line in employee_asset_transfer:
            if line.due_date <= fields.Date.today() and line.state == 'waiting':
                line.state = 'expired'
            if line.due_date <= fields.Date.today() and line.state == 'done':
                employee_asset_return = self.env['employee.asset.return'].create({
                    'employee_asset_transfer_id': line.id,
                    'branch_id': line.branch_id.id,
                    'due_date': line.due_date + relativedelta(months=1),
                    'description': line.description,
                    'assets_line': [(0, 0, {'asset_id': line.asset_id.id, 'employee_id': line.employee_id.id, 'notes': line.notes}) for line in self.assets_line],

                })
                if employee_asset_return:
                    line.state = 'expired'
        return True
    
    def action_cancel(self):
        self.state = 'cancelled'
        
    def action_waiting(self):
        if self.assets_line:
            for line in self.assets_line:
                if not line.asset_id:
                    raise ValidationError(_('Please add asset line before to the next step.'))
        self.state = 'waiting'
    
    def action_done(self):
        asset_employee_management_line = self.assets_line
        if asset_employee_management_line:
            try:
                for line in asset_employee_management_line:
                    line.asset_id.held_by_id = line.employee_id.partner_id.id
                self.state = 'done'
            except Exception as e:
                raise UserError(_('Error: ' + str(e)))
        else:
            raise UserError(_('Please add asset line before approve.'))
        
    def action_expired(self):
        self.state = 'expired'
        
class EmployeeAssetTransferLine(models.Model):
    _name = 'employee.asset.transfer.line'
    _description = 'Employee Asset Transfer Line'
    
    employee_asset_transfer_id = fields.Many2one('employee.asset.transfer', string='Employee Asset Transfer')
    asset_id = fields.Many2one('maintenance.equipment', string='Asset')
    employee_id = fields.Many2one('res.users', string='Employee', required=True)
    notes = fields.Text(string='Notes')
    held_by_id = fields.Many2one('res.partner', string='Held By')
    asset_category_id = fields.Many2one(comodel_name='maintenance.equipment.category', string='Category', required=True)
    asset_id_domain = fields.Char(string='Asset Domain', compute='_compute_asset_id_domain')
    
    @api.onchange('asset_id')
    def onchange_asset_id(self):
        print('onchange_asset_id')
        if self.asset_id:
            self.held_by_id = self.asset_id.held_by_id.id
            self.asset_category_id = self.asset_id.category_id.id
            
    @api.depends('asset_category_id')
    def _compute_asset_id_domain(self):
        if self.asset_category_id:
            self.asset_id_domain = json.dumps([('category_id', '=', self.asset_category_id.id)])
        else:
            self.asset_id_domain = json.dumps([])