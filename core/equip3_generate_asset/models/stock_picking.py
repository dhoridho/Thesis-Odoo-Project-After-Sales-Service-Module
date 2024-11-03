# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
import logging
from datetime import datetime, date, timedelta
_logger = logging.getLogger(__name__)

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _convert_to_asset(self):
        for move_line in self.move_line_ids:
            open_asset = move_line.product_id.asset_category_id.open_asset or False
            if move_line.product_id.type == 'asset' and open_asset:
                date = first_depreciation_manual_date = fields.Date.context_today(self)
                asset_category = move_line.product_id.asset_category_id

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

                if move_line.product_id.asset_entry_perqty:
                    for qty in list(range(int(move_line.qty_done))):
                        asset_vals = {
                            "name": move_line.product_id.name,
                            "category_id": move_line.product_id.asset_category_id.id,
                            "value": move_line.move_id.purchase_line_id.price_unit,
                            "partner_id": self.partner_id.id,
                            "prorata": asset_category.prorata,
                            "first_depreciation_manual_date": first_depreciation_manual_date,
                            "cut_off_asset_date": asset_category.cut_off_asset_date,
                            "product_id": move_line.product_id.id,
                            "branch_id": self.branch_id.id,
                            "serial_number_id": move_line.lot_id.id,
                            "method_number": asset_category.method_number,
                            "method_period": asset_category.method_period,
                        }
                        if move_line.product_id.product_tmpl_id.type == 'asset':
                            asset_vals['product_template_id'] = move_line.product_id.product_tmpl_id.id
                        asset_values = self.env['account.asset.asset'].create(asset_vals).compute_depreciation_board()

                else:
                    asset_vals = {
                        "name": move_line.product_id.name,
                        "category_id": move_line.product_id.asset_category_id.id,
                        "value": move_line.qty_done * move_line.move_id.purchase_line_id.price_unit,
                        "partner_id": self.partner_id.id,
                        "prorata": asset_category.prorata,
                        "first_depreciation_manual_date": first_depreciation_manual_date,
                        "cut_off_asset_date": asset_category.cut_off_asset_date,
                        "product_id": move_line.product_id.id,
                        "branch_id": self.branch_id.id,
                        "serial_number_id": move_line.lot_id.id,
                        "method_number": asset_category.method_number,
                        "method_period": asset_category.method_period,
                        
                    }
                    if move_line.product_id.product_tmpl_id.type == 'asset':
                        asset_vals['product_template_id'] = move_line.product_id.product_tmpl_id.id
                    asset_values = self.env['account.asset.asset'].create(asset_vals).compute_depreciation_board()