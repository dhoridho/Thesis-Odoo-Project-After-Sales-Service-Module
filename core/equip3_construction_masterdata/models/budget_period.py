from dataclasses import field
from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression
from datetime import datetime, time
from dateutil.relativedelta import relativedelta
from lxml import etree


class BudgetPeriod(models.Model):
    _name = 'project.budget.period'
    _description = 'Budget Period'

    name = fields.Char('Period Name')
    state = fields.Selection([('draft','Draft'), ('open','Open'), ('closed','Closed'),],string = "State", readonly=True, default='draft')
    start_date = fields.Date('Start Date')
    end_date = fields.Date('End Date')
    project = fields.Many2one(comodel_name='project.project', string='Project', required=False)
    create_on = fields.Datetime('Create On', default=fields.Datetime.now)
    create_by = fields.Many2one('res.users','Create By', default=lambda self : self.env.user.id)
    company = fields.Many2one('res.company','Company', default=lambda self : self.env.company.id)
    budget_period_line_ids = fields.One2many('budget.period.line', 'budget_period_line_id', string='Budget Period Line')
    is_hide_create_month = fields.Boolean(default=False)
    is_hide_open_period = fields.Boolean(default=True)
    is_hide_close_period = fields.Boolean(default=True)
    branch_id = fields.Many2one('res.branch', string='Branch', default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, 
                                domain=lambda self: [('id', 'in', self.env.branches.ids),('company_id','=', self.env.company.id)])
    department_type = fields.Selection(related='project.department_type', string='Type of Department')
    
    
    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=True, submenu=True):
        res = super(BudgetPeriod, self).fields_view_get(
            view_id=view_id, view_type=view_type,toolbar=toolbar,submenu=submenu)
        root = etree.fromstring(res['arch'])
        if self.env.user.has_group('abs_construction_management.group_construction_user') and not self.env.user.has_group('equip3_construction_accessright_setting.group_construction_engineer'):
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
        else:
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'true')
            res['arch'] = etree.tostring(root)
        return res
    
    @api.onchange('department_type')
    def _onchange_department_type(self):
        for rec in self:
            if  self.env.user.has_group('abs_construction_management.group_construction_user') and not self.env.user.has_group('equip3_construction_accessright_setting.group_construction_director'):
                if rec.department_type == 'project':
                    return {
                        'domain': {'project': [('department_type', '=', 'project'), ('primary_states', '!=', 'cancelled'), ('company_id', '=', rec.company.id),('id','in',self.env.user.project_ids.ids)]}
                    }
                elif rec.department_type == 'department':
                    return {
                        'domain': {'project': [('department_type', '=', 'department'), ('primary_states', '!=', 'cancelled'), ('company_id', '=', rec.company.id),('id','in',self.env.user.project_ids.ids)]}
                    }
            else:
                if rec.department_type == 'project':
                    return {
                        'domain': {'project': [('department_type', '=', 'project'), ('primary_states', '!=', 'cancelled'), ('company_id', '=', rec.company.id)]}
                    }
                elif rec.department_type == 'department':
                    return {
                        'domain': {'project': [('department_type', '=', 'department'), ('primary_states', '!=', 'cancelled'), ('company_id', '=', rec.company.id)]}
                    }
    

    @api.constrains('name')
    def check_name(self):
        for record in self:
            if record.name:
                check_name = self.search([('name', '=', record.name), ('id', '!=', record.id), ('state', '!=', 'closed')])
                if check_name:
                    raise ValidationError("Period Name must be unique!")
    
    @api.constrains('project')
    def check_project(self):
        for record in self:
            if record.project:
                check_project = self.search([('project', '=', record.project.id), ('id', '!=', record.id), ('state', '!=', 'closed')])
                if check_project:
                    raise ValidationError("This project already have period")
    
    @api.onchange('start_date', 'end_date')
    def _onchange_date(self):
        for record in self:
            if record.start_date and record.end_date:
                if record.start_date > record.end_date:
                    raise ValidationError("End Date must be greater than Start Date!")

    def action_create_period(self):
        for period in self:
            period._create_period()
            period.state = 'draft'
            period.is_hide_create_month = True
            period.is_hide_open_period = False
            # period.message_post(body=_('Periods Status: Draft'))

    def _create_period(self):
        self.ensure_one()
        obj_period = self.env["budget.period.line"]
        start_date = datetime.strptime(str(self.start_date), "%Y-%m-%d")
        ends_date = datetime.strptime(str(self.end_date), "%Y-%m-%d")
        while start_date.strftime("%Y-%m-%d") <= ends_date.strftime("%Y-%m-%d"):
            end_date = start_date + relativedelta(months=+1, days=-1)
            year_date = start_date.strftime("%Y")
            month_date = start_date.strftime("%B")

            if end_date.strftime("%Y-%m-%d") > ends_date.strftime("%Y-%m-%d"):
                end_date = ends_date

            obj_period.create({
                "year": year_date,
                "month": month_date,
                "state": "draft",
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d"),
                "budget_period_line_id": self.id,
            })
            start_date = start_date + relativedelta(months=+1)

    def action_open(self):
        for record in self:
            if record.budget_period_line_ids:
                data = []
                for line in record.budget_period_line_ids:
                    data.append((1, line.id, {'state': 'open'}))
                record.budget_period_line_ids = data 
            record.state = 'open'
            record.is_hide_open_period = True
            record.is_hide_close_period = False

    def action_closed(self):
        for record in self:
            if record.budget_period_line_ids:
                data = []
                for line in record.budget_period_line_ids:
                    data.append((1, line.id, {'state': 'closed'}))
            record.budget_period_line_ids = data 
            record.state = 'closed'
            record.is_hide_close_period = True

    def action_reset(self):
        for record in self:
            if record.budget_period_line_ids:
                data = []
                for line in record.budget_period_line_ids:
                    data.append((1, line.id, {'state': 'draft'}))
            record.budget_period_line_ids = data 
            record.state = 'draft'
            record.is_hide_create_month = True
            record.is_hide_open_period = False
            record.is_hide_close_period = True


class BudgetPeriodLine(models.Model):
    _name = 'budget.period.line'
    _description = 'Budget Period Line'
    _rec_name = 'name'

    name = fields.Char('Name', compute='_compute_name')
    budget_period_line_id = fields.Many2one('project.budget.period', 'Budget Period Line ID')
    line_project_ids = fields.Many2one(comodel_name='project.project', string='Project', required=False, related="budget_period_line_id.project")
    year = fields.Char('Year')
    month = fields.Char('Month')
    start_date = fields.Date('Start Date')
    end_date = fields.Date('End Date')
    state = fields.Selection([('draft','Draft'), ('open','Open'), ('closed','Closed'),],string = "State", readonly=True, default='draft')

    def _compute_name(self):
        for rec in self:
            record = rec.month + ' ' + rec.year
            rec.write({'name' : record })

    

