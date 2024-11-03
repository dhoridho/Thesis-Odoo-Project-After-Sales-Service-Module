
from odoo import api , fields , models
from datetime import datetime, date


class AccountAssetAssets(models.Model):
    _inherit = "account.asset.asset"

    @api.depends('value', 'salvage_value', 'depreciation_line_ids.move_check', 'depreciation_line_ids.amount')
    def _amount_residual(self):
        res = super(AccountAssetAssets, self)._amount_residual()
        for rec in self:
            return_asset = self.env['return.of.assets'].search([('lot_id','in',self.serial_number_id.ids)])
            if return_asset:
                for asset in return_asset:
                    if asset.current_value != rec.asset_value_residual:
                        asset.current_value = rec.asset_value_residual
        return res

