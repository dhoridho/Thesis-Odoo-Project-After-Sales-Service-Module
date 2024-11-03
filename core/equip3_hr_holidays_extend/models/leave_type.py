from odoo import api, fields, models, _
from odoo.tools.float_utils import float_round
from datetime import date
from odoo.exceptions import ValidationError
from lxml import etree


class HrLeaveType(models.Model):
    _name = 'hr.leave.type'
    _description = "Hr Leave Type"
    _inherit = ['hr.leave.type', 'mail.thread']

    name = fields.Char('Leave Type', required=True, translate=True, tracking=True)
    gender = fields.Selection([('male', 'Male'), ('female', 'Female')], string='Gender')
    is_dashboard = fields.Boolean('Show on Dashboard', default=False, tracking=True)
    leave_entitlement = fields.Float('Entitlement Leave', required=True, tracking=True, 
                                      help='\tIs the amount or number of leave entitlements based on the leave method; ')
    extra_leave_after = fields.Integer('Extra Leave After', tracking=True)
    extra_leave_frequency = fields.Integer('Extra Leave per Frequency', tracking=True)
    interval_unit = fields.Selection([('yearly', 'Yearly'), ('monthly', 'Monthly')], string='Interval Unit',
                                     tracking=True)
    maximum_extra_leave = fields.Integer('Maximum Extra Leave', tracking=True)
    months = fields.Integer(tracking=True)
    days = fields.Integer(tracking=True)
    year = fields.Char(string=' ', default='year(s) -')
    month = fields.Char(string=' ', default='month(s) -')
    day = fields.Char(string=' ', default='day(s)')
    allow_minus = fields.Boolean('Allow Minus', default=False, tracking=True)
    maximum_minus = fields.Integer('Maximum Minus', tracking=True)
    allow_past_date = fields.Boolean('Allow Past Date', default=False, tracking=True)
    past_days = fields.Integer('Past Dated Days', tracking=True)
    carry_forward = fields.Selection(
        [('none', 'None'), ('remaining_amount', 'Remaining Amount'), ('specific_days', 'Specific Days')],
        string='Carry Forward', tracking=True,
        help='\tThis feature is used to enable the feature of carrying over leave from the current year to the following year (also applies in minus conditions); ')
    no_of_days = fields.Integer('Number of Days', required=True, tracking=True)
    carry_forward_expiry = fields.Integer('Number of Days Expiry', tracking=True)
    rounding = fields.Selection([
        ('no_rounding', 'No Rounding'), ('rounding_up', 'Rounding Up'), ('rounding_down', 'Rounding Down')],
        string='Rounding', tracking=True)
    request_unit = fields.Selection([
        ('day', 'Day'), ('half_day', 'Half Day'), ('hour', 'Hours')],
        default='day', string='Take Leave in', required=True, tracking=True, 
        help='\tDay : Will only able to be requested in units of Days; '
             '\tHalf Day : Will able to be requested on a Half Day schema; '
             '\tHours : Will able to be requested on a specific Hours ')
    leave_method = fields.Selection(
        [('annually', 'Annually'), ('anniversary', 'Anniversary'), ('monthly', 'Monthly'), ('none', 'None')],
        string='Leave Method', tracking=True, required=True)
    monthly_start_valid_based_on = fields.Selection(
        [('leave_method_schema','Leave Method Schema'),
         ('years_of_service', 'Years of Service')],
         string='Start Valid Based On', tracking=True, required=True, default='leave_method_schema')
    year_method_monthly = fields.Integer('Year Method Monthly', tracking=True)
    month_method_monthly = fields.Integer('Month Method Monthly', tracking=True)
    day_method_monthly = fields.Integer('Day Method Monthly', tracking=True)
    
    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain += [('company_id', 'in', self.env.context.get('allowed_company_ids'))]

        result = super(HrLeaveType, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return result
    
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain.extend([('company_id', 'in', self.env.context.get('allowed_company_ids'))])
        return super(HrLeaveType, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
    
    @api.model
    def get_allocation_validation_type_selection(self):
        return [('hr', 'By Leaves Officer'),
                ('manager', "By Employee's Manager"),
                ('both', "By Employee's Manager and Leaves Officer"),
                ('by_approval_matrix', "By Approval Matrix")]
    
    allocation_validation_type = fields.Selection(get_allocation_validation_type_selection, default='manager', string='Allocation Validation')
    leave_months_appear = fields.Selection([
        ('1', 'January'),
        ('2', 'February'),
        ('3', 'March'),
        ('4', 'April'),
        ('5', 'May'),
        ('6', 'June'),
        ('7', 'July'),
        ('8', 'August'),
        ('9', 'September'),
        ('10', 'October'),
        ('11', 'November'),
        ('12', 'December')], default='1', string='Leave Date Appear', tracking=True, 
        help='\tAppearance of leave in the coming year; ')
    leave_date_appear = fields.Selection([
        ('1', '1'),
        ('2', '2'),
        ('3', '3'),
        ('4', '4'),
        ('5', '5'),
        ('6', '6'),
        ('7', '7'),
        ('8', '8'),
        ('9', '9'),
        ('10', '10'),
        ('11', '11'),
        ('12', '12'),
        ('13', '13'),
        ('14', '14'),
        ('15', '15'),
        ('16', '16'),
        ('17', '17'),
        ('18', '18'),
        ('19', '19'),
        ('20', '20'),
        ('21', '21'),
        ('22', '22'),
        ('23', '23'),
        ('24', '24'),
        ('25', '25'),
        ('26', '26'),
        ('27', '27'),
        ('28', '28'),
        ('29', '29'),
        ('30', '30'),
        ('31', '31')
    ], default='1', string='Leave Date Appear', tracking=True)
    valid_leave = fields.Selection(
        [('one_year', '1 Year After Allocation'), ('end_year', 'End of the Running Year')],
        string='Valid until', tracking=True)
    maximum_leave = fields.Integer(string="Maximum Leave")
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, tracking=True)
    branch_id = fields.Many2one("res.branch", string="Branch", domain="[('company_id', '=', company_id)]",
                                tracking=True)
    limit_days = fields.Integer(string="Limit Days to Apply", tracking=True)
    minimum_days_before = fields.Integer('Minimum Days Before Application', tracking=True)
    is_required = fields.Boolean(string="Required Attachment", default=True, tracking=True)
    day_count = fields.Selection([('work_day', 'Work Day'), ('calendar_day', "Calendar Day")], default='work_day',
                                 string='Day Count By', tracking=True,
                                 help='\tWill be used as the main reference in calculating the target days; '
                                      '\tWork Day: will compare with the employees work schedule; '
                                      '\tCalendar Day: compares with the existing calendar schedule; ')
    set_by = fields.Selection([('duration', "Duration"), ('times', 'Times')], default='duration',
                              string='Set By', tracking=True, required=True,
                              help='\tDuration : will count the sum of days requested for; '
                                   '\tTimes : will be calculated based on per leave request, not the sum of days; ')
    allocation_type = fields.Selection([
        ('no', 'No Limit'),
        ('fixed_allocation', 'Allow Employees Requests'),
        ('fixed', 'Set by Leave Officer')],
        default='no', string='Mode', tracking=True,
        help='\tNo Limit: no allocation by default, users can freely request time off; '
             '\tAllow Employees Requests: allocated by HR and users can request time off and allocations; '
             '\tSet by Time Off Officer: allocated by HR and cannot be bypassed; users can request time off; ')
    
    @api.model
    def get_leave_validation_type_selection(self):
        return [('no_validation', 'No Validation'),
                ('by_employee_hierarchy', "By Employee Hierarchy"),
                ('by_approval_matrix', "By Approval Matrix"),
                ('both', "By Employee's Manager and Leave Officer")]
    
    leave_validation_type = fields.Selection(get_leave_validation_type_selection,
        default=False, string='Leave Validation')
    leave_validation_type_clone = fields.Selection(selection=[
        ('no_validation', 'No Validation'),
        ('by_employee_hierarchy', "By Employee Hierarchy"),
        ('by_approval_matrix', "By Approval Matrix"), ('both', "By Employee's Manager and Leave Officer")],
        default=False, string='Leave Validation', required=True)
    leave_notif_subtype_id = fields.Many2one('mail.message.subtype', string='Leave Notification Subtype',
                                             default=lambda self: self.env.ref('hr_holidays.mt_leave',
                                                                               raise_if_not_found=False))
    approval_level = fields.Integer(string="Approval Levels", default=1)
    create_calendar_meeting = fields.Boolean(string="Display Leave in Calendar", default=True)
    employee_id = fields.Many2one('hr.employee', string='Attendance Employee')
    expiry_days = fields.Integer()
    repeated_allocation = fields.Boolean("Repeated Allocation", help='\tTurning on this boolean will grant the employee access to recurring leave allocations in the same year; ')
    overtime_extra_leave = fields.Boolean("Overtime Extra Leave", help='\tTurning on this boolean will give access to the feature to add leave based on Actual Overtime; ')
    min_days_before_alloc = fields.Integer('Minimum Days Before Application')
    total_actual_hours = fields.Boolean("Total Actual Hours")
    formula = fields.Text(string='Formula', 
        default='''if actual_hours >= 4 and actual_hours < 8:
    duration = 0.5
elif actual_hours >= 8:
    duration = 1.0''')
    count_on_payslip = fields.Boolean('Count on Payslip', help='\tThis feature is used to activate the feature of bringing the remaining leave to be cashed out/encashment leave; ')
    carry_forward_expiry_selection = fields.Selection(selection=[
        ('number_of_days', 'Number of Days Expiry'),
        ('leave_method_expiry', 'Leave Method Expiry')],
        default=False, string='Carry Forward Expiry')
    is_limit_period = fields.Boolean('Has Period Limit')
    limit_period = fields.Integer('Limit Period')
    urgent_leave = fields.Boolean('Urgent Leave', help='\tEnabling this feature allows users to request urgent leave that will override any existing conditions; ')
    attendance_status = fields.Selection([
        ('absent', 'Absent'),
        ('present', 'Present'),
        ('leave', 'Leave')], default='leave', string='Attendance Status')
    attachment_notes = fields.Text('Attachment Notes', default='*')
    allocation_valid_until = fields.Selection(selection=[
        ('end_of_year', 'End of Year'),
        ('spesific_days', "Specific Days"),
        ('number_of_days', "Number of Days")],
        default='end_of_year', string='Valid Until')
    allocation_months_expired = fields.Selection([
        ('1', 'January'),
        ('2', 'February'),
        ('3', 'March'),
        ('4', 'April'),
        ('5', 'May'),
        ('6', 'June'),
        ('7', 'July'),
        ('8', 'August'),
        ('9', 'September'),
        ('10', 'October'),
        ('11', 'November'),
        ('12', 'December')], default='', string='Allocation Month Expired', tracking=True)
    allocation_date_expired = fields.Selection([
        ('1', '1'),
        ('2', '2'),
        ('3', '3'),
        ('4', '4'),
        ('5', '5'),
        ('6', '6'),
        ('7', '7'),
        ('8', '8'),
        ('9', '9'),
        ('10', '10'),
        ('11', '11'),
        ('12', '12'),
        ('13', '13'),
        ('14', '14'),
        ('15', '15'),
        ('16', '16'),
        ('17', '17'),
        ('18', '18'),
        ('19', '19'),
        ('20', '20'),
        ('21', '21'),
        ('22', '22'),
        ('23', '23'),
        ('24', '24'),
        ('25', '25'),
        ('26', '26'),
        ('27', '27'),
        ('28', '28'),
        ('29', '29'),
        ('30', '30'),
        ('31', '31')
    ], default='', string='Allocation Date Expired', tracking=True)
    is_show_attendance_report = fields.Boolean('Show on Attendance Report')
    is_prorate = fields.Boolean('Prorate', help='\tTurning on this boolean will enable the prorated feature when granting employee leave; ')
    prorate_rounding = fields.Selection(selection=[
        ('rounding_down', 'Rounding Down'),
        ('rounding_up', 'Rounding Up')],
        default='rounding_down', string='Rounding')
    is_count_join_month = fields.Boolean('Count Joining Month')

    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=True, submenu=True):
        res = super(HrLeaveType, self).fields_view_get(
            view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        if not self.env.user.has_group('hr_holidays.group_hr_holidays_user'):
            root = etree.fromstring(res['arch'])
            root.set('create', 'false')
            root.set('edit', 'false')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)

        return res

    @api.onchange('leave_validation_type_clone')
    def _onchange_leave_validation_type_clone(self):
        for record in self:
            if record.leave_validation_type_clone:
                record.leave_validation_type = record.leave_validation_type_clone

    # @api.constrains('leave_validation_type')
    # def _check_validation_type(self):
    #     if self.leave_validation_type in ('hr', 'manager'):
    #         raise ValidationError(
    #             _('You can not choose empty space.'))

    def name_get(self):
        # if not self.employee_id:
        #     # leave counts is based on employee_id, would be inaccurate if not based on correct employee
        #     return super(HrLeaveType, self).name_get()
        if not self._context.get('employee_id'):
            # leave counts is based on employee_id, would be inaccurate if not based on correct employee
            return super(HrLeaveType, self).name_get()
        res = []
        for record in self:
            name = record.name
            # employee_id = record.employee_id
            employee_id = int(self._context.get('employee_id'))
            check_period = date.today().year
            leave_balance = record.env['hr.leave.balance'].search(
                [('employee_id', '=', employee_id), ('holiday_status_id', '=', record.id),
                 ('current_period', '=', str(check_period))], limit=1)
            if record.allocation_type and leave_balance:
                name = "%(name)s (%(count)s)" % {
                    'name': name,
                    'count': _('%g remaining out of %g') % (
                        float_round(float(leave_balance.remaining), precision_digits=2) or 0.0,
                        float_round(float(leave_balance.assigned) + float(leave_balance.bring_forward) + float(leave_balance.extra_leave), precision_digits=2) or 0.0,
                    ) + (_(' hours') if record.request_unit == 'hour' else _(' days'))
                }
            res.append((record.id, name))
            # record.update({
            #     'employee_id': False,
            # })
        return res

    @api.onchange('leave_method')
    def _onchange_valid_leave(self):
        for record in self:
            if record.leave_method == 'monthly':
                record.valid_leave = 'end_year'