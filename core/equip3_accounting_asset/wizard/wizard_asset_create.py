from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class WizardAssetCreate(models.TransientModel):
    _name = 'wizard.asset.create'
    _description = 'Create Asset Wizard'

    date = fields.Date('Date')
    first_depreciation_manual_date = fields.Date('First Depreciation Date')
    salvage_value = fields.Float('Salvage Value')
    method = fields.Selection(
        [('linear', 'Straight-line Method'), ('degressive', 'Degressive'),('double_declining', 'Double Declining')],
        string='Computation Method', help="Choose the method to use to compute the amount of depreciation lines.\n  * Linear: Calculated on basis of: Gross Value / Number of Depreciations\n"
             "  * Degressive: Calculated on basis of: Residual Value * Degressive Factor")
    method_time = fields.Selection(
        [('number', 'Number of Entries'), ('end', 'Ending Date')],
        string='Time Method Based On', default='number',
        help="Choose the method to use to compute the dates and number of entries.\n"
             "  * Number of Entries: Fix the number of entries and the time between 2 depreciations.\n"
             "  * Ending Date: Choose the time between 2 depreciations and the date the depreciations won't go beyond.")
    prorata = fields.Boolean(string='Prorata Temporis',
                             help='Indicates that the first depreciation entry for this asset have to be done from the purchase date instead of the first of January')
    cut_off_asset_date = fields.Integer(string='Cut Off Asset Date', default=31)
    method_number_fiscal = fields.Integer(string='Number of Depreciations', default=5, help="The number of depreciations needed to depreciate your asset")
    method_period_fiscal = fields.Integer(string='Number of Months in a Period', default=12, 
        help="The amount of time between two depreciations, in months")


    def create_new_asset(self):
        cip_id = self.env.context.get('active_id')
        assets_obj = self.env['account.asset.asset']
        cip = self.env['asset.cip'].browse(cip_id)

        amount = 0
        for line in cip.lines:
            amount += line.amount
            if not line.move_check:
                raise UserError(_(
                'The progress of Construction in Progress is not yet done. Please post the related journal entries.'))
   
        cip.state = 'posted'
        category_id = cip.asset_category
        move_line_1 = {
            'name': cip.asset_name,
            'account_id': cip.cip_account.id,
            'debit': 0.0,
            'credit': amount,
            'journal_id': category_id.journal_id.id,
            # 'partner_id': partner.id,
            # 'analytic_account_id': category_id.account_analytic_id.id if category_id.type == 'sale' else False,
            'currency_id': cip.currency.id
            # 'amount_currency': company_currency != current_currency and - 1.0 * line.amount or 0.0,
        }
        move_line_2 = {
            'name': cip.asset_name,
            'account_id': cip.asset_category.account_asset_id.id,
            'credit': 0.0,
            'debit': amount,
            'journal_id': category_id.journal_id.id,
            # 'partner_id': partner.id,
            # 'analytic_account_id': category_id.account_analytic_id.id if category_id.type == 'purchase' else False,
            'currency_id': cip.currency.id
            # 'amount_currency': company_currency != current_currency and line.amount or 0.0,
        }
        move_vals = {
            'ref': cip.name,
            # 'date': depreciation_date or False,
            'journal_id': category_id.journal_id.id,
            'branch_id': cip.branch_id.id,
            'line_ids': [(0, 0, move_line_1), (0, 0, move_line_2)],
        }
        move = self.env['account.move'].create(move_vals)
        cip.move_id = move.id

        for wizard in self:
            name = cip.asset_name
            values = 0
            for line in cip.lines:
                values += line.amount

            values = {'name' : name,
                        'category_id' : cip.asset_category.id,
                        'value' : values,
                        'date' : wizard.date,
                        'first_depreciation_manual_date' : wizard.first_depreciation_manual_date,
                        'salvage_value' : wizard.salvage_value,
                        'method' : wizard.method,
                        'method_time' : wizard.method_time,
                        'prorata' : wizard.prorata,
                        'cut_off_asset_date' : wizard.cut_off_asset_date,
                        'method_number_fiscal' : wizard.method_number_fiscal,
                        'method_period_fiscal' : wizard.method_period_fiscal,
                        'account_cip_id' : cip.id,
                        'branch_id' : cip.branch_id.id,
                        }
            assets = assets_obj.create(values)
        return True


    