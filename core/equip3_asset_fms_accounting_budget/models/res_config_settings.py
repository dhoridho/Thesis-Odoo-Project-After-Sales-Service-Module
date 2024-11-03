from odoo import _, api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    is_allow_asset_budget_config = fields.Boolean(string="Allow Asset Budget", config_parameter='equip3_asset_fms_accounting_budget.is_allow_asset_budget_config')
