from odoo import api, fields, models, _
from odoo.exceptions import UserError


class EmployeeAssetReturn(models.Model):
    _name = 'employee.asset.return'
    _inherit = ['mail.thread','mail.activity.mixin']
    _description = 'Asset Employee Return'

    name = fields.Char(string='Sequence Asset Return', required=True, default=lambda self: _('New'), copy=False)
    branch_id = fields.Many2one('res.branch', string='Branch',default=lambda self: self.env.branches if len(self.env.branches) == 1 else False,
                    domain=lambda self: [('id', 'in', self.env.branches.ids)])
    due_date = fields.Date(string='Due Date', required=True)
    description = fields.Text(string='Description')
    assets_line = fields.One2many('employee.asset.return.line', 'employee_asset_return_id', string='Assets')
    state = fields.Selection([('draft', 'Draft'), ('waiting', 'Waiting'), ('done', 'Done'), ('expired', 'Expired'), ('cancelled', 'Cancelled')], string='State', default='draft', tracking=True)
    employee_asset_transfer_id = fields.Many2one('employee.asset.transfer', string='Reference')
    
    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('asset.employee.return') or _('New')
        duedate = vals.get('due_date')
        result = super(EmployeeAssetReturn, self).create(vals)
        result.check_due_date(duedate)
        return result
    
    def write(self, vals):
        if vals.get('due_date'):
            self.check_due_date(vals.get('due_date'))
        result = super(EmployeeAssetReturn, self).write(vals)
        return result
    
    def check_due_date(self, date):
        if date:
            date = fields.Date.from_string(date)
            if date <= fields.Date.today():
                raise UserError(_('Due Date must be greater than today.'))
            else:
                return True

    def scheduled_employee_asset_return(self):
        employee_asset_return = self.env['employee.asset.return'].search([('state', 'in', ['waiting', 'draft'])])
        for line in employee_asset_return:
            if line.due_date <= fields.Date.today():
                for asset in line.assets_line:
                    notification_ids = [(0, 0, {
                        'res_partner_id': asset.employee_id.partner_id.id,
                        'notification_type': 'inbox'
                    })]
                    line.message_post(
                        body=("You have exceeded your due date, please return %s. See %s for further details." % (asset.asset_id.name, line.name)),
                        message_type="notification",
                        subtype_xmlid="mail.mt_comment",
                        author_id=self.env.user.partner_id.id,
                        notification_ids=notification_ids
                    )
                line.action_expired()
        return True
    
    def action_cancel(self):
        self.state = 'cancelled'
        
    def action_waiting(self):
        self.state = 'waiting'
    
    def action_done(self):
        asset_employee_management_line = self.assets_line
        if asset_employee_management_line:
            try:
                for line in asset_employee_management_line:
                    line.asset_id.owner = False
                self.state = 'done'
            except Exception as e:
                raise UserError(_('Error: ' + str(e)))
        else:
            raise UserError(_('Please add asset line before approve.'))
        
    def action_expired(self):
        self.state = 'expired'
        
class EmployeeAssetReturnLine(models.Model):
    _name = 'employee.asset.return.line'
    _description = 'Employee Asset Return Line'
    
    employee_asset_return_id = fields.Many2one('employee.asset.return', string='Employee Asset Return')
    asset_id = fields.Many2one('maintenance.equipment', string='Asset', required=True)
    employee_id = fields.Many2one('res.users', string='Employee', required=True)
    notes = fields.Text(string='Notes')