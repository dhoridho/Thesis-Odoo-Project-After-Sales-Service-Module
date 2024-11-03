# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError

class HRTimesheetApprovalMatrix(models.Model):
    _name = 'hr.timesheet.approval.matrix'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Timesheet Approval Matrix"
    _order = 'create_date desc'

    name = fields.Char('Name')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company.id)
    apply_to = fields.Selection(
        [('by_employee', 'By Employee'), ('by_job_position', 'By Job Position'), ('by_department', 'By Department')])
    employee_ids = fields.Many2many('hr.employee')
    job_ids = fields.Many2many('hr.job')
    department_ids = fields.Many2many('hr.department')
    level = fields.Integer(compute="_get_level")
    approval_matrix_ids = fields.One2many('hr.timesheet.approval.matrix.line', 'approval_matrix_id')

    @api.model
    def create(self, vals):
        res = super(HRTimesheetApprovalMatrix, self).create(vals)
        if len(res.approval_matrix_ids) == 0:
            raise ValidationError(_("Approval User Lines cannot be empty!"))

        employees = []
        for employee in res.employee_ids:
            employees += [employee.id]

        jobs = []
        for job in res.job_ids:
            jobs += [job.id]

        departments = []
        for department in res.department_ids:
            departments += [department.id]

        if res.apply_to == 'by_employee':
            matrix = self.search([('employee_ids', 'in', employees), ('id', '!=', res.id)])
            if matrix:
                employee_names = []
                for rec in matrix:
                    for employee in rec.employee_ids:
                        if employee.name not in employee_names and employee.id in employees:
                            employee_names += [employee.name]
                error_message = ''
                num = 1
                for employee in employee_names:
                    error_message += str(num) + '. ' + employee + '\n'
                    num += 1
                raise ValidationError(_("Employees has assigned in another Timesheet Approval Matrix : \n %s") %
                                      (error_message))
        elif res.apply_to == 'by_job_position':
            matrix = self.search([('job_ids', 'in', jobs), ('id', '!=', res.id)])
            if matrix:
                job_names = []
                for rec in matrix:
                    for job in rec.job_ids:
                        if job.name not in job_names and job.id in jobs:
                            job_names += [job.name]
                error_message = ''
                num = 1
                for job in job_names:
                    error_message += str(num) + '. ' + job + '\n'
                    num += 1
                raise ValidationError(_("Job Position has assigned in another Timesheet Approval Matrix : \n %s") %
                                      (error_message))
        elif res.apply_to == 'by_department':
            matrix = self.search([('department_ids', 'in', departments), ('id', '!=', res.id)])
            if matrix:
                department_names = []
                for rec in matrix:
                    for department in rec.department_ids:
                        if department.name not in department_names and department.id in departments:
                            department_names += [department.name]
                error_message = ''
                num = 1
                for department in department_names:
                    error_message += str(num) + '. ' + department + '\n'
                    num += 1
                raise ValidationError(_("Departments has assigned in another Timesheet Approval Matrix : \n %s") %
                                      (error_message))
        return res

    def write(self, vals):
        res = super(HRTimesheetApprovalMatrix, self).write(vals)
        for rec in self:
            line_ids = len(rec.approval_matrix_ids)
            if line_ids == 0:
                raise ValidationError(_("Approval User Lines cannot be empty!"))

            employees = []
            for employee in rec.employee_ids:
                employees += [employee.id]

            jobs = []
            for job in rec.job_ids:
                jobs += [job.id]

            departments = []
            for department in rec.department_ids:
                departments += [department.id]

            if rec.apply_to == 'by_employee':
                matrix = self.search([('employee_ids', 'in', employees), ('id', '!=', rec.id)])
                if matrix:
                    employee_names = []
                    for rec in matrix:
                        for employee in rec.employee_ids:
                            if employee.name not in employee_names and employee.id in employees:
                                employee_names += [employee.name]
                    error_message = ''
                    num = 1
                    for employee in employee_names:
                        error_message += str(num) + '. ' + employee + '\n'
                        num += 1
                    raise ValidationError(_("Employees has assigned in another Timesheet Approval Matrix : \n %s") %
                                          (error_message))
            elif rec.apply_to == 'by_job_position':
                matrix = self.search([('job_ids', 'in', jobs), ('id', '!=', rec.id)])
                if matrix:
                    job_names = []
                    for rec in matrix:
                        for job in rec.job_ids:
                            if job.name not in job_names and job.id in jobs:
                                job_names += [job.name]
                    error_message = ''
                    num = 1
                    for job in job_names:
                        error_message += str(num) + '. ' + job + '\n'
                        num += 1
                    raise ValidationError(_("Job Position has assigned in another Timesheet Approval Matrix : \n %s") %
                                          (error_message))
            elif rec.apply_to == 'by_department':
                matrix = self.search([('department_ids', 'in', departments), ('id', '!=', rec.id)])
                if matrix:
                    department_names = []
                    for rec in matrix:
                        for department in rec.department_ids:
                            if department.name not in department_names and department.id in departments:
                                department_names += [department.name]
                    error_message = ''
                    num = 1
                    for department in department_names:
                        error_message += str(num) + '. ' + department + '\n'
                        num += 1
                    raise ValidationError(_("Departments has assigned in another Timesheet Approval Matrix : \n %s") %
                                          (error_message))
        return res

    @api.depends('approval_matrix_ids')
    def _get_level(self):
        for record in self:
            if record.approval_matrix_ids:
                record.level = len(record.approval_matrix_ids)
            else:
                record.level = 0

    @api.onchange('approval_matrix_ids')
    def _onchange_approval_matrix_line(self):
        sl = 0
        for line in self.approval_matrix_ids:
            sl = sl + 1
            line.sequence = sl


class HRTimesheetApprovalMatrixLine(models.Model):
    _name = 'hr.timesheet.approval.matrix.line'

    approval_matrix_id = fields.Many2one('hr.timesheet.approval.matrix', ondelete="cascade")
    sequence = fields.Integer('Sequence')
    approvers = fields.Many2many('res.users')
    minimum_approver = fields.Integer(default=1)
    approver_types = fields.Selection(
        [('by_hierarchy', 'By Hierarchy'),
         ('specific_approver', 'Specific Approver')], default="specific_approver", string="Approver Types")

    @api.onchange("approver_types")
    def _onchange_approver_types(self):
        if self.approver_types == 'by_hierarchy':
            self.approvers = False

    @api.model
    def default_get(self, fields):
        res = super(HRTimesheetApprovalMatrixLine, self).default_get(fields)
        if self.env.context:
            context_keys = self.env.context.keys()
            next_sequence = 1
            if 'approval_matrix_ids' in context_keys:
                if len(self.env.context.get('approval_matrix_ids')) > 0:
                    next_sequence = len(self.env.context.get('approval_matrix_ids')) + 1
        res.update({'sequence': next_sequence})
        return res



