from odoo import fields, models, api, _
from odoo.exceptions import ValidationError

class HrOfferingApprovalMatrix(models.Model):
    _name = 'hr.offering.approval.matrix'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Recruitment Approval Matrix"
    _order = 'create_date desc'

    name = fields.Char()
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company.id)
    apply_to = fields.Selection(
        [('by_employee', 'By Employee'), ('by_department', 'By Department'), ('by_job_position', 'By Job Position')])
    employee_ids = fields.Many2many('hr.employee', string="Employee")
    department_ids = fields.Many2many('hr.department', string="Department",domain="[('company_id', '=', company_id)]")
    job_ids = fields.Many2many('hr.job', string="Job Position",domain="[('company_id', '=', company_id)]")
    level = fields.Integer(compute="_get_level")
    approval_matrix_ids = fields.One2many('hr.offering.approval.matrix.line', 'approval_matrix_id')

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        domain.extend(['|',('company_id', '=', False),('company_id', 'in', self.env.companies.ids)])
        return super(HrOfferingApprovalMatrix, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        domain.extend(['|',('company_id', '=', False),('company_id', 'in', self.env.companies.ids)])
        return super(HrOfferingApprovalMatrix, self).read_group(domain=domain, fields=fields, groupby=groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)

   

    @api.model
    def create(self, vals):
        res = super(HrOfferingApprovalMatrix, self).create(vals)
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
                raise ValidationError(_("Employees has assigned in another Offering Letter Approval Matrix : \n %s") %
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
                raise ValidationError(_("Job Position has assigned in another Offering Letter Approval Matrix : \n %s") %
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
                raise ValidationError(_("Departments has assigned in another Offering Letter Approval Matrix : \n %s") %
                                      (error_message))
        return res

    def write(self, vals):
        res = super(HrOfferingApprovalMatrix, self).write(vals)
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
                    raise ValidationError(_("Employees has assigned in another Offering Letter Approval Matrix : \n %s") %
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
                    raise ValidationError(_("Job Position has assigned in another Offering Letter Approval Matrix : \n %s") %
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
                    raise ValidationError(_("Departments has assigned in another Offering Letter Approval Matrix : \n %s") %
                                          (error_message))
        return res
    
    @api.depends('approval_matrix_ids')
    def _get_level(self):
        for rec in self:
            if rec.approval_matrix_ids:
                rec.level = len(rec.approval_matrix_ids)
            else:
                rec.level = 0

    @api.onchange('approval_matrix_ids')
    def _onchange_approval_matrix_line(self):
        sl = 0
        for line in self.approval_matrix_ids:
            sl = sl + 1
            line.sequence = sl
    
class HrOfferingApprovalMatrixLine(models.Model):
    _name = 'hr.offering.approval.matrix.line'

    approval_matrix_id = fields.Many2one('hr.offering.approval.matrix')
    sequence = fields.Integer('Sequence')
    company_id = fields.Many2one('res.company', related='approval_matrix_id.company_id')
    approvers = fields.Many2many('res.users',domain="[('company_id', '=', company_id)]")
    minimum_approver = fields.Integer(default=1)
    approver_type = fields.Selection(
        [('by_hierarchy', 'By Hierarchy'),
         ('specific_approver', 'Specific Approver')], default="specific_approver", string="Approver Type")

    @api.onchange("approver_type")
    def _onchange_approver_type(self):
        if self.approver_type == 'by_hierarchy':
            self.approvers = False
    
    @api.model
    def default_get(self, fields):
        res = super(HrOfferingApprovalMatrixLine, self).default_get(fields)
        if self.env.context:
            context_keys = self.env.context.keys()
            next_sequence = 1
            if 'approval_matrix_ids' in context_keys:
                if len(self.env.context.get('approval_matrix_ids')) > 0:
                    next_sequence = len(self.env.context.get('approval_matrix_ids')) + 1
        res.update({'sequence': next_sequence})
        return res