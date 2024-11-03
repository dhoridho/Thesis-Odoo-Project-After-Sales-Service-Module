from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class SalaryIncrementApprovalMatrix(models.Model):
    _name = "salary.increment.approval.matrix"

    name = fields.Char(string='Name')
    level = fields.Integer('Level', compute='_compute_get_level')
    apply_to = fields.Selection([
        ('employee', 'By Employee'),
        ('job_position', 'By Job Position'),
        ('department', 'By Department')],
        string='Apply To')
    employee_ids = fields.Many2many('hr.employee', string='Employee')
    department_ids = fields.Many2many('hr.department', string='Department')
    job_ids = fields.Many2many('hr.job', string='Job Position')
    approval_matrix_ids = fields.One2many('salary.increment.approval.matrix.line', 'approval_id',
                                                string='Approver')
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)
    
    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain += [('company_id', 'in', self.env.context.get('allowed_company_ids'))]

        result = super(SalaryIncrementApprovalMatrix, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return result
    
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain.extend([('company_id', 'in', self.env.context.get('allowed_company_ids'))])
        return super(SalaryIncrementApprovalMatrix, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
    
    def _compute_get_level(self):
        if self:
            for rec in self:
                approval_line = self.env['salary.increment.approval.matrix.line'].search(
                    [('approval_id', '=', rec.id)])
                rec.level = len(approval_line.ids)

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
    
class SalaryIncrementApprovalLine(models.Model):
    _name = 'salary.increment.approval.matrix.line'

    approval_id = fields.Many2one('salary.increment.approval.matrix', string="Matrix Line", ondelete="cascade")
    sequence = fields.Integer('Sequence')
    approver_ids = fields.Many2many('res.users', string="Approvers")
    minimum_approver = fields.Integer(string="Minimum Approver", default="1")
    approver_types = fields.Selection(
        [('by_hierarchy', 'By Hierarchy'),
         ('specific_approver', 'Specific Approver')], default="specific_approver", string="Approver Types")

    @api.onchange("approver_types")
    def _onchange_approver_types(self):
        if self.approver_types == 'by_hierarchy':
            self.approver_ids = False

    @api.model
    def default_get(self, fields):
        res = super(SalaryIncrementApprovalLine, self).default_get(fields)
        if self.env.context:
            context_keys = self.env.context.keys()
            next_sequence = 1
            if 'approval_matrix_ids' in context_keys:
                if len(self.env.context.get('approval_matrix_ids')) > 0:
                    next_sequence = len(self.env.context.get('approval_matrix_ids')) + 1
        res.update({'sequence': next_sequence})
        return res