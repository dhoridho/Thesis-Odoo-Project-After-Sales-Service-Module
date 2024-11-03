from odoo import _, api, fields, models
from datetime import datetime
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta


class CostSheetValidationWizard(models.TransientModel):
    _name = 'cost.sheet.validation.wizard'
    _description = 'Cost Sheet Validation Wizard'

    cost_sheet_id = fields.Many2one('job.cost.sheet', string='Cost Sheet')
    is_approval_matrix = fields.Boolean(string='Is Approval Matrix', default=False)
    warning_message = fields.Text(string='Warning Message', readonly=True, compute='_compute_warning_message')

    @api.depends('cost_sheet_id')
    def _compute_warning_message(self):
        for rec in self:
            rec.warning_message = False
            if rec.cost_sheet_id:
                rec.warning_message = _('The cost amount is over the contract amount by %s. Are you sure you want to continue?') % (rec.cost_sheet_id.amount_total - rec.cost_sheet_id.amount_contract_total)

    def action_confirm(self):
        for rec in self:
            if rec.is_approval_matrix:
                return rec.cost_sheet_id.request_approval(is_continue=True)
            return rec.cost_sheet_id.action_in_progress(is_continue=True)