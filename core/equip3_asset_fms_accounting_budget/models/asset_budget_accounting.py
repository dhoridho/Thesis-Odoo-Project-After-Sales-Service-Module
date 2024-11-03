from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

class AssetBudgetAccountingLine(models.Model):
    _inherit = 'asset.budget.accounting.line'
    
    def is_allow_asset_budget(self):
        return eval(self.env['ir.config_parameter'].sudo().get_param('equip3_asset_fms_accounting_budget.is_allow_asset_budget_config', 'False'))

    @api.depends('budget_amount', 'used_amount')
    def _compute_remaining_amount(self):
        is_allow_asset_budget = self.is_allow_asset_budget()
        
        for line in self:
            if line:
                if not is_allow_asset_budget:
                    line.remaining_amount = line.budget_amount
                else:
                    line.remaining_amount = line.budget_amount - line.used_amount if line.budget_amount > line.used_amount else 0
                
    @api.depends('asset_budget_id', 'asset_budgetary_position_id', 'account_tag_ids', 'date_from', 'date_to')
    def _compute_used_amount(self):
        is_allow_asset_budget = self.is_allow_asset_budget()
        if not is_allow_asset_budget:
            for record in self:
                record.used_amount = 0.0
        else:
            return super(AssetBudgetAccountingLine, self)._compute_used_amount()
            
            
    @api.depends('planned_amount', 'carry_over_amount', 'transfer_amount', 'change_request_amount')
    def _compute_budget_amount(self):
        is_allow_asset_budget = eval(self.env['ir.config_parameter'].sudo().get_param('equip3_asset_fms_accounting_budget.is_allow_asset_budget_config', 'False'))
        for line in self:
            line.budget_amount = 0
            if is_allow_asset_budget:
                line.budget_amount = line.planned_amount + line.carry_over_amount + line.transfer_amount + line.change_request_amount