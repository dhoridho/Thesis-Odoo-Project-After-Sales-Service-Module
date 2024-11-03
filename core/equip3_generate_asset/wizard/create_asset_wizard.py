# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class CreateAssetWizard(models.TransientModel):
    _inherit = "create.asset.wizard"

    def _create_main_asset(self, line, asset_parts_ids):
        res = super(CreateAssetWizard, self)._create_main_asset(line, asset_parts_ids)
        if line.product_id:
            res.product_template_id = line.product_id.product_tmpl_id
        return res

    # def create_asset(self):
    #     self._check_create_asset_ids()
    #     if self.create_asset_ids:
    #         self.inventory_id.is_asset_created = True
    #         equip = self.env['maintenance.equipment']
    #         try:
    #             for line in self.create_asset_ids:
    #                 asset_parts_ids = []
    #                 for parts in line.part_sn_ids:
    #                     asset_parts = self.env['maintenance.equipment'].create({
    #                         'name': parts.asset_part_id.name,
    #                         'serial_no': parts.sn,
    #                         'category_id': parts.category_id.id,
    #                         'branch_id': parts.parts_fill_id.branch_id.id,
    #                         'vehicle_checkbox': False,
    #                         'owner': parts.parts_fill_id.owner.id,
    #                         'fac_area': parts.parts_fill_id.fac_area.id,
    #                         'held_by_id': parts.parts_fill_id.held_by_id.id,
    #                     })
    #                     asset_parts_ids.append(asset_parts)
    #                 asset_vals = {
    #                     'name': line.asset_name,
    #                     'category_id': line.asset_cat.id,
    #                     'owner' : line.owner.id,
    #                     'branch_id': line.branch_id.id,
    #                     'asset_value': line.account_asset_id.value,
    #                     'fac_area' : line.fac_area.id,
    #                     'serial_no': line.serial_number,
    #                     'effective_date': line.eff_date,
    #                     'vehicle_checkbox': True if line.asset_type == 'vehicle' else False,
    #                     'held_by_id': line.held_by_id.id,
    #                 }
    #                 if line.product_id.product_tmpl_id.type == 'asset':
    #                     asset_vals['product_template_id'] = line.product_id.product_tmpl_id.id
    #                 create_asset = equip.create(asset_vals)
    #                 if create_asset:
    #                     line.account_asset_id.equipment_id = create_asset.id
    #                     create_asset.account_asset_id.unlink()
    #                     create_asset.account_asset_id = line.account_asset_id.id
    #                     create_asset.vehicle_parts_ids = [(0, 0, {
    #                         'maintenance_equipment_id': create_asset.id,
    #                         'equipment_id': parts.id,
    #                         'serial_no': parts.serial_no,
    #                     }) for parts in asset_parts_ids]
    #             self.env['stock.picking'].browse(self.inventory_id.id).write({'is_asset_created': True})
    #         except Exception as e:
    #             # print("exception is occurred",e)
    #             raise Warning(e)
    #     return {'type': 'ir.actions.act_window_close'}