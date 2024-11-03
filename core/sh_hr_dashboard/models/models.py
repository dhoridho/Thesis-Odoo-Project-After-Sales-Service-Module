# Part of Softhealer Technologies.
from datetime import datetime

from pytz import timezone
import pytz
from odoo import models, fields


class HR(models.Model):
    _inherit = 'hr.employee'

    date_of_joining = fields.Date("Date of Joining")


class HRPublic(models.Model):
    _inherit = 'hr.employee.public'

    date_of_joining = fields.Date("Date of Joining")


class HRDashboard(models.Model):
    _name = 'sh.hr.dashboard'
    _description = 'HR Dashboard'
    

    def create_expense(self):
        employee = self.env['hr.employee'].sudo().search(
            [('user_id', '=', self.env.user.id)], limit=1)
        if employee:

            return {
                'name': "Expense",
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'hr.expense',
                'target': 'current',
                'context': {'default_employee_id': employee.id}
            }

    def create_attendance(self):
        employee = self.env['hr.employee'].sudo().search(
            [('user_id', '=', self.env.user.id)], limit=1)
        if employee:
            attendance = self.env['hr.attendance'].sudo().search(
                [('check_out', '=', False), ('employee_id', '=', employee.id)], order='id desc', limit=1)
            if attendance:
                return {
                    'name': "Attendance",
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'hr.attendance',
                    'target': 'current',
                    'res_id': attendance.id
                }
            else:
                return {
                    'name': "Attendance",
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'hr.attendance',
                    'target': 'current',
                    'context': {'default_employee_id': employee.id}
                }

    def create_leave(self):
        employee = self.env['hr.employee'].sudo().search(
            [('user_id', '=', self.env.user.id)], limit=1)
        if employee:

            return {
                'name': "Leave Request",
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'hr.leave',
                'target': 'current',
                'context': {'default_employee_id': employee.id}
            }

    def get_department_leader(self):
        for record in self:
            record.is_department_leader = False
            if  self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_departmen_leader') and not self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_officer'):
                record.is_department_leader = True
                
    def get_child_employee(self):
        now = datetime.now(timezone(self.env.user.tz))
        local_tzinfo = pytz.timezone(self.env.user.tz)

        for record in self:
            employee_ids = []
            attendance_ids = []
            my_employee = self.env['hr.employee'].sudo().search([('user_id','=',self.env.user.id)])
            if my_employee:
                for child_record in my_employee.child_ids:
                    employee_ids.append(child_record.id)
                    child_record._get_amployee_hierarchy(employee_ids,child_record.child_ids,my_employee.id)
            record.child_count = len(employee_ids)
            child_attendance = self.env['hr.attendance'].sudo().search([('employee_id','in',employee_ids)],limit=200)
            if child_attendance:
                for data_attendance in child_attendance:
                    if data_attendance.check_in:
                        check_in = datetime.strptime(str(data_attendance.check_in), '%Y-%m-%d %H:%M:%S')
                        localtime = check_in.astimezone(local_tzinfo)
                        if localtime.date() == now.date():
                            attendance_ids.append(data_attendance.id)
         
            record.attendance_child_count = len(attendance_ids)

        
        
    def open_employee_leave(self):

        return {
            'name': "Leaves",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form,activity',
            'res_model': 'hr.leave',
            'domain': [('employee_id.user_id', '=', self.env.user.id)],
            'target': 'current',
        }

    def get_leave_count(self):
        for rec in self:
            rec.leave_count = 0
            rec.allocated_leave_count = 0
            allocated_leaves = self.env['hr.leave.allocation'].sudo().search(
                [('employee_id.user_id', '=', self.env.user.id), ('state', '=', 'validate')])
            for allocated_leave in allocated_leaves:
                rec.allocated_leave_count += allocated_leave.number_of_days

            requested_leaves = self.env['hr.leave'].sudo().search(
                [('employee_id.user_id', '=', self.env.user.id), ('state', '=', 'validate')])
            for requested_leave in requested_leaves:
                rec.leave_count += requested_leave.number_of_days

    def get_leave_balance(self):
        now = datetime.now()
        for rec in self:
            rec.leave_balance = 0
            rec.leave_assigned = 0
            if  self.env.user.has_group('hr.group_hr_user') and not self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_departmen_leader'):
                leave_balances = self.env['hr.leave.balance'].sudo().search(
                    [('employee_id.user_id', '=', self.env.user.id)])
                for leave_balance in leave_balances:
                    if leave_balance.holiday_status_id.is_dashboard:
                        rec.leave_balance += leave_balance.remaining
                leave_assigneds = self.env['hr.leave.balance'].sudo().search(
                    [('employee_id.user_id', '=', self.env.user.id)])
                for leave_assigned in leave_assigneds:
                    if leave_assigned.holiday_status_id.is_dashboard:
                        rec.leave_assigned += (leave_assigned.assigned + leave_assigned.bring_forward + leave_assigned.extra_leave)
            
            if  self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_departmen_leader') and not self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_officer'):
                employee_ids = []
                employee_leave_ids = []
                my_employee = self.env['hr.employee'].sudo().search([('user_id','=',self.env.user.id)])
                if my_employee:
                    for child_record in my_employee.child_ids:
                        employee_ids.append(child_record.id)
                        child_record._get_amployee_hierarchy(employee_ids,child_record.child_ids,my_employee.id)
                    leave_employees = self.env['hr.leave'].search([('employee_id','in',employee_ids)])
                    if leave_employees:
                        for employee_leaves  in leave_employees.filtered(lambda line:line.request_date_from <= now.date() and line.request_date_to >= now.date() and line.state == 'validate'):
                            employee_leave_ids.append(employee_leaves)
                        
                rec.leave_assigned = len(set(employee_ids))
                rec.leave_balance = len(set(employee_leave_ids))

    def open_employee_attendnace(self):

        return {
            'name': "Attendance",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,kanban,form',
            'res_model': 'hr.attendance',
            'domain': [('employee_id.user_id', '=', self.env.user.id)],
            'target': 'current',
        }

    def get_attendance_count(self):
        for rec in self:
            rec.attendance_count = self.env['hr.attendance'].sudo().search_count(
                [('employee_id.user_id', '=', self.env.user.id)])

    def open_employee_expense(self):

        return {
            'name': "Expense",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,kanban,form,graph,pivot,activity',
            'res_model': 'hr.expense',
            'domain': [('employee_id.user_id', '=', self.env.user.id)],
            'target': 'current',
        }

    def get_expense_count(self):
        for rec in self:
            rec.expense_count = 0
            expenses = self.env['hr.expense'].sudo().search(
                [('employee_id.user_id', '=', self.env.user.id)])
            if expenses:
                for expense in expenses:
                    rec.expense_count += expense.total_amount

    def open_employee_contract(self):

        return {
            'name': "Contract",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form,activity',
            'res_model': 'hr.contract',
            'domain': [('employee_id.user_id', '=', self.env.user.id)],
            'target': 'current',
        }

    def get_contract_count(self):
        for rec in self:
            rec.contract_count = self.env['hr.contract'].sudo().search_count(
                [('employee_id.user_id', '=', self.env.user.id)])

    def get_login_user(self):
        for rec in self:
            rec.user_id = self.env.uid

    name = fields.Char("Name")
    user_id = fields.Many2one(
        'res.users', string="User", compute='get_login_user')
    leave_count = fields.Integer("Leave Count", compute='get_leave_count')
    allocated_leave_count = fields.Integer(
        "Allocated Leave Count", compute='get_leave_count')
    attendance_count = fields.Integer(
        "Attendance Count", compute='get_attendance_count')
    expense_count = fields.Integer(
        "Expense Count", compute='get_expense_count')
    contract_count = fields.Integer(
        "Contract Count", compute='get_contract_count')
    leave_balance = fields.Integer("Leave Balance", compute='get_leave_balance')
    leave_assigned = fields.Integer("Leave ASsigned", compute='get_leave_balance')
    is_department_leader = fields.Boolean(compute='get_department_leader')
    child_count = fields.Integer(compute='get_child_employee')
    attendance_child_count = fields.Integer(compute='get_child_employee')

    def custom_menu(self):
        res_id = self.env.ref("sh_hr_dashboard.sh_dahsboard_rec_1").id
        view_id = self.env.ref('sh_hr_dashboard.sh_hr_dashboard_kanban').id
        action = self.env.ref("sh_hr_dashboard.sh_hr_dashboard_act_window")
        result = action.read()[0]
        result.update({
            'res_id': res_id,
            'view_id': view_id,
            'target': 'current',
        })
        if self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_officer'):
            result['name'] = 'HR Dashboard'
        elif self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_manager'):
            result['name'] = 'HR Dashboard'
        elif self.env.user.has_group('hr.group_hr_manager'):
            result['name'] = 'HR Dashboard'
        elif self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_departmen_leader'):
            my_dept = self.env['hr.employee'].sudo().search([('user_id', '=', self.env.user.id)], limit=1)
            result['name'] = my_dept.department_id.name + ' ' + 'Dashboard' if my_dept.department_id else 'Dashboard'
        elif self.env.user.has_group('hr.group_hr_user'):
            result['name'] = 'HR Dashboard'
        return result