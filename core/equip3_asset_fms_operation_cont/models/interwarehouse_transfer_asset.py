from odoo import models, fields, api, _


class InterwarehouseTransferAsset(models.Model):
    _inherit = "stock.picking"
    
    is_asset_created = fields.Boolean(string='Create Asset', default=False, copy=False)
    is_asset_product = fields.Boolean(string='Asset Product', default=False, compute='_compute_is_asset_product')
    
    @api.depends('move_lines')
    def _compute_is_asset_product(self):
        self.is_asset_product = False
        for rec in self.move_lines:
            if rec.product_id.type == 'asset':
                self.is_asset_product = True
                break
            
    
    def create_assets(self):
        view_id = self.env.ref('equip3_asset_fms_operation_cont.create_asset_wizard_view_form')
        if view_id:
            return {
                'name': _('Create Asset'),
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'create.asset.wizard',
                'views': [(view_id.id, 'form')],
                'view_id': view_id.id,
                'context': {'default_picking_id': self.id},
                'target': 'new',
            }