from odoo import models, fields, api, _
from odoo.exceptions import UserError


class MRPProduction(models.Model):
    _inherit = 'mrp.production'

    project_id = fields.Many2one('project.project', string='Project', domain="[('primary_states','=', 'progress'), ('construction_type','=', 'engineering')]")
    contract = fields.Many2one('sale.order.const', string="Contract", domain="[('project_id','=', project_id)]")
    cost_sheet = fields.Many2one('job.cost.sheet', string='Cost Sheet', force_save="1")
    project_budget = fields.Many2one('project.budget', string='Periodical Budget', domain="[('project_id','=', project_id)]", force_save="1")
    budgeting_method = fields.Selection([
        ('product_budget', 'Based on Product Budget'),
        ('gop_budget', 'Based on Group of Product Budget'),
        ('budget_type', 'Based on Budget Type'),
        ('total_budget', 'Based on Total Budget')], string='Budgeting Method', related='project_id.budgeting_method', store = True)
    job_order = fields.Many2one('project.task', string='Job Order', compute='_get_job_order')

    project_scope = fields.Many2one('project.scope.line', string='Project Scope',
                                    domain="[('project_id','=', self.project_id)]")
    section_name = fields.Many2one('section.line', string='Section',
                                   domain="[('project_scope','=', project_scope), ('project_id','=', self.project_id)]")
    variable_ref = fields.Many2one('variable.template', string='Variable')
    final_finish_good_id = fields.Many2one('product.product', 'Final Finished Goods')
    cs_manufacture_id = fields.Many2one('cost.manufacture.line', 'CS Manufacture ID')
    bd_manufacture_id = fields.Many2one('budget.manufacture.line', 'BD Manufacture ID')

    def _get_job_order(self):
        job_id = False
        job_id = self.env['project.task'].search([('project_id', '=', self.project_id.id), ('sale_order', '=', self.contract.id), ('production_id', '=', self.id)], limit=1)
        self.job_order = job_id

    def action_job_order_cons(self):
        action = self.job_order.get_formview_action()
        action['domain'] = [('id', '=', self.job_order.id)]
        return action

    @api.onchange('project_id')
    def _onchange_project(self):
        for rec in self:
            for proj in rec.project_id:
                self.cost_sheet = rec.env['job.cost.sheet'].search([('project_id', '=', proj.id), ('state', '!=', 'cancelled')])
                self.analytic_tag_ids = proj.analytic_idz

    def action_confirm(self):
        res = super(MRPProduction, self).action_confirm()
        for data in self:
            job_id = self.env['project.task'].search([('project_id', '=', data.project_id.id), ('sale_order', '=', data.contract.id), ('production_id', '=', data.id)], limit=1)
            pic = data.user_id
            start_plan = data.date_planned_start
            end_plan = data.date_planned_finished
            job_id.write({'assigned_to': pic.id,
                          'planned_start_date': start_plan,
                          'planned_end_date': end_plan})
        return res