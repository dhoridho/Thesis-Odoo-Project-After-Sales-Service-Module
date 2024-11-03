from odoo import api, fields, models, _

class AccountCashFlowStatement(models.TransientModel):
    _inherit = 'account.cash.flow.statement'

    def _get_report_values(self, data, option):
        res = super(AccountCashFlowStatement, self)._get_report_values(data, option)

        if data['type_report'] == 'indirect':
            state = """ and state = 'posted' """ if data.get('target_move') == 'Posted' else ''
            account_tag_operating_indirect_id = self.env.ref('equip3_accounting_report_cashflow_id.account_tag_operating_indirect').id

            account_type_prepayments = self.env.ref('account.data_account_type_prepayments').id
            account_type_receipt = self.env.ref('account.data_account_type_receivable').id
            account_type_payable = self.env.ref('account.data_account_type_payable').id
            account_type_other_income = self.env.ref('account.data_account_type_other_income').id
            account_type_expense = self.env.ref('account.data_account_type_expenses').id
            account_type_current_assets = self.env.ref('account.data_account_type_current_assets').id
            account_type_current_liabilities = self.env.ref('account.data_account_type_current_liabilities').id

            cashin_account_type_ids = [account_type_current_assets, account_type_current_liabilities, account_type_receipt, account_type_payable]
            cashout_account_type_ids = [account_type_current_assets, account_type_current_liabilities, account_type_payable]
            addition_account_type_ids = [account_type_expense, account_type_current_assets, account_type_current_liabilities, account_type_prepayments, account_type_payable]
            deduction_account_type_ids = [account_type_other_income, account_type_current_assets, account_type_current_liabilities, account_type_receipt, account_type_payable]

            opt = "" 

            query8 = self._query_8(opt, state, cashin_account_type_ids, data, account_tag_operating_indirect_id)
            cf_operating_cashin_indirect = query8['result']
            cf_operating_cashin_indirect_account = query8['result_account']

            query9 = self._query_9(opt, state, cashout_account_type_ids, data, account_tag_operating_indirect_id)
            cf_operating_cashout_indirect = query9['result']
            cf_operating_cashout_indirect_account = query9['result_account']

            query_addition = self._query_addition(opt, state, addition_account_type_ids, data, account_tag_operating_indirect_id)
            cf_operating_addition = query_addition['result']
            cf_operating_addition_account = query_addition['result_account']

            query_deduction = self._query_deduction(opt, state, deduction_account_type_ids, data, account_tag_operating_indirect_id)
            cf_operating_deduction = query_deduction['result']
            cf_operating_deduction_account = query_deduction['result_account']

            res['cf_operating_cashin_indirect'] = cf_operating_cashin_indirect
            res['cf_operating_cashin_indirect_account'] = cf_operating_cashin_indirect_account
            res['cf_operating_cashout_indirect'] = cf_operating_cashout_indirect
            res['cf_operating_cashout_indirect_account'] = cf_operating_cashout_indirect_account
            res['cf_operating_addition'] = cf_operating_addition
            res['cf_operating_addition_account'] = cf_operating_addition_account
            res['cf_operating_deduction'] = cf_operating_deduction
            res['cf_operating_deduction_account'] = cf_operating_deduction_account

        return res