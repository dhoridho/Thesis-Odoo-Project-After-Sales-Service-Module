# -*- coding: utf-8 -*-
from odoo import fields, models, api
from odoo.exceptions import ValidationError

class ProbationPeriod(models.Model):
    _name = 'employee.probation.period'
    _description = 'Probation Period'

    name = fields.Char("Name", required=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True, default=lambda self: self.env.company)
    department_ids = fields.Many2many('hr.department', required=True, string ="Department", domain="[('company_id', '=', company_id)]")
    start_date = fields.Date("Start Date", required=True)
    end_date = fields.Date("End Date", required=True)

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain += [('company_id', 'in', self.env.context.get('allowed_company_ids'))]

        result = super(ProbationPeriod, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return result
    
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain.extend([('company_id', 'in', self.env.context.get('allowed_company_ids'))])
        return super(ProbationPeriod, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
    
    @api.constrains('start_date','end_date')
    def _check_date_range(self):
        for rec in self:
            if rec.start_date > rec.end_date:
                raise ValidationError("End Date must be greater than Start Date.")