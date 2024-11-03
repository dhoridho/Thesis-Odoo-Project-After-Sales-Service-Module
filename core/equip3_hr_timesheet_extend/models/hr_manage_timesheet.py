# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import datetime, timedelta, time
from odoo.exceptions import UserError, ValidationError
import pytz
from odoo.osv import expression
from lxml import etree
import copy

class HrManageTimesheet(models.Model):
    _inherit = 'hr.timesheet'

    @api.returns('self')
    def _get_creator(self):
        return self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1) or False

    employees_ids = fields.Many2many('hr.employee','employees', domain=[('user_id','!=',False)])
    created_by = fields.Many2one('hr.employee', default=_get_creator)
    user_ids = fields.Many2many('res.users', 'tmp_user_emp_rel', string='Users')
    is_manage_timesheet = fields.Boolean('Is Manage Timesheet', default=False)

    @api.model
    def create(self, vals):
        record = super(HrManageTimesheet, self).create(vals)
        user_employees = []
        if record.employees_ids:
            for rec in record.employees_ids:
                employee = self.env['hr.employee'].search([('id', '=', rec.id)])
                if employee:
                    for i in employee:
                        user_employees.append(i.user_id.id)
        record.user_ids = [(6,0,user_employees)]
        return record
    
    def write(self, vals):
        if 'employees_ids' in vals:
            user_employees = []
            for employee in vals['employees_ids'][0][2]:
                    employee_obj = self.env['hr.employee'].search([('id', '=', employee)])
                    if employee_obj:
                        for i in employee_obj:
                            user_employees.append(i.user_id.id)
            vals['user_ids'] = [(6,0,user_employees)]
        res = super(HrManageTimesheet, self).write(vals)
        return res

    @api.onchange('is_manage_timesheet','employees_ids')
    def _domain_employee_id(self):
        if self.is_manage_timesheet and self.employees_ids:
            domain = [data.id for data in self.employees_ids]
            for rec in self.timesheet_line_ids:
                rec.employee_domain_ids = [(6,0,domain)]
        elif self.is_manage_timesheet and not self.employees_ids:
            for rec in self.timesheet_line_ids:
                rec.employee_domain_ids = []
    
    @api.onchange('employee_id', 'start_date', 'end_date')
    def _onchange_period(self):
        if (not self.employee_id) or (not self.start_date) or (not self.end_date):
            return
        self.timesheet_line_ids = [(5, 0, 0)]
        employee = self.employee_id
        employees = self.employees_ids
        period_start = self.start_date
        period_end = self.end_date
        delta = period_end - period_start
        days = [period_start + timedelta(days=i) for i in range(delta.days + 1)]
        if employees:
            analytic_line = self.env['account.analytic.line'].search([('employee_id','=',employees.ids)])
        else:
            analytic_line = self.env['account.analytic.line'].search([('employee_id','=',employee.id)])

        for date in days:
            for line in analytic_line:
                if line.date == date:
                    timesheet_lines = [(0, 0, {
                                'date': line.date,
                                'employee_id': line.employee_id.id,
                                'name': line.name,
                                'project_id': line.project_id.id,
                                'task_id': line.task_id.id,
                                'unit_amount': line.unit_amount,
                                'timesheet_id': self.id,
                                'analytic_line_id': line.id,
                                'employee_domain_ids':self.employees_ids,
                            })]
                    self.timesheet_line_ids = timesheet_lines
                