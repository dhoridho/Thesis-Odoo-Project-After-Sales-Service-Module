# -*- coding: utf-8 -*-
from odoo import fields, models, api
from datetime import date
from dateutil.relativedelta import relativedelta
from odoo.exceptions import Warning
from lxml import etree

class EmployeeProbation(models.Model):
    _inherit = 'employee.probation'

    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('on_going', 'On Going'),
        ('done', 'Done'),
        ('pass', 'Pass'),
        ('not_pass', 'Failed')], default='draft', string='Stage', tracking=True)
    show_submit = fields.Boolean()
    show_update_contract = fields.Boolean(default=True)
    contract_id = fields.Many2one('hr.contract', string="Contract", domain="[('employee_id','=',employee_id)]")
    employee_probation_period = fields.Selection([('by_specific_date', 'Specific Date'),('with_masterdata', 'Using Masterdata Periods')],
                                                 default='with_masterdata', string='Period', required=True, tracking=True)
    emp_probation_period_id = fields.Many2one('employee.probation.period', string="Period")
    reviewer_ids = fields.Many2many('res.users', string="Reviewer")

    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=False, submenu=False):
        res = super(EmployeeProbation, self).fields_view_get(
            view_id=view_id, view_type=view_type)
        if self.env.context.get('probation_reviewer'):
            root = etree.fromstring(res['arch'])
            root.set('create', 'false')
            root.set('edit', 'true')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
        return res

    @api.model
    def create(self, vals):
        vals['show_submit'] = True
        return super(EmployeeProbation, self).create(vals)
    
    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain += [('company_id', 'in', self.env.context.get('allowed_company_ids'))]

        result = super(EmployeeProbation, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return result
    
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain.extend([('company_id', 'in', self.env.context.get('allowed_company_ids'))])
        return super(EmployeeProbation, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
    
    @api.onchange('employee_id')
    def onchange_employee_id(self):
        if self.employee_id:
            contract = self.env['hr.contract'].search([('employee_id','=',self.employee_id.id),('state','=','open')],limit=1)
            if contract:
                self.contract_id = contract.id
        return super(EmployeeProbation, self).onchange_employee_id()
    
    @api.onchange('contract_id')
    def onchange_contract_id(self):
        if self.contract_id:
            self.start_date = self.contract_id.date_start
        else:
            self.start_date = False
    
    @api.onchange('employee_probation_period')
    def onchange_employee_probation_period(self):
        for rec in self:
            if rec.employee_probation_period == "with_masterdata":
                rec.start_date = False
                rec.end_date = False
            else:
                rec.emp_probation_period_id = False
                rec.start_date = False
                rec.end_date = False
    
    @api.onchange('department_id','company_id')
    def onchange_department_company(self):
        for rec in self:
            if rec.company_id and rec.department_id:
                return {'domain': {'emp_probation_period_id': [('company_id', '=', rec.company_id.id),('department_ids', 'in', [rec.department_id.id])]}}
            else:
                return {'domain': {'emp_probation_period_id': [('id', '=', 0)]}}

    @api.onchange('emp_probation_period_id')
    def _onchange_emp_probation_period(self):
        for rec in self:
            if rec.emp_probation_period_id:
                rec.start_date = rec.emp_probation_period_id.start_date
                rec.end_date = rec.emp_probation_period_id.end_date
    
    def action_submit(self):
        for rec in self:
            rec.state = 'submitted'
            if rec.probation_mass_line_id:
                rec.probation_mass_line_id.state = 'submitted'
    
    def action_pass(self):
        for rec in self:
            if not rec.review_ids:
                raise Warning("This employee has not had a probationary review. Provide at least one evaluation before determining if this employee passed or failed this probationary period.")
            rec.state = 'pass'
    
    def action_not_pass(self):
        for rec in self:
            if not rec.review_ids:
                raise Warning("This employee has not had a probationary review. Provide at least one evaluation before determining if this employee passed or failed this probationary period.")
            rec.state = 'not_pass'
            if rec.contract_id:
                rec.contract_id.date_end = rec.end_date
    
    def update_contract(self):
        view_id = self.env.ref('hr_contract.hr_contract_view_form')
        if self.contract_id:
            return {
                    'name': 'Contract',
                    'type': 'ir.actions.act_window',
                    'view_mode': 'form',
                    'target': 'new',
                    'res_model': 'hr.contract',
                    'res_id': self.contract_id.id,
                    'view_id': view_id.id,
                    }
        else:
            return False
    
    api.model
    def cron_update_state(self):
        records = self.env['employee.probation'].sudo().search([('state','in',['submitted','on_going'])])
        probation_mass = self.env["employee.probation.mass"].search([('state', '!=', 'draft')])
        today = date.today()
        for rec in records:
            if today >= rec.start_date:
                rec.state = 'on_going'
                if rec.probation_mass_line_id:
                    rec.probation_mass_line_id.state = 'on_going'
            if today >= rec.end_date:
                rec.state = 'done'
                if rec.probation_mass_line_id:
                    rec.probation_mass_line_id.state = 'done'
        
        # Update probation mass line state
        for probation in probation_mass:
            # If state of lines equals to 'on_going' the state of probation mass will be updated to be 'on_going'
            if all(employee.state == 'on_going' for employee in probation.employee_ids):
                probation.state = 'on_going'
            # If state of lines equals to 'done' the state of probation mass will be updated to be 'done'
            elif all(employee.state == 'done' for employee in probation.employee_ids):
                probation.state = 'done'