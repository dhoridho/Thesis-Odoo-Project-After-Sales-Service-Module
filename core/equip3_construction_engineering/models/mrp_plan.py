from odoo import models, fields, api


class MrpPlan(models.Model):
    _inherit = 'mrp.plan'

    project_id = fields.Many2one('project.project', string='Project', domain="[('primary_states','=', 'progress'), ('construction_type','=', 'engineering')]")
    contract = fields.Many2one('sale.order.const', string="Contract", domain="[('project_id','=', project_id)]")
    cost_sheet = fields.Many2one('job.cost.sheet', string='Cost Sheet', force_save="1")
    project_budget = fields.Many2one('project.budget', string='Project Budget', domain="[('project_id','=', project_id)]", force_save="1")
    budgeting_method = fields.Selection([
        ('product_budget', 'Based on Product Budget'),
        ('gop_budget', 'Based on Group of Product Budget'),
        ('budget_type', 'Based on Budget Type'),
        ('total_budget', 'Based on Total Budget')], string='Budgeting Method', related='project_id.budgeting_method', store = True)

    @api.onchange('project_id')
    def _onchange_project(self):
        for rec in self:
            for proj in rec.project_id:
                self.cost_sheet = rec.env['job.cost.sheet'].search([('project_id', '=', proj.id), ('state', '!=', 'cancelled')])
                self.analytic_tag_ids = proj.analytic_idz

    def action_confirm(self):
        res = super(MrpPlan, self).action_confirm()
        for mrp in self.mrp_order_ids:
            job_id = self.env['project.task'].search([('project_id', '=', mrp.project_id.id), ('sale_order', '=', mrp.contract.id), ('production_id', '=', mrp.id)], limit=1)
            pic = mrp.user_id
            start_plan = mrp.date_planned_start
            end_plan = mrp.date_planned_finished
            job_id.write({'assigned_to': pic.id,
                          'planned_start_date': start_plan,
                          'planned_end_date': end_plan})
        return res
        
        