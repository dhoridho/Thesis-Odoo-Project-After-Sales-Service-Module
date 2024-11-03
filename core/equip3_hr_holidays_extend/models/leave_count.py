from odoo import api, fields, models, _
from datetime import date, timedelta
from dateutil import relativedelta as rd
from dateutil.relativedelta import relativedelta
from lxml import etree
import math


class HrLeaveCount(models.Model):
    _name = 'hr.leave.count'
    _description = 'Hr Leave Count'
    _order = 'id desc'
    


    name = fields.Char('Name', copy=False, related="employee_id.name")
    active = fields.Boolean(string='Active', default=True, store=True)
    employee_id = fields.Many2one('hr.employee', string='Employee')
    department_id = fields.Many2one('hr.department', string='Department', related="employee_id.department_id",
                                    store=True)
    job_id = fields.Many2one('hr.job', string='Job Position', related="employee_id.job_id",
                                    store=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    holiday_status_id = fields.Many2one("hr.leave.type", string="Leave Type")
    start_date = fields.Date('Start Valid Date', required="1")
    expired_date = fields.Date('Valid Until', required="1")
    hr_months = fields.Integer('Hr Months')
    hr_years_monthly = fields.Integer('Hr Years Monthly')
    hr_years = fields.Integer('Hr Years', group_operator='avg')
    count = fields.Float('Count')
    is_expired = fields.Boolean(string='Expired', compute='compute_current_period', store=True)
    description = fields.Char('Description')
    holiday_type = fields.Selection([
        ('employee', 'By Employee'),
        ('category', 'By Employee Tag')
    ], string='Allocation Mode', readonly=True)
    check_date = fields.Date('Current Year', store=True, compute='compute_current_period')
    leave_balance_id = fields.Many2one("hr.leave.balance", domain="[('employee_id','=',employee_id),('holiday_status_id','=',holiday_status_id),('active','=',True)]", string="Leave Balance")
    
    def custom_menu(self):
        search_view_id = self.env.ref("equip3_hr_holidays_extend.view_hr_leave_count_filter")
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
                'name': 'Leave Count',
                'res_model': 'hr.leave.count',
                'target': 'current',
                'view_mode': 'tree,form',
                'domain': [('employee_id','in',employee_ids)],
                'context': {'search_default_group_employee_id':1,'search_default_group_name':1,'is_supervisor':True},
            'search_view_id':search_view_id.id,
            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Leave Count',
                'res_model': 'hr.leave.count',
                'target': 'current',
                'view_mode': 'tree,form',
                'domain': [],
                'context': {'search_default_group_employee_id':1,'search_default_group_name':1},
                'search_view_id':search_view_id.id,
            }
    
    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=True, submenu=True):
        res = super(HrLeaveCount, self).fields_view_get(
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

    @api.depends('employee_id', 'hr_years', 'start_date')
    def compute_current_period(self):
        current_date = fields.Date.today()
        for balance in self:
            if balance.start_date and balance.expired_date:
                if balance.expired_date >= current_date >= balance.start_date:
                    balance.is_expired = False
                else:
                    balance.is_expired = True
            if balance.hr_years:
                balance.check_date = date(balance.hr_years, balance.start_date.month, balance.start_date.day)
            else:
                balance.check_date = 0

    def create_allocation_leave_count(self):
        current_date = fields.Date.today()
        current_year = current_date.year
        for emp in self.env['hr.employee'].search([('active', '=', True)]):
            for leave_type in emp.leave_struct_id.leaves_ids:
                current_balance = self.env['hr.leave.balance'].search(
                    [('employee_id', '=', emp.id), ('holiday_status_id', '=', leave_type.id),('active', '=', True)], order='id desc', limit=1)
                for count in self.env['hr.leave.count'].with_context(active_test=False).search(
                        [('employee_id', '=', emp.id), ('holiday_status_id', '=', leave_type.id),
                         ('description', '=', 'Allocation')], order='id desc',
                        limit=1):
                    start_date = False
                    end_date = False
                    leave_balance_id = False
                    if count.holiday_status_id.leave_method == 'monthly':
                        if count.holiday_status_id.monthly_start_valid_based_on == 'years_of_service':
                            yos_leave_type = emp.date_of_joining + relativedelta(
                                years=count.holiday_status_id.year_method_monthly,months=count.holiday_status_id.month_method_monthly, days=count.holiday_status_id.day_method_monthly)
                            yos_employee = emp.date_of_joining + relativedelta(
                                years=emp.years_of_service,months=emp.months, days=emp.days)
                            if yos_employee < yos_leave_type:
                                start_yos = yos_leave_type
                            else:
                                start_yos = count.start_date + relativedelta(months=1)
                        else:
                            start_yos = count.start_date + relativedelta(months=1)
                        start_date = count.start_date + relativedelta(months=1)
                        start_date_month = date(current_date.year, current_date.month, start_date.day)
                        # if count.start_date != start_date_month:
                        if count.hr_months != current_date.month:
                            if count.expired_date > current_date:
                                if yos_employee < start_yos:
                                    start_date = start_yos
                                else:
                                    start_date = start_date
                                end_date = count.expired_date
                                if int(current_balance.current_period) == current_date.year:
                                    current_balance.assigned = current_balance.assigned + leave_type.leave_entitlement
                                leave_balance_id = count.leave_balance_id
                            else:
                                if yos_employee < start_yos:
                                    start_date = start_yos
                                else:
                                    start_date = start_date
                                end_date = count.expired_date + relativedelta(years=1)
                                leave_balance_id = self.env['hr.leave.balance'].create({
                                                        'employee_id': emp.id,
                                                        'holiday_status_id': leave_type.id,
                                                        'leave_entitlement': leave_type.leave_entitlement,
                                                        'assigned': leave_type.leave_entitlement,
                                                        'hr_years': current_date.year,
                                                        'hr_years_monthly': current_date.year,
                                                        'start_date': start_date,
                                                        'current_period': current_year,
                                                    })
                                current_balance.active = False
                    elif leave_type.leave_method == 'none':
                        if leave_type.allocation_valid_until == "number_of_days":
                            start_date = count.expired_date + relativedelta(days=1)
                            start_date_month = date(current_date.year, current_date.month, start_date.day)
                            valid_to = start_date + relativedelta(days=leave_type.expiry_days)
                            date_end_year = date(current_date.year, 12, 31)
                            if valid_to <= date_end_year:
                                valid_to_date = valid_to
                            else:
                                valid_to_date = date_end_year
                            if count.expired_date <= current_date:
                                end_date = valid_to_date
                                if int(current_balance.current_period) == current_date.year:
                                    current_balance.assigned = current_balance.assigned + leave_type.leave_entitlement
                                    leave_balance_id = current_balance
                                else:
                                    leave_balance_id = self.env['hr.leave.balance'].create({
                                                            'employee_id': emp.id,
                                                            'holiday_status_id': leave_type.id,
                                                            'leave_entitlement': leave_type.leave_entitlement,
                                                            'assigned': leave_type.leave_entitlement,
                                                            'hr_years': current_date.year,
                                                            'hr_years_monthly': current_date.year,
                                                            'start_date': start_date,
                                                            'current_period': current_year,
                                                        })
                                    current_balance.active = False
                        elif leave_type.allocation_valid_until == "spesific_days":
                            start_date = count.expired_date + relativedelta(days=1)
                            valid_specific_month = int(leave_type.allocation_months_expired)
                            valid_specific_date = int(leave_type.allocation_date_expired)
                            next_year = current_date.year + 1
                            if count.expired_date <= current_date:
                                start_date_before = count.start_date + relativedelta(days=1)
                                start_date_year = date(current_date.year, start_date.month, start_date.day)
                                if start_date_before != start_date_year:
                                    leave_balance_id = self.env['hr.leave.balance'].create({
                                                            'employee_id': emp.id,
                                                            'holiday_status_id': leave_type.id,
                                                            'start_date': start_date,
                                                            'leave_entitlement': leave_type.leave_entitlement,
                                                            'assigned': leave_type.leave_entitlement,
                                                            'hr_years': current_date.year,
                                                            'hr_years_monthly': current_date.year,
                                                            'current_period': current_year,
                                                        })
                                    current_balance.active = False
                                    end_date = date(next_year, valid_specific_month, valid_specific_date)
                        elif leave_type.allocation_valid_until == "end_of_year":
                            start_date = date(current_date.year, 1, 1)
                            if count.start_date.year != current_date.year:
                                leave_balance_id = self.env['hr.leave.balance'].create({
                                                        'employee_id': emp.id,
                                                        'holiday_status_id': leave_type.id,
                                                        'start_date': start_date,
                                                        'leave_entitlement': leave_type.leave_entitlement,
                                                        'assigned': leave_type.leave_entitlement,
                                                        'hr_years': current_date.year,
                                                        'hr_years_monthly': current_date.year,
                                                        'current_period': current_year,
                                                    })
                                current_balance.active = False
                                end_date = count.expired_date + relativedelta(years=1)
                    else:
                        start_date = date(current_date.year, count.start_date.month, count.start_date.day)
                        if count.start_date != start_date:
                            leave_balance_id = self.env['hr.leave.balance'].create({
                                                    'employee_id': emp.id,
                                                    'holiday_status_id': leave_type.id,
                                                    'start_date': start_date,
                                                    'leave_entitlement': leave_type.leave_entitlement,
                                                    'assigned': leave_type.leave_entitlement,
                                                    'hr_years': current_date.year,
                                                    'hr_years_monthly': current_date.year,
                                                    'current_period': current_year,
                                                })
                            current_balance.active = False
                            end_date = count.expired_date + relativedelta(years=1)
                    if end_date:
                        if leave_balance_id:
                            balance_id = leave_balance_id.id
                        else:
                            balance_id = False
                        self.env['hr.leave.count'].create({
                            'employee_id': emp.id,
                            'holiday_status_id': leave_type.id,
                            'count': leave_type.leave_entitlement,
                            'start_date': start_date,
                            'expired_date': end_date,
                            'hr_years': current_date.year,
                            'hr_months': current_date.month,
                            'leave_balance_id': balance_id,
                            'description': 'Allocation',
                        })

    def expired_carry_forward(self):
        for count in self.env['hr.leave.count'].with_context(active_test=False).search(
                [('is_expired', '=', True), ('description', '=', 'Carry Forward')]):
            for balance in self.env['hr.leave.balance'].search(
                    [('employee_id', '=', count.employee_id.id), ('holiday_status_id', '=', count.holiday_status_id.id),
                     ('current_period', '=', count.hr_years), ('count_ids', 'not in', count.id)]):
                if balance:
                    balance.bring_forward = balance.bring_forward - count.count
                    balance.count_ids = [(4, count.id)]

    def create_allocation_new_employee(self):
        for emp in self.env['hr.employee'].search([('active', '=', True)]):
            hr_years = self.env['hr.years'].search([('name', '=', date.today().year),('status', '=', 'open')], limit=1)
            if emp.date_of_joining:
                for leave in emp.leave_struct_id.leaves_ids:
                    if leave.leave_method == 'anniversary':
                        one_year_ago = int(hr_years.name) - 1
                        if emp.date_of_joining.year == one_year_ago or emp.date_of_joining.year == hr_years.name:
                            start_date = emp.date_of_joining
                            var = int(hr_years.name) - 1
                            # to_date = date(var, 12, 31)
                            to_date = date.today()
                            diff = rd.relativedelta(to_date, start_date)
                            months = diff.months + (12 * diff.years) + 1
                            valid_month = int(start_date.strftime("%m"))
                            valid_date = int(start_date.strftime("%d"))
                            valid_start_date = date(hr_years.name, valid_month, valid_date)
                            valid_to_year = valid_start_date + relativedelta(years=1)
                            valid_to_date = valid_to_year + relativedelta(days=-1)
                            if months == 12:
                                if leave.is_prorate:
                                    count_join_month = 0
                                    if leave.is_count_join_month:
                                        count_join_month = 1
                                    if leave.prorate_rounding == "rounding_down":
                                        assigned_anniversary = math.floor(((12 - valid_month) / 12) * leave.leave_entitlement) + count_join_month
                                    elif leave.prorate_rounding == "rounding_up":
                                        assigned_anniversary = math.ceil(((12 - valid_month) / 12) * leave.leave_entitlement) + count_join_month
                                else:
                                    assigned_anniversary = leave.leave_entitlement
                            elif months > 12:
                                assigned_anniversary = leave.leave_entitlement
                            else:
                                assigned_anniversary = 0
                            self.env.cr.execute(
                                """SELECT id, employee_id FROM hr_leave_balance where employee_id = %d and holiday_status_id 
                                = %d and hr_years = %d and active = 'true' ORDER BY id DESC LIMIT 1""" % (
                                    emp.id, leave.id, hr_years.name))
                            leave_balance_active = self.env.cr.dictfetchall()
                            if leave.carry_forward in ['remaining_amount','specific_days']:
                                is_limit_period = leave.is_limit_period
                                limit_period = leave.limit_period
                            else:
                                is_limit_period = False
                                limit_period = int(0)
                            if not leave_balance_active and assigned_anniversary > 0:
                                if not leave.gender or leave.gender == emp.gender:
                                    leave_balance_id = self.env['hr.leave.balance'].create({
                                                            'employee_id': emp.id,
                                                            'holiday_status_id': leave.id,
                                                            'leave_entitlement': leave.leave_entitlement,
                                                            'assigned': assigned_anniversary,
                                                            'hr_years': hr_years.name,
                                                            'current_period': hr_years.name,
                                                            'start_date': valid_start_date,
                                                            'is_limit_period': is_limit_period,
                                                            'limit_period': limit_period,
                                                            'hr_years_id': hr_years.id,
                                                        })
                                self.env.cr.execute(
                                    """SELECT employee_id FROM hr_leave_count where employee_id = %d and holiday_status_id 
                                    = %d and hr_years = %d and active = 'true'""" % (
                                        emp.id, leave.id, hr_years.name))
                                hr_leave_count = self.env.cr.fetchall()
                                if not hr_leave_count and assigned_anniversary > 0:
                                    if not leave.gender or leave.gender == emp.gender:
                                        self.env['hr.leave.count'].create({
                                            'employee_id': emp.id,
                                            'holiday_status_id': leave.id,
                                            'count': assigned_anniversary,
                                            'hr_years': hr_years.name,
                                            'start_date': valid_start_date,
                                            'expired_date': valid_to_date,
                                            'leave_balance_id': leave_balance_id.id,
                                            'description': 'Allocation',
                                        })
                    elif leave.leave_method != 'anniversary':
                        if emp.date_of_joining.year == hr_years.name:
                            if leave.leave_method == 'annually':
                                assigned = 0
                                start_date = emp.date_of_joining
                                var = int(hr_years.name) - 1
                                to_date = date(var, 12, 31)
                                diff = rd.relativedelta(to_date, start_date)
                                if start_date.year >= int(hr_years.name):
                                    months = 0
                                else:
                                    months = diff.months + (12 * diff.years) + 1
                                valid_month = int(leave.leave_months_appear)
                                valid_date = int(leave.leave_date_appear)
                                valid_start_date = date(hr_years.name, valid_month, valid_date)
                                valid_to_date = date(hr_years.name, 12, 31)
                                if months >= 12:
                                    assigned = assigned + leave.leave_entitlement
                                else:
                                    assigned = assigned + (leave.leave_entitlement / 12) * months
                                self.env.cr.execute(
                                    """SELECT id, employee_id FROM hr_leave_balance where employee_id = %d and holiday_status_id 
                                    = %d and hr_years = %d and active = 'true' ORDER BY id DESC LIMIT 1""" % (
                                        emp.id, leave.id, hr_years.name))
                                leave_balance_active = self.env.cr.dictfetchall()
                                if leave.carry_forward in ['remaining_amount','specific_days']:
                                    is_limit_period = leave.is_limit_period
                                    limit_period = leave.limit_period
                                else:
                                    is_limit_period = False
                                    limit_period = int(0)
                                if not leave_balance_active and assigned > 0:
                                    if not leave.gender or leave.gender == emp.gender:
                                        leave_balance_id = self.env['hr.leave.balance'].create({
                                                                'employee_id': emp.id,
                                                                'holiday_status_id': leave.id,
                                                                'leave_entitlement': leave.leave_entitlement,
                                                                'assigned': assigned,
                                                                'current_period': hr_years.name,
                                                                'hr_years': hr_years.name,
                                                                'start_date': valid_start_date,
                                                                'is_limit_period': is_limit_period,
                                                                'limit_period': limit_period,
                                                                'hr_years_id': hr_years.id,
                                                            })
                                    self.env.cr.execute(
                                        """SELECT employee_id FROM hr_leave_count where employee_id = %d and holiday_status_id 
                                        = %d and hr_years = %d and active = 'true'""" % (
                                            emp.id, leave.id, hr_years.name))
                                    hr_leave_count = self.env.cr.fetchall()
                                    if not hr_leave_count and assigned > 0:
                                        if not leave.gender or leave.gender == emp.gender:
                                            self.env['hr.leave.count'].create({
                                                'employee_id': emp.id,
                                                'holiday_status_id': leave.id,
                                                'count': assigned,
                                                'start_date': valid_start_date,
                                                'expired_date': valid_to_date,
                                                'hr_years': hr_years.name,
                                                'leave_balance_id': leave_balance_id.id,
                                                'description': 'Allocation',
                                            })
                            elif leave.leave_method == 'monthly':
                                if leave.monthly_start_valid_based_on == 'years_of_service':
                                    yos_leave_type = emp.date_of_joining + relativedelta(
                                        years=leave.year_method_monthly,months=leave.month_method_monthly, days=leave.day_method_monthly)
                                    yos_employee = emp.date_of_joining + relativedelta(
                                        years=emp.years_of_service,months=emp.months, days=emp.days)
                                    if yos_employee < yos_leave_type:
                                        start_yos = yos_leave_type
                                    else:
                                        start_yos = emp.date_of_joining
                                else:
                                    start_yos = emp.date_of_joining
                                start_date = emp.date_of_joining
                                current_year = hr_years.name
                                current_day = date.today()
                                valid_month = int(start_date.strftime("%m"))
                                valid_date = int(start_date.strftime("%d"))
                                valid_start_date = date(hr_years.name, valid_month, valid_date)
                                valid_monthly_start_date = valid_start_date + relativedelta(months=1)
                                monthly_assigned = 0
                                while valid_monthly_start_date < current_day:
                                    if monthly_assigned < leave.maximum_leave:
                                        monthly_assigned += leave.leave_entitlement
                                    valid_monthly_start_date += relativedelta(months=1)
                                self.env.cr.execute(
                                    """SELECT id, employee_id FROM hr_leave_balance where employee_id = %d and holiday_status_id 
                                    = %d and hr_years_monthly = %d and active = 'true' ORDER BY id DESC LIMIT 1""" % (
                                        emp.id, leave.id, current_year))
                                leave_balance_active = self.env.cr.dictfetchall()
                                if leave.carry_forward in ['remaining_amount','specific_days']:
                                    is_limit_period = leave.is_limit_period
                                    limit_period = leave.limit_period
                                else:
                                    is_limit_period = False
                                    limit_period = int(0)
                                if not leave_balance_active and monthly_assigned > 0:
                                    if not leave.gender or leave.gender == emp.gender:
                                        if valid_start_date < start_yos:
                                            valid_start_date = start_yos
                                        else:
                                            valid_start_date = valid_start_date
                                        leave_balance_id = self.env['hr.leave.balance'].create({
                                                                'employee_id': emp.id,
                                                                'holiday_status_id': leave.id,
                                                                'leave_entitlement': leave.leave_entitlement,
                                                                'assigned': monthly_assigned,
                                                                'hr_years': hr_years.name,
                                                                'hr_years_monthly': hr_years.name,
                                                                'current_period': hr_years.name,
                                                                'start_date': valid_start_date,
                                                                'is_limit_period': is_limit_period,
                                                                'limit_period': limit_period,
                                                                'hr_years_id': hr_years.id,
                                                            })
                                    start_list = []
                                    to_count_date = 0
                                    if leave.maximum_leave and leave.leave_entitlement:
                                        to_count_date = math.ceil(leave.maximum_leave / leave.leave_entitlement)
                                    if current_year == start_date.year:
                                        monthly_start_date = start_date
                                        monthly_to_date = monthly_start_date + relativedelta(months=to_count_date)
                                        while monthly_start_date < monthly_to_date:
                                            if monthly_start_date >= start_yos:
                                                start_yos += relativedelta(months=1)
                                            monthly_start_date += relativedelta(months=1)
                                            if monthly_start_date < current_day:
                                                row = [None, None]
                                                row[0] = monthly_start_date
                                                row[1] = start_yos
                                                start_list.append(row)
                                    else:
                                        valid_date = int(start_date.strftime("%d"))
                                        monthly_start_date = date(current_year, 1, valid_date)
                                        monthly_to_date = monthly_start_date + relativedelta(months=to_count_date)
                                        while monthly_start_date < monthly_to_date and monthly_start_date < current_day:
                                            row = [None, None]
                                            row[0] = monthly_start_date
                                            row[1] = start_yos
                                            start_list.append(row)
                                            if monthly_start_date >= start_yos:
                                                start_yos += relativedelta(months=1)
                                            monthly_start_date += relativedelta(months=1)
                                    to_date = ''
                                    value = 0
                                    final_value = leave.leave_entitlement
                                    for count_start_date in start_list:
                                        if leave.valid_leave == 'one_year':
                                            monthly_to_date = count_start_date[0] + relativedelta(years=1)
                                            to_date = monthly_to_date - relativedelta(days=1)
                                        elif leave.valid_leave == 'end_year':
                                            to_date = date(current_year, 12, 31)
                                        current_count_month = count_start_date[0].month
                                        self.env.cr.execute(
                                            """SELECT employee_id FROM hr_leave_count where employee_id = %d and holiday_status_id 
                                            = %d and hr_months = %d and hr_years_monthly = %d and active = 'true'""" % (
                                                emp.id, leave.id, current_count_month, current_year))
                                        hr_leave_count = self.env.cr.fetchall()
                                        value += leave.leave_entitlement
                                        if value > leave.maximum_leave:
                                            last_before = value - leave.leave_entitlement
                                            final_value = leave.maximum_leave - last_before
                                        if not hr_leave_count:
                                            if not leave.gender or leave.gender == emp.gender:
                                                self.env['hr.leave.count'].create({
                                                    'employee_id': emp.id,
                                                    'holiday_status_id': leave.id,
                                                    'count': final_value,
                                                    'hr_years': hr_years.name,
                                                    'hr_months': current_count_month,
                                                    'hr_years_monthly': hr_years.name,
                                                    'start_date': count_start_date[1],
                                                    'expired_date': to_date,
                                                    'leave_balance_id': leave_balance_id.id,
                                                    'description': 'Allocation',
                                                })
                            elif leave.leave_method == 'none':
                                start_date = emp.date_of_joining
                                valid_month = int(start_date.strftime("%m"))
                                valid_date = int(start_date.strftime("%d"))
                                valid_start_date = date(hr_years.name, valid_month, valid_date)
                                if leave.allocation_valid_until == 'end_of_year':
                                    valid_to_date = date(hr_years.name, 12, 31)
                                elif leave.allocation_valid_until == 'spesific_days':
                                    valid_specific_month = int(leave.allocation_months_expired)
                                    valid_specific_date = int(leave.allocation_date_expired)
                                    next_year = int(hr_years.name) + 1
                                    valid_to_date = date(next_year, valid_specific_month, valid_specific_date)
                                elif leave.allocation_valid_until == 'number_of_days':
                                    valid_to_date = valid_start_date + relativedelta(days=leave.expiry_days)
                                assigned_none = leave.leave_entitlement
                                self.env.cr.execute(
                                    """SELECT id, employee_id FROM hr_leave_balance where employee_id = %d and holiday_status_id 
                                    = %d and hr_years = %d and active = 'true' ORDER BY id DESC LIMIT 1""" % (
                                        emp.id, leave.id, hr_years.name))
                                leave_balance_active = self.env.cr.dictfetchall()
                                if leave.carry_forward in ['remaining_amount','specific_days']:
                                    is_limit_period = leave.is_limit_period
                                    limit_period = leave.limit_period
                                else:
                                    is_limit_period = False
                                    limit_period = int(0)
                                if not leave_balance_active:
                                    if not leave.gender or leave.gender == emp.gender:
                                        leave_balance_id = self.env['hr.leave.balance'].create({
                                                            'employee_id': emp.id,
                                                            'holiday_status_id': leave.id,
                                                            'leave_entitlement': leave.leave_entitlement,
                                                            'assigned': assigned_none,
                                                            'hr_years': hr_years.name,
                                                            'current_period': hr_years.name,
                                                            'start_date': valid_start_date,
                                                            'is_limit_period': is_limit_period,
                                                            'limit_period': limit_period,
                                                            'hr_years_id': hr_years.id,
                                                        })
                                    self.env.cr.execute(
                                        """SELECT employee_id FROM hr_leave_count where employee_id = %d and holiday_status_id 
                                        = %d and hr_years = %d and active = 'true'""" % (
                                            emp.id, leave.id, hr_years.name))
                                    hr_leave_count = self.env.cr.fetchall()
                                    if not hr_leave_count:
                                        if not leave.gender or leave.gender == emp.gender:
                                            self.env['hr.leave.count'].create({
                                                'employee_id': emp.id,
                                                'holiday_status_id': leave.id,
                                                'count': assigned_none,
                                                'hr_years': hr_years.name,
                                                'start_date': valid_start_date,
                                                'expired_date': valid_to_date,
                                                'leave_balance_id': leave_balance_id.id,
                                                'description': 'Allocation',
                                            })

    @api.model
    def _cron_unlink_expire_leave_count(self):
        self.create_allocation_new_employee()
        self.expired_carry_forward()
        current_date = fields.Date.today()
        self.create_allocation_leave_count()
        leave_balance = self.env['hr.leave.balance'].search([('current_period', '<', current_date.year)])
        if leave_balance:
            for lb in leave_balance:
                lb.active = False
        leave_count = self.env['hr.leave.count'].search(
            [('expired_date', '<', current_date), ('active', '=', True)])
        if leave_count:
            for lc in leave_count:
                # leave_balance_reduce = self.env['hr.leave.balance'].search(
                #     [('employee_id', '=', lc.employee_id.id), ('holiday_status_id', '=', lc.holiday_status_id.id),
                #      ('current_period', '<', current_date.year)])
                # leave_balance_reduce.active = False

                leave_balance_active = self.env['hr.leave.balance'].search([('employee_id', '=', lc.employee_id.id),
                                                                        ('holiday_status_id', '=', lc.holiday_status_id.id),
                                                                        ('current_period', '=', current_date.year),
                                                                        ('active', '=', True)], limit=1)
                assigned = 0
                if lc.description == "Leave Allocation Request":
                    assigned = leave_balance_active.assigned - lc.count
                else:
                    if lc.holiday_status_id.leave_method == 'none' and lc.description == "Allocation":
                        if lc.holiday_status_id.allocation_valid_until == "number_of_days":
                            assigned = leave_balance_active.assigned - lc.count
                        else:
                            assigned = leave_balance_active.assigned
                    else:
                        assigned = leave_balance_active.assigned
                leave_balance_active.assigned = assigned
                lc.active = False
                lc.is_expired = True
