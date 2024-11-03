# -*- coding: utf-8 -*-
from odoo import models, fields, api

class EmployeeChecklists(models.Model):
    _name = 'employee.checklists'
    _description = "Employee Checklists"

    name = fields.Char(string='Name', copy=False, required=1, help="Checklist Name")
    document_type = fields.Selection([('entry', 'Entry Process'),
                                      ('exit', 'Exit Process')], string='Checklist Type', help='Type of Checklist',
                                     required=1)
    activity_type = fields.Selection([('to_do', 'To Do'),
                                      ('upload_document', 'Upload Document')], string='Activity Type',
                                     required=1)
    responsible_user_id = fields.Many2one('res.users', string="Responsible User", required="1", domain="[('company_id','=',company_id)]")
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company, readonly=True)

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain += [('company_id', 'in', self.env.context.get('allowed_company_ids'))]

        result = super(EmployeeChecklists, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return result
    
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain.extend([('company_id', 'in', self.env.context.get('allowed_company_ids'))])
        return super(EmployeeChecklists, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)