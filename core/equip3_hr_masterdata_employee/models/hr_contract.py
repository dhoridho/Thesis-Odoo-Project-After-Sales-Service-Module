from odoo import api, fields, models, _


class HrContractWage(models.Model):
    _inherit = 'hr.contract'
    _description = 'HR Contract'

    parent_id = fields.Many2one('hr.employee', 
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", string='Manager')
    job_id = fields.Many2one('hr.job', 'Job Position', domain="['|','&',('company_id', '=', False),('department_id','=',department_id),'&',('company_id', '=', company_id),('department_id','=',department_id)]")

    @api.depends('employee_id')
    def _compute_employee_contract(self):
        for contract in self.filtered('employee_id'):
            contract.job_id = contract.employee_id.job_id
            contract.department_id = contract.employee_id.department_id
            contract.resource_calendar_id = contract.employee_id.resource_calendar_id
            contract.company_id = contract.employee_id.company_id
    
    @api.onchange('department_id')
    def onchange_department(self):
        context = self.env.context
        if self.department_id:
            self.parent_id = self.department_id.manager_id
            self.job_id = False
        if context.get('default_job_id'):
            self.job_id = context.get('default_job_id')

    @api.onchange('wage')
    def onchange_wage(self):
        for rec in self:
            if rec.wage and rec.employee_id.grade_id.minimum_sal and rec.employee_id.grade_id.maximum_sal:
                if rec.wage < rec.employee_id.grade_id.minimum_sal or rec.wage > rec.employee_id.grade_id.maximum_sal:
                    warning = {
                        'title': _('Wage does not match!'),
                        'message': _(
                            'The Wage does not match with Range Salary of Grade %s. \nAre you sure to continue with '
                            'the current wage ?') % rec.employee_id.grade_id.name,
                    }
                    return {'warning': warning}
