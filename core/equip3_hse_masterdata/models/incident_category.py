# -*- coding: utf-8 -*-

import string
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class IncidentCategory(models.Model):
    _name = 'incident.category'
    _description = 'Incident Category'
    _check_company_auto = True
    
    company_id = fields.Many2one('res.company', string="Company", required=True, tracking=True, readonly=True, default=lambda self: self.env.company.id)
    branch_id = fields.Many2one('res.branch', string='Branch', required=True, default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, 
                domain=lambda self: [('id', 'in', self.env.branches.ids)])
    name = fields.Char(string='Name', required=True)
    incident_level = fields.Integer(string='Level')
    note = fields.Html(string='Description')

    @api.constrains('name')
    def _check_existing_record(self):
        for record in self:
            name = self.env['incident.category'].search(
                [('name', '=', record.name)])
            if len(name) > 1:
                raise ValidationError(
                    f'The name in this incident category is the same as another incident category. Please change the name')
    
    def name_get(self):
        result = []
        for record in self:
            result += [(record.id, record.name + ' - Level ' + str(record.incident_level))]
        return result