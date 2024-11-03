from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
import logging
from datetime import datetime, date, timedelta

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _action_done(self):
        res = super(StockPicking, self)._action_done()
        AccountMove = self.env['account.move']
        CurrencyRate = self.env['res.currency.rate']
        create_asset = False

        for picking in self:
            if picking.move_line_ids:
                date_today = str(date.today())
                purchase_order = self.env['purchase.order'].search([('name', '=', picking.group_id.name), ('is_assets_orders', '=', 'True')], limit=1)

                if not purchase_order:
                    continue

                create_asset = True
                order_lines = purchase_order.order_line
                current_currency = purchase_order.currency_id
                company_currency = purchase_order.company_id.currency_id

                # Fetch the latest currency rate
                currency_rate_record = CurrencyRate.search([('currency_id', '=', current_currency.id)], order='id desc', limit=1)
                conversion_rate = currency_rate_record.conversion if currency_rate_record else 1.0

                # Optimize the move line processing
                for move_line in picking.move_line_ids.filtered(lambda l: l.product_id.categ_id.property_valuation == 'real_time' and l.product_id.type == 'asset'):
                    matched_order_lines = order_lines.filtered(lambda ol: ol.product_id == move_line.product_id and ol.name == move_line.move_id.name)

                    for order_line in matched_order_lines:

                        price_unit = order_line.price_unit * move_line.qty_done
                        price_rate = price_unit * conversion_rate if order_line.currency_id != company_currency else price_unit
                        amount_currency = order_line.price_subtotal

                        line_ids = [
                            {
                                'date': date_today,
                                'name': f"{picking.name} {move_line.product_id.name} {date_today}",
                                'account_id': move_line.product_id.categ_id.property_stock_valuation_account_id.id,
                                'analytic_tag_ids': [(6, 0, move_line.move_id.analytic_account_group_ids.ids)],
                                'debit': max(price_rate, 0.0),
                                'credit': -min(price_rate, 0.0),
                                'amount_currency': amount_currency,
                                'currency_id': order_line.currency_id.id,
                                'purchase_line_id': order_line.id,
                                'product_id': order_line.product_id.id
                            },
                            {
                                'date': date_today,
                                'name': f"{picking.name} {move_line.product_id.name} {date_today}",
                                'account_id': move_line.product_id.categ_id.property_stock_account_input_categ_id.id,
                                'analytic_tag_ids': [(6, 0, move_line.move_id.analytic_account_group_ids.ids)],
                                'debit': -min(price_rate, 0.0),
                                'credit': max(price_rate, 0.0),
                                'amount_currency': -amount_currency,
                                'currency_id': order_line.currency_id.id,
                                'purchase_line_id': order_line.id,
                                'product_id': order_line.product_id.id
                            }
                        ]

                        move_vals = {
                            'name': '/',
                            'currency_id': current_currency.id,
                            'date': date_today,
                            'ref': f"{picking.name} {move_line.product_id.name}",
                            'journal_id': move_line.product_id.categ_id.property_stock_journal.id,
                            'branch_id': purchase_order.branch_id.id,
                            'analytic_group_ids': [(6, 0, move_line.move_id.analytic_account_group_ids.ids)],
                            'line_ids': line_ids
                        }
                        created_move = AccountMove.create(move_vals)
                        created_move.post()

        if create_asset:
            # Call `_convert_to_asset`.
            self._convert_to_asset()

        return res

    def _convert_to_asset(self):
        for move_line in self.move_line_ids:
            if move_line.product_id.type == 'asset':
                date = first_depreciation_manual_date = fields.Date.context_today(self)
                asset_category = move_line.product_id.asset_category_id

                date_list = str(date).split('-')
                cut_off_date_str = len(str(asset_category.cut_off_asset_date))>=2 and str(asset_category.cut_off_asset_date) or '0' + str(asset_category.cut_off_asset_date)
                cut_off_date = '%s-%s-%s'%(date_list[0], date_list[1], cut_off_date_str)
                if not asset_category.prorata and str(date) > cut_off_date:
                    month = (int(date_list[1]) < 10 and '0%s'%(int(date_list[1])+1))\
                            or (int(date_list[1]) >= 10 and int(date_list[1]) < 12 and str(int(date_list[1])+1))\
                            or '01'
                    year = int(date_list[1]) < 12 and str(int(date_list[0])) or str(int(date_list[0])+1)
                    first_depreciation_manual_date = '%s-%s-%s'%(year, month, '01')
                elif not asset_category.prorata and str(date) <= cut_off_date:
                    first_depreciation_manual_date = '%s-%s-%s'%(date_list[0], date_list[1], '01')
                else:
                    first_depreciation_manual_date = date

                value = move_line.move_id.purchase_line_id
                price_unit = value.price_unit
                current_currency = value.currency_id
                company_currency = value.company_id.currency_id
                currency_rate = self.env['res.currency.rate'].search([('currency_id', '=', current_currency.id)], order='id desc', limit=1)
                rates = currency_rate.conversion
                
                if company_currency != current_currency:
                    price_unit = price_unit * rates

                price_done = move_line.qty_done * price_unit

                if move_line.product_id.asset_entry_perqty:
                    for qty in list(range(int(move_line.qty_done))):
                        asset_vals = {
                                "name" : move_line.product_id.name,
                                "category_id" : move_line.product_id.asset_category_id.id,
                                "value" :  price_unit,
                                "partner_id" : self.partner_id.id,
                                "prorata" : asset_category.prorata,
                                "first_depreciation_manual_date" : first_depreciation_manual_date,
                                "cut_off_asset_date" : asset_category.cut_off_asset_date,
                                "product_id":move_line.product_id.id,
                                "branch_id":self.branch_id.id,
                                "po_ref": self.origin,
                                "analytic_tag_ids": [(6, 0, self.analytic_account_group_ids._origin.ids)],
                            }
                        self.env['account.asset.asset'].create(asset_vals).compute_depreciation_board()
                else:
                    asset_vals = {
                        "name": move_line.product_id.name,
                        "category_id" : move_line.product_id.asset_category_id.id,
                        "value" :  price_done,
                        "partner_id" : self.partner_id.id,
                        "prorata" : asset_category.prorata,
                        "first_depreciation_manual_date" : first_depreciation_manual_date,
                        "cut_off_asset_date" : asset_category.cut_off_asset_date,
                        "product_id": move_line.product_id.id,
                        "branch_id":self.branch_id.id,
                        "po_ref": self.origin,
                        "analytic_tag_ids": [(6, 0, self.analytic_account_group_ids._origin.ids)],
                    }

                    self.env['account.asset.asset'].create(asset_vals).compute_depreciation_board()
