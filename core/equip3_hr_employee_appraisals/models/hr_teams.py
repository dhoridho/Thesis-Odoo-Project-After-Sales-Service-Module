# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class HrTeams(models.Model):
    _name = 'hr.teams'
    _description = 'HR Team'

    name = fields.Char('Team Name')
    leader_team_id = fields.Many2one('hr.employee', string='Leader Team')
    team_member_ids = fields.Many2many('hr.employee', string='Team Member')
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company.id)

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain += [('company_id', 'in', self.env.context.get('allowed_company_ids'))]

        result = super(HrTeams, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return result
    
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain.extend([('company_id', 'in', self.env.context.get('allowed_company_ids'))])
        return super(HrTeams, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)