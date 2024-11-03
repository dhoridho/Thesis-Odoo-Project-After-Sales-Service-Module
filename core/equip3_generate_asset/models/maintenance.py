# -*- coding: utf-8 -*-

from odoo import api, fields, models,_
from datetime import date, datetime, timedelta



class MaintenanceEquipment(models.Model):
    _inherit = 'maintenance.equipment'

    product_template_id = fields.Many2one('product.template', string="Product")
    lot_id = fields.Many2one('stock.production.lot')

    def create_account_asset(self):
        current_date = fields.Date.today()
        category_id = self.env['account.asset.category'].search([('type', '=', 'purchase')], limit=1)
        vals = {
            'name' : self.name,
            'company_id' : self.company_id.id,
            'date' : current_date,
            'first_depreciation_manual_date' : current_date,
            'equipment_id' : self.id,
            'value' : self.asset_value,
            'branch_id' : self.branch_id.id,
            'product_template_id': self.product_template_id.id,
            'serial_number_id': self.lot_id.id,
            'partner_id': self.owner.id,
        }

        if category_id:
            vals['category_id'] = category_id.id
            
        context = self._context
        if context.get('active_model') == 'stock.picking':
            
            date = first_depreciation_manual_date = fields.Date.context_today(self)
            asset_category = self.product_template_id.asset_category_id

            date_list = str(date).split('-')
            cut_off_date_str = len(str(asset_category.cut_off_asset_date)) >= 2 and str(
                asset_category.cut_off_asset_date) or '0' + str(asset_category.cut_off_asset_date)
            cut_off_date = '%s-%s-%s' % (date_list[0], date_list[1], cut_off_date_str)
            if not asset_category.prorata and str(date) > cut_off_date:
                month = (int(date_list[1]) < 10 and '0%s' % (int(date_list[1]) + 1)) \
                        or (int(date_list[1]) >= 10 and int(date_list[1]) < 12 and str(int(date_list[1]) + 1)) \
                        or '01'
                year = int(date_list[1]) < 12 and str(int(date_list[0])) or str(int(date_list[0]) + 1)
                first_depreciation_manual_date = '%s-%s-%s' % (year, month, '01')
            elif not asset_category.prorata and str(date) <= cut_off_date:
                first_depreciation_manual_date = '%s-%s-%s' % (date_list[0], date_list[1], '01')
            else:
                first_depreciation_manual_date = date
            
            vals['first_depreciation_manual_date'] = first_depreciation_manual_date
            vals['category_id'] = self.product_template_id.asset_category_id.id
            vals['prorata'] = self.product_template_id.asset_category_id.prorata
            vals['cut_off_asset_date'] = self.product_template_id.asset_category_id.cut_off_asset_date
            vals['method_number'] = self.product_template_id.asset_category_id.method_number
            vals['method_period'] = self.product_template_id.asset_category_id.method_period
            print('➡ vals:', vals)

        open_asset = self.product_template_id.asset_category_id.open_asset or False
        if not open_asset:
            asset_id = self.env['account.asset.asset'].create(vals)
            asset_id.compute_depreciation_board()
            self.account_asset_id = asset_id.id