from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError


class PurchaseRequisition(models.Model):
    _inherit = 'purchase.requisition'

    project_id = fields.Many2one('project.project', string='Project',domain=lambda self:[('company_id','=',self.env.company.id),('primary_states','=','progress')])
    cost_sheet_id = fields.Many2one('job.cost.sheet', string='Cost Sheet')
    project_budget_id = fields.Many2one('project.budget', string='Project Budget')
    budgeting_method = fields.Selection(related='project_id.budgeting_method', string='Budgeting Method')
    analytic_account_id = fields.Many2one(related='project_id.analytic_account_id', string='Analytic Account', readonly=True)
