# -*- coding: utf-8 -*-

from odoo import api, fields, models, _, tools
from lxml import  etree
from odoo.exceptions import ValidationError


class ExpenseApprovalMatrix(models.Model):
    _name = 'hr.expense.approval.matrix'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Expense Approval Matrix"
    _order = 'create_date desc'

    @api.model
    def _multi_company_domain(self):
        return [('company_id','=', self.env.company.id)]
    
    name = fields.Char('Name')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company.id)
    apply_to = fields.Selection(
        [('by_employee', 'By Employee'), ('by_job_position', 'By Job Position'), ('by_department', 'By Department')])
    employee_ids = fields.Many2many('hr.employee', domain=_multi_company_domain)
    deparment_ids = fields.Many2many('hr.department', domain=_multi_company_domain)
    job_ids = fields.Many2many('hr.job', domain=_multi_company_domain)
    minimum_amount = fields.Float('Minimum Amount')
    maximum_amount = fields.Float('Maximum Amount')

    level = fields.Integer(compute="_get_level")
    # career_transition_type = fields.Many2many('career.transition.type')
    approval_matrix_ids = fields.One2many('hr.expense.approval.matrix.line', 'approval_matrix_id')
    
    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain += [('company_id', 'in', self.env.context.get('allowed_company_ids'))]

        result = super(ExpenseApprovalMatrix, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return result
    
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain.extend([('company_id', 'in', self.env.context.get('allowed_company_ids'))])
        return super(ExpenseApprovalMatrix, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
    
    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=True, submenu=True):
        res = super(ExpenseApprovalMatrix, self).fields_view_get(
            view_id=view_id, view_type=view_type,toolbar=toolbar,submenu=submenu)
        if  self.env.user.has_group('hr_expense.group_hr_expense_user'):
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

class ExpenseApprovalMatrixline(models.Model):
    _name = 'hr.expense.approval.matrix.line'

    @api.model
    def _multi_company_domain(self):
        return [('company_id','=', self.env.company.id)]
    
    approval_matrix_id = fields.Many2one('hr.expense.approval.matrix')
    sequence = fields.Integer()
    approvers = fields.Many2many('res.users', domain=_multi_company_domain)
    minimum_approver = fields.Integer(default=1)
    approver_types = fields.Selection(
        [('by_hierarchy', 'By Hierarchy'),
        ('specific_approver', 'Specific Approver')], default="specific_approver", string="Approver Types")

    @api.model
    def default_get(self, fields):
        res = super(ExpenseApprovalMatrixline, self).default_get(fields)
        if self.env.context:
            context_keys = self.env.context.keys()
            next_sequence = 1
            if 'approval_matrix_ids' in context_keys:
                if len(self.env.context.get('approval_matrix_ids')) > 0:
                    next_sequence = len(self.env.context.get('approval_matrix_ids')) + 1
        res.update({'sequence': next_sequence})
        return res
