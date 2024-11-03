# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class HrSptType(models.Model):
    _name = 'hr.spt.type'
    _description = 'HR SPT Type'

    name = fields.Char('Name', required=True)
    code = fields.Char('Code', required=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company.id, readonly=True)
    
    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context
        if context.get('allowed_company_ids'):
            domain += [('company_id', 'in', self.env.context.get('allowed_company_ids'))]

        result = super(HrSptType, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return result

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain.extend([('company_id', 'in', self.env.context.get('allowed_company_ids'))])
        return super(HrSptType, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
    
    

    @api.constrains('code')
    def check_name(self):
        for record in self:
            if record.code:
                check_code = self.search([('code', '=', record.code), ('id', '!=', record.id)])
                if check_code:
                    raise ValidationError("Code must be unique!")

class HrSptCategory(models.Model):
    _name = 'hr.spt.category'
    _description = 'HR SPT Category'

    name = fields.Char('Name', required=True)
    spt_type = fields.Many2one('hr.spt.type', string='SPT Type')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company.id, readonly=True)
    
    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context
        if context.get('allowed_company_ids'):
            domain += [('company_id', 'in', self.env.context.get('allowed_company_ids'))]

        result = super(HrSptCategory, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return result

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain.extend([('company_id', 'in', self.env.context.get('allowed_company_ids'))])
        return super(HrSptCategory, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
