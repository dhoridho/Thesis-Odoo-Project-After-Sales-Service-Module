from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class MaintenanceWorkOrder(models.Model):
    _inherit = 'maintenance.work.order'
    
    @api.model
    def _is_allow_asset_budget(self):
        return eval(self.env['ir.config_parameter'].sudo().get_param('equip3_asset_fms_accounting_budget.is_allow_asset_budget_config', 'False'))
    
    is_allow_asset_budget = fields.Boolean(string='Is Allow Asset Budget', default=_is_allow_asset_budget)
    

    def _check_asset_budget_amount_mwo(self):
        is_allow_asset_budget = self.is_allow_asset_budget
        if not is_allow_asset_budget:
            return
        for task in self.task_check_list_ids:
            if task.used_budget > task.remaining_budget:
                raise ValidationError('Cannot proceed. The used budget is greater than the remaining budget!')

    
    # def state_done(self):
    #     res = super(MaintenanceWorkOrder, self).state_done()
    #     is_allow_asset_budget = self._is_allow_asset_budget()
    #     if is_allow_asset_budget:
    #         self._check_asset_budget_amount_mwo()
    #     return res