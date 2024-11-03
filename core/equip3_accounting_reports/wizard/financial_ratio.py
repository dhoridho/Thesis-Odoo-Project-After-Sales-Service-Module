import time
from odoo import fields, models, api, _

import io
import json
from odoo.exceptions import AccessError, UserError, AccessDenied

try:
    from odoo.tools.misc import xlsxwriter
except ImportError:
    import xlsxwriter

class FinancialRatioView(models.TransientModel):
    _inherit = "account.common.report"
    _name = 'account.financial.ratio'

    journal_ids = fields.Many2many('account.journal',

                                   string='Journals', required=True,
                                   default=[])
    display_account = fields.Selection(
        [('all', 'All'), ('movement', 'With movements'),
         ('not_zero', 'With balance is not equal to 0')],
        string='Display Accounts', required=True, default='movement')

    @api.model
    def view_report(self, option):
        r = self.env['account.financial.ratio'].search([('id', '=', option[0])])

        data = {
            'display_account': r.display_account,
            'model':self,
            'journals': r.journal_ids,
            'target_move': r.target_move,

        }
        if r.date_from:
            data.update({
                'date_from':r.date_from,
            })
        if r.date_to:
            data.update({
                'date_to':r.date_to,
            })

        filters = self.get_filter(option)
        records = self._get_report_values(data)
        currency = self._get_currency()
        
        return {
            'name': "Financial Ratio",
            'type': 'ir.actions.client',
            'tag': 'f_r',
            'filters': filters,            
            'report_lines': records['Accounts'],
            'debit_total': records['debit_total'],
            'credit_total': records['credit_total'],
            'currency': currency,
            'report_lines_current_ratio' : records['current_ratio'],
            'report_lines_quick_ratio' : records['quick_ratio'],
            'report_lines_capital_ratio' : records['capital_ratio'],
            'report_lines_cash_ratio' : records['cash_ratio'],
            'report_lines_debt_to_asset_ratio' : records['debt_to_asset_ratio'],
            'report_lines_debt_to_equity_ratio' : records['debt_to_equity_ratio'],
            'report_lines_long_term_debt_to_equity_ratio' : records['long_term_debt_to_equity_ratio'],
            'report_lines_times_interest_earned_ratio' : records['times_interest_earned_ratio'],
            'report_lines_EBITDA' : records['EBITDA'],
            'report_lines_return_on_asset' : records['return_on_asset'],
            'report_lines_return_on_equity' : records['return_on_equity'],
            'report_lines_profit_margin' : records['profit_margin'],
            'report_lines_gross_profit_margin' : records['gross_profit_margin'],
            'report_lines_ar_turnover_ratio' : records['ar_turnover_ratio'],
            'report_lines_merchandise_inventory' : records['merchandise_inventory'],
            'report_lines_total_assets' : records['total_assets'],
            'report_lines_net_fixed_assets' : records['net_fixed_assets'],
        }

    def get_filter(self, option):
        data = self.get_filter_data(option)
        filters = {}
        if data.get('journal_ids'):
            filters['journals'] = self.env['account.journal'].browse(data.get('journal_ids')).mapped('code')
        else:
            filters['journals'] = ['All']
        if data.get('target_move'):
            filters['target_move'] = data.get('target_move')
        if data.get('date_from'):
            filters['date_from'] = data.get('date_from')
        if data.get('date_to'):
            filters['date_to'] = data.get('date_to')

        filters['company_id'] = ''
        filters['journals_list'] = data.get('journals_list')
        filters['company_name'] = data.get('company_name')
        filters['target_move'] = data.get('target_move').capitalize()

        return filters

    def get_filter_data(self, option):
        r = self.env['account.financial.ratio'].search([('id', '=', option[0])])
        default_filters = {}
        company_id = self.env.company
        company_domain = [('company_id', '=', company_id.id)]
        journals = r.journal_ids if r.journal_ids else self.env['account.journal'].search(company_domain)

        filter_dict = {
            'journal_ids': r.journal_ids.ids,
            'company_id': company_id.id,
            'date_from': r.date_from,
            'date_to': r.date_to,
            'target_move': r.target_move,
            'journals_list': [(j.id, j.name, j.code) for j in journals],
            'company_name': company_id and company_id.name,
        }
        filter_dict.update(default_filters)
        return filter_dict

    def _get_list_report(self,report_name):
        list_report=[]
        if isinstance(report_name, list) == True:
            for list_rec in report_name:
                rec_list_report = self.env['account.financial.report'].search([('name', '=', list_rec)])
                for rec_reports in rec_list_report.account_type_ids:
                    list_report.append(rec_reports.name)
        else:
            rec_list_report = self.env['account.financial.report'].search([('name', '=', report_name)])
            for rec_reports in rec_list_report.account_type_ids:
                list_report.append(rec_reports.name)
        return list_report

    def _get_report_values(self, data):
        docs = data['model']
        display_account = data['display_account']
        journals = data['journals']        
        accounts = self.env['account.account'].search([])
        if not accounts:
            raise UserError(_("No Accounts Found! Please Add One"))
        account_res = self._get_accounts(accounts, display_account, data)        
        debit_total = 0
        debit_total = sum(x['debit'] for x in account_res)
        credit_total = sum(x['credit'] for x in account_res)

        account_types = self.env['account.account.type'].search([])
        if not account_types:
            raise UserError(_("No Account Types Found! Please Add One"))

        account_type_current_ratio = self._get_account_types(account_res, display_account, data, ['Current Assets' ,'Bank and Cash', 'Petty Cash','Receivable', 'Outstanding Receipt' ,'Inventory', 'Prepayments', 'Other Receivable', 'Supplies', 'Current Liabilities', 'Payable', 'Credit Card', 'Other Payable'])
        current_Current_Asset = self._get_account_types_total(account_type_current_ratio, ['Current Assets' ,'Bank and Cash', 'Petty Cash','Receivable', 'Outstanding Receipt' ,'Inventory', 'Prepayments', 'Other Receivable', 'Supplies'], "Current Asset", data)
        current_Current_Liability = self._get_account_types_total(account_type_current_ratio, ['Current Liabilities', 'Payable', 'Credit Card', 'Other Payable'], "Current Liability", data)
        # current_ratio = [current_Current_Asset[0] if len(current_Current_Asset) > 0 else {}, current_Current_Liability[0] if len(current_Current_Liability) > 0 else {}]        
        current_ratio = self._value_type(current_Current_Asset,current_Current_Liability, data)

        account_type_quick_ratio = self._get_account_types(account_res, display_account, data, ['Current Assets' ,'Bank and Cash', 'Petty Cash','Receivable', 'Outstanding Receipt' ,'Inventory', 'Prepayments', 'Other Receivable', 'Supplies', 'Inventory', 'Current Liabilities', 'Payable', 'Credit Card', 'Other Payable'])
        quick_Current_Asset = self._get_account_types_total(account_type_quick_ratio, ['Current Assets' ,'Bank and Cash', 'Petty Cash','Receivable', 'Outstanding Receipt' ,'Inventory', 'Prepayments', 'Other Receivable', 'Supplies'], "Current Asset", data)
        quick_Current_Inventory = self._get_account_types_total(account_type_quick_ratio, ['Inventory'], "Inventory", data)
        quick_Current_Liability = self._get_account_types_total(account_type_quick_ratio, ['Current Liabilities', 'Payable', 'Credit Card', 'Other Payable'], "Current Liability", data)
        # quick_ratio = [quick_Current_Asset_Inventory[0] if len(quick_Current_Asset_Inventory) > 0 else {},quick_Current_Liability[0] if len(quick_Current_Liability) > 0 else {}]       
        quick_ratio = self._value_type_div_minus(quick_Current_Asset,quick_Current_Liability,quick_Current_Inventory, data)

        ##
        account_type_capital_ratio = self._get_account_types(account_res, display_account, data, ['Current Assets' ,'Bank and Cash', 'Petty Cash','Receivable', 'Outstanding Receipt' ,'Inventory', 'Prepayments', 'Other Receivable', 'Supplies', 'Current Liabilities', 'Payable', 'Credit Card', 'Other Payable'])
        capital_Current_Asset = self._get_account_types_total(account_type_capital_ratio, ['Current Assets' ,'Bank and Cash', 'Petty Cash','Receivable', 'Outstanding Receipt' ,'Inventory', 'Prepayments', 'Other Receivable', 'Supplies'], "Current Asset", data)
        capital_Current_Liability = self._get_account_types_total(account_type_capital_ratio, ['Current Liabilities', 'Payable', 'Credit Card', 'Other Payable'], "Current Liability", data)
        capital_ratio = self._value_type_minus(capital_Current_Asset,capital_Current_Liability, data)
        
        account_type_cash_ratio = self._get_account_types(account_res, display_account, data, ['Bank and Cash', 'Petty Cash', 'Current Liabilities', 'Payable', 'Credit Card', 'Other Payable'])
        ratio_Cash_Equivalent = self._get_account_types_total(account_type_cash_ratio, ['Bank and Cash', 'Petty Cash'], "(Cash + Cash Equivalent)", data)
        ratio_Current_Liability = self._get_account_types_total(account_type_cash_ratio, ['Current Liabilities', 'Payable', 'Credit Card', 'Other Payable'], "Current Liability", data)
        # cash_ratio = [ratio_Cash_Equivalent[0] if len(ratio_Cash_Equivalent) > 0 else {},ratio_Current_Liability[0] if len(ratio_Current_Liability) > 0 else {}]
        cash_ratio = self._value_type(ratio_Cash_Equivalent,ratio_Current_Liability, data)

        account_type_debt_to_asset_ratio = self._get_account_types(account_res, display_account, data, ['Current Liabilities', 'Payable', 'Credit Card', 'Other Payable', 'Non-current Liabilities', 'Long Term Liability', 'Current Assets', 'Bank and Cash', 'Petty Cash', 'Receivable', 'Outstanding Receipt', 'Inventory', 'Prepayments', 'Other Receivable', 'Supplies', 'Non-current Assets', 'Fixed Assets', 'Building', 'Vehicle', 'Property', 'Accumulated Depreciation'])
        to_asset_ratio_Liability = self._get_account_types_total(account_type_debt_to_asset_ratio, ['Current Liabilities', 'Payable', 'Credit Card', 'Other Payable', 'Non-current Liabilities', 'Long Term Liability'], "Total Liability", data)
        to_asset_ratio_Asset = self._get_account_types_total(account_type_debt_to_asset_ratio, ['Current Assets', 'Bank and Cash', 'Petty Cash', 'Receivable', 'Outstanding Receipt', 'Inventory', 'Prepayments', 'Other Receivable', 'Supplies', 'Non-current Assets', 'Fixed Assets', 'Building', 'Vehicle', 'Property', 'Accumulated Depreciation'], "Total Asset", data)
        # debt_to_asset_ratio = [to_asset_ratio_Liability[0] if len(to_asset_ratio_Liability) > 0 else {},to_asset_ratio_Asset[0] if len(to_asset_ratio_Asset) > 0 else {}]
        debt_to_asset_ratio = self._value_type(to_asset_ratio_Liability,to_asset_ratio_Asset, data) 
        
        account_type_debt_to_equity_ratio = self._get_account_types(account_res, display_account, data, ['Current Liabilities', 'Payable', 'Credit Card', 'Other Payable', 'Non-current Liabilities', 'Long Term Liability', 'Current Year Earnings', 'Equity', 'Prive', 'Retained Earnings'])
        to_equity_ratio_Liability = self._get_account_types_total(account_type_debt_to_equity_ratio, ['Current Liabilities', 'Payable', 'Credit Card', 'Other Payable', 'Non-current Liabilities', 'Long Term Liability'], "Total Liability", data)
        to_equity_ratio_Equity = self._get_account_types_total(account_type_debt_to_equity_ratio, ['Current Year Earnings', 'Equity', 'Prive', 'Retained Earnings'], "Total Equity", data)
        # debt_to_equity_ratio = [to_equity_ratio_Liability[0] if len(to_equity_ratio_Liability) > 0 else {},to_equity_ratio_Equity[0]  if len(to_equity_ratio_Equity) > 0 else {}]
        debt_to_equity_ratio = self._value_type(to_equity_ratio_Liability,to_equity_ratio_Equity, data)

        account_type_long_term_debt_to_equity_ratio = self._get_account_types(account_res, display_account, data, ['Non-current Liabilities' ,'Long Term Liability', 'Current Year Earnings', 'Equity', 'Prive', 'Retained Earnings'])
        long_term_debt_to_equity_ratio_Liability = self._get_account_types_total(account_type_long_term_debt_to_equity_ratio, ['Non-current Liabilities' ,'Long Term Liability'], "Long Term Liability", data)
        long_term_debt_to_equity_ratio_Equity = self._get_account_types_total(account_type_long_term_debt_to_equity_ratio, ['Current Year Earnings', 'Equity', 'Prive', 'Retained Earnings'], "Total equity", data)
        # long_term_debt_to_equity_ratio = [long_term_debt_to_equity_ratio_Liability[0] if len(long_term_debt_to_equity_ratio_Liability) > 0 else {},long_term_debt_to_equity_ratio_Equity[0] if len(long_term_debt_to_equity_ratio_Equity) > 0 else {}]
        long_term_debt_to_equity_ratio = self._value_type(long_term_debt_to_equity_ratio_Liability,long_term_debt_to_equity_ratio_Equity, data)
        
        account_type_times_interest_earned_ratio = self._get_account_types(account_res, display_account, data, ['Cost of Revenue', 'Income', 'Expenses', 'Other Income', 'Other Expense', 'Amortization', 'Depreciation', 'Interest Expense'])
        earned_ratio_EBITDA_1 = self._get_account_types_total_minus(account_type_times_interest_earned_ratio, ['Income', 'Cost of Revenue', 'Expenses'], "EBITDA", data)
        earned_ratio_EBITDA_2 = self._get_account_types_total_minus(account_type_times_interest_earned_ratio, ['Other Income', 'Other Expense', 'Amortization', 'Depreciation'], "EBITDA", data)
        earned_ratio_Expense = self._get_account_types_total(account_type_times_interest_earned_ratio, ['Interest Expense'], "Interest Expense", data)
        # times_interest_earned_ratio = [earned_ratio_EBITDA[0] if len(earned_ratio_EBITDA) > 0 else {},earned_ratio_Expense[0] if len(earned_ratio_Expense) > 0 else {}]
        times_interest_earned_ratio = self._value_type_div_plus(earned_ratio_EBITDA_1, earned_ratio_EBITDA_2, earned_ratio_Expense, data)

        account_type_EBITDA = self._get_account_types(account_res, display_account, data, ['Income', 'Cost of Revenue', 'Expenses', 'Other Income', 'Other Expense'])
        ratio_EBITDA_1 = self._get_account_types_total_minus(account_type_EBITDA, ['Income', 'Cost of Revenue', 'Expenses'], "Net Income + Interst + Tax + Depreciation + Amortization", data)
        ratio_EBITDA_2 = self._get_account_types_total_minus(account_type_EBITDA, ['Other Income', 'Other Expense'], "Net Income + Interst + Tax + Depreciation + Amortization", data)
        # EBITDA = [ratio_EBITDA[0] if len(ratio_EBITDA) > 0 else {}]
        EBITDA = self._value_type_one_row(ratio_EBITDA_1, ratio_EBITDA_2, data)

        account_type_return_on_asset = self._get_account_types(account_res, display_account, data, ['Income', 'Cost of Revenue', 'Expenses', 'Other Income', 'Other Expense', 'Amortization', 'Depreciation', 'Interest Expense', 'Interest Revenue', 'Tax', 'Current Assets', 'Bank and Cash', 'Petty Cash', 'Receivable', 'Outstanding Receipt', 'Inventory', 'Prepayments', 'Other Receivable', 'Supplies', 'Non-current Assets', 'Fixed Assets', 'Building', 'Vehicle', 'Property', 'Accumulated Depreciation'])
        return_on_asset_Net_Income = self._get_account_types_total(account_type_return_on_asset, ['Income', 'Cost of Revenue', 'Expenses', 'Other Income', 'Other Expense', 'Amortization', 'Depreciation', 'Interest Expense', 'Interest Revenue', 'Tax'], "Net Income", data)
        return_on_asset_Total_Asset = self._get_account_types_total(account_type_return_on_asset, ['Current Assets', 'Bank and Cash', 'Petty Cash', 'Receivable', 'Outstanding Receipt', 'Inventory', 'Prepayments', 'Other Receivable', 'Supplies', 'Non-current Assets', 'Fixed Assets', 'Building', 'Vehicle', 'Property', 'Accumulated Depreciation'], "Total Asset", data)
        # return_on_asset = [return_on_asset_Net_Income[0] if len(return_on_asset_Net_Income) > 0 else {},return_on_asset_Total_Asset[0] if len(return_on_asset_Total_Asset) > 0 else {}]
        return_on_asset = self._value_type(return_on_asset_Net_Income,return_on_asset_Total_Asset, data)
        
        account_type_return_on_equity = self._get_account_types(account_res, display_account, data, self._get_list_report(['Income', 'Cost of Revenue', 'Expenses', 'Other Income', 'Other Expense', 'Amortization', 'Depreciation', 'Interest Expense', 'Interest Revenue', 'Tax', 'Current Year Earnings', 'Equity', 'Prive', 'Retained Earnings']))
        return_on_equity_Net_Income_1 = self._get_account_types_total_minus(account_type_return_on_equity, self._get_list_report(['Income', 'Cost of Revenue', 'Expenses']), "Net Income", data)
        return_on_equity_Net_Income_2 = self._get_account_types_total_minus(account_type_return_on_equity, self._get_list_report(['Other Income', 'Other Expense', 'Amortization', 'Depreciation', 'Interest Expense', 'Interest Revenue', 'Tax']), "Net Income", data)
        return_on_equity_Total_Equity = self._get_account_types_total(account_type_return_on_equity, self._get_list_report(['Current Year Earnings', 'Equity', 'Prive', 'Retained Earnings']), "Total Asset", data)
        # return_on_equity = [return_on_equity_Net_Income[0] if len(return_on_equity_Net_Income) > 0 else {},return_on_equity_Total_Equity[0] if len(return_on_equity_Total_Equity) > 0 else {}]
        return_on_equity = self._value_type_div_plus(return_on_equity_Net_Income_1, return_on_equity_Net_Income_2, return_on_equity_Total_Equity, data)

        ##
        account_type_net_profit_margin = self._get_account_types(account_res, display_account, data, ['Income', 'Cost of Revenue', 'Expenses', 'Other Income', 'Other Expense', 'Amortization', 'Depreciation', 'Interest Expense', 'Interest Revenue', 'Tax', 'Income'])
        profit_margin_Net_Profit_1 = self._get_account_types_total_minus(account_type_net_profit_margin, ['Income', 'Cost of Revenue', 'Expenses'], "Net Profit", data)
        profit_margin_Net_Profit_2 = self._get_account_types_total_minus(account_type_net_profit_margin, ['Other Income', 'Other Expense', 'Amortization', 'Depreciation', 'Interest Expense', 'Interest Revenue', 'Tax'], "Net Profit", data)
        profit_margin_Sales = self._get_account_types_total(account_type_net_profit_margin, ['Income'], "Sales", data)
        profit_margin = self._value_type_div_plus(profit_margin_Net_Profit_1, profit_margin_Net_Profit_2, profit_margin_Sales, data)

        account_type_gross_profit_margin = self._get_account_types(account_res, display_account, data, ['Income', 'Cost of Revenue', 'Income'])
        gross_profit_margin_Profit = self._get_account_types_total_minus(account_type_gross_profit_margin, ['Income', 'Cost of Revenue'], "Net Profit", data)
        gross_profit_margin_Sales = self._get_account_types_total(account_type_gross_profit_margin, ['Income'], "Sales", data)
        gross_profit_margin = self._value_type(gross_profit_margin_Profit,gross_profit_margin_Sales, data)

        ###
        account_type_ar_turnover_ratio = self._get_account_types(account_res, display_account, data, ['Income','Receivable'])
        ar_turnover_ratio_Revenue = self._get_account_types_total(account_type_ar_turnover_ratio, ['Income'], "Sales", data)
        ar_turnover_ratio_Receivable = self._get_account_types_total(account_type_ar_turnover_ratio, ['Receivable'], "Receivable", data)
        ar_turnover_ratio = self._value_type_turnover(ar_turnover_ratio_Revenue,ar_turnover_ratio_Receivable, data)

        ###
        account_type_merchandise_inventory = self._get_account_types(account_res, display_account, data, ['Cost of Revenue','Inventory'])
        merchandise_inventory_Cost_Of_Revenue = self._get_account_types_total(account_type_merchandise_inventory, ['Cost of Revenue'], "Sales", data)
        merchandise_inventory_Inventory = self._get_account_types_total(account_type_merchandise_inventory, ['Inventory'], "Inventory", data)
        merchandise_inventory = self._value_type_turnover(merchandise_inventory_Cost_Of_Revenue,merchandise_inventory_Inventory, data)        

        ###
        account_type_total_assets = self._get_account_types(account_res, display_account, data, ['Income ', 'Current Assets', 'Bank and Cash', 'Petty Cash', 'Receivable', 'Outstanding Receipt', 'Inventory', 'Prepayments', 'Other Receivable', 'Supplies', 'Non-current Assets', 'Fixed Assets', 'Building', 'Vehicle', 'Property', 'Accumulated Depreciation'])
        total_assets_Revenue = self._get_account_types_total(account_type_total_assets, ['Income '], "Sales", data)
        total_assets_Total_Assets = self._get_account_types_total(account_type_total_assets, ['Current Assets', 'Bank and Cash', 'Petty Cash', 'Receivable', 'Outstanding Receipt', 'Inventory', 'Prepayments', 'Other Receivable', 'Supplies', 'Non-current Assets', 'Fixed Assets', 'Building', 'Vehicle', 'Property', 'Accumulated Depreciation'], "Total Assets", data)
        total_assets = self._value_type_turnover(total_assets_Revenue,total_assets_Total_Assets, data)
        
        ###
        account_type_net_fixed_assets = self._get_account_types(account_res, display_account, data, ['Income', 'Non-current Assets', 'Fixed Assets', 'Building', 'Vehicle', 'Property', 'Accumulated Depreciation'])
        net_fixed_assets_Revenue = self._get_account_types_total(account_type_net_fixed_assets, ['Income'], "Sales", data)
        net_fixed_assets_Fixed_Asset = self._get_account_types_total(account_type_net_fixed_assets, ['Non-current Assets', 'Fixed Assets', 'Building', 'Vehicle', 'Property', 'Accumulated Depreciation'], "Fixed Asset", data)
        net_fixed_assets = self._value_type_turnover(net_fixed_assets_Revenue,net_fixed_assets_Fixed_Asset, data)

        return {
            'doc_ids': self.ids,
            'debit_total': debit_total,
            'credit_total': credit_total,
            'docs': docs,
            'time': time,
            'Accounts': account_res,
            'current_ratio' : current_ratio,
            'quick_ratio' : quick_ratio,
            'capital_ratio' : capital_ratio,
            'cash_ratio' : cash_ratio,
            'debt_to_asset_ratio' : debt_to_asset_ratio,
            'debt_to_equity_ratio' : debt_to_equity_ratio,
            'long_term_debt_to_equity_ratio' : long_term_debt_to_equity_ratio,
            'times_interest_earned_ratio' : times_interest_earned_ratio,
            'EBITDA' : EBITDA,
            'return_on_asset' : return_on_asset,
            'return_on_equity' : return_on_equity,
            'profit_margin' : profit_margin,
            'gross_profit_margin' : gross_profit_margin,
            'ar_turnover_ratio' : ar_turnover_ratio,
            'merchandise_inventory' : merchandise_inventory,
            'total_assets' : total_assets,
            'net_fixed_assets' : net_fixed_assets,
        }

    def _value_type_div_plus(self,value1,value2,value3,data):
        res_val1 = 0.0
        res_val2 = 0.0
        res_val3 = 0.0
        res_init_val1 = 0.0
        res_init_val2 = 0.0
        res_init_val3 = 0.0
        value = []
        
        if len(value1)>0:
            for x in value1:
                res_val1 = x['balance']
                if data.get('date_from'):
                    balance = x['Init_balance']
                    if balance != None:
                        res_init_val1 = balance['balance']
        
        if len(value2)>0:
            for x in value2:
                res_val2 = x['balance']
                if data.get('date_from'):
                    balance = x['Init_balance']
                    if balance != None:
                        res_init_val2 = balance['balance']

        if len(value3)>0:
            for x in value3:
                res_val3 = x['balance']
                if data.get('date_from'):
                    balance = x['Init_balance']
                    if balance != None:
                        res_init_val3 = balance['balance']

        if res_val3 == 0:
            total_balance = 0
        else:
            total_balance = ((res_val1+res_val2) / res_val3) * (100)
        
        total_init_balance = 0.0        
        res = dict((fn, 0.0) for fn in ['balance'])
        if total_balance != 0:
            total_balance = int(total_balance)
            res['balance'] = total_balance
        

        if data.get('date_from'):
            if res_init_val3 == 0:
                total_init_balance = 0
            else:
                total_init_balance = ((res_init_val1+res_init_val2) / res_init_val3) * (100)
            if total_init_balance != 0:
                res['Init_balance'] = {'balance' : total_init_balance}
                if 'balance' not in res:
                    res['balance'] = 0
        value.append(res)
        return value

    def _value_type_div_minus(self,value1,value2,value3_minus,data):
        res_val1 = 0.0
        res_val2 = 0.0
        res_val3_minus = 0.0
        res_init_val1 = 0.0
        res_init_val2 = 0.0
        res_init_val3_minus = 0.0
        value = []
        
        if len(value1)>0:
            for x in value1:
                res_val1 = x['balance']
                if data.get('date_from'):
                    balance = x['Init_balance']
                    if balance != None:
                        res_init_val1 = balance['balance']
        
        if len(value3_minus)>0:
            for x in value3_minus:
                res_val3_minus = x['balance']
                if data.get('date_from'):
                    balance = x['Init_balance']
                    if balance != None:
                        res_init_val3_minus = balance['balance']   

        if len(value2)>0:
            for x in value2:
                res_val2 = x['balance']
                if data.get('date_from'):
                    balance = x['Init_balance']
                    if balance != None:
                        res_init_val2 = balance['balance']

        if res_val2 == 0:
            total_balance = 0
        else:
            total_balance = ((res_val1-res_val3_minus) / res_val2) * (100)
        
        total_init_balance = 0.0        
        res = dict((fn, 0.0) for fn in ['balance'])
        if total_balance != 0:
            total_balance = int(total_balance)
            res['balance'] = total_balance
        if data.get('date_from'):
            if res_init_val2 == 0:
                total_init_balance = 0
            else:
                total_init_balance = ((res_init_val1-res_init_val3_minus) / res_init_val2) * (100)
            if total_init_balance != 0:
                res['Init_balance'] = {'balance' : total_init_balance}
                if 'balance' not in res:
                    res['balance'] = 0
        value.append(res)
        return value

    def _value_type_minus(self,value1,value2,data):
        res_val1 = 0.0
        res_val2 = 0.0
        res_init_val1 = 0.0
        res_init_val2 = 0.0
        value = []
        if len(value1)>0:
            for x in value1:
                res_val1 = x['balance']
                if data.get('date_from'):
                    balance = x['Init_balance']
                    if balance != None:
                        res_init_val1 = balance['balance']
        if len(value2)>0:
            for x in value2:
                res_val2 = x['balance']
                if data.get('date_from'):
                    balance = x['Init_balance']
                    if balance != None:
                        res_init_val2 = balance['balance']                        
        total_balance = (res_val1 - res_val2) * (100)
        total_init_balance = 0.0        
        res = dict((fn, 0.0) for fn in ['balance'])
        if total_balance != 0:
            total_balance = int(total_balance)
            res['balance'] = total_balance
        
        if data.get('date_from'):
            total_init_balance = (res_init_val1 - res_init_val2)
            if total_init_balance != 0:
                res['Init_balance'] = {'balance' : total_init_balance}
                if 'balance' not in res:
                    res['balance'] = 0
        value.append(res)
        return value

    def _value_type_turnover(self,value1,value2,data):
        res_val1 = 0.0
        res_val2 = 0.0
        res_init_val1 = 0.0
        res_init_val2 = 0.0
        value = []
        if len(value1)>0:
            for x in value1:
                res_val1 = x['balance']
                if data.get('date_from'):
                    balance = x['Init_balance']
                    if balance != None:
                        res_init_val1 = balance['balance']
        if len(value2)>0:
            for x in value2:
                res_val2 = x['balance']
                if data.get('date_from'):
                    balance = x['Init_balance']
                    if balance != None:
                        res_init_val2 = balance['balance']                        
        if res_val2 == 0:
            total_balance = 0
        else:
            total_balance = (res_val1 / ((res_val2-res_val2-1)/2)) * (100)
        
        total_init_balance = 0.0
        res = dict((fn, 0.0) for fn in ['balance'])
        if total_balance != 0:
            total_balance = int(total_balance)
            res['balance'] = total_balance
        if data.get('date_from'):
            if res_init_val2 == 0:
                total_init_balance = 0
            else:
                total_init_balance = (res_init_val1 / ((res_init_val2-res_init_val2-1)/2)) * (100)
            if total_init_balance != 0:
                res['Init_balance'] = {'balance' : total_init_balance}
                if 'balance' not in res:
                    res['balance'] = 0
        value.append(res)
        return value

    def _value_type(self,value1,value2,data):
        res_val1 = 0.0
        res_val2 = 0.0
        res_init_val1 = 0.0
        res_init_val2 = 0.0
        value = []
        if len(value1)>0:
            for x in value1:
                res_val1 = x['balance']
                if data.get('date_from'):
                    balance = x['Init_balance']
                    if balance != None:
                        res_init_val1 = balance['balance']
        if len(value2)>0:
            for x in value2:
                res_val2 = x['balance']
                if data.get('date_from'):
                    balance = x['Init_balance']
                    if balance != None:
                        res_init_val2 = balance['balance']                        
        if res_val2 == 0:
            total_balance = 0
        else:
            total_balance = (res_val1 / res_val2) * (100)
        total_init_balance = 0.0        
        res = dict((fn, 0.0) for fn in ['balance'])
        if total_balance != 0:
            total_balance = int(total_balance)
            res['balance'] = total_balance
        
        if data.get('date_from'):
            if res_init_val2 == 0:
                total_init_balance = 0
            else:
                total_init_balance = (res_init_val1 / res_init_val2) * (100)
            if total_init_balance != 0:
                res['Init_balance'] = {'balance' : total_init_balance}
                if 'balance' not in res:
                    res['balance'] = 0
        value.append(res)
        return value

    def _value_type_one_row(self,value1,value2,data):
        res_val1 = 0.0
        res_val2 = 0.0
        res_init_val1 = 0.0
        res_init_val2 = 0.0
        value = []
        if len(value1)>0:
            for x in value1:
                res_val1 = x['balance']
                if data.get('date_from'):
                    balance = x['Init_balance']
                    if balance != None:
                        res_init_val1 = balance['balance']
        if len(value2)>0:
            for x in value2:
                res_val2 = x['balance']
                if data.get('date_from'):
                    balance = x['Init_balance']
                    if balance != None:
                        res_init_val2 = balance['balance']                        
        if res_val2 == 0:
            total_balance = 0
        else:
            total_balance = (res_val1 + res_val2)
        total_init_balance = 0.0        
        res = dict((fn, 0.0) for fn in ['balance'])
        if total_balance != 0:
            total_balance = int(total_balance)
            res['balance'] = total_balance
        
        if data.get('date_from'):
            if res_init_val2 == 0:
                total_init_balance = 0
            else:
                total_init_balance = (res_init_val1 + res_init_val2)
            if total_init_balance != 0:
                res['Init_balance'] = {'balance' : total_init_balance}
                if 'balance' not in res:
                    res['balance'] = 0
        value.append(res)
        return value

    @api.model
    def create(self, vals):
        vals['target_move'] = 'posted'
        res = super(FinancialRatioView, self).create(vals)
        return res

    def write(self, vals):
        if vals.get('target_move'):
            vals.update({'target_move': vals.get('target_move').lower()})
        if vals.get('journal_ids'):
            vals.update({'journal_ids': [(6, 0, vals.get('journal_ids'))]})
        if vals.get('journal_ids') == []:
            vals.update({'journal_ids': [(5,)]})
        res = super(FinancialRatioView, self).write(vals)
        return res

    def _get_accounts(self, accounts, display_account, data):

        account_result = {}
        # Prepare sql query base on selected parameters from wizard
        tables, where_clause, where_params = self.env['account.move.line']._query_get()
        tables = tables.replace('"', '')
        if not tables:
            tables = 'account_move_line'
        wheres = [""]
        if where_clause.strip():
            wheres.append(where_clause.strip())
        filters = " AND ".join(wheres)
        if data['target_move'] == 'posted':
            filters += " AND account_move_line__move_id.state = 'posted'"
        else:
            filters += " AND account_move_line__move_id.state in ('draft','posted')"
        if data.get('date_from'):
            filters += " AND account_move_line.date >= '%s'" % data.get('date_from')
        if data.get('date_to'):
            filters += " AND account_move_line.date <= '%s'" % data.get('date_to')

        if data['journals']:
            filters += ' AND jrnl.id IN %s' % str(tuple(data['journals'].ids) + tuple([0]))
        tables += 'JOIN account_journal jrnl ON (account_move_line.journal_id=jrnl.id)'
        # compute the balance, debit and credit for the provided accounts
        request = (
                    "SELECT account_id AS id, SUM(debit) AS debit, SUM(credit) AS credit, (SUM(debit) - SUM(credit)) AS balance" + \
                    " FROM " + tables + " WHERE account_id IN %s " + filters + " GROUP BY account_id")
        params = (tuple(accounts.ids),) + tuple(where_params)
        self.env.cr.execute(request, params)

        value_fetch = self.env.cr.dictfetchall()        
        for row in value_fetch:        
            account_result[row.pop('id')] = row
        
        account_res = []
        for account in accounts:
            res = dict((fn, 0.0) for fn in ['credit', 'debit', 'balance'])
            currency = account.currency_id and account.currency_id or account.company_id.currency_id
            res['code'] = account.code
            res['name'] = account.name
            res['id'] = account.id
            res['type_id'] = account.user_type_id.id
            res['type_name'] = account.user_type_id.name
            if data.get('date_from'):

                res['Init_balance'] = self.get_init_bal(account, display_account, data)

            if account.id in account_result:
                res['debit'] = account_result[account.id].get('debit')
                res['credit'] = account_result[account.id].get('credit')
                res['balance'] = account_result[account.id].get('balance')
            if display_account == 'all':
                account_res.append(res)
            if display_account == 'not_zero' and not currency.is_zero(
                    res['balance']):
                account_res.append(res)
            if display_account == 'movement' and (
                    not currency.is_zero(res['debit']) or not currency.is_zero(
                    res['credit'])):
                account_res.append(res)
        return account_res

    def get_init_bal(self, account, display_account, data):            
        if data.get('date_from'):

            tables, where_clause, where_params = self.env[
                'account.move.line']._query_get()
            tables = tables.replace('"', '')
            if not tables:
                tables = 'account_move_line'
            wheres = [""]
            if where_clause.strip():
                wheres.append(where_clause.strip())
            filters = " AND ".join(wheres)
            if data['target_move'] == 'posted':
                filters += " AND account_move_line__move_id.state = 'posted'"
            else:
                filters += " AND account_move_line__move_id.state in ('draft','posted')"
            if data.get('date_from'):
                filters += " AND account_move_line.date < '%s'" % data.get('date_from')

            if data['journals']:
                filters += ' AND jrnl.id IN %s' % str(tuple(data['journals'].ids) + tuple([0]))
            tables += 'JOIN account_journal jrnl ON (account_move_line.journal_id=jrnl.id)'

            # compute the balance, debit and credit for the provided accounts
            request = (
                    "SELECT account_id AS id, SUM(debit) AS debit, SUM(credit) AS credit, (SUM(debit) - SUM(credit)) AS balance" + \
                    " FROM " + tables + " WHERE account_id = %s" % account.id + filters + " GROUP BY account_id")
            params = tuple(where_params)
            self.env.cr.execute(request, params)

            value_fetch = self.env.cr.dictfetchall()           
            for row in value_fetch:
                return row

    @api.model
    def _get_currency(self):
        journal = self.env['account.journal'].browse(
            self.env.context.get('default_journal_id', False))
        if journal.currency_id:
            return journal.currency_id.id
        lang = self.env.user.lang
        if not lang:
            lang = 'en_US'
        lang = lang.replace("_", '-')
        currency_array = [self.env.company.currency_id.symbol,
                          self.env.company.currency_id.position,
                          lang]
        return currency_array

    def _get_account_types(self, accounts, display_account, data, account_types):
        account_type_res = []
        for account in accounts:                        
            res = dict((fn, 0.0) for fn in ['balance'])
            if account['type_name'] in account_types:
                x = list(filter(lambda a: a['type_name'] == account['type_name'], account_type_res))
                if len(x) > 0:
                    x[0]['balance'] += account['balance']
                    if data.get('date_from'):
                        balance = account['Init_balance']
                        if balance != None:
                            if 'Init_balance' not in res:
                                res['Init_balance'] = 0         
                            res['Init_balance'] += balance['balance']
                        else:
                            res['Init_balance'] = balance
                else:
                    res['balance'] = account['balance']
                    res['type_id'] = account['type_id']
                    res['type_name'] = account['type_name']

                    if data.get('date_from'):
                        balance = account['Init_balance']
                        if balance != None:
                            res['Init_balance'] = {'balance' : balance['balance']}
                        else:
                            res['Init_balance'] = balance
                    account_type_res.append(res)
        return account_type_res

    def _get_account_types_total(self, account_types, types, name_type,data):
        account_type_res = []
        for account_detail in account_types:
            res = dict((fn, 0.0) for fn in ['balance'])
            if account_detail['type_name'] in types:
                x = list(filter(lambda a: a['type_name'] == name_type, account_type_res))
                if len(x) > 0:
                    x[0]['balance'] += account_detail['balance']                    
                    if data.get('date_from'):
                        balance = account_detail['Init_balance']
                        if balance != None:
                            if 'Init_balance' not in res:
                                res['Init_balance'] = 0                       
                            res['Init_balance'] += balance['balance']
                        else:
                            res['Init_balance'] = balance
                else:
                    res['balance'] = account_detail['balance']
                    res['type_name'] = name_type
                    if data.get('date_from'):
                        balance = account_detail['Init_balance']
                        if balance != None:
                            res['Init_balance'] = {'balance' : balance['balance']}
                        else:
                            res['Init_balance'] = balance
                    account_type_res.append(res)
        return account_type_res


    def _get_account_types_total_minus(self, account_types, types, name_type,data):
        account_type_res = []
        for account_detail in account_types:
            res = dict((fn, 0.0) for fn in ['balance'])
            if account_detail['type_name'] in types:
                x = list(filter(lambda a: a['type_name'] == name_type, account_type_res))
                if len(x) > 0:
                    x[0]['balance'] -= account_detail['balance']
                    if data.get('date_from'):
                        balance = account_detail['Init_balance']
                        if balance != None:
                            if 'Init_balance' not in res:
                                res['Init_balance'] = 0         
                            res['Init_balance'] -= balance['balance']
                        else:
                            res['Init_balance'] = balance
                else:
                    res['balance'] = account_detail['balance']
                    res['type_name'] = name_type
                    if data.get('date_from'):
                        balance = account_detail['Init_balance']
                        if balance != None:
                            res['Init_balance'] = {'balance' : balance['balance']}
                        else:
                            res['Init_balance'] = balance
                    account_type_res.append(res)
        return account_type_res        

    def get_dynamic_xlsx_report(self, data, response ,report_data, dfr_data):
        report_data_main = json.loads(report_data)
        output = io.BytesIO()
        total = json.loads(dfr_data)
        filters = json.loads(data)
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet()
        head = workbook.add_format({'bold': True})
        sub_heading = workbook.add_format({'bold': True, 'border': 1, 'border_color': 'black'})
        text_bold = workbook.add_format({'bold': True, 'border': 1, 'border_color': 'black'})
        txt = workbook.add_format({'border': 1, 'num_format': '#,##0.00%'})
        txt_l = workbook.add_format({'border': 1, 'bold': True, 'num_format': '#,##0.00%'})
        sheet.merge_range('A2:C3', filters.get('company_name') + ':' + ' Financial Ratio', head)
        date_head = workbook.add_format({'bold': True})
        date_style = workbook.add_format({})
        if filters.get('date_from'):
            sheet.write('A4', 'From: '+filters.get('date_from'), date_head)
        if filters.get('date_to'):
            sheet.merge_range('B4:C4', 'To: '+ filters.get('date_to'), date_head)

        sheet.set_column(5, 0, 35)
        if filters.get('date_from'):
            sheet.set_column(6, 1, 15)
            sheet.set_column(7, 2, 15)
        else:
            sheet.set_column(6, 1, 15)

        sheet.merge_range('A5:B6', 'Target Moves: '+ filters.get('target_move'), date_head)
        sheet.write('A7', '', sub_heading)
        if filters.get('date_from'):
            sheet.write('B7', 'Initial Ratio', sub_heading)
            sheet.write('C7', 'Ratio', sub_heading)
            sheet.merge_range('A8:C8', 'Liquidity Ratio', text_bold)
            sheet.merge_range('A13:C13', 'Solvability Ratio', text_bold)
            sheet.merge_range('A19:C19', 'Profitability Ratio', text_bold)
            sheet.merge_range('A23:C23', 'Activity Ratio', text_bold)
        else:
            sheet.write('B7', 'Ratio', sub_heading)
            sheet.merge_range('A8:B8', 'Liquidity Ratio', text_bold)
            sheet.merge_range('A13:B13', 'Solvability Ratio', text_bold)
            sheet.merge_range('A19:B19', 'Profitability Ratio', text_bold)
            sheet.merge_range('A24:B24', 'Activity Ratio', text_bold)

        ## Liquidity Ratio ##
        for current_ratio in total.get('report_lines_current_ratio'):
            sheet.write('A9', 'Current Ratio', txt)
            if filters.get('date_from'):
                if current_ratio.get('Init_balance'):
                    sheet.write('B9', current_ratio['Init_balance']['balance'] / 100, txt)
                else:
                    sheet.write('B9', float(0), txt)
                sheet.write('C9', current_ratio['balance'] / 100, txt)
            else:
                sheet.write('B9', current_ratio['balance'] / 100, txt)

        for quick_ratio in total.get('report_lines_quick_ratio'):
            sheet.write('A10', 'Quick Ratio', txt)
            if filters.get('date_from'):
                if quick_ratio.get('Init_balance'):
                    sheet.write('B10', quick_ratio['Init_balance']['balance'] / 100, txt)
                else:
                    sheet.write('B10', float(0), txt)
                sheet.write('C10', quick_ratio['balance'] / 100, txt)
            else:
                sheet.write('B10', quick_ratio['balance'] / 100, txt)
        
        for capital_ratio in total.get('report_lines_capital_ratio'):
            sheet.write('A11', 'Net Working Capital Ratio', txt)
            if filters.get('date_from'):
                if capital_ratio.get('Init_balance'):
                    sheet.write('B11', capital_ratio['Init_balance']['balance'] / 100, txt)
                else:
                    sheet.write('B11', float(0), txt)
                sheet.write('C11', capital_ratio['balance'] / 100, txt)
            else:
                sheet.write('B11', capital_ratio['balance'] / 100, txt)
        
        for cash_ratio in total.get('report_lines_cash_ratio'):
            sheet.write('A12', 'Cash Ratio', txt)
            if filters.get('date_from'):
                if cash_ratio.get('Init_balance'):
                    sheet.write('B12', cash_ratio['Init_balance']['balance'] / 100, txt)
                else:
                    sheet.write('B12', float(0), txt)
                sheet.write('C12', cash_ratio['balance'] / 100, txt)
            else:
                sheet.write('B12', cash_ratio['balance'] / 100, txt)
        
        ## Solvability Ratio ##
        for debt_to_asset_ratio in total.get('report_lines_debt_to_asset_ratio'):
            sheet.write('A14', 'Debt to Asset Ratio', txt)
            if filters.get('date_from'):
                if debt_to_asset_ratio.get('Init_balance'):
                    sheet.write('B14', debt_to_asset_ratio['Init_balance']['balance'] / 100, txt)
                else:
                    sheet.write('B14', float(0), txt)
                sheet.write('C14', debt_to_asset_ratio['balance'] / 100, txt)
            else:
                sheet.write('B14', debt_to_asset_ratio['balance'] / 100, txt)
        
        for debt_to_equity_ratio in total.get('report_lines_debt_to_equity_ratio'):
            sheet.write('A15', 'Debt to Equity Ratio', txt)
            if filters.get('date_from'):
                if debt_to_equity_ratio.get('Init_balance'):
                    sheet.write('B15', debt_to_equity_ratio['Init_balance']['balance'] / 100, txt)
                else:
                    sheet.write('B15', float(0), txt)
                sheet.write('C15', debt_to_equity_ratio['balance'] / 100, txt)
            else:
                sheet.write('B15', debt_to_equity_ratio['balance'] / 100, txt)
        
        for long_term_debt_to_equity_ratio in total.get('report_lines_long_term_debt_to_equity_ratio'):
            sheet.write('A16', 'Long Term Debt to Equity Ratio', txt)
            if filters.get('date_from'):
                if long_term_debt_to_equity_ratio.get('Init_balance'):
                    sheet.write('B16', long_term_debt_to_equity_ratio['Init_balance']['balance'] / 100, txt)
                else:
                    sheet.write('B16', float(0), txt)
                sheet.write('C16', long_term_debt_to_equity_ratio['balance'] / 100, txt)
            else:
                sheet.write('B16', long_term_debt_to_equity_ratio['balance'] / 100, txt)
        
        for times_interest_earned_ratio in total.get('report_lines_times_interest_earned_ratio'):
            sheet.write('A17', 'Times Interest Earned Ratio', txt)
            if filters.get('date_from'):
                if times_interest_earned_ratio.get('Init_balance'):
                    sheet.write('B17', times_interest_earned_ratio['Init_balance']['balance'] / 100, txt)
                else:
                    sheet.write('B17', float(0), txt)
                sheet.write('C17', times_interest_earned_ratio['balance'] / 100, txt)
            else:
                sheet.write('B17', times_interest_earned_ratio['balance'] / 100, txt)
        
        for EBITDA in total.get('report_lines_EBITDA'):
            sheet.write('A18', 'EBITDA', txt)
            if filters.get('date_from'):
                if EBITDA.get('Init_balance'):
                    sheet.write('B18', EBITDA['Init_balance']['balance'] / 100, txt)
                else:
                    sheet.write('B18', float(0), txt)
                sheet.write('C18', EBITDA['balance'] / 100, txt)
            else:
                sheet.write('B18', EBITDA['balance'] / 100, txt)
        
        ## Profitability Ratio ##
        for return_on_asset in total.get('report_lines_return_on_asset'):
            sheet.write('A20', 'Return On Asset', txt)
            if filters.get('date_from'):

                if return_on_asset.get('Init_balance'):
                    sheet.write('B20', return_on_asset['Init_balance']['balance'] / 100, txt)
                else:
                    sheet.write('B20', float(0), txt)
                sheet.write('C20', return_on_asset['balance'] / 100, txt)
            else:
                sheet.write('B20', return_on_asset['balance'] / 100, txt)
        
        for return_on_equity in total.get('report_lines_return_on_equity'):
            sheet.write('A21', 'Return On Equity', txt)
            if filters.get('date_from'):
                if return_on_equity.get('Init_balance'):
                    sheet.write('B21', return_on_equity['Init_balance']['balance'] / 100, txt)
                else:
                    sheet.write('B21', float(0), txt)
                sheet.write('C21', return_on_equity['balance'] / 100, txt)
            else:
                sheet.write('B21', return_on_equity['balance'] / 100, txt)
        
        for profit_margin in total.get('report_lines_profit_margin'):
            sheet.write('A22', 'Net Profit Margin', txt)
            if filters.get('date_from'):
                if profit_margin.get('Init_balance'):
                    sheet.write('B22', profit_margin['Init_balance']['balance'] / 100, txt)
                else:
                    sheet.write('B22', float(0), txt)
                sheet.write('C22', profit_margin['balance'] / 100, txt)
            else:
                sheet.write('B22', profit_margin['balance'] / 100, txt)
        
        for gross_profit_margin in total.get('report_lines_gross_profit_margin'):
            sheet.write('A23', 'Gross Profit Margin', txt)
            if filters.get('date_from'):
                if gross_profit_margin.get('Init_balance'):
                    sheet.write('B23', gross_profit_margin['Init_balance']['balance'] / 100, txt)
                else:
                    sheet.write('B23', float(0), txt)
                sheet.write('C23', gross_profit_margin['balance'] / 100, txt)
            else:
                sheet.write('B23', gross_profit_margin['balance'] / 100, txt)
        
        ## Activity Ratio ##
        for ar_turnover_ratio in total.get('report_lines_ar_turnover_ratio'):
            sheet.write('A25', 'Account Receivable Turnover Ratio', txt)
            if filters.get('date_from'):
                if ar_turnover_ratio.get('Init_balance'):
                    sheet.write('B25', ar_turnover_ratio['Init_balance']['balance'] / 100, txt)
                else:
                    sheet.write('B25', float(0), txt)
                sheet.write('C25', ar_turnover_ratio['balance'] / 100, txt)
            else:
                sheet.write('B25', ar_turnover_ratio['balance'] / 100, txt)
        
        for merchandise_inventory in total.get('report_lines_merchandise_inventory'):
            sheet.write('A26', 'Merchandise Inventory Turnover Ratio', txt)
            if filters.get('date_from'):
                if merchandise_inventory.get('Init_balance'):
                    sheet.write('B26', merchandise_inventory['Init_balance']['balance'] / 100, txt)
                else:
                    sheet.write('B26', float(0), txt)
                sheet.write('C26', merchandise_inventory['balance'] / 100, txt)
            else:
                sheet.write('B26', merchandise_inventory['balance'] / 100, txt)

        for total_assets in total.get('report_lines_total_assets'):
            sheet.write('A27', 'Total Asset Turnover Ratio', txt)
            if filters.get('date_from'):
                if total_assets.get('Init_balance'):
                    sheet.write('B27', total_assets['Init_balance']['balance'] / 100, txt)
                else:
                    sheet.write('B27', float(0), txt)
                sheet.write('C27', total_assets['balance'] / 100, txt)
            else:
                sheet.write('B27', total_assets['balance'] / 100, txt)
        
        for net_fixed_assets in total.get('report_lines_net_fixed_assets'):
            sheet.write('A28', 'Fixed Asset Turnover Ratio', txt)
            if filters.get('date_from'):
                if net_fixed_assets.get('Init_balance'):
                    sheet.write('B28', net_fixed_assets['Init_balance']['balance'] / 100, txt)
                else:
                    sheet.write('B28', float(0), txt)
                sheet.write('C28', net_fixed_assets['balance'] / 100, txt)
            else:
                sheet.write('B28', net_fixed_assets['balance'] / 100, txt)

        workbook.close()
        output.seek(0)
        response.stream.write(output.read())
        output.close()
