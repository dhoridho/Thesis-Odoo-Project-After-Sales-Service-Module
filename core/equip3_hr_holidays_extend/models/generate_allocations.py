from odoo import api, fields, models, _
from datetime import date, timedelta
from dateutil import relativedelta as rd
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError
import datetime, math


class LeaveAllocateGenerator(models.Model):
    _name = 'hr.leave.allocate.generator'
    _description = 'Leave Allocate Generator'
    _inherit = ['mail.thread']
    _order = 'id desc'

    @api.model
    def _multi_company_domain(self):
        return [('company_id','=', self.env.company.id)]

    name = fields.Char('Name', copy=False, states={'generated': [('readonly', True)]})
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirmed'), ('generated', 'Generated')],
                             string='Status', default='draft')
    hr_years_id = fields.Many2one('hr.years', string='HR Years', domain=[('status', '=', 'open')],
                                  states={'generated': [('readonly', True)]})
    allocation_type = fields.Selection([
        ('employee', 'Employee'),
        ('company', 'Company'),
        ('department', 'Department')],
        default='employee', string='Mode', required=True, states={'generated': [('readonly', True)]})
    employee_ids = fields.Many2many('hr.employee', string='Employee', states={'generated': [('readonly', True)]}, domain=_multi_company_domain)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company,
                                 states={'generated': [('readonly', True)]})
    department_ids = fields.Many2many("hr.department", string="Department", states={'generated': [('readonly', True)]}, domain=_multi_company_domain)

    @api.onchange('name')
    def onchange_employee(self):
        res = {}
        contract_obj = self.env['hr.contract'].search([('state', '=', 'open')])
        employee_obj = self.env['hr.employee'].search(
            [('contract_ids', '!=', False), ('contract_ids', 'in', contract_obj.ids)])
        if employee_obj:
            employee_list = []
            for vals in employee_obj:
                employee_list.append(vals.id)
                res['domain'] = {'employee_ids': [('id', 'in', employee_list)]}
        else:
            res['domain'] = {'employee_ids': []}
        return res

    def unlink(self):
        for rec in self:
            if rec.state == 'generated':
                raise ValidationError(_('Cannot delete in Generated status'))
        return super(LeaveAllocateGenerator, self).unlink()

    def action_confirm(self):
        if self.allocation_type == 'department' and not self.department_ids:
            raise ValidationError(_('Please add Department in line'))
        if self.allocation_type == 'employee' and not self.employee_ids:
            raise ValidationError(_('Please add Employee in line'))
        self.write({'state': 'confirm'})

    def action_approve(self):
        if self.allocation_type == 'department':
            for department in self.department_ids:
                for dept in self.env['hr.employee'].search(
                        [('department_id', '=', department.id), ('company_id', '=', self.env.company.id)]):
                    for emp in dept.leave_struct_id.leaves_ids:
                        assigned = 0
                        if emp.leave_method == 'annually':
                            start_date = dept.date_of_joining
                            var = int(self.hr_years_id.name) - 1
                            to_date = date(var, 12, 31)
                            diff = rd.relativedelta(to_date, start_date)
                            if start_date.year >= int(self.hr_years_id.name):
                                months = 0
                            else:
                                months = diff.months + (12 * diff.years) + 1
                            valid_month = int(emp.leave_months_appear)
                            valid_date = int(emp.leave_date_appear)
                            if int(self.hr_years_id.name) > start_date.year:
                                valid_start_date = date(self.hr_years_id.name, 1, 1)
                            else:
                                valid_start_date = date(self.hr_years_id.name, valid_month, valid_date)
                            valid_to_date = date(self.hr_years_id.name, 12, 31)
                            if months >= 12:
                                assigned = assigned + emp.leave_entitlement
                            else:
                                assigned = assigned + (emp.leave_entitlement / 12) * months
                            employee = dept.id
                            self.env.cr.execute(
                                """SELECT id, employee_id FROM hr_leave_balance where employee_id = %d and holiday_status_id 
                                = %d and hr_years = %d and active = 'true' ORDER BY id DESC LIMIT 1""" % (
                                    employee, emp.id, self.hr_years_id.name))
                            leave_balance_active = self.env.cr.dictfetchall()
                            if emp.carry_forward in ['remaining_amount','specific_days']:
                                is_limit_period = emp.is_limit_period
                                limit_period = emp.limit_period
                            else:
                                is_limit_period = False
                                limit_period = int(0)
                            if not leave_balance_active and assigned > 0:
                                if not emp.gender or emp.gender == dept.gender:
                                    leave_balance_id = self.env['hr.leave.balance'].create({
                                                            'employee_id': dept.id,
                                                            'holiday_status_id': emp.id,
                                                            'leave_entitlement': emp.leave_entitlement,
                                                            'assigned': assigned,
                                                            'current_period': self.hr_years_id.name,
                                                            'hr_years': self.hr_years_id.name,
                                                            'hr_years_id': self.hr_years_id.id,
                                                            'start_date': valid_start_date,
                                                            'is_limit_period': is_limit_period,
                                                            'limit_period': limit_period,
                                                            'leave_generate_id': self.id,
                                                        })
                            elif leave_balance_active and emp.repeated_allocation == True:
                                leave_balance = self.env['hr.leave.balance'].browse(leave_balance_active[0].get('id'))
                                if not emp.gender or emp.gender == dept.gender:
                                    assign = leave_balance.assigned + assigned
                                    leave_balance.write({'assigned': assign,'limit_period': limit_period,'is_limit_period': is_limit_period})
                                    leave_balance_id = leave_balance
                            self.env.cr.execute(
                                """SELECT employee_id FROM hr_leave_count where employee_id = %d and holiday_status_id 
                                = %d and hr_years = %d and active = 'true'""" % (
                                    employee, emp.id, self.hr_years_id.name))
                            hr_leave_count = self.env.cr.fetchall()
                            if not hr_leave_count and assigned > 0:
                                if not emp.gender or emp.gender == dept.gender:
                                    self.env['hr.leave.count'].create({
                                        'employee_id': dept.id,
                                        'holiday_status_id': emp.id,
                                        'count': assigned,
                                        'start_date': valid_start_date,
                                        'expired_date': valid_to_date,
                                        'hr_years': self.hr_years_id.name,
                                        'leave_balance_id': leave_balance_id.id,
                                        'description': 'Allocation',
                                    })
                            elif hr_leave_count and emp.repeated_allocation == True:
                                if not emp.gender or emp.gender == dept.gender:
                                    self.env['hr.leave.count'].create({
                                        'employee_id': dept.id,
                                        'holiday_status_id': emp.id,
                                        'count': assigned,
                                        'start_date': valid_start_date,
                                        'expired_date': valid_to_date,
                                        'hr_years': self.hr_years_id.name,
                                        'leave_balance_id': leave_balance_id.id,
                                        'description': 'Allocation',
                                    })
                        elif emp.leave_method == 'anniversary':
                            start_date = dept.date_of_joining
                            var = int(self.hr_years_id.name) - 1
                            # to_date = date(var, 12, 31)
                            to_date = date.today()
                            diff = rd.relativedelta(to_date, start_date)
                            months = diff.months + (12 * diff.years) + 1
                            valid_month = int(start_date.strftime("%m"))
                            valid_date = int(start_date.strftime("%d"))
                            valid_start_date = date(self.hr_years_id.name, valid_month, valid_date)
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
                            employee = dept.id
                            self.env.cr.execute(
                                """SELECT id, employee_id FROM hr_leave_balance where employee_id = %d and holiday_status_id 
                                = %d and hr_years = %d and active = 'true' ORDER BY id DESC LIMIT 1""" % (
                                    employee, emp.id, self.hr_years_id.name))
                            leave_balance_active = self.env.cr.dictfetchall()
                            if emp.carry_forward in ['remaining_amount','specific_days']:
                                is_limit_period = emp.is_limit_period
                                limit_period = emp.limit_period
                            else:
                                is_limit_period = False
                                limit_period = int(0)
                            if not leave_balance_active and assigned_anniversary > 0:
                                if not emp.gender or emp.gender == dept.gender:
                                    leave_balance_id = self.env['hr.leave.balance'].create({
                                                            'employee_id': dept.id,
                                                            'holiday_status_id': emp.id,
                                                            'leave_entitlement': emp.leave_entitlement,
                                                            'assigned': assigned_anniversary,
                                                            'hr_years': self.hr_years_id.name,
                                                            'current_period': self.hr_years_id.name,
                                                            'leave_generate_id': self.id,
                                                            'start_date': valid_start_date,
                                                            'is_limit_period': is_limit_period,
                                                            'limit_period': limit_period,
                                                            'hr_years_id': self.hr_years_id.id,
                                                        })
                            elif leave_balance_active and emp.repeated_allocation == True:
                                leave_balance = self.env['hr.leave.balance'].browse(leave_balance_active[0].get('id'))
                                if not emp.gender or emp.gender == dept.gender:
                                    assign = leave_balance.assigned + assigned_anniversary
                                    leave_balance.write({'assigned': assign,'limit_period': limit_period,'is_limit_period': is_limit_period})
                                    leave_balance_id = leave_balance
                            self.env.cr.execute(
                                """SELECT employee_id FROM hr_leave_count where employee_id = %d and holiday_status_id 
                                = %d and hr_years = %d and active = 'true'""" % (
                                    employee, emp.id, self.hr_years_id.name))
                            hr_leave_count = self.env.cr.fetchall()
                            if not hr_leave_count and assigned_anniversary > 0:
                                if not emp.gender or emp.gender == dept.gender:
                                    self.env['hr.leave.count'].create({
                                        'employee_id': dept.id,
                                        'holiday_status_id': emp.id,
                                        'count': assigned_anniversary,
                                        'hr_years': self.hr_years_id.name,
                                        'start_date': valid_start_date,
                                        'expired_date': valid_to_date,
                                        'leave_balance_id': leave_balance_id.id,
                                        'description': 'Allocation',
                                    })
                            elif hr_leave_count and emp.repeated_allocation == True:
                                if not emp.gender or emp.gender == dept.gender:
                                    self.env['hr.leave.count'].create({
                                        'employee_id': dept.id,
                                        'holiday_status_id': emp.id,
                                        'count': assigned_anniversary,
                                        'hr_years': self.hr_years_id.name,
                                        'start_date': valid_start_date,
                                        'expired_date': valid_to_date,
                                        'leave_balance_id': leave_balance_id.id,
                                        'description': 'Allocation',
                                    })
                        elif emp.leave_method == 'monthly':
                            if emp.monthly_start_valid_based_on == 'years_of_service':
                                yos_leave_type = dept.date_of_joining + relativedelta(
                                    years=emp.year_method_monthly,months=emp.month_method_monthly, days=emp.day_method_monthly)
                                yos_employee = dept.date_of_joining + relativedelta(
                                    years=dept.years_of_service,months=dept.months, days=dept.days)
                                if yos_employee < yos_leave_type:
                                    start_yos = yos_leave_type
                                else:
                                    start_yos = dept.date_of_joining
                            else:
                                start_yos = dept.date_of_joining
                            start_date = dept.date_of_joining
                            current_year = self.hr_years_id.name
                            current_day = date.today()
                            valid_month = int(start_date.strftime("%m"))
                            valid_date = int(start_date.strftime("%d"))
                            valid_start_date = date(self.hr_years_id.name, valid_month, valid_date)
                            employee = dept.id
                            valid_monthly_start_date = valid_start_date + relativedelta(months=1)
                            monthly_assigned = 0
                            while valid_monthly_start_date < current_day:
                                if monthly_assigned < emp.maximum_leave:
                                    monthly_assigned += emp.leave_entitlement
                                valid_monthly_start_date += relativedelta(months=1)
                            self.env.cr.execute(
                                """SELECT id, employee_id FROM hr_leave_balance where employee_id = %d and holiday_status_id 
                                = %d and hr_years_monthly = %d and active = 'true' ORDER BY id DESC LIMIT 1""" % (
                                    employee, emp.id, current_year))
                            leave_balance_active = self.env.cr.dictfetchall()
                            if emp.carry_forward in ['remaining_amount','specific_days']:
                                is_limit_period = emp.is_limit_period
                                limit_period = emp.limit_period
                            else:
                                is_limit_period = False
                                limit_period = int(0)
                            if not leave_balance_active and monthly_assigned > 0:
                                if not emp.gender or emp.gender == dept.gender:
                                    if valid_start_date < start_yos:
                                        valid_start_date = start_yos
                                    else:
                                        valid_start_date = valid_start_date
                                    leave_balance_id = self.env['hr.leave.balance'].create({
                                                            'employee_id': dept.id,
                                                            'holiday_status_id': emp.id,
                                                            'leave_entitlement': emp.leave_entitlement,
                                                            'assigned': monthly_assigned,
                                                            'hr_years_monthly': self.hr_years_id.name,
                                                            'hr_years': self.hr_years_id.name,
                                                            'current_period': self.hr_years_id.name,
                                                            'leave_generate_id': self.id,
                                                            'start_date': valid_start_date,
                                                            'is_limit_period': is_limit_period,
                                                            'limit_period': limit_period,
                                                            'hr_years_id': self.hr_years_id.id,
                                                        })
                            elif leave_balance_active and emp.repeated_allocation == True:
                                leave_balance = self.env['hr.leave.balance'].browse(leave_balance_active[0].get('id'))
                                if not emp.gender or emp.gender == dept.gender:
                                    assign = leave_balance.assigned + emp.leave_entitlement
                                    leave_balance.write({'assigned': assign,'limit_period': limit_period,'is_limit_period': is_limit_period})
                                    leave_balance_id = leave_balance

                            start_list = []
                            to_count_date = 0
                            if emp.maximum_leave and emp.leave_entitlement:
                                to_count_date = math.ceil(emp.maximum_leave / emp.leave_entitlement)
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
                            final_value = emp.leave_entitlement
                            for count_start_date in start_list:
                                if emp.valid_leave == 'one_year':
                                    monthly_to_date = count_start_date[0] + relativedelta(years=1)
                                    to_date = monthly_to_date - relativedelta(days=1)
                                elif emp.valid_leave == 'end_year':
                                    to_date = date(current_year, 12, 31)
                                current_count_month = count_start_date[0].month
                                self.env.cr.execute(
                                    """SELECT employee_id FROM hr_leave_count where employee_id = %d and holiday_status_id 
                                    = %d and hr_months = %d and hr_years_monthly = %d and active = 'true'""" % (
                                        employee, emp.id, current_count_month, current_year))
                                hr_leave_count = self.env.cr.fetchall()
                                value += emp.leave_entitlement
                                if value > emp.maximum_leave:
                                    last_before = value - emp.leave_entitlement
                                    final_value = emp.maximum_leave - last_before
                                if not hr_leave_count:
                                    if not emp.gender or emp.gender == dept.gender:
                                        self.env['hr.leave.count'].create({
                                            'employee_id': dept.id,
                                            'holiday_status_id': emp.id,
                                            'count': final_value,
                                            'hr_months': current_count_month,
                                            'hr_years_monthly': self.hr_years_id.name,
                                            'hr_years': self.hr_years_id.name,
                                            'start_date': count_start_date[1],
                                            'expired_date': to_date,
                                            'leave_balance_id': leave_balance_id,
                                            'description': 'Allocation',
                                        })
                                elif hr_leave_count and emp.repeated_allocation == True:
                                    if not emp.gender or emp.gender == dept.gender:
                                        self.env['hr.leave.count'].create({
                                            'employee_id': dept.id,
                                            'holiday_status_id': emp.id,
                                            'count': final_value,
                                            'hr_months': current_count_month,
                                            'hr_years_monthly': self.hr_years_id.name,
                                            'hr_years': self.hr_years_id.name,
                                            'start_date': count_start_date[1],
                                            'expired_date': to_date,
                                            'leave_balance_id': leave_balance_id,
                                            'description': 'Allocation',
                                        })
                        elif emp.leave_method == 'none':
                            contract = dept.contract_id
                            start_date = contract.date_start
                            valid_month = int(start_date.strftime("%m"))
                            valid_date = int(start_date.strftime("%d"))
                            if int(self.hr_years_id.name) > start_date.year:
                                valid_start_date = date(self.hr_years_id.name, 1, 1)
                            else:
                                valid_start_date = date(self.hr_years_id.name, valid_month, valid_date)
                            if emp.allocation_valid_until == 'end_of_year':
                                valid_to_date = date(self.hr_years_id.name, 12, 31)
                            elif emp.allocation_valid_until == 'spesific_days':
                                valid_specific_month = int(emp.allocation_months_expired)
                                valid_specific_date = int(emp.allocation_date_expired)
                                next_year = int(self.hr_years_id.name) + 1
                                valid_to_date = date(next_year, valid_specific_month, valid_specific_date)
                            elif emp.allocation_valid_until == 'number_of_days':
                                valid_to_date = valid_start_date + relativedelta(days=emp.expiry_days)
                            assigned_none = emp.leave_entitlement
                            employee = dept.id
                            self.env.cr.execute(
                                """SELECT id, employee_id FROM hr_leave_balance where employee_id = %d and holiday_status_id 
                                = %d and hr_years = %d and active = 'true' ORDER BY id DESC LIMIT 1""" % (
                                    employee, emp.id, self.hr_years_id.name))
                            leave_balance_active = self.env.cr.dictfetchall()
                            if emp.carry_forward in ['remaining_amount','specific_days']:
                                is_limit_period = emp.is_limit_period
                                limit_period = emp.limit_period
                            else:
                                is_limit_period = False
                                limit_period = int(0)
                            if not leave_balance_active:
                                if not emp.gender or emp.gender == dept.gender:
                                    leave_balance_id = self.env['hr.leave.balance'].create({
                                                            'employee_id': dept.id,
                                                            'holiday_status_id': emp.id,
                                                            'leave_entitlement': emp.leave_entitlement,
                                                            'assigned': assigned_none,
                                                            'hr_years': self.hr_years_id.name,
                                                            'current_period': self.hr_years_id.name,
                                                            'leave_generate_id': self.id,
                                                            'start_date': valid_start_date,
                                                            'is_limit_period': is_limit_period,
                                                            'limit_period': limit_period,
                                                            'hr_years_id': self.hr_years_id.id,
                                                        })
                            elif leave_balance_active and emp.repeated_allocation == True:
                                leave_balance = self.env['hr.leave.balance'].browse(leave_balance_active[0].get('id'))
                                if not emp.gender or emp.gender == dept.gender:
                                    assign = leave_balance.assigned + assigned_none
                                    leave_balance.write({'assigned': assign,'limit_period': limit_period,'is_limit_period': is_limit_period})
                                    leave_balance_id = leave_balance
                            self.env.cr.execute(
                                """SELECT employee_id FROM hr_leave_count where employee_id = %d and holiday_status_id 
                                = %d and hr_years = %d and active = 'true'""" % (
                                    employee, emp.id, self.hr_years_id.name))
                            hr_leave_count = self.env.cr.fetchall()
                            if not hr_leave_count:
                                if not emp.gender or emp.gender == dept.gender:
                                    self.env['hr.leave.count'].create({
                                        'employee_id': dept.id,
                                        'holiday_status_id': emp.id,
                                        'count': assigned_none,
                                        'hr_years': self.hr_years_id.name,
                                        'start_date': valid_start_date,
                                        'expired_date': valid_to_date,
                                        'leave_balance_id': leave_balance_id.id,
                                        'description': 'Allocation',
                                    })
                            elif hr_leave_count and emp.repeated_allocation == True:
                                if not emp.gender or emp.gender == dept.gender:
                                    self.env['hr.leave.count'].create({
                                        'employee_id': dept.id,
                                        'holiday_status_id': emp.id,
                                        'count': assigned_none,
                                        'hr_years': self.hr_years_id.name,
                                        'start_date': valid_start_date,
                                        'expired_date': valid_to_date,
                                        'leave_balance_id': leave_balance_id.id,
                                        'description': 'Allocation',
                                    })
        elif self.allocation_type == 'company':
            for company in self.env['hr.employee'].search([('company_id', '=', self.company_id.id)]):
                for emp in company.leave_struct_id.leaves_ids:
                    assigned = 0
                    if emp.leave_method == 'annually':
                        start_date = company.date_of_joining
                        var = int(self.hr_years_id.name) - 1
                        to_date = date(var, 12, 31)
                        diff = rd.relativedelta(to_date, start_date)
                        if start_date.year >= int(self.hr_years_id.name):
                            months = 0
                        else:
                            months = diff.months + (12 * diff.years) + 1
                        valid_month = int(emp.leave_months_appear)
                        valid_date = int(emp.leave_date_appear)
                        if int(self.hr_years_id.name) > start_date.year:
                            valid_start_date = date(self.hr_years_id.name, 1, 1)
                        else:
                            valid_start_date = date(self.hr_years_id.name, valid_month, valid_date)
                        valid_to_date = date(self.hr_years_id.name, 12, 31)
                        if months >= 12:
                            assigned = assigned + emp.leave_entitlement
                        else:
                            assigned = assigned + (emp.leave_entitlement / 12) * months
                        employee = company.id
                        self.env.cr.execute(
                            """SELECT id, employee_id FROM hr_leave_balance where employee_id = %d and holiday_status_id 
                            = %d and hr_years = %d and active = 'true' ORDER BY id DESC LIMIT 1""" % (
                                employee, emp.id, self.hr_years_id.name))
                        leave_balance_active = self.env.cr.dictfetchall()
                        if emp.carry_forward in ['remaining_amount','specific_days']:
                            is_limit_period = emp.is_limit_period
                            limit_period = emp.limit_period
                        else:
                            is_limit_period = False
                            limit_period = int(0)
                        if not leave_balance_active and assigned > 0:
                            if not emp.gender or emp.gender == company.gender:
                                leave_balance_id = self.env['hr.leave.balance'].create({
                                                        'employee_id': company.id,
                                                        'holiday_status_id': emp.id,
                                                        'leave_entitlement': emp.leave_entitlement,
                                                        'assigned': assigned,
                                                        'current_period': self.hr_years_id.name,
                                                        'leave_generate_id': self.id,
                                                        'hr_years': self.hr_years_id.name,
                                                        'start_date': valid_start_date,
                                                        'is_limit_period': is_limit_period,
                                                        'limit_period': limit_period,
                                                        'hr_years_id': self.hr_years_id.id,
                                                    })
                        elif leave_balance_active and emp.repeated_allocation == True:
                            leave_balance = self.env['hr.leave.balance'].browse(leave_balance_active[0].get('id'))
                            if not emp.gender or emp.gender == company.gender:
                                assign = leave_balance.assigned + assigned
                                leave_balance.write({'assigned': assign,'limit_period': limit_period,'is_limit_period': is_limit_period})
                                leave_balance_id = leave_balance
                        self.env.cr.execute(
                            """SELECT employee_id FROM hr_leave_count where employee_id = %d and holiday_status_id 
                                = %d and hr_years = %d and active = 'true'""" % (
                                employee, emp.id, self.hr_years_id.name))
                        hr_leave_count = self.env.cr.fetchall()
                        if not hr_leave_count and assigned > 0:
                            if not emp.gender or emp.gender == company.gender:
                                self.env['hr.leave.count'].create({
                                    'employee_id': company.id,
                                    'holiday_status_id': emp.id,
                                    'count': assigned,
                                    'start_date': valid_start_date,
                                    'expired_date': valid_to_date,
                                    'hr_years': self.hr_years_id.name,
                                    'leave_balance_id': leave_balance_id.id,
                                    'description': 'Allocation',
                                })
                        elif hr_leave_count and emp.repeated_allocation == True:
                            if not emp.gender or emp.gender == company.gender:
                                self.env['hr.leave.count'].create({
                                    'employee_id': company.id,
                                    'holiday_status_id': emp.id,
                                    'count': assigned,
                                    'start_date': valid_start_date,
                                    'expired_date': valid_to_date,
                                    'hr_years': self.hr_years_id.name,
                                    'leave_balance_id': leave_balance_id.id,
                                    'description': 'Allocation',
                                })
                    elif emp.leave_method == 'anniversary':
                        start_date = company.date_of_joining
                        var = int(self.hr_years_id.name) - 1
                        # to_date = date(var, 12, 31)
                        to_date = date.today()
                        diff = rd.relativedelta(to_date, start_date)
                        months = diff.months + (12 * diff.years) + 1
                        valid_month = int(start_date.strftime("%m"))
                        valid_date = int(start_date.strftime("%d"))
                        valid_start_date = date(self.hr_years_id.name, valid_month, valid_date)
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
                        employee = company.id
                        self.env.cr.execute(
                            """SELECT id, employee_id FROM hr_leave_balance where employee_id = %d and holiday_status_id 
                            = %d and hr_years = %d and active = 'true' ORDER BY id DESC LIMIT 1""" % (
                                employee, emp.id, self.hr_years_id.name))
                        leave_balance_active = self.env.cr.dictfetchall()
                        if emp.carry_forward in ['remaining_amount','specific_days']:
                            is_limit_period = emp.is_limit_period
                            limit_period = emp.limit_period
                        else:
                            is_limit_period = False
                            limit_period = int(0)
                        if not leave_balance_active and assigned_anniversary > 0:
                            if not emp.gender or emp.gender == company.gender:
                                leave_balance_id = self.env['hr.leave.balance'].create({
                                                        'employee_id': company.id,
                                                        'holiday_status_id': emp.id,
                                                        'leave_entitlement': emp.leave_entitlement,
                                                        'assigned': assigned_anniversary,
                                                        'hr_years': self.hr_years_id.name,
                                                        'current_period': self.hr_years_id.name,
                                                        'leave_generate_id': self.id,
                                                        'start_date': valid_start_date,
                                                        'is_limit_period': is_limit_period,
                                                        'limit_period': limit_period,
                                                        'hr_years_id': self.hr_years_id.id,
                                                    })
                        elif leave_balance_active and emp.repeated_allocation == True:
                            leave_balance = self.env['hr.leave.balance'].browse(leave_balance_active[0].get('id'))
                            if not emp.gender or emp.gender == company.gender:
                                assign = leave_balance.assigned + assigned_anniversary
                                leave_balance.write({'assigned': assign,'limit_period': limit_period,'is_limit_period': is_limit_period})
                                leave_balance_id = leave_balance
                        self.env.cr.execute(
                            """SELECT employee_id FROM hr_leave_count where employee_id = %d and holiday_status_id 
                            = %d and hr_years = %d and active = 'true'""" % (
                                employee, emp.id, self.hr_years_id.name))
                        hr_leave_count = self.env.cr.fetchall()
                        if not hr_leave_count and assigned_anniversary > 0:
                            if not emp.gender or emp.gender == company.gender:
                                self.env['hr.leave.count'].create({
                                    'employee_id': company.id,
                                    'holiday_status_id': emp.id,
                                    'count': assigned_anniversary,
                                    'hr_years': self.hr_years_id.name,
                                    'start_date': valid_start_date,
                                    'expired_date': valid_to_date,
                                    'leave_balance_id': leave_balance_id.id,
                                    'description': 'Allocation',
                                })
                        elif hr_leave_count and emp.repeated_allocation == True:
                            if not emp.gender or emp.gender == company.gender:
                                self.env['hr.leave.count'].create({
                                    'employee_id': company.id,
                                    'holiday_status_id': emp.id,
                                    'count': assigned_anniversary,
                                    'hr_years': self.hr_years_id.name,
                                    'start_date': valid_start_date,
                                    'expired_date': valid_to_date,
                                    'leave_balance_id': leave_balance_id.id,
                                    'description': 'Allocation',
                                })
                    elif emp.leave_method == 'monthly':
                        if emp.monthly_start_valid_based_on == 'years_of_service':
                            yos_leave_type = company.date_of_joining + relativedelta(
                                years=emp.year_method_monthly,months=emp.month_method_monthly, days=emp.day_method_monthly)
                            yos_employee = company.date_of_joining + relativedelta(
                                years=company.years_of_service,months=company.months, days=company.days)
                            if yos_employee < yos_leave_type:
                                start_yos = yos_leave_type
                            else:
                                start_yos = company.date_of_joining
                        else:
                            start_yos = company.date_of_joining
                        start_date = company.date_of_joining
                        current_year = self.hr_years_id.name
                        current_day = date.today()
                        valid_month = int(start_date.strftime("%m"))
                        valid_date = int(start_date.strftime("%d"))
                        valid_start_date = date(self.hr_years_id.name, valid_month, valid_date)
                        employee = company.id
                        valid_monthly_start_date = valid_start_date + relativedelta(months=1)
                        monthly_assigned = 0
                        while valid_monthly_start_date < current_day:
                            if monthly_assigned < emp.maximum_leave:
                                monthly_assigned += emp.leave_entitlement
                            valid_monthly_start_date += relativedelta(months=1)
                        self.env.cr.execute(
                            """SELECT id, employee_id FROM hr_leave_balance where employee_id = %d and holiday_status_id 
                            = %d and hr_years_monthly = %d and active = 'true' ORDER BY id DESC LIMIT 1""" % (
                                employee, emp.id, current_year))
                        leave_balance_active = self.env.cr.dictfetchall()
                        if emp.carry_forward in ['remaining_amount','specific_days']:
                            is_limit_period = emp.is_limit_period
                            limit_period = emp.limit_period
                        else:
                            is_limit_period = False
                            limit_period = int(0)
                        if not leave_balance_active and monthly_assigned > 0:
                            if not emp.gender or emp.gender == company.gender:
                                if valid_start_date < start_yos:
                                    valid_start_date = start_yos
                                else:
                                    valid_start_date = valid_start_date
                                leave_balance_id = self.env['hr.leave.balance'].create({
                                                        'employee_id': company.id,
                                                        'holiday_status_id': emp.id,
                                                        'leave_entitlement': emp.leave_entitlement,
                                                        'assigned': monthly_assigned,
                                                        'hr_years_monthly': self.hr_years_id.name,
                                                        'hr_years': self.hr_years_id.name,
                                                        'current_period': self.hr_years_id.name,
                                                        'leave_generate_id': self.id,
                                                        'start_date': valid_start_date,
                                                        'is_limit_period': is_limit_period,
                                                        'limit_period': limit_period,
                                                        'hr_years_id': self.hr_years_id.id,
                                                    })
                        elif leave_balance_active and emp.repeated_allocation == True:
                            leave_balance = self.env['hr.leave.balance'].browse(leave_balance_active[0].get('id'))
                            if not emp.gender or emp.gender == company.gender:
                                assign = leave_balance.assigned + emp.leave_entitlement
                                leave_balance.write({'assigned': assign,'limit_period': limit_period,'is_limit_period': is_limit_period})
                                leave_balance_id = leave_balance

                        start_list = []
                        to_count_date = 0
                        if emp.maximum_leave and emp.leave_entitlement:
                            to_count_date = math.ceil(emp.maximum_leave / emp.leave_entitlement)
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
                        final_value = emp.leave_entitlement
                        for count_start_date in start_list:
                            if emp.valid_leave == 'one_year':
                                monthly_to_date = count_start_date[0] + relativedelta(years=1)
                                to_date = monthly_to_date - relativedelta(days=1)
                            elif emp.valid_leave == 'end_year':
                                to_date = date(current_year, 12, 31)
                            current_count_month = count_start_date[0].month
                            self.env.cr.execute(
                                """SELECT employee_id FROM hr_leave_count where employee_id = %d and holiday_status_id 
                                = %d and hr_months = %d and hr_years_monthly = %d and active = 'true'""" % (
                                    employee, emp.id, current_count_month, current_year))
                            hr_leave_count = self.env.cr.fetchall()
                            value += emp.leave_entitlement
                            if value > emp.maximum_leave:
                                last_before = value - emp.leave_entitlement
                                final_value = emp.maximum_leave - last_before
                            if not hr_leave_count:
                                if not emp.gender or emp.gender == company.gender:
                                    self.env['hr.leave.count'].create({
                                        'employee_id': company.id,
                                        'holiday_status_id': emp.id,
                                        'count': final_value,
                                        'hr_months': current_count_month,
                                        'hr_years_monthly': self.hr_years_id.name,
                                        'hr_years': self.hr_years_id.name,
                                        'start_date': count_start_date[1],
                                        'expired_date': to_date,
                                        'leave_balance_id': leave_balance_id.id,
                                        'description': 'Allocation',
                                    })
                            elif hr_leave_count and emp.repeated_allocation == True:
                                if not emp.gender or emp.gender == company.gender:
                                    self.env['hr.leave.count'].create({
                                        'employee_id': company.id,
                                        'holiday_status_id': emp.id,
                                        'count': final_value,
                                        'hr_months': current_count_month,
                                        'hr_years_monthly': self.hr_years_id.name,
                                        'hr_years': self.hr_years_id.name,
                                        'start_date': count_start_date[1],
                                        'expired_date': to_date,
                                        'leave_balance_id': leave_balance_id.id,
                                        'description': 'Allocation',
                                    })
                    elif emp.leave_method == 'none':
                        contract = company.contract_id
                        start_date = contract.date_start
                        valid_month = int(start_date.strftime("%m"))
                        valid_date = int(start_date.strftime("%d"))
                        if int(self.hr_years_id.name) > start_date.year:
                            valid_start_date = date(self.hr_years_id.name, 1, 1)
                        else:
                            valid_start_date = date(self.hr_years_id.name, valid_month, valid_date)
                        if emp.allocation_valid_until == 'end_of_year':
                            valid_to_date = date(self.hr_years_id.name, 12, 31)
                        elif emp.allocation_valid_until == 'spesific_days':
                            valid_specific_month = int(emp.allocation_months_expired)
                            valid_specific_date = int(emp.allocation_date_expired)
                            next_year = int(self.hr_years_id.name) + 1
                            valid_to_date = date(next_year, valid_specific_month, valid_specific_date)
                        elif emp.allocation_valid_until == 'number_of_days':
                            valid_to_date = valid_start_date + relativedelta(days=emp.expiry_days)
                        assigned_none = emp.leave_entitlement
                        employee = company.id
                        self.env.cr.execute(
                            """SELECT id, employee_id FROM hr_leave_balance where employee_id = %d and holiday_status_id 
                            = %d and hr_years = %d and active = 'true' ORDER BY id DESC LIMIT 1""" % (
                                employee, emp.id, self.hr_years_id.name))
                        leave_balance_active = self.env.cr.dictfetchall()
                        if emp.carry_forward in ['remaining_amount','specific_days']:
                            is_limit_period = emp.is_limit_period
                            limit_period = emp.limit_period
                        else:
                            is_limit_period = False
                            limit_period = int(0)
                        if not leave_balance_active:
                            if not emp.gender or emp.gender == company.gender:
                                leave_balance_id = self.env['hr.leave.balance'].create({
                                                        'employee_id': company.id,
                                                        'holiday_status_id': emp.id,
                                                        'leave_entitlement': emp.leave_entitlement,
                                                        'assigned': assigned_none,
                                                        'hr_years': self.hr_years_id.name,
                                                        'current_period': self.hr_years_id.name,
                                                        'leave_generate_id': self.id,
                                                        'start_date': valid_start_date,
                                                        'is_limit_period': is_limit_period,
                                                        'limit_period': limit_period,
                                                        'hr_years_id': self.hr_years_id.id,
                                                    })
                        elif leave_balance_active and emp.repeated_allocation == True:
                            leave_balance = self.env['hr.leave.balance'].browse(leave_balance_active[0].get('id'))
                            if not emp.gender or emp.gender == company.gender:
                                assign = leave_balance.assigned + assigned_none
                                leave_balance.write({'assigned': assign,'limit_period': limit_period,'is_limit_period': is_limit_period})
                                leave_balance_id = leave_balance
                        self.env.cr.execute(
                            """SELECT employee_id FROM hr_leave_count where employee_id = %d and holiday_status_id 
                            = %d and hr_years = %d and active = 'true'""" % (
                                employee, emp.id, self.hr_years_id.name))
                        hr_leave_count = self.env.cr.fetchall()
                        if not hr_leave_count:
                            if not emp.gender or emp.gender == company.gender:
                                self.env['hr.leave.count'].create({
                                    'employee_id': company.id,
                                    'holiday_status_id': emp.id,
                                    'count': assigned_none,
                                    'hr_years': self.hr_years_id.name,
                                    'start_date': valid_start_date,
                                    'expired_date': valid_to_date,
                                    'leave_balance_id': leave_balance_id.id,
                                    'description': 'Allocation',
                                })
                        elif hr_leave_count and emp.repeated_allocation == True:
                            if not emp.gender or emp.gender == company.gender:
                                self.env['hr.leave.count'].create({
                                    'employee_id': company.id,
                                    'holiday_status_id': emp.id,
                                    'count': assigned_none,
                                    'hr_years': self.hr_years_id.name,
                                    'start_date': valid_start_date,
                                    'expired_date': valid_to_date,
                                    'leave_balance_id': leave_balance_id.id,
                                    'description': 'Allocation',
                                })
        elif self.allocation_type == 'employee':
            for line in self.employee_ids:
                for leave in line.leave_struct_id.leaves_ids:
                    assigned = 0
                    carry_forward = False
                    if leave.leave_method == 'annually':
                        start_date = line.date_of_joining
                        var = int(self.hr_years_id.name) - 1
                        to_date = date(var, 12, 31)
                        diff = rd.relativedelta(to_date, start_date)
                        if start_date.year >= int(self.hr_years_id.name):
                            months = 0
                        else:
                            months = diff.months + (12 * diff.years) + 1
                        valid_month = int(leave.leave_months_appear)
                        valid_date = int(leave.leave_date_appear)
                        if int(self.hr_years_id.name) > start_date.year:
                            valid_start_date = date(self.hr_years_id.name, 1, 1)
                        else:
                            valid_start_date = date(self.hr_years_id.name, valid_month, valid_date)
                        valid_to_date = date(self.hr_years_id.name, 12, 31)
                        if months >= 12:
                            assigned = assigned + leave.leave_entitlement
                        else:
                            assigned = assigned + (leave.leave_entitlement / 12) * months
                        employee = line.id
                        self.env.cr.execute(
                            """SELECT id, employee_id FROM hr_leave_balance where employee_id = %d and holiday_status_id 
                            = %d and hr_years = %d and active = 'true' ORDER BY id DESC LIMIT 1""" % (
                                employee, leave.id, self.hr_years_id.name))
                        leave_balance_active = self.env.cr.dictfetchall()
                        if leave.carry_forward in ['remaining_amount','specific_days']:
                            is_limit_period = leave.is_limit_period
                            limit_period = leave.limit_period
                            carry_forward = leave.carry_forward
                        else:
                            is_limit_period = False
                            limit_period = int(0)
                        if not leave_balance_active and assigned > 0:
                            if not leave.gender or leave.gender == line.gender:
                                leave_balance_id = self.env['hr.leave.balance'].create({
                                                        'employee_id': line.id,
                                                        'holiday_status_id': leave.id,
                                                        'leave_entitlement': leave.leave_entitlement,
                                                        'assigned': assigned,
                                                        'current_period': self.hr_years_id.name,
                                                        'leave_generate_id': self.id,
                                                        'hr_years': self.hr_years_id.name,
                                                        'start_date': valid_start_date,
                                                        'is_limit_period': is_limit_period,
                                                        'limit_period': limit_period,
                                                        'hr_years_id': self.hr_years_id.id,
                                                        'carry_forward': carry_forward,
                                                    })
                        elif leave_balance_active and leave.repeated_allocation == True:
                            leave_balance = self.env['hr.leave.balance'].browse(leave_balance_active[0].get('id'))
                            if not leave.gender or leave.gender == line.gender:
                                assign = leave_balance.assigned + assigned
                                leave_balance.write({'assigned': assign,'limit_period': limit_period,'is_limit_period': is_limit_period})
                                leave_balance_id = leave_balance
                        self.env.cr.execute(
                            """SELECT employee_id FROM hr_leave_count where employee_id = %d and holiday_status_id 
                            = %d and hr_years = %d and active = 'true'""" % (
                                employee, leave.id, self.hr_years_id.name))
                        hr_leave_count = self.env.cr.fetchall()
                        if not hr_leave_count and assigned > 0:
                            if not leave.gender or leave.gender == line.gender:
                                self.env['hr.leave.count'].create({
                                    'employee_id': line.id,
                                    'holiday_status_id': leave.id,
                                    'count': assigned,
                                    'start_date': valid_start_date,
                                    'expired_date': valid_to_date,
                                    'hr_years': self.hr_years_id.name,
                                    'leave_balance_id': leave_balance_id.id,
                                    'description': 'Allocation',
                                })
                        elif hr_leave_count and leave.repeated_allocation == True:
                            if not leave.gender or leave.gender == line.gender:
                                self.env['hr.leave.count'].create({
                                    'employee_id': line.id,
                                    'holiday_status_id': leave.id,
                                    'count': assigned,
                                    'start_date': valid_start_date,
                                    'expired_date': valid_to_date,
                                    'hr_years': self.hr_years_id.name,
                                    'leave_balance_id': leave_balance_id.id,
                                    'description': 'Allocation',
                                })
                    elif leave.leave_method == 'anniversary':
                        start_date = line.date_of_joining
                        var = int(self.hr_years_id.name) - 1
                        # to_date = date(var, 12, 31)
                        to_date = date.today()
                        diff = rd.relativedelta(to_date, start_date)
                        months = diff.months + (12 * diff.years) + 1
                        valid_month = int(start_date.strftime("%m"))
                        valid_date = int(start_date.strftime("%d"))
                        valid_start_date = date(self.hr_years_id.name, valid_month, valid_date)
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
                        employee = line.id
                        self.env.cr.execute(
                            """SELECT id, employee_id FROM hr_leave_balance where employee_id = %d and holiday_status_id 
                            = %d and hr_years = %d and active = 'true' ORDER BY id DESC LIMIT 1""" % (
                                employee, leave.id, self.hr_years_id.name))
                        leave_balance_active = self.env.cr.dictfetchall()
                        if leave.carry_forward in ['remaining_amount','specific_days']:
                            is_limit_period = leave.is_limit_period
                            limit_period = leave.limit_period
                            carry_forward = leave.carry_forward
                        else:
                            is_limit_period = False
                            limit_period = int(0)
                        if not leave_balance_active and assigned_anniversary > 0:
                            if not leave.gender or leave.gender == line.gender:
                                leave_balance_id = self.env['hr.leave.balance'].create({
                                                        'employee_id': line.id,
                                                        'holiday_status_id': leave.id,
                                                        'leave_entitlement': leave.leave_entitlement,
                                                        'assigned': assigned_anniversary,
                                                        'hr_years': self.hr_years_id.name,
                                                        'current_period': self.hr_years_id.name,
                                                        'leave_generate_id': self.id,
                                                        'start_date': valid_start_date,
                                                        'is_limit_period': is_limit_period,
                                                        'limit_period': limit_period,
                                                        'hr_years_id': self.hr_years_id.id,
                                                        'carry_forward': carry_forward
                                                    })
                        elif leave_balance_active and leave.repeated_allocation == True:
                            leave_balance = self.env['hr.leave.balance'].browse(leave_balance_active[0].get('id'))
                            if not leave.gender or leave.gender == line.gender:
                                assign = leave_balance.assigned + assigned_anniversary
                                leave_balance.write({'assigned': assign,'limit_period': limit_period,'is_limit_period': is_limit_period})
                                leave_balance_id = leave_balance
                        self.env.cr.execute(
                            """SELECT employee_id FROM hr_leave_count where employee_id = %d and holiday_status_id 
                            = %d and hr_years = %d and active = 'true'""" % (
                                employee, leave.id, self.hr_years_id.name))
                        hr_leave_count = self.env.cr.fetchall()
                        if not hr_leave_count and assigned_anniversary > 0:
                            if not leave.gender or leave.gender == line.gender:
                                self.env['hr.leave.count'].create({
                                    'employee_id': line.id,
                                    'holiday_status_id': leave.id,
                                    'count': assigned_anniversary,
                                    'hr_years': self.hr_years_id.name,
                                    'start_date': valid_start_date,
                                    'expired_date': valid_to_date,
                                    'leave_balance_id': leave_balance_id.id,
                                    'description': 'Allocation',
                                })
                        elif hr_leave_count and leave.repeated_allocation == True:
                            if not leave.gender or leave.gender == line.gender:
                                self.env['hr.leave.count'].create({
                                    'employee_id': line.id,
                                    'holiday_status_id': leave.id,
                                    'count': assigned_anniversary,
                                    'hr_years': self.hr_years_id.name,
                                    'start_date': valid_start_date,
                                    'expired_date': valid_to_date,
                                    'leave_balance_id': leave_balance_id.id,
                                    'description': 'Allocation',
                                })
                    elif leave.leave_method == 'monthly':
                        if leave.monthly_start_valid_based_on == 'years_of_service':
                            yos_leave_type = line.date_of_joining + relativedelta(
                                years=leave.year_method_monthly,months=leave.month_method_monthly, days=leave.day_method_monthly)
                            yos_employee = line.date_of_joining + relativedelta(
                                years=line.years_of_service,months=line.months, days=line.days)
                            if yos_employee < yos_leave_type:
                                start_yos = yos_leave_type
                            else:
                                start_yos = line.date_of_joining
                        else:
                            start_yos = line.date_of_joining
                        start_date = line.date_of_joining
                        current_year = self.hr_years_id.name
                        current_day = date.today()
                        valid_month = int(start_date.strftime("%m"))
                        valid_date = int(start_date.strftime("%d"))
                        valid_start_date = date(self.hr_years_id.name, valid_month, valid_date)
                        valid_monthly_start_date = valid_start_date + relativedelta(months=1)
                        employee = line.id
                        monthly_assigned = 0
                        while valid_monthly_start_date < current_day:
                            if monthly_assigned < leave.maximum_leave:
                                monthly_assigned += leave.leave_entitlement
                            valid_monthly_start_date += relativedelta(months=1)
                        self.env.cr.execute(
                            """SELECT id, employee_id FROM hr_leave_balance where employee_id = %d and holiday_status_id 
                            = %d and hr_years_monthly = %d and active = 'true' ORDER BY id DESC LIMIT 1""" % (
                                employee, leave.id, current_year))
                        leave_balance_active = self.env.cr.dictfetchall()
                        if leave.carry_forward in ['remaining_amount','specific_days']:
                            is_limit_period = leave.is_limit_period
                            limit_period = leave.limit_period
                        else:
                            is_limit_period = False
                            limit_period = int(0)
                        if not leave_balance_active and monthly_assigned > 0:
                            if not leave.gender or leave.gender == line.gender:
                                if valid_start_date < start_yos:
                                    valid_start_date = start_yos
                                else:
                                    valid_start_date = valid_start_date
                                leave_balance_id = self.env['hr.leave.balance'].create({
                                                        'employee_id': line.id,
                                                        'holiday_status_id': leave.id,
                                                        'leave_entitlement': leave.leave_entitlement,
                                                        'assigned': monthly_assigned,
                                                        'hr_years': self.hr_years_id.name,
                                                        'hr_years_monthly': self.hr_years_id.name,
                                                        'current_period': self.hr_years_id.name,
                                                        'leave_generate_id': self.id,
                                                        'start_date': valid_start_date,
                                                        'is_limit_period': is_limit_period,
                                                        'limit_period': limit_period,
                                                        'hr_years_id': self.hr_years_id.id,
                                                    })
                        elif leave_balance_active and leave.repeated_allocation == True:
                            leave_balance = self.env['hr.leave.balance'].browse(leave_balance_active[0].get('id'))
                            if not leave.gender or leave.gender == line.gender:
                                assign = leave_balance.assigned + leave.maximum_leave
                                leave_balance.write({'assigned': assign,'limit_period': limit_period,'is_limit_period': is_limit_period})
                                leave_balance_id = leave_balance

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
                                    employee, leave.id, current_count_month, current_year))
                            hr_leave_count = self.env.cr.fetchall()
                            value += leave.leave_entitlement
                            if value > leave.maximum_leave:
                                last_before = value - leave.leave_entitlement
                                final_value = leave.maximum_leave - last_before
                            if not hr_leave_count:
                                if not leave.gender or leave.gender == line.gender:
                                    self.env['hr.leave.count'].create({
                                        'employee_id': line.id,
                                        'holiday_status_id': leave.id,
                                        'count': final_value,
                                        'hr_years': self.hr_years_id.name,
                                        'hr_months': current_count_month,
                                        'hr_years_monthly': self.hr_years_id.name,
                                        'start_date': count_start_date[1],
                                        'expired_date': to_date,
                                        'leave_balance_id': leave_balance_id.id,
                                        'description': 'Allocation',
                                    })
                            elif hr_leave_count and leave.repeated_allocation == True:
                                if not leave.gender or leave.gender == line.gender:
                                    self.env['hr.leave.count'].create({
                                        'employee_id': line.id,
                                        'holiday_status_id': leave.id,
                                        'count': final_value,
                                        'hr_years': self.hr_years_id.name,
                                        'hr_months': current_count_month,
                                        'hr_years_monthly': self.hr_years_id.name,
                                        'start_date': count_start_date[1],
                                        'expired_date': to_date,
                                        'leave_balance_id': leave_balance_id.id,
                                        'description': 'Allocation',
                                    })
                    elif leave.leave_method == 'none':
                        contract = line.contract_id
                        start_date = contract.date_start
                        valid_month = int(start_date.strftime("%m"))
                        valid_date = int(start_date.strftime("%d"))
                        if int(self.hr_years_id.name) > start_date.year:
                            valid_start_date = date(self.hr_years_id.name, 1, 1)
                        else:
                            valid_start_date = date(self.hr_years_id.name, valid_month, valid_date)
                        if leave.allocation_valid_until == 'end_of_year':
                            valid_to_date = date(self.hr_years_id.name, 12, 31)
                        elif leave.allocation_valid_until == 'spesific_days':
                            valid_specific_month = int(leave.allocation_months_expired)
                            valid_specific_date = int(leave.allocation_date_expired)
                            next_year = int(self.hr_years_id.name) + 1
                            valid_to_date = date(next_year, valid_specific_month, valid_specific_date)
                        elif leave.allocation_valid_until == 'number_of_days':
                            valid_to_date = valid_start_date + relativedelta(days=leave.expiry_days)
                        assigned_none = leave.leave_entitlement
                        employee = line.id
                        self.env.cr.execute(
                            """SELECT id, employee_id FROM hr_leave_balance where employee_id = %d and holiday_status_id 
                            = %d and hr_years = %d and active = 'true' ORDER BY id DESC LIMIT 1""" % (
                                employee, leave.id, self.hr_years_id.name))
                        leave_balance_active = self.env.cr.dictfetchall()
                        if leave.carry_forward in ['remaining_amount','specific_days']:
                            is_limit_period = leave.is_limit_period
                            limit_period = leave.limit_period
                            carry_forward = leave.carry_forward
                        else:
                            is_limit_period = False
                            limit_period = int(0)
                        if not leave_balance_active:
                            if not leave.gender or leave.gender == line.gender:
                                leave_balance_id = self.env['hr.leave.balance'].create({
                                                    'employee_id': line.id,
                                                    'holiday_status_id': leave.id,
                                                    'leave_entitlement': leave.leave_entitlement,
                                                    'assigned': assigned_none,
                                                    'hr_years': self.hr_years_id.name,
                                                    'current_period': self.hr_years_id.name,
                                                    'leave_generate_id': self.id,
                                                    'start_date': valid_start_date,
                                                    'is_limit_period': is_limit_period,
                                                    'limit_period': limit_period,
                                                    'hr_years_id': self.hr_years_id.id,
                                                    'carry_forward': carry_forward
                                                })
                        elif leave_balance_active and leave.repeated_allocation == True:
                            leave_balance = self.env['hr.leave.balance'].browse(leave_balance_active[0].get('id'))
                            if not leave.gender or leave.gender == line.gender:
                                assign = leave_balance.assigned + assigned_none
                                leave_balance.write({'assigned': assign,'limit_period': limit_period,'is_limit_period': is_limit_period})
                                leave_balance_id = leave_balance
                        self.env.cr.execute(
                            """SELECT employee_id FROM hr_leave_count where employee_id = %d and holiday_status_id 
                            = %d and hr_years = %d and active = 'true'""" % (
                                employee, leave.id, self.hr_years_id.name))
                        hr_leave_count = self.env.cr.fetchall()
                        if not hr_leave_count:
                            if not leave.gender or leave.gender == line.gender:
                                self.env['hr.leave.count'].create({
                                    'employee_id': line.id,
                                    'holiday_status_id': leave.id,
                                    'count': assigned_none,
                                    'hr_years': self.hr_years_id.name,
                                    'start_date': valid_start_date,
                                    'expired_date': valid_to_date,
                                    'leave_balance_id': leave_balance_id.id,
                                    'description': 'Allocation',
                                })
                        elif hr_leave_count and leave.repeated_allocation == True:
                            if not leave.gender or leave.gender == line.gender:
                                self.env['hr.leave.count'].create({
                                    'employee_id': line.id,
                                    'holiday_status_id': leave.id,
                                    'count': assigned_none,
                                    'hr_years': self.hr_years_id.name,
                                    'start_date': valid_start_date,
                                    'expired_date': valid_to_date,
                                    'leave_balance_id': leave_balance_id.id,
                                    'description': 'Allocation',
                                })
        self.write({'state': 'generated'})
