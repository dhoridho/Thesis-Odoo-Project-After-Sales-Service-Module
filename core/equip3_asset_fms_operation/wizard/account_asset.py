from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class AssetAssetSale(models.TransientModel):
    _inherit = 'asset.asset.sale'

    def confirm_asset_sale(self):
        res = super(AssetAssetSale, self).confirm_asset_sale()
        asset_id = False
        if self.env.context.get('asset_id'): 
            asset_id = self.env.context.get('asset_id')
            equip_obj = self.env['maintenance.equipment'].browse(self.env.context.get('active_id'))
            if equip_obj:
                equip_obj.state = 'sold'
        else:
            asset_id = self.env.context.get('active_id')

        asset = self.env['account.asset.asset'].browse(asset_id)
        move_obj = self.env['account.move']
        asset_moves = self.env['account.move'].search_count([('account_asset_id', '=', asset.id)])
        if asset_moves:
            # raise ValidationError("You can not create another asset sale journal entry while you have done it before!")
            return res

        if self.amount <= 0:
            raise ValidationError(_('To make a sale, the sale price must be filled in first'))
        company_id = asset.category_id.company_id
        draft_depreciation_lines = all((not line.move_id or (line.move_id and line.move_id.state == 'draft')) for line in asset.depreciation_line_ids)
        posted_depreciation_lines = any(line.move_id and line.move_id.state == 'posted' for line in asset.depreciation_line_ids)
        if not self.is_invoice:
            tax_amount = round((asset.value * self.tax_id.amount) / 100, 2)
            final_amount = asset.value + tax_amount
            if draft_depreciation_lines and not posted_depreciation_lines:
                difference_amount = self.amount - final_amount
                vals = {
                    'name': '/',
                    'ref': asset.name,
                    'account_asset_id': asset.id,
                    'date': fields.Date.context_today(self),
                    'journal_id': self.journal_id.id,
                    'branch_id': asset.branch_id.id,
                    'analytic_group_ids': [(6, 0, asset.analytic_tag_ids.ids)],
                }
                vals_debit_1 = {
                    'account_id' : self.journal_id.default_account_id.id,
                    'name' : asset.name,
                    'currency_id' : self.currency_id.id,
                    'debit' : self.amount,
                    'credit' : 0,
                    'date' : fields.Date.context_today(self),
                    'journal_id' : self.journal_id.id,
                    'analytic_tag_ids': [(6, 0, asset.analytic_tag_ids.ids)],
                }
                if self.amount < final_amount:
                    if not asset.category_id.account_sales_loss:
                        raise ValidationError("Please Add Account Sales Loss and try again!")
                    vals_debit_2 = {
                        'account_id' : asset.category_id.account_sales_loss.id,
                        'name' : asset.name,
                        'currency_id' : self.currency_id.id,
                        'debit' : abs(difference_amount),
                        'credit' : 0,
                        'date' : fields.Date.context_today(self),
                        'journal_id' : self.journal_id.id,
                        'analytic_tag_ids': [(6, 0, asset.analytic_tag_ids.ids)],
                    }
                vals_credit_1 = {
                    'debit' : 0,
                    'credit' : asset.value,
                    'name' : asset.name,
                    'date' : fields.Date.context_today(self),
                    'journal_id' : self.journal_id.id,
                    'account_id' : asset.category_id.account_asset_id.id,
                    'currency_id' : self.currency_id.id,
                    'analytic_tag_ids': [(6, 0, asset.analytic_tag_ids.ids)],
                }
                vals_credit_2 = {
                    'debit' : 0,
                    'credit' : tax_amount,
                    'name' : asset.name,
                    'date' : fields.Date.context_today(self),
                    'journal_id' : self.journal_id.id,
                    'account_id' : self.tax_id.invoice_repartition_line_ids[-1].account_id.id,
                    'currency_id' : self.currency_id.id,
                    'analytic_tag_ids': [(6, 0, asset.analytic_tag_ids.ids)],
                }
                if self.amount > final_amount:
                    if not asset.category_id.account_sales_profit:
                        raise ValidationError("Please Add Account Sales Profit and try again!")
                    vals_credit_3 = {
                        'account_id' : asset.category_id.account_sales_profit.id,
                        'name' : asset.name,
                        'currency_id' : self.currency_id.id,
                        'debit' : 0,
                        'credit' : abs(difference_amount),
                        'date' : fields.Date.context_today(self),
                        'journal_id' : self.journal_id.id,
                        'analytic_tag_ids': [(6, 0, asset.analytic_tag_ids.ids)],
                    }
                if self.amount == final_amount:
                    vals.update({'line_ids' : [
                        (0, 0, vals_debit_1),
                        (0, 0, vals_credit_1),
                        (0, 0, vals_credit_2),
                    ]})
                elif self.amount < final_amount:
                    vals.update({'line_ids' : [
                        (0, 0, vals_debit_1),
                        (0, 0, vals_debit_2),
                        (0, 0, vals_credit_1),
                        (0, 0, vals_credit_2),
                    ]})
                elif self.amount > final_amount:
                    vals.update({'line_ids' : [
                        (0, 0, vals_debit_1),
                        (0, 0, vals_credit_1),
                        (0, 0, vals_credit_2),
                        (0, 0, vals_credit_3),
                    ]})
                move_id = move_obj.create(vals)
            elif not draft_depreciation_lines and posted_depreciation_lines:
                posted_lines = asset.depreciation_line_ids.filtered(lambda r: r.move_id and r.move_id.state == 'posted')
                posted_amount = sum(posted_lines.mapped('amount'))
                sale_amount = (self.amount + posted_amount)
                difference_amount = sale_amount - final_amount
                vals = {
                    'name': '/',
                    'ref': asset.name,
                    'account_asset_id': asset.id,
                    'date': fields.Date.context_today(self),
                    'journal_id': self.journal_id.id,
                    'branch_id': asset.branch_id.id,
                    'analytic_group_ids': [(6, 0, asset.analytic_tag_ids.ids)],
                }
                vals_debit_1 = {
                    'account_id' : self.journal_id.default_account_id.id,
                    'name' : asset.name,
                    'currency_id' : self.currency_id.id,
                    'debit' : self.amount,
                    'credit' : 0,
                    'date' : fields.Date.context_today(self),
                    'journal_id' : self.journal_id.id,
                    'analytic_tag_ids': [(6, 0, asset.analytic_tag_ids.ids)],
                }
                vals_debit_2 = {
                    'account_id' : asset.category_id.account_depreciation_expense_id.id,
                    'name' : asset.name,
                    'currency_id' : self.currency_id.id,
                    'debit' : posted_amount,
                    'credit' : 0,
                    'date' : fields.Date.context_today(self),
                    'journal_id' : self.journal_id.id,
                    'analytic_tag_ids': [(6, 0, asset.analytic_tag_ids.ids)],
                }
                if sale_amount < final_amount:
                    if not asset.category_id.account_sales_loss:
                        raise ValidationError("Please Add Account Sales Loss and try again!")
                    vals_debit_3 = {
                        'account_id' : asset.category_id.account_sales_loss.id,
                        'name' : asset.name,
                        'currency_id' : self.currency_id.id,
                        'debit' : abs(difference_amount),
                        'credit' : 0,
                        'date' : fields.Date.context_today(self),
                        'journal_id' : self.journal_id.id,
                        'analytic_tag_ids': [(6, 0, asset.analytic_tag_ids.ids)],
                    }
                vals_credit_1 = {
                    'debit' : 0,
                    'credit' : asset.value,
                    'name' : asset.name,
                    'date' : fields.Date.context_today(self),
                    'journal_id' : self.journal_id.id,
                    'account_id' : asset.category_id.account_asset_id.id,
                    'currency_id' : self.currency_id.id,
                    'analytic_tag_ids': [(6, 0, asset.analytic_tag_ids.ids)],
                }
                vals_credit_2 = {
                    'debit' : 0,
                    'credit' : tax_amount,
                    'name' : asset.name,
                    'date' : fields.Date.context_today(self),
                    'journal_id' : self.journal_id.id,
                    'account_id' : self.tax_id.invoice_repartition_line_ids[-1].account_id.id,
                    'currency_id' : self.currency_id.id,
                    'analytic_tag_ids': [(6, 0, asset.analytic_tag_ids.ids)],
                }
                if sale_amount > final_amount:
                    if not asset.category_id.account_sales_profit:
                        raise ValidationError("Please Add Account Sales Profit and try again!")
                    vals_credit_3 = {
                        'account_id' : asset.category_id.account_sales_profit.id,
                        'name' : asset.name,
                        'currency_id' : self.currency_id.id,
                        'debit' : 0,
                        'credit' : abs(difference_amount),
                        'date' : fields.Date.context_today(self),
                        'journal_id' : self.journal_id.id,
                        'analytic_tag_ids': [(6, 0, asset.analytic_tag_ids.ids)],
                    }
                if sale_amount == final_amount:
                    vals.update({'line_ids' : [
                        (0, 0, vals_debit_1),
                        (0, 0, vals_debit_2),
                        (0, 0, vals_credit_1),
                        (0, 0, vals_credit_2),
                    ]})
                elif sale_amount < final_amount:
                    vals.update({'line_ids' : [
                        (0, 0, vals_debit_1),
                        (0, 0, vals_debit_2),
                        (0, 0, vals_debit_3),
                        (0, 0, vals_credit_1),
                        (0, 0, vals_credit_2),
                    ]})
                elif sale_amount > final_amount:
                    vals.update({'line_ids' : [
                        (0, 0, vals_debit_1),
                        (0, 0, vals_debit_2),
                        (0, 0, vals_credit_1),
                        (0, 0, vals_credit_2),
                        (0, 0, vals_credit_3),
                    ]})
                move_id = move_obj.create(vals)
        elif self.is_invoice:
            asset_value = asset.value
            if draft_depreciation_lines and not posted_depreciation_lines:
                difference_amount = self.amount - asset_value
                vals = {
                    'name': '/',
                    'ref': asset.name,
                    'account_asset_id': asset.id,
                    'date': fields.Date.context_today(self),
                    'journal_id': self.asset_journal_id.id,
                    'branch_id': asset.branch_id.id,
                    'analytic_group_ids': [(6, 0, asset.analytic_tag_ids.ids)],
                }
                vals_debit_1 = {
                    'account_id' : self.transit_account_id.id,
                    'name' : asset.name,
                    'currency_id' : self.currency_id.id,
                    'debit' : self.amount,
                    'credit' : 0,
                    'date' : fields.Date.context_today(self),
                    'journal_id': self.asset_journal_id.id,
                    'analytic_tag_ids': [(6, 0, asset.analytic_tag_ids.ids)],
                }
                if self.amount < asset_value:
                    if not asset.category_id.account_sales_loss:
                        raise ValidationError("Please Add Account Sales Loss and try again!")
                    vals_debit_2 = {
                        'account_id' : asset.category_id.account_sales_loss.id,
                        'name' : asset.name,
                        'currency_id' : self.currency_id.id,
                        'debit' : abs(difference_amount),
                        'credit' : 0,
                        'date' : fields.Date.context_today(self),
                        'journal_id': self.asset_journal_id.id,
                        'analytic_tag_ids': [(6, 0, asset.analytic_tag_ids.ids)],
                    }
                vals_credit_1 = {
                    'debit' : 0,
                    'credit' : asset_value,
                    'name' : asset.name,
                    'date' : fields.Date.context_today(self),
                    'journal_id': self.asset_journal_id.id,
                    'account_id' : asset.category_id.account_asset_id.id,
                    'currency_id' : self.currency_id.id,
                    'analytic_tag_ids': [(6, 0, asset.analytic_tag_ids.ids)],
                }
                if self.amount > asset_value:
                    if not asset.category_id.account_sales_profit:
                        raise ValidationError("Please Add Account Sales Profit and try again!")
                    vals_credit_2 = {
                        'account_id' : asset.category_id.account_sales_profit.id,
                        'name' : asset.name,
                        'currency_id' : self.currency_id.id,
                        'debit' : 0,
                        'credit' : abs(difference_amount),
                        'date' : fields.Date.context_today(self),
                        'journal_id': self.asset_journal_id.id,
                        'analytic_tag_ids': [(6, 0, asset.analytic_tag_ids.ids)],
                    }
                if self.amount == asset_value:
                    vals.update({'line_ids' : [
                        (0, 0, vals_debit_1),
                        (0, 0, vals_credit_1),
                    ]})
                elif self.amount < asset_value:
                    vals.update({'line_ids' : [
                        (0, 0, vals_debit_1),
                        (0, 0, vals_debit_2),
                        (0, 0, vals_credit_1),
                    ]})
                elif self.amount > asset_value:
                    vals.update({'line_ids' : [
                        (0, 0, vals_debit_1),
                        (0, 0, vals_credit_1),
                        (0, 0, vals_credit_2),
                    ]})
                move_id = move_obj.create(vals)
            elif not draft_depreciation_lines and posted_depreciation_lines:
                posted_lines = asset.depreciation_line_ids.filtered(lambda r: r.move_id and r.move_id.state == 'posted')
                posted_amount = sum(posted_lines.mapped('amount'))
                sale_amount = (self.amount + posted_amount)
                difference_amount = sale_amount - asset_value
                vals = {
                    'name': '/',
                    'ref': asset.name,
                    'account_asset_id': asset.id,
                    'date': fields.Date.context_today(self),
                    'journal_id': self.asset_journal_id.id,
                    'branch_id': asset.branch_id.id,
                    'analytic_group_ids': [(6, 0, asset.analytic_tag_ids.ids)],
                }
                vals_debit_1 = {
                    'account_id' : self.transit_account_id.id,
                    'name' : asset.name,
                    'currency_id' : self.currency_id.id,
                    'debit' : self.amount,
                    'credit' : 0,
                    'date' : fields.Date.context_today(self),
                    'journal_id' : self.asset_journal_id.id,
                    'analytic_tag_ids': [(6, 0, asset.analytic_tag_ids.ids)],
                }
                vals_debit_2 = {
                    'account_id' : asset.category_id.account_depreciation_expense_id.id,
                    # 'account_id' : asset.category_id.account_depreciation_id.id,
                    'name' : asset.name,
                    'currency_id' : self.currency_id.id,
                    'debit' : posted_amount,
                    'credit' : 0,
                    'date' : fields.Date.context_today(self),
                    'journal_id' : self.asset_journal_id.id,
                    'analytic_tag_ids': [(6, 0, asset.analytic_tag_ids.ids)],
                }
                if sale_amount < asset_value:
                    if not asset.category_id.account_sales_loss:
                        raise ValidationError("Please Add Account Sales Loss and try again!")
                    vals_debit_3 = {
                        'account_id' : asset.category_id.account_sales_loss.id,
                        'name' : asset.name,
                        'currency_id' : self.currency_id.id,
                        'debit' : abs(difference_amount),
                        'credit' : 0,
                        'date' : fields.Date.context_today(self),
                        'journal_id' : self.asset_journal_id.id,
                        'analytic_tag_ids': [(6, 0, asset.analytic_tag_ids.ids)],
                    }
                vals_credit_1 = {
                    'debit' : 0,
                    'credit' : asset_value,
                    'name' : asset.name,
                    'date' : fields.Date.context_today(self),
                    'journal_id' : self.asset_journal_id.id,
                    'account_id' : asset.category_id.account_asset_id.id,
                    'currency_id' : self.currency_id.id,
                    'analytic_tag_ids': [(6, 0, asset.analytic_tag_ids.ids)],
                }
                if sale_amount > asset_value:
                    if not asset.category_id.account_sales_profit:
                        raise ValidationError("Please Add Account Sales Profit and try again!")
                    vals_credit_2 = {
                        'account_id' : asset.category_id.account_sales_profit.id,
                        'name' : asset.name,
                        'currency_id' : self.currency_id.id,
                        'debit' : 0,
                        'credit' : abs(difference_amount),
                        'date' : fields.Date.context_today(self),
                        'journal_id' : self.asset_journal_id.id,
                        'analytic_tag_ids': [(6, 0, asset.analytic_tag_ids.ids)],
                    }
                if sale_amount == asset_value:
                    vals.update({'line_ids' : [
                        (0, 0, vals_debit_1),
                        (0, 0, vals_debit_2),
                        (0, 0, vals_credit_1),
                    ]})
                elif sale_amount < asset_value:
                    vals.update({'line_ids' : [
                        (0, 0, vals_debit_1),
                        (0, 0, vals_debit_2),
                        (0, 0, vals_debit_3),
                        (0, 0, vals_credit_1),
                    ]})
                elif sale_amount > asset_value:
                    vals.update({'line_ids' : [
                        (0, 0, vals_debit_1),
                        (0, 0, vals_debit_2),
                        (0, 0, vals_credit_1),
                        (0, 0, vals_credit_2),
                    ]})
                move_id = move_obj.create(vals)
            inv_vals = {
                'date': fields.Date.context_today(self),
                'invoice_date': fields.Date.context_today(self),
                'journal_id': self.asset_journal_id.id,
                'currency_id' : self.currency_id.id,
                'move_type' : 'out_invoice',
                'partner_id' :  self.partner_id.id,
                'account_asset_id': asset.id,
            }
            inv_line_vals = {
                'name' : asset.name,
                'quantity' : 1.00,
                'price_unit' : abs(self.amount),
                'account_id' : self.transit_account_id.id,
            }
            moveobj = self.env['account.move'].with_context(default_move_type='out_invoice')
            inv_vals.update({'invoice_line_ids' : [(0, 0, inv_line_vals)]})
            move_obj |= moveobj.create(inv_vals)
        asset.delete_depreciation()
        asset.state = 'sold'
