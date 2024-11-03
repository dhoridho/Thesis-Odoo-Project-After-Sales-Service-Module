from odoo import api, fields, models, tools, _


class AssetModify(models.TransientModel):
    _inherit = 'asset.modify'


    def modify(self):
        res = super(AssetModify, self).modify()
        asset_id = self.env.context.get('active_id', False)
        asset = self.env['account.asset.asset'].browse(asset_id)
        for line in asset.depreciation_line_ids:
            if not line.move_check:
                line.create_move()

        return res