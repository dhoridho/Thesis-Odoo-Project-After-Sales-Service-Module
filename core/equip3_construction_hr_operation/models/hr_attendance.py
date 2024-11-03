from odoo import models, fields, api
from datetime import date, datetime, timedelta
from odoo.exceptions import UserError, ValidationError
import json
from dateutil.relativedelta import relativedelta
from odoo.tools.misc import split_every


class HRAttendance(models.Model):
    _inherit = 'hr.attendance'

    project_id = fields.Many2one('project.project', string='Project')
    project_task_id = fields.Many2one('project.task', string='Job Order')
    group_of_product_id = fields.Many2one('group.of.product', string='Group of Position')
    product_id = fields.Many2one('product.product', string='Position')
    uom_id = fields.Many2one('uom.uom', string='Periodic')
    rate = fields.Float(string='Rate')
    rate_amount = fields.Float(string='Amount Rate', compute='_compute_rate_amount')
    rate_periodic = fields.Selection([
        ('hourly', 'Hourly'),
        ('daily', 'Daily'),
        ('monthly', 'Monthly'),
    ], string='Periodic',)
    hourly_rate = fields.Float(string='Hourly Rate')
    late_deduction_amount = fields.Float(string='Late Deduction Amount', compute='_compute_late_deduction_amount')

    def _compute_late_deduction_amount(self):
        for rec in self:
            late_deduction_amount = 0
            late_deduction_rule = rec.working_schedule_id.late_dedution_rules_id

            if late_deduction_rule and rec.check_in_diff > 0:
                if late_deduction_rule.late_deduction_lines:
                    for line in late_deduction_rule.late_deduction_lines:
                        if not line.is_multiple:
                            if round(rec.check_in_diff, 2) >= round(line.time, 2):
                                late_deduction_amount = line.amount
                        else:
                            if round(rec.check_in_diff, 2) >= round(line.time, 2):
                                if round(rec.check_in_diff, 2) <= round(line.maximum_time, 2):
                                    diff = int(round(rec.check_in_diff / line.time, 2))
                                else:
                                    diff = line.maximum_time / line.time
                                late_deduction_amount = line.amount * diff
            rec.late_deduction_amount = late_deduction_amount

    def _compute_rate_amount(self):
        for rec in self:
            rec.rate_amount = (rec.hourly_rate * rec.worked_hours) - rec.late_deduction_amount

    @api.onchange('active_location_id')
    def onchange_active_location_construction(self):
        for rec in self:
            if rec.active_location_id:
                active_location_id = rec.active_location_id[0]
                # project_information = (self.env['construction.project.information']
                #                        .search([('active_location_id', '=', active_location_id.id),
                #                                 ('employee_id', '=', rec.employee_id.id)], limit=1))
                project_information = rec.employee_id.project_information_ids.filtered(
                    lambda x: x.active_location_id.active_location_id.id == active_location_id.id)
                if project_information:
                    rec.project_id = project_information[0].project_id
                    rec.project_task_id = project_information[0].project_task_id
                    rec.group_of_product_id = project_information[0].group_of_product_id
                    rec.product_id = project_information[0].product_id
                    # rec.uom_id = project_information[0].uom_id
                    rec.rate = project_information[0].rate_amount
                    rec.rate_amount = project_information[0].rate_amount
                    rec.rate_periodic = project_information[0].rate_periodic
                    rec.hourly_rate = project_information[0].labour_cost_rate_id.hourly_rate

    # Override to change attendance logic according to Construction's Labour Cost Rate needs
    @api.model
    def _cron_update_attendance_status(self):
        setting_update_attendance_status_limit = int(self.env['ir.config_parameter'].sudo().get_param(
            'equip3_hr_attendance_extend.update_attendance_status_limit'))
        limit_days = date.today() - relativedelta(days=setting_update_attendance_status_limit)
        employee_data = self.env['hr.employee'].search([('active', '=', True)])
        for emp in split_every(100, employee_data):
            for employee in emp:
                for employee_calendar in self.env['employee.working.schedule.calendar'].search(
                        [('employee_id', '=', employee.id), ('date_start', '>=', limit_days),
                         ('date_start', '<', date.today()), ('day_type', '!=', 'day_off')]):
                    if employee_calendar.checkout.date() < date.today():
                        attendance = self.env['hr.attendance'].search(
                            [('employee_id', '=', employee_calendar.employee_id.id),
                             ('start_working_date', '=', employee_calendar.date_start)])
                        for vals in attendance:
                            if vals.attendance_status != 'travel':
                                if not vals.check_in:
                                    vals.attendance_status = 'absent'
                                    vals.is_absent = True
                                if not vals.check_out:
                                    vals.attendance_status = 'absent'
                                    vals.is_absent = True
                        contract = self.env['hr.contract'].search(
                            [('employee_id', '=', employee_calendar.employee_id.id)], order='id desc', limit=1)
                        if not attendance and not contract.date_end:
                            self.env['hr.attendance'].create({
                                'employee_id': employee.id,
                                'check_in': False,
                                'check_out': False,
                                'start_working_times': employee_calendar.checkin,
                                'start_working_date': employee_calendar.date_start,
                                'calendar_id': employee_calendar.id,
                                'attendance_status': 'absent',
                                'is_absent': True,
                                'is_created': True
                            })
                        elif not attendance and contract.date_end and contract.date_end >= date.today():
                            self.env['hr.attendance'].create({
                                'employee_id': employee.id,
                                'check_in': False,
                                'check_out': False,
                                'start_working_times': employee_calendar.checkin,
                                'start_working_date': employee_calendar.date_start,
                                'calendar_id': employee_calendar.id,
                                'attendance_status': 'absent',
                                'is_absent': True,
                                'is_created': True
                            })
                # one_month = date.today() - relativedelta(months=1)
                for leave in self.env['hr.leave'].search(
                        [('employee_id', '=', employee.id), ('request_date_from', '>=', limit_days),
                         ('request_date_from', '<=', date.today()), ('state', '=', 'validate')]):
                    start_leave = leave.request_date_from
                    while start_leave <= leave.request_date_to:
                        if start_leave <= date.today():
                            attendance_leave = self.env['hr.attendance'].search(
                                [('employee_id', '=', leave.employee_id.id),
                                 ('start_working_date', '=', start_leave)])
                            attendance_leave.leave_type = leave.holiday_status_id.id
                            attendance_leave.attendance_status = leave.holiday_status_id.attendance_status
                            if not attendance_leave:
                                self.env['hr.attendance'].create({
                                    'employee_id': employee.id,
                                    'check_in': False,
                                    'check_out': False,
                                    'start_working_date': start_leave,
                                    'leave_id': leave.id,
                                    'leave_type': leave.holiday_status_id.id,
                                    'attendance_status': leave.holiday_status_id.attendance_status,
                                    'is_created': True
                                })
                        start_leave += relativedelta(days=1)
                for attendance in self.env['hr.attendance'].search(
                        [('employee_id', '=', employee.id), ('is_created', '!=', True), ('active', '=', True)]):
                    if attendance.check_in_diff <= 0 and attendance.worked_hours >= attendance.minimum_hours:
                        if attendance.check_out and attendance.check_out_diff <= 0:
                            attendance.attendance_status = 'present'
                            attendance.is_created = True
                        else:
                            attendance.attendance_status = 'absent'
                            attendance.is_created = True
                    else:
                        attendance.attendance_status = 'absent'
                        attendance.is_created = True

            self._cr.commit()
        self.sub_cron_attendance_absent()
        self.sub_cron_delete_archived_attendance()



