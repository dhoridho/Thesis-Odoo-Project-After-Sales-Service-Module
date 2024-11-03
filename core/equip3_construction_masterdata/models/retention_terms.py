# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class RetentionTerm(models.Model):
    _name = 'retention.term'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _description = 'Retention Terms'
    _order = 'days asc'
    
    name = fields.Char(string='Retention Terms', required=True)
    company_id = fields.Many2one('res.company', 'Company', index=True, default=lambda self: self.env.company, readonly=True)
    branch_id = fields.Many2one('res.branch', string="Branch", default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, domain=lambda self: [('id', 'in', self.env.branches.ids),('company_id','=', self.env.company.id)])
    days = fields.Integer(string='Number of Days', default=0, required=True)
    sequence = fields.Integer(default=0)
    
    @api.constrains('name')
    def _check_existing_record_name(self):
        for record in self:
            name_id = self.env['retention.term'].search(
                [('name', '=', record.name)])
            if len(name_id) > 1:
                raise ValidationError(
                    f'The retention term name already exists, which is the same with other name.\nPlease change the retention term name.')    
