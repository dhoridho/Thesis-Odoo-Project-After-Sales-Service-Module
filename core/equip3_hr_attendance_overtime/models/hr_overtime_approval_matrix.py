# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError
from lxml import etree

class HROvertimeApprovalMatrix(models.Model):
    _name = 'hr.overtime.approval.matrix'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Overtime Approval Matrix"
    _order = 'create_date desc'

    @api.model
    def _multi_company_domain(self):
        return [('company_id','=', self.env.company.id)]
    
    name = fields.Char('Name')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company.id)
    apply_to = fields.Selection(
        [('by_employee', 'By Employee'), ('by_job_position', 'By Job Position'), ('by_department', 'By Department')])
    employee_ids = fields.Many2many('hr.employee', domain=_multi_company_domain)
    job_ids = fields.Many2many('hr.job', domain=_multi_company_domain)
    deparment_ids = fields.Many2many('hr.department', domain=_multi_company_domain)
    level = fields.Integer(compute="_get_level")
    approval_matrix_ids = fields.One2many('hr.overtime.approval.matrix.line', 'approval_matrix_id')
    
    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain += [('company_id', 'in', self.env.context.get('allowed_company_ids'))]

        result = super(HROvertimeApprovalMatrix, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return result
    
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain.extend([('company_id', 'in', self.env.context.get('allowed_company_ids'))])
        return super(HROvertimeApprovalMatrix, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
    
    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=True, submenu=True):
        res = super(HROvertimeApprovalMatrix, self).fields_view_get(
            view_id=view_id, view_type=view_type,toolbar=toolbar,submenu=submenu)
        if  self.env.user.has_group('equip3_hr_attendance_overtime.group_overtime_admin'):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'true')
            res['arch'] = etree.tostring(root)
        else:
            root = etree.fromstring(res['arch'])
            root.set('create', 'false')
            root.set('edit', 'false')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
            
        return res

    @api.model
    def create(self, vals):
        res = super(HROvertimeApprovalMatrix, self).create(vals)
        if len(res.approval_matrix_ids) == 0:
            raise ValidationError(_("Approval User Lines cannot be empty!"))

        employees = []
        for employee in res.employee_ids:
            employees += [employee.id]

        jobs = []
        for job in res.job_ids:
            jobs += [job.id]

        deparments = []
        for deparment in res.deparment_ids:
            deparments += [deparment.id]

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
                raise ValidationError(_("Employees has assigned in another Overtime Approval Matrix : \n %s") %
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
                raise ValidationError(_("Job Position has assigned in another Overtime Approval Matrix : \n %s") %
                                      (error_message))
        elif res.apply_to == 'by_department':
            matrix = self.search([('deparment_ids', 'in', deparments), ('id', '!=', res.id)])
            if matrix:
                department_names = []
                for rec in matrix:
                    for department in rec.deparment_ids:
                        if department.name not in department_names and department.id in deparments:
                            department_names += [department.name]
                error_message = ''
                num = 1
                for department in department_names:
                    error_message += str(num) + '. ' + department + '\n'
                    num += 1
                raise ValidationError(_("Departments has assigned in another Overtime Approval Matrix : \n %s") %
                                      (error_message))
        return res

    def write(self, vals):
        res = super(HROvertimeApprovalMatrix, self).write(vals)
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

            deparments = []
            for deparment in rec.deparment_ids:
                deparments += [deparment.id]

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
                    raise ValidationError(_("Employees has assigned in another Overtime Approval Matrix : \n %s") %
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
                    raise ValidationError(_("Job Position has assigned in another Overtime Approval Matrix : \n %s") %
                                          (error_message))
            elif rec.apply_to == 'by_department':
                matrix = self.search([('deparment_ids', 'in', deparments), ('id', '!=', rec.id)])
                if matrix:
                    department_names = []
                    for rec in matrix:
                        for department in rec.deparment_ids:
                            if department.name not in department_names and department.id in deparments:
                                department_names += [department.name]
                    error_message = ''
                    num = 1
                    for department in department_names:
                        error_message += str(num) + '. ' + department + '\n'
                        num += 1
                    raise ValidationError(_("Departments has assigned in another Overtime Approval Matrix : \n %s") %
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

    @api.constrains('approval_matrix_ids')
    def _constrains_approval_matrix(self):
        for rec in self:
            if len(rec.approval_matrix_ids.filtered(lambda r: r.approver_types == "by_hierarchy")) > 1:
                raise ValidationError("You Only Able to set One Lines of  Approver Type with By Hierarchy type")

class HROvertimeApprovalMatrixLine(models.Model):
    _name = 'hr.overtime.approval.matrix.line'

    @api.model
    def _multi_company_domain(self):
        return [('company_id','=', self.env.company.id)]
    
    approval_matrix_id = fields.Many2one('hr.overtime.approval.matrix')
    sequence = fields.Integer('Sequence')
    approvers = fields.Many2many('res.users', domain=_multi_company_domain)
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
        res = super(HROvertimeApprovalMatrixLine, self).default_get(fields)
        if self.env.context:
            context_keys = self.env.context.keys()
            next_sequence = 1
            if 'approval_matrix_ids' in context_keys:
                if len(self.env.context.get('approval_matrix_ids')) > 0:
                    next_sequence = len(self.env.context.get('approval_matrix_ids')) + 1
        res.update({'sequence': next_sequence})
        return res



