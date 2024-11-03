# -*- coding: utf-8 -*-

import string
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import date, datetime, timedelta

class MultipleIncidentReport(models.Model):
    _name = 'incident.report.multiple'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _description = 'Multiple Incident report'
    _order = 'date_of_accident DESC'
    _check_company_auto = True
    
    company_id = fields.Many2one('res.company', string="Company", required=True, tracking=True, readonly=True, default=lambda self: self.env.company.id)
    branch_id = fields.Many2one('res.branch', string='Branch', required=True, default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, 
                domain=lambda self: [('id', 'in', self.env.branches.ids)])
    name = fields.Char(string='Number', required=True, copy=False, readonly=True,
                       states={'draft': [('readonly', True)]}, index=True, default=lambda self: _('New'))
    date_of_accident = fields.Datetime(string='Date of Accident', required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed')], sstring='Status', readonly=True, copy=False, index=True, tracking=True, default='draft')
    incident_category_id = fields.Many2one('incident.category','Incident Category', required=True)
    description = fields.Text('Incident Description', required=True)
    number_of_accident = fields.Integer(string="Number of Accident",compute='_comute_accident_number')
    employee_incident_ids = fields.One2many('incident.report.employee', 'multiple_incident_id')

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('incident.report.multiple.sequence')
        return super(MultipleIncidentReport, self).create(vals)

    def _comute_accident_number(self):
        for res in self:
            count = res.env['incident.report.employee'].search_count([('multiple_incident_id', '=', res.id)])
            res.number_of_accident = count

    @api.onchange('date_of_accident')
    def depends_date_accident(self):
        for res in self:
            for line in res.employee_incident_ids:
                line.write({'date_of_accident': res.date_of_accident})

    @api.onchange('company_id')
    def depends_company_accident(self):
        for res in self:
            for line in res.employee_incident_ids:
                line.company_id = res.company_id

    @api.onchange('incident_category_id', 'description',)
    def depends_accident(self):
        for res in self:
            for line in res.employee_incident_ids:
                line.write({'incident_category_id': res.incident_category_id.id,
                            'description': res.description})

    @api.onchange('branch_id')
    def depends_branch_accident(self):
        for res in self:
            for line in res.employee_incident_ids:
                line.branch_id = res.branch_id

    def button_confirm(self):
        for res in self:
            if not res.employee_incident_ids:
                raise ValidationError("Can't confirm this record because there's no employee in incident line!")
            else:
                res.write({'state': 'confirm'})

    @api.onchange('date_of_accident')
    def depends_date_of_accident(self):
        for res in self:
            current_date = datetime.now()
            if res.date_of_accident:
                if res.date_of_accident > current_date:
                    raise ValidationError("Can not input more than the current time.")
    

    # def button_complete(self):
    #     for res in self:
    #         res.write({'state': 'complete'})