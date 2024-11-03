from odoo import api, fields, models
from datetime import datetime

class AccountVoucher(models.Model):
    _inherit = 'account.pettycash.voucher.wizard'


    project_id = fields.Many2one ('project.project', string="Project")
    cost_sheet = fields.Many2one('job.cost.sheet', string='Cost Sheet', domain="[('project_id','=', project_id)]", force_save="1")
    project_budget = fields.Many2one('project.budget', 'Project Budget', force_save="1")

    @api.onchange('project_id')
    def _onchange_project(self):
        for rec in self:
            for proj in rec.project_id:
                rec.cost_sheet = rec.env['job.cost.sheet'].search([('project_id', '=', proj.id), ('state', '!=', 'cancelled')])

    @api.onchange('date', 'project_id')
    def _get_project_budget(self):
        for rec in self:
            Job_cost_sheet = rec.cost_sheet
            if rec.date and rec.project_id:
                schedule = datetime.strptime(str(self.date), "%Y-%m-%d")
                month_date = schedule.strftime("%B")
                if rec.project_id.budgeting_period == 'monthly':
                    data = rec.env['budget.period.line'].search([('month', '=', month_date),
                                                                ('line_project_ids', '=', Job_cost_sheet.project_id.id),], limit=1)
                    budget = rec.env['project.budget'].search([('project_id', '=', Job_cost_sheet.project_id.id),
                                                                ('cost_sheet', '=', Job_cost_sheet.id),
                                                                ('month', '=', data.id)], limit=1)
                    rec.project_budget = budget
                elif rec.project_id.budgeting_period == 'custom':
                    budget = rec.env['project.budget'].search([('project_id', '=', Job_cost_sheet.project_id.id),
                                                                ('cost_sheet', '=', Job_cost_sheet.id),
                                                                ('bd_start_date', '<=', rec.date),
                                                                ('bd_end_date', '>=', rec.date)], limit=1)
                    rec.project_budget = budget
                else:
                    pass

    
