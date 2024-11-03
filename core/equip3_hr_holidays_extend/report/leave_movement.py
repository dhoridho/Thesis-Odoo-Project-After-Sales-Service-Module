# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools, exceptions, _
from odoo.osv import expression


class LeaveMovement(models.Model):
    _name = "hr.leave.movement"
    _description = 'Leave Summary / Report'
    _auto = False
    _order = "date_from DESC, employee_id"

    employee_id = fields.Many2one('hr.employee', string="Employee", readonly=True)
    name = fields.Char('Description', readonly=True)
    number_of_days = fields.Float('Number of Days', readonly=True)
    leave_type = fields.Selection([
        ('request', 'Leave Request'),
        ('allocation', 'Allocation'),
        ('cancel', 'Leave Cancellation')
    ], string='Request Type', readonly=True)
    current_period = fields.Integer('Current Period', readonly=True)
    department_id = fields.Many2one('hr.department', string='Department', readonly=True)
    category_id = fields.Many2one('hr.employee.category', string='Employee Tag', readonly=True)
    holiday_status_id = fields.Many2one("hr.leave.type", string="Leave Type", readonly=True)
    state = fields.Selection([
        ('draft', 'To Submit'),
        ('cancel', 'Cancelled'),
        ('confirm', 'To Approve'),
        ('refuse', 'Refused'),
        ('validate1', 'Second Approval'),
        ('validate', 'Approved')
    ], string='Status', readonly=True)
    holiday_type = fields.Selection([
        ('employee', 'By Employee'),
        ('category', 'By Employee Tag')
    ], string='Allocation Mode', readonly=True)
    date_from = fields.Datetime('Start Date', readonly=True)
    date_to = fields.Datetime('End Date', readonly=True)
    payslip_status = fields.Boolean('Reported in last payslips', readonly=True)
    current_year = fields.Date('Current Year', readonly=True)
    carry_forward_expiry = fields.Boolean('Carry Forward Expiry', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self._cr, 'hr_leave_movement')

        self._cr.execute("""
            CREATE or REPLACE view hr_leave_movement as (
                SELECT row_number() over(ORDER BY leaves.employee_id) as id,
            leaves.employee_id as employee_id, leaves.name as name,
                leaves.number_of_days as number_of_days, leaves.leave_type as leave_type,
                leaves.category_id as category_id, leaves.department_id as department_id,
                leaves.holiday_status_id as holiday_status_id, leaves.current_year as current_year,
                leaves.current_period as current_period, leaves.carry_forward_expiry as carry_forward_expiry, 
                leaves.state as state,
                leaves.holiday_type as holiday_type, leaves.date_from as date_from,
                leaves.date_to as date_to, leaves.payslip_status as payslip_status
                from (select
                    request.employee_id as employee_id,
                    'Leave Request' as name,
                    request.number_of_days as number_of_days,
                    request.category_id as category_id,
                    request.department_id as department_id,
                    request.holiday_status_id as holiday_status_id,
                    request.state as state,
                    request.holiday_type,
                    request.date_from as date_from,
                    request.date_to as date_to,
                    request.payslip_status as payslip_status,
                    request.current_period as current_period,
                    request.request_date_to as current_year,
                    False as carry_forward_expiry,
                    'request' as leave_type
                from hr_leave as request
                union all select
                    cancel.employee_id as employee_id,
                    'Leave Cancellation' as name,
                    cancel.number_of_days as number_of_days,
                    null as category_id,
                    cancel.department_id as department_id,
                    cancel.holiday_status_id as holiday_status_id,
                    cancel.state as state,
                    cancel.holiday_type,
                    cancel.request_date_from as date_from,
                    cancel.request_date_to as date_to,
                    FALSE as payslip_status,
                    cancel.current_period as current_period,
                    cancel.request_date_to as current_year,
                    False as carry_forward_expiry,
                    'cancel' as leave_type
                from hr_leave_cancelation as cancel
                union all select
                    balance.employee_id as employee_id,
                    'Leave Allocation' as name,
                    balance.assigned as number_of_days,
                    null as category_id,
                    balance.department_id as department_id,
                    balance.holiday_status_id as holiday_status_id,
                    'validate' as state,
                    balance.holiday_type,
                    null as date_from,
                    null as date_to,
                    FALSE as payslip_status,
                    balance.hr_years as current_period,
                    balance.check_date as current_year,
                    False as carry_forward_expiry,
                    'allocation' as leave_type
                from hr_leave_balance as balance where balance.description is null
                union all select
                    balance.employee_id as employee_id,
                    'Leave Allocation Request' as name,
                    balance.assigned as number_of_days,
                    null as category_id,
                    balance.department_id as department_id,
                    balance.holiday_status_id as holiday_status_id,
                    'validate' as state,
                    balance.holiday_type,
                    null as date_from,
                    null as date_to,
                    FALSE as payslip_status,
                    balance.hr_years as current_period,
                    balance.check_date as current_year,
                    False as carry_forward_expiry,
                    'allocation' as leave_type
                from hr_leave_balance as balance where balance.description = 'Leave Allocation Request'
                union all select
                    count.employee_id as employee_id,
                    'Carry Forward' as name,
                    count.count as number_of_days,
                    null as category_id,
                    null as department_id,
                    count.holiday_status_id as holiday_status_id,
                    'validate' as state,
                    count.holiday_type,
                    null as date_from,
                    null as date_to,
                    FALSE as payslip_status,
                    count.hr_years as current_period,
                    count.check_date as current_year,
                    False as carry_forward_expiry,
                    'allocation' as leave_type
                from hr_leave_count as count where count.description = 'Carry Forward' and count.is_expired = False
                union all select
                    count.employee_id as employee_id,
                    'Carry Forward Expiry' as name,
                    count.count as number_of_days,
                    null as category_id,
                    null as department_id,
                    count.holiday_status_id as holiday_status_id,
                    'validate' as state,
                    count.holiday_type,
                    null as date_from,
                    null as date_to,
                    FALSE as payslip_status,
                    count.hr_years as current_period,
                    count.check_date as current_year,
                    False as carry_forward_expiry,
                    'allocation' as leave_type
                from hr_leave_count as count where count.description = 'Carry Forward' and count.is_expired = True
                union all select
                    count.employee_id as employee_id,
                    'Extra Leave' as name,
                    count.count as number_of_days,
                    null as category_id,
                    null as department_id,
                    count.holiday_status_id as holiday_status_id,
                    'validate' as state,
                    count.holiday_type,
                    null as date_from,
                    null as date_to,
                    FALSE as payslip_status,
                    count.hr_years as current_period,
                    count.check_date as current_year,
                    False as carry_forward_expiry,
                    'allocation' as leave_type
                from hr_leave_count as count where count.description = 'Extra Leave') leaves
            );
        """)

    @api.model
    def action_time_off_analysis(self):
        # domain = [('holiday_type', '=', 'employee')]
        domain = []
        if self.env.context.get('active_ids'):
            domain = expression.AND([
                domain,
                [('employee_id', 'in', self.env.context.get('active_ids', []))]
            ])

        return {
            'name': _('Leave Movement'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.leave.movement',
            'view_mode': 'tree,pivot,form',
            'search_view_id': self.env.ref('equip3_hr_holidays_extend.view_hr_leave_movement_filter_report').id,
            'domain': domain,
            'context': {
                'search_default_group_employee': True,
                'search_default_group_type': True,
                'search_default_year': True,
                'search_default_validated': True,
            }
        }

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain += [('employee_id.company_id', 'in', self.env.context.get('allowed_company_ids'))]

        result = super(LeaveMovement, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return result
    
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        context = self.env.context
        domain = domain or []
        
        if not self.user_has_groups('hr_holidays.group_hr_holidays_user') and 'name' in groupby:
            raise exceptions.UserError(_('Such grouping is not allowed.'))
        
        if context.get('allowed_company_ids'):
            domain.extend([('employee_id.company_id', 'in', self.env.context.get('allowed_company_ids'))])
        return super(LeaveMovement, self).read_group(domain, fields, groupby, offset=offset, limit=limit,
                                                     orderby=orderby, lazy=lazy)
