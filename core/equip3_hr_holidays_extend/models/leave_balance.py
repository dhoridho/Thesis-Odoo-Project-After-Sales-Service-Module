from odoo import api, fields, models, _
from datetime import date, timedelta
import datetime
from dateutil.relativedelta import relativedelta
import math
from lxml import etree


class MyLeaveBalance(models.Model):
    _name = 'hr.leave.balance'
    _description = 'My Leave Balance'
    _inherit = ['mail.thread']
    _order = 'id desc'
    _rec_name = 'employee_id'

    @api.model
    def _multi_company_domain(self):
        return [('company_id','=', self.env.company.id)]

    employee_id = fields.Many2one('hr.employee', string='Employee', tracking=True, domain=_multi_company_domain)
    department_id = fields.Many2one('hr.department', string='Department', related="employee_id.department_id",
                                    store=True)
    job_id = fields.Many2one('hr.job', string='Job Position', related="employee_id.job_id",
                                    store=True)
    state = fields.Selection([('draft', 'To Submit'), ('confirm', 'To Approve'), ('validate', 'Approved')],
                             string='Status', default='draft', tracking=True)
    active = fields.Boolean(string='Active', default=True)
    holiday_status_id = fields.Many2one("hr.leave.type", string="Leave Type", domain=_multi_company_domain)
    is_dashboard = fields.Boolean(
        related='holiday_status_id.is_dashboard', 
        store=True, 
        readonly=True,
        string='Show on Dashboard')
    set_by = fields.Selection(string='Set By', related='holiday_status_id.set_by', store=True)
    leave_generate_id = fields.Many2one("hr.leave.allocate.generator", string="Generator")
    code = fields.Char('Code', tracking=True, related='holiday_status_id.code')
    leave_entitlement = fields.Float('Entitlement', tracking=True)
    assigned = fields.Float('Assigned', tracking=True)
    used = fields.Float('Used', tracking=True, compute='compute_balance', compute_sudo=True)
    carry_forward_value = fields.Float('Carry Forward Value', tracking=True)
    carry_forward = fields.Selection(
        [('none', 'None'), ('remaining_amount', 'Remaining Amount'), ('specific_days', 'Specific Days')],
        string='Carry Forward Type', tracking=True)
    bring_forward = fields.Float('Carry Forward', tracking=True)
    current_period = fields.Char('Current Period', tracking=True, store=True)
    remaining = fields.Float('Balance', tracking=True, compute="compute_balance", compute_sudo=True)
    balance = fields.Float('Balance', tracking=True, compute="compute_balance", store=True)
    holiday_type = fields.Selection([
        ('employee', 'By Employee'),
        ('category', 'By Employee Tag')
    ], string='Allocation Mode', readonly=True)
    hr_years_id = fields.Many2one('hr.years', 'Hr ID')
    hr_years = fields.Integer('Hr Years')
    hr_years_monthly = fields.Integer('Hr Years Monthly')
    company_id = fields.Many2one("res.company", string="Company", default=lambda self: self.env.company)
    count_ids = fields.Many2many("hr.leave.count", string="Count")
    start_date = fields.Date('Start Valid Date')
    extra_leave = fields.Integer('Extra Leaves', tracking=True)
    check_date = fields.Date('Current Year', store=True, compute='compute_current_period')
    description = fields.Char('Description')
    is_limit_period = fields.Boolean('Is Limit Period')
    limit_period = fields.Integer('Limit Period')

    def name_get(self):
        result = []
        for rec in self:
            name = rec.employee_id.name + ' - ' + rec.holiday_status_id.name + ' - ' + rec.current_period
            result.append((rec.id, name))
        return result
    

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain += [('company_id', 'in', self.env.context.get('allowed_company_ids'))]

        result = super(MyLeaveBalance, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return result
    
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain.extend([('company_id', 'in', self.env.context.get('allowed_company_ids'))])
        return super(MyLeaveBalance, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
    
    def custom_menu(self):
        search_view_id = self.env.ref("equip3_hr_holidays_extend.equip3_view_leave_balance_filter")
        if self.env.user.has_group('equip3_hr_employee_access_right_setting.group_responsible') and not self.env.user.has_group('hr_holidays.group_hr_holidays_user'):
            employee_ids = []
            my_employee = self.env['hr.employee'].sudo().search([('user_id', '=', self.env.user.id),('company_id','in',self.env.company.ids)])
            if my_employee:
                for child_record in my_employee.child_ids:
                    employee_ids.append(my_employee.id)
                    employee_ids.append(child_record.id)
                    child_record._get_amployee_hierarchy(employee_ids, child_record.child_ids, my_employee.id)
            return {
                'type': 'ir.actions.act_window',
                'name': 'Leave Balance',
                'res_model': 'hr.leave.balance',
                'target': 'current',
                'view_mode': 'tree,form',
                'domain': [('employee_id','in',employee_ids)],
                'context': {'search_default_group_employee_id':1,'is_supervisor':True},
            'search_view_id':search_view_id.id,
            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Leave Balance',
                'res_model': 'hr.leave.balance',
                'target': 'current',
                'view_mode': 'tree,form',
                'domain': [],
                'context': {'search_default_group_employee_id':1,'search_default_filter_is_dashboard':1},
                'search_view_id':search_view_id.id,
            }
    
    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=True, submenu=True):
        res = super(MyLeaveBalance, self).fields_view_get(
            view_id=view_id, view_type=view_type,toolbar=toolbar,submenu=submenu)
        if self.env.user.has_group('hr_holidays.group_hr_holidays_manager'):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
        else:
            root = etree.fromstring(res['arch'])
            root.set('create', 'false')
            root.set('edit', 'false')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
        return res

    @api.depends('employee_id', 'current_period', 'start_date')
    def compute_current_period(self):
        for balance in self:
            if balance.employee_id:
                balance.check_date = date(int(balance.current_period), balance.start_date.month, balance.start_date.day)
            else:
                balance.check_date = 0

    @api.model
    def create(self, vals):
        balance = super(MyLeaveBalance, self).create(vals)
        year = int(balance.current_period) - 1
        leave_balance = self.env['hr.leave.balance'].search(
            [('employee_id', '=', balance.employee_id.id),
             ('holiday_status_id', '=', balance.holiday_status_id.id),
             ('current_period', '=', year)])
        if balance.holiday_status_id:
            if balance.holiday_status_id.leave_method == 'none' and balance.holiday_status_id.allocation_type == 'fixed_allocation':
                valid_to_date = balance.start_date + relativedelta(days=balance.holiday_status_id.expiry_days)
            else:
                if balance.holiday_status_id.count_on_payslip or balance.holiday_status_id.carry_forward_expiry_selection == 'leave_method_expiry':
                    if balance.holiday_status_id.leave_method == 'annually':
                        valid_to_date = date(balance.start_date.year, 12, 31)
                    elif balance.holiday_status_id.leave_method == 'anniversary':
                        valid_to_year = balance.start_date + relativedelta(years=1)
                        valid_to_date = valid_to_year + relativedelta(days=-1)
                    elif balance.holiday_status_id.leave_method == 'monthly':
                        if balance.holiday_status_id.valid_leave == 'one_year':
                            monthly_to_date = balance.start_date + relativedelta(years=1)
                            valid_to_date = monthly_to_date - relativedelta(days=1)
                        elif balance.holiday_status_id.valid_leave == 'end_year':
                            valid_to_date = date(balance.start_date.year, 12, 31)
                else:
                    valid_to_date = balance.start_date + relativedelta(days=balance.holiday_status_id.carry_forward_expiry)
            if leave_balance:
                balance.carry_forward = balance.holiday_status_id.carry_forward
                balance.is_limit_period = leave_balance.is_limit_period
                if balance.is_limit_period:
                    balance.limit_period = leave_balance.limit_period
                else:
                    balance.limit_period = 0
                bring_forward = 0
                for leave_type in balance.holiday_status_id:
                    if not leave_type.count_on_payslip:
                        if not balance.is_limit_period or (balance.is_limit_period and balance.limit_period > 0) or (balance.is_limit_period and balance.limit_period == 0 and leave_balance.remaining < 0):
                            if leave_type.carry_forward == 'remaining_amount':
                                if leave_type.rounding == 'rounding_up':
                                    balance.bring_forward = math.ceil(leave_balance.remaining)
                                elif leave_type.rounding == 'rounding_down':
                                    balance.bring_forward = math.floor(leave_balance.remaining)
                                else:
                                    balance.bring_forward = leave_balance.remaining
                                if balance.is_limit_period and balance.limit_period > 0:
                                    balance.limit_period = leave_balance.limit_period - 1
                            elif leave_type.carry_forward == 'specific_days' and leave_type.no_of_days < float(
                                    leave_balance.remaining):
                                if leave_type.rounding == 'rounding_up':
                                    balance.bring_forward = math.ceil(leave_type.no_of_days)
                                elif leave_type.rounding == 'rounding_down':
                                    balance.bring_forward = math.floor(leave_type.no_of_days)
                                else:
                                    balance.bring_forward = leave_type.no_of_days
                                if balance.is_limit_period and balance.limit_period > 0:
                                    balance.limit_period = leave_balance.limit_period - 1
                            elif leave_type.carry_forward == 'specific_days' and leave_type.no_of_days > float(
                                    leave_balance.remaining):
                                if leave_type.rounding == 'rounding_up':
                                    balance.bring_forward = math.ceil(leave_balance.remaining)
                                elif leave_type.rounding == 'rounding_down':
                                    balance.bring_forward = math.floor(leave_balance.remaining)
                                else:
                                    balance.bring_forward = leave_balance.remaining
                                if balance.is_limit_period and balance.limit_period > 0:
                                    balance.limit_period = leave_balance.limit_period - 1
                if not balance.holiday_status_id.count_on_payslip:
                    if balance.bring_forward != 0:
                        leave_count = self.env['hr.leave.count'].search([('leave_balance_id','=',leave_balance.id),('description','!=','Carry Forward')], order="id desc, expired_date desc", limit=1)
                        count_start_date = leave_count.expired_date + relativedelta(days=1)
                        self.env['hr.leave.count'].create({
                            'employee_id': balance.employee_id.id,
                            'holiday_status_id': balance.holiday_status_id.id,
                            'count': balance.bring_forward,
                            'start_date': count_start_date,
                            'expired_date': valid_to_date,
                            'hr_years': int(balance.current_period),
                            'leave_balance_id': balance.id,
                            'description': 'Carry Forward',
                        })
        return balance

    @api.depends('assigned', 'used', 'carry_forward_value')
    def compute_balance(self):
        for vals in self:
            if vals.current_period:
                firstday = datetime.datetime(int(vals.current_period), 1, 1)
                lastday = datetime.datetime(int(vals.current_period), 12, 31)
                leave = self.env['hr.leave'].search(
                    [('employee_id', '=', vals.employee_id.id),
                     ('holiday_status_id', '=', vals.holiday_status_id.id),
                    #  ('request_date_from', '<=', lastday),
                    #  ('request_date_to', '>=', firstday),
                     ('leave_balance_id', '=', vals.id),
                     ('state', 'in', ['confirm','validate1','validate'])])
                leave_company = self.env['hr.leave'].search(
                    [('holiday_type', '=', 'company'),
                     ('holiday_status_id', '=', vals.holiday_status_id.id),
                     ('request_date_from', '<=', lastday),
                     ('request_date_to', '>=', firstday),
                    # ('leave_balance_id', '=', vals.id),
                     ('state', 'in', ['confirm','validate1','validate'])])
                leave_department = self.env['hr.leave'].search(
                    [('holiday_type', '=', 'department'),
                     ('holiday_status_id', '=', vals.holiday_status_id.id),
                     ('request_date_from', '<=', lastday),
                     ('request_date_to', '>=', firstday),
                    # ('leave_balance_id', '=', vals.id),
                     ('state', 'in', ['confirm','validate1','validate'])])
                leave_category = self.env['hr.leave'].search(
                    [('holiday_type', '=', 'category'),
                     ('holiday_status_id', '=', vals.holiday_status_id.id),
                     ('request_date_from', '<=', lastday),
                     ('request_date_to', '>=', firstday),
                    # ('leave_balance_id', '=', vals.id),
                     ('state', 'in', ['confirm','validate1','validate'])])
                total_count = 0
                total_count_company = 0
                total_count_department = 0
                total_count_category = 0
                if vals.holiday_status_id.set_by == 'duration':
                    for line in leave:
                        if line.holiday_type == 'employee':
                            total_count += line.number_of_days
                else:
                    total_count = len(leave)

                if vals.holiday_status_id.set_by == 'duration':
                    for line_company in leave_company:
                        if vals.employee_id.sudo().company_id == line_company.mode_company_id:
                            total_count_company += line_company.number_of_days
                else:
                    total_count_company = len(leave_company)
                if vals.holiday_status_id.set_by == 'duration':
                    for line_department in leave_department:
                        if vals.employee_id.sudo().department_id == line_department.department_id:
                            total_count_department += line_department.number_of_days
                else:
                    total_count_department = len(leave_department)
                if vals.holiday_status_id.set_by == 'duration':
                    for line_category in leave_category:
                        if vals.employee_id.sudo().category_ids in line_category.category_id:
                            total_count_category += line_category.number_of_days
                else:
                    total_count_category = len(leave_category)
                vals.used = total_count + total_count_company + total_count_department + total_count_category
                vals.remaining = vals.assigned - vals.used + vals.bring_forward + vals.extra_leave
                vals.balance = vals.assigned - vals.used + vals.bring_forward + vals.extra_leave

                leave_type_master = vals.env['hr.leave.type'].search([])
                leave_type_master.update({
                    'employee_id': False,
                })
            else:
                vals.used = 0
                vals.remaining = 0
                vals.balance = 0

    @api.model
    def _cron_extra_leave_balance(self):
        current_date = fields.Date.today()
        for balance in self.env['hr.leave.balance'].search([]):
            start_list = []
            count = 0
            if balance.employee_id.date_of_joining:
                if balance.extra_leave < balance.holiday_status_id.maximum_extra_leave:
                    start_extra_leave = balance.employee_id.date_of_joining + relativedelta(
                        years=balance.holiday_status_id.extra_leave_after,
                        months=balance.holiday_status_id.months, days=balance.holiday_status_id.days)
                    if balance.holiday_status_id.interval_unit == 'monthly':
                        start_extra_leave = start_extra_leave - relativedelta(months=1)
                        end_extra_balance = ''
                        if balance.holiday_status_id.extra_leave_frequency and balance.holiday_status_id.maximum_extra_leave:
                            end_count = balance.holiday_status_id.maximum_extra_leave / balance.holiday_status_id.extra_leave_frequency
                            end_extra_balance = start_extra_leave + relativedelta(months=round(end_count))
                        if current_date >= start_extra_leave:
                            while start_extra_leave < end_extra_balance:
                                start_extra_leave += relativedelta(months=1)
                                if balance.holiday_status_id.maximum_extra_leave >= count:
                                    if current_date >= start_extra_leave:
                                        count += balance.holiday_status_id.extra_leave_frequency
                                        start_list.append(start_extra_leave)
                    elif balance.holiday_status_id.interval_unit == 'yearly':
                        start_extra_leave = start_extra_leave - relativedelta(years=1)
                        end_extra_balance = ''
                        if balance.holiday_status_id.extra_leave_frequency and balance.holiday_status_id.maximum_extra_leave:
                            end_count = balance.holiday_status_id.maximum_extra_leave / balance.holiday_status_id.extra_leave_frequency
                            end_extra_balance = start_extra_leave + relativedelta(years=round(end_count))
                        if current_date >= start_extra_leave:
                            while start_extra_leave < end_extra_balance:
                                start_extra_leave += relativedelta(years=1)
                                if balance.holiday_status_id.maximum_extra_leave >= count:
                                    if current_date >= start_extra_leave:
                                        count += balance.holiday_status_id.extra_leave_frequency
                                        start_list.append(start_extra_leave)
                    balance.extra_leave = count
                for date in start_list:
                    if current_date.year > start_list[-1].year and date == start_list[-1]:
                        date = datetime.date(current_date.year, date.month, date.day)
                    if balance.holiday_status_id.interval_unit == 'monthly' and balance.holiday_status_id.leave_method == 'monthly':
                        leave = self.env['hr.leave.count'].search([('employee_id', '=', balance.employee_id.id),
                                                                   ('holiday_status_id', '=',
                                                                    balance.holiday_status_id.id),
                                                                   ('description', '=', 'Allocation')],
                                                                  order="start_date asc")
                        for leave_count in leave:
                            if date.year == leave_count.hr_years:
                                leave_count_exist = self.env['hr.leave.count'].search(
                                    [('employee_id', '=', balance.employee_id.id), ('holiday_status_id', '=',
                                                                                    balance.holiday_status_id.id),
                                     ('start_date', '=', date), ('description', '=', 'Extra Leave')])
                                if not leave_count_exist:
                                    if count == balance.holiday_status_id.maximum_extra_leave:
                                        if date == start_list[0]:
                                            date = datetime.date(current_date.year, date.month, date.day)
                                        self.env['hr.leave.count'].create({
                                            'employee_id': balance.employee_id.id,
                                            'holiday_status_id': balance.holiday_status_id.id,
                                            'count': count,
                                            'hr_months': leave_count.hr_months,
                                            'hr_years_monthly': leave_count.hr_years_monthly,
                                            'hr_years': leave_count.start_date.year,
                                            'start_date': date,
                                            'expired_date': leave_count.expired_date,
                                            'description': 'Extra Leave',
                                        })
                                    elif count != balance.holiday_status_id.maximum_extra_leave:
                                        self.env['hr.leave.count'].create({
                                            'employee_id': balance.employee_id.id,
                                            'holiday_status_id': balance.holiday_status_id.id,
                                            'count': balance.holiday_status_id.extra_leave_frequency,
                                            'hr_months': leave_count.hr_months,
                                            'hr_years_monthly': leave_count.hr_years_monthly,
                                            'hr_years': leave_count.start_date.year,
                                            'start_date': date,
                                            'expired_date': leave_count.expired_date,
                                            'description': 'Extra Leave',
                                        })
                    elif balance.holiday_status_id.interval_unit == 'monthly' and balance.holiday_status_id.leave_method != 'monthly':
                        if current_date.year > start_list[-1].year and date == start_list[-1]:
                            date = datetime.date(current_date.year, date.month, date.day)
                        leave_count = self.env['hr.leave.count'].search([('employee_id', '=', balance.employee_id.id),
                                                                         ('holiday_status_id', '=',
                                                                          balance.holiday_status_id.id),
                                                                         ('hr_years', '=', date.year),
                                                                         ('description', '=', 'Allocation')])
                        if leave_count:
                            leave_count_exist = self.env['hr.leave.count'].search(
                                [('employee_id', '=', balance.employee_id.id), ('holiday_status_id', '=',
                                                                                balance.holiday_status_id.id),
                                 ('start_date', '=', date), ('description', '=', 'Extra Leave')])
                            if not leave_count_exist:
                                if count == balance.holiday_status_id.maximum_extra_leave:
                                    if date == start_list[0]:
                                        date = datetime.date(current_date.year, date.month, date.day)
                                    self.env['hr.leave.count'].create({
                                        'employee_id': balance.employee_id.id,
                                        'holiday_status_id': balance.holiday_status_id.id,
                                        'count': count,
                                        'hr_months': leave_count.hr_months,
                                        'hr_years_monthly': leave_count.hr_years_monthly,
                                        'hr_years': leave_count.start_date.year,
                                        'start_date': date,
                                        'expired_date': leave_count.expired_date,
                                        'description': 'Extra Leave',
                                    })
                                elif count != balance.holiday_status_id.maximum_extra_leave:
                                    self.env['hr.leave.count'].create({
                                        'employee_id': balance.employee_id.id,
                                        'holiday_status_id': balance.holiday_status_id.id,
                                        'count': balance.holiday_status_id.extra_leave_frequency,
                                        'hr_months': leave_count.hr_months,
                                        'hr_years_monthly': leave_count.hr_years_monthly,
                                        'hr_years': leave_count.start_date.year,
                                        'start_date': date,
                                        'expired_date': leave_count.expired_date,
                                        'description': 'Extra Leave',
                                    })
                    elif balance.holiday_status_id.interval_unit == 'yearly' and balance.holiday_status_id.leave_method != 'monthly':
                        if current_date.year > start_list[-1].year and date == start_list[-1]:
                            date = datetime.date(current_date.year, date.month, date.day)
                        leave_count = self.env['hr.leave.count'].search([('employee_id', '=', balance.employee_id.id),
                                                                         ('holiday_status_id', '=',
                                                                          balance.holiday_status_id.id),
                                                                         ('hr_years', '=', date.year),
                                                                         ('description', '=', 'Allocation')])
                        if leave_count:
                            leave_count_exist = self.env['hr.leave.count'].search(
                                [('employee_id', '=', balance.employee_id.id), ('holiday_status_id', '=',
                                                                                balance.holiday_status_id.id),
                                 ('start_date', '=', leave_count.start_date), ('description', '=', 'Extra Leave')])
                            if not leave_count_exist:
                                self.env['hr.leave.count'].create({
                                    'employee_id': balance.employee_id.id,
                                    'holiday_status_id': balance.holiday_status_id.id,
                                    'count': count,
                                    'hr_months': leave_count.hr_months,
                                    'hr_years_monthly': leave_count.hr_years_monthly,
                                    'hr_years': leave_count.start_date.year,
                                    'start_date': leave_count.start_date,
                                    'expired_date': leave_count.expired_date,
                                    'description': 'Extra Leave',
                                })
                    elif balance.holiday_status_id.interval_unit == 'yearly' and balance.holiday_status_id.leave_method == 'monthly':
                        if current_date.year > start_list[-1].year and date == start_list[-1]:
                            date = datetime.date(current_date.year, date.month, date.day)
                        leave_count = self.env['hr.leave.count'].search([('employee_id', '=', balance.employee_id.id),
                                                                         ('holiday_status_id', '=',
                                                                          balance.holiday_status_id.id),
                                                                         ('hr_years', '=', date.year),
                                                                         ('description', '=', 'Allocation')],
                                                                        limit=1, order="start_date asc")
                        if leave_count:
                            leave_count_exist = self.env['hr.leave.count'].search(
                                [('employee_id', '=', balance.employee_id.id), ('holiday_status_id', '=',
                                                                                balance.holiday_status_id.id),
                                 ('start_date', '=', leave_count.start_date), ('description', '=', 'Extra Leave')])
                            if not leave_count_exist:
                                self.env['hr.leave.count'].create({
                                    'employee_id': balance.employee_id.id,
                                    'holiday_status_id': balance.holiday_status_id.id,
                                    'count': count,
                                    'hr_months': leave_count.hr_months,
                                    'hr_years_monthly': leave_count.hr_years_monthly,
                                    'hr_years': leave_count.start_date.year,
                                    'start_date': leave_count.start_date,
                                    'expired_date': leave_count.expired_date,
                                    'description': 'Extra Leave',
                                })
