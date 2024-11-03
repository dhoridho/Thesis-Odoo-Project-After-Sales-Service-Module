from odoo import models, fields, api


class MrpWorkcenter(models.Model):
    _inherit = 'mrp.workcenter'

    type = fields.Selection([
        ('asset', 'Asset'),
        ('non_asset', 'Non asset'),
    ], string='Type', default='non_asset')
    
    asset_id = fields.Many2one('account.asset.asset', 'Asset Name',)
    
    @api.onchange('type', 'asset_id')
    def _onchange_type(self):
        if self.type == 'asset' and self.asset_id:
            self.name = self.asset_id.name


class MrpWorkcenterLabor(models.Model):
    _inherit = 'mrp.workcenter.labor'

    cost_per_hour = fields.Float(string='Cost per Hour')
