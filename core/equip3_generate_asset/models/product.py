# -*- coding: utf-8 -*-

from odoo import api, fields, models,_


class ProductTemplate(models.Model):
    _inherit = "product.template"

    def get_asset_depreciation(self):
        self.update_asset_name('account.asset.asset')
        return {
            'type': 'ir.actions.act_window',
            'name': _('Asset Depreciation'),
            'res_model': 'account.asset.asset',
            'view_mode': 'tree,form',
            'domain': [('product_template_id', '=', self.id)]
        }

    def get_asset_control(self):
        # self.update_asset_name('maintenance.equipment')
        return {
            'type': 'ir.actions.act_window',
            'name': _('Asset Control'),
            'res_model': 'maintenance.equipment',
            'view_mode': 'tree,form',
            'domain': [('product_template_id', '=', self.id)]
        }

    def update_asset_name(self, model_name):
        for rec in self:
            acc_rec = self.env[model_name].sudo().search([('product_template_id', '=', rec.id)])
            if acc_rec:
                acc_rec.write({"name": rec.name})