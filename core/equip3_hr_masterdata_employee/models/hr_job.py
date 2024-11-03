from odoo import api, fields, models, _


class HrJob(models.Model):
    _inherit = 'hr.job'
    _description = 'Hr Job'

    classification_id = fields.Many2one("employee.job.classification", string="Job Classification")
    department_id = fields.Many2one('hr.department', string='Department', domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    company_id = fields.Many2one("res.company", string="Company", default=lambda self: self.env.company,
                                 tracking=True, required=True)
    branch_id = fields.Many2one("res.branch", string="Branch", domain="[('company_id', '=', company_id)]",
                                tracking=True)
    parent_job_position_id = fields.Many2one("hr.job", string="Parent Job Position", domain="['|','&',('company_id','=',False),('department_id','=',department_id),('id','!=',id),'&',('company_id','=',company_id),('department_id','=',department_id),('id','!=',id)]", help="Used as 'Parent' information from a Job Position. Not filled in with value, means the Highest Position in the Job Hierarchy in a Department")
    no_of_running_employee = fields.Integer(compute='_compute_running_employees', string="Current Running Employees")

    def _compute_running_employees(self):
        employee_data = self.env['hr.employee'].read_group([('contract_state','=','open'), ('job_id', 'in', self.ids)], ['job_id'], ['job_id'])
        result = dict((data['job_id'][0], data['job_id_count']) for data in employee_data)
        for job in self:
            job.no_of_running_employee = result.get(job.id, 0)

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain += [('company_id', 'in', self.env.context.get('allowed_company_ids'))]

        result = super(HrJob, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return result
    
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain.extend([('company_id', 'in', self.env.context.get('allowed_company_ids'))])
        return super(HrJob, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
    
    @api.onchange('parent_job_position_id','department_id')
    def _onchange_parent_job_position(self):
        departments = []
        jobs = []
        if self.department_id:
            departments.append(self.department_id.id)
            if self.department_id.parent_id:
                parent_id = self.department_id.parent_id
                while (parent_id):
                    departments.append(parent_id.id)
                    parent_id = parent_id.parent_id
            job_ids = self.env['hr.job'].search([('department_id','in',departments)])
            if job_ids:
                for job in job_ids:
                    jobs.append(job.id)
        return {
            'domain': {'parent_job_position_id': [('id', 'in', jobs)]},
        }