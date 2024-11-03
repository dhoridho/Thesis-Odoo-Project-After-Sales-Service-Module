# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class CustomCrmLeadLost(models.TransientModel):
    _inherit = 'crm.lead.lost'

    def action_lost_reason_apply(self):
        leads = self.env['crm.lead'].browse(self.env.context.get('active_ids'))
        project = self.env['project.project'].search([('lead_id', '=', leads.id), ('name', '=', leads.project_id)],limit=1)
        main_contract = self.env['sale.order.const'].search([('project_id', '=', project.id), ('contract_category', '=', 'main'), ('state', 'in', ('sale','done'))],limit=1)
        if project: 
            if not main_contract:
                project.primary_states = 'lost'
            else: 
                raise ValidationError(_('Cannot "Mark Lost" this opportunity because this project already has a contract')) 
        res = super(CustomCrmLeadLost, self).action_lost_reason_apply()
        return res


class Restore(models.TransientModel):
    _inherit = "restore.lead.type"
    _description = "Restore"

    def action_submit(self):
        leads = self.env['crm.lead'].browse(self.env.context.get('active_ids'))
        project = self.env['project.project'].search([('lead_id', '=', leads.id), ('name', '=', leads.project_id)],limit=1)
        if project:
            project.primary_states = 'draft'
        res = super(Restore, self).action_submit()
        return res


class OpportunityDetails(models.Model):
    _inherit = 'crm.lead'

    count_job_cons = fields.Integer(compute="_compute_count_job_cons")
    count_contract_cons = fields.Integer(compute="_compute_count_contract_cons")
    
    def _compute_count_job_cons(self):
        for res in self:
            job = self.env['job.estimate'].search_count([('lead_id', '=', res.id), ('project_id.name', '=', res.project_id)])
            res.count_job_cons = job

    def action_job_cons(self):
        return {
            'name': ("BOQ"),
            'view_mode': 'tree,form',
            'res_model': 'job.estimate',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': [('lead_id', '=', self.id), ('project_id.name', '=', self.project_id)],
        }

    def _compute_count_contract_cons(self):
        for res in self:
            contract = self.env['sale.order.const'].search_count([('opportunity_id', '=', res.id), ('project_id.name', '=', res.project_id), ('state', 'in', ('sale','done'))])
            res.count_contract_cons = contract

    def action_contract_cons(self):
        return {
            'name': ("Contracts"),
            'view_mode': 'tree,form',
            'res_model': 'sale.order.const',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'domain': [('opportunity_id', '=', self.id), ('project_id.name', '=', self.project_id), ('state', 'in', ('sale','done'))],
        }
    
    def action_project(self):
        project = self.env['project.project'].search([('lead_id', '=', self.id), ('name', '=', self.project_id)],limit=1)
        context="{'form_view_ref': 'equip3_construction_masterdata.edit_project', 'is_sale_project':True}"
        action = project.get_formview_action(context)
        return action
    
    def _prepare_vals(self, record, list_project, project, short_name, customer, list_sales, team, director, branch):
        return {
            'name': project,
            'project_short_name': short_name,
            'project_scope_ids': list_project,
            'partner_id': customer,
            'sales_person_id' : [(6, 0, [v.id for v in list_sales])],
            'sales_staff' : [(6, 0, [v.id for v in list_sales])],
            'sales_team' : team,
            'project_director': director,
            'branch_id': branch,
            'department_type': 'project',
            'lead_id': record.id
        }

    @api.model
    def create(self, vals):
        res = super(OpportunityDetails, self).create(vals)
    
        list_project = []
        list_sales = []
        for record in self:
            project = False
            for crm_line in record.project_scope_ids:
                list_project.append(
                    (0, 0, {'project_scope': crm_line.project_scope.id, 'description': crm_line.scope_description})
                )
            
            for sales in record.salesperson_lines:
                list_sales.append(sales.salesperson_id)
                
            project = record.project_id
            short_name = record.project_short_name
            customer = record.partner_id.id
            team = record.team_id.id
            director = record.env.user.id
            branch = record.branch_id.id

            vals = record._prepare_vals(record, list_project, project, short_name, customer, list_sales, team, director, branch)

            project_exist = self.env['project.project'].search([('lead_id', '=', record.id)],limit=1)
            if record.project_id:
                if not project_exist:
                    project = self.env['project.project'].create(vals)

        return res

    def write(self, vals):
        res = super(OpportunityDetails, self).write(vals)
        
        # Project Scope on Edit
        for rec in self:
            project_exist = self.env['project.project'].search([('lead_id', '=', rec.id)],limit=1)

            list_project = []
            list_sales = []
            for crm_line in rec.project_scope_ids:
                list_project.append(
                    (0, 0, {'project_scope': crm_line.project_scope.id, 
                            'description': crm_line.scope_description})
                )
            
            for sales in rec.salesperson_lines:
                list_sales.append(sales.salesperson_id)
            
            project = rec.project_id
            short_name = rec.project_short_name
            customer = rec.partner_id.id
            team = rec.team_id.id
            director = rec.env.user.id
            branch = rec.branch_id.id

            if project_exist:
                for pro in project_exist:
                    if pro.primary_states == 'draft':
                        pro.project_scope_ids = [(5, 0, 0)]
                        pro.project_section_ids = [(5, 0, 0)]
                        pro.write({'name': project,
                                   'partner_id': customer,
                                   'project_short_name': short_name,
                                   'project_scope_ids': list_project,
                                   'sales_person_id' : [(6, 0, [v.id for v in list_sales])],
                                   'sales_staff' : [(6, 0, [v.id for v in list_sales])],
                                   'sales_team' : team,
                                   'branch_id': branch
                                  })
                        
                        # for warehouse in pro.warehouse_address:
                        #     warehouse.write({'name': project,
                        #                      'code': short_name,
                        #                     })
                            
                        for analytic in pro.analytic_account_id:
                            analytic.write({'name': project,
                                            'partner_id': customer,
                                            })
                    
                    # else:
                    #     raise ValidationError(_('Cannot edit this opportunity because the project of this opportunity not in state draft anymore')) 
            
            else:
                
                vals = rec._prepare_vals(rec, list_project, project, short_name, customer, list_sales, team, director, branch)
                if rec.project_id:
                    project = self.env['project.project'].create(vals)
                            
        return res
    

    def _compute_job_count(self): 
        for rec in self:
            rec.job_count = len(self.env['job.estimate'].search([('lead_id', '=', self.id)]))

    def _compute_projects_count(self):
        for rec in self:
            rec.project_count = self.env['project.project'].search_count([('lead_id', '=', rec.id), ('name', '=', rec.project_id)])

    job_count = fields.Integer('Job Count', compute='_compute_job_count')
    project_count = fields.Integer('Project Count', compute='_compute_projects_count')
    project_short_name = fields.Char(string="Short Name", size=5, track_visibility='onchange')
    is_project = fields.Boolean(string="Is Project", compute='_get_is_project')

    @api.depends('project_id') 
    def _get_is_project(self):
        for rec in self:
            if rec.project_id:
                rec.is_project = True
            else:
                rec.is_project = False

    def action_set_won_rainbowman(self):
        list_project = []
        list_sales = []
        for record in self:

            for crm_line in record.project_scope_ids:
                list_project.append(
                    (0, 0, {'project_scope': crm_line.project_scope.id, 'description': crm_line.scope_description}))

            for sales in record.salesperson_lines:
                list_sales.append(sales.salesperson_id)

            project = record.project_id
            short_name = record.project_short_name
            customer = record.partner_id.id
            team = record.team_id.id
            director = record.env.user.id
            branch = record.branch_id.id

            vals = record._prepare_vals(record, list_project, project, short_name, customer, list_sales, team, director, branch)

            res = super(OpportunityDetails, self).action_set_won_rainbowman()
            project_exist = self.env['project.project'].search([('lead_id', '=', record.id)],limit=1)
            if record.project_id:
                if record.partner_id.id == False:
                    raise ValidationError(_('If you want to confirm won, customer must be filled')) 
                
                if not project_exist:
                    new_project = self.env['project.project'].create(vals)
                    new_project.primary_states = 'progress'
                    
                else:
                    project_exist.primary_states = 'progress'
                    project_exist.partner_id = customer

            return res

    def action_job_new(self):
        list_project = []
        list_sales = []
        for record in self:
            for crm_line in record.project_scope_ids:
                list_project.append(
                    (0, 0, {'project_scope': crm_line.project_scope.id, 'description': crm_line.scope_description})
                )
            
            for sales in record.salesperson_lines:
                list_sales.append(sales.salesperson_id)
                
            project = record.project_id
            short_name = record.project_short_name
            customer = record.partner_id.id
            team = record.team_id.id
            director = record.env.user.id
            branch = record.branch_id.id

            vals = record._prepare_vals(record, list_project, project, short_name, customer, list_sales, team, director, branch)

            project_exist = self.env['project.project'].search([('lead_id', '=', record.id)],limit=1)
            if project:
                if not project_exist:
                    project = self.env['project.project'].create(vals)
                else:
                    project = self.env['project.project'].search([('lead_id', '=', record.id)], limit=1)
                    if project:
                        if project.primary_states == 'lost':
                            raise ValidationError(_('Cannot create a BOQ form project lost'))
                        else: 
                            # project.partner_id = customer
                            # convert above code to query
                            self.env.cr.execute("UPDATE project_project SET partner_id = %s WHERE lead_id = %s", (customer, record.id))
            else:
                raise ValidationError(_('Cannot create a BOQ, please fill the project name first')) 

            action = self.env["ir.actions.actions"]._for_xml_id(
                "equip3_construction_sales_operation.action_job_estimate_new")

            action['context'] = {
                'default_lead_id': record.id,
                'default_partner_id': record.partner_id.id,
                'default_project_id': project.id,
            }
            
            return action

    def action_job_estimate(self):
        action = self.env["ir.actions.actions"]._for_xml_id(
            "bi_job_cost_estimate_customer.action_job_estimate")
        job_ids = self.env['job.estimate'].search([('lead_id', '=', self.id)])
        action['domain'] = [('id', 'in', job_ids.ids)]

        return action

    def action_project_counts(self):
        action = self.env["ir.actions.actions"]._for_xml_id(
            "project.open_view_project_all")
        projs_ids = self.env['project.project'].search([('lead_id', '=', self.id)])
        action['domain'] = [('id', 'in', projs_ids.ids)]
        return action

    def _get_access_value(self):
        project_names = []
        for rec in self:
            for allowed_project in rec.env.user.project_ids:
                project_names.append(allowed_project.name)

            if len(project_names)>0:
                if rec.project_id in project_names:
                    return True
                else:
                    return False
            else:
                return False
            
    @api.constrains('project_scope_ids')
    def _check_exist_project_scope1(self):
        exist_scope_list1 = []
        for line1 in self.project_scope_ids:
            if line1.project_scope.id in exist_scope_list1:
                raise ValidationError(_('The Project Scope "%s" already exists. Please change this Project Scope.'%((line1.project_scope.name))))
            exist_scope_list1.append(line1.project_scope.id)
    
    @api.onchange('project_scope_ids')
    def _check_exist_project_scope2(self):
        exist_scope_list2 = []
        for line2 in self.project_scope_ids:
            if line2.project_scope.id in exist_scope_list2:
                raise ValidationError(_('The Project Scope "%s" already exists. Please change this Project Scope.'%((line2.project_scope.name))))
            exist_scope_list2.append(line2.project_scope.id)

    project_id = fields.Char(String='Project Name', tracking=True)
    project_scope_ids = fields.One2many('project.scope.line.ids', 'sequence', string='Project Scope', required=True,
                                    tracking=True, ondelete='cascade')
    is_allowed_access = fields.Boolean(String="Is Allowed Access", default = _get_access_value)


class ProjectScopeLine(models.Model):
    _name = 'project.scope.line.ids'
    _description = 'Project Scope Line'
    _order = 'sequence'

    sequence = fields.Integer(string="Sequence", default=0, readonly=True)
    name = fields.Char(String='Project Scope')
    project_scope = fields.Many2one('project.scope.line', string='Project Scope')
    scope_description = fields.Text(String='Description')
