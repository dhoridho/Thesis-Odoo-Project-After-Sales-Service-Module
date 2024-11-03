# -*- coding: utf-8 -*-
from odoo import models, fields, api

class EmployeeExitChecklist(models.Model):
    _name = 'employee.exit.checklist'
    _description = "Employee Exit Checklist"

    name = fields.Char('Name', required=1)
    department_ids = fields.Many2many('hr.department', string="Department", domain="[('company_id', '=', company_id)]", required=1)
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company, readonly=True)
    checklist_line_ids = fields.Many2many('employee.checklists', string='Checklist Lines')

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain += [('company_id', 'in', self.env.context.get('allowed_company_ids'))]

        result = super(EmployeeExitChecklist, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return result
    
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain.extend([('company_id', 'in', self.env.context.get('allowed_company_ids'))])
        return super(EmployeeExitChecklist, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)