from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

class MaintenanceRepairOrder(models.Model):
    _inherit = 'maintenance.repair.order'

    @api.model
    def _is_allow_asset_budget(self):
        return eval(self.env['ir.config_parameter'].sudo().get_param('equip3_asset_fms_accounting_budget.is_allow_asset_budget_config', 'False'))
    
    is_allow_asset_budget = fields.Boolean(string='Is Allow Asset Budget', default=_is_allow_asset_budget)
    
    def _check_asset_budget_amount(self):
        for task in self.task_check_list_ids:
            if task.used_budget > task.remaining_budget:
                raise ValidationError('Cannot proceed. The used budget is greater than the remaining budget!')

    # def state_done(self):
    #     res = super(MaintenanceRepairOrder, self).state_done()
    #     is_allow_asset_budget = self._is_allow_asset_budget()
    #     if is_allow_asset_budget:
    #         self._check_asset_budget_amount()
    #     return res