from odoo import api, models, fields, _

class AccountingFlowWizard(models.TransientModel):
    _name = 'accounting.flow.wizard'

    name = fields.Char(string='Name', default='Accounting Flow')

    def button_chart_account(self):
        action = self.env.ref('account.action_account_form').read()[0]
        return action

    def button_profit_loss(self):
        action = self.env.ref('dynamic_accounts_report.action_dynamic_profit_and_loss').read()[0]
        return action
    
    def button_journals(self):
        action = self.env.ref('account.action_account_journal_form').read()[0]
        return action
    
    def button_budget(self):
        action = self.env.ref('om_account_budget.act_crossovered_budget_view').read()[0]
        return action
    
    def button_balance_sheet(self):
        action = self.env.ref('dynamic_accounts_report.action_dynamic_balance_sheet').read()[0]
        return action
    
    def button_analytic_group(self):
        action = self.env.ref('analytic.account_analytic_tag_action').read()[0]
        return action
    
    def button_journal_entries(self):
        action = self.env.ref('account.action_move_journal_line').read()[0]
        return action
    
    def button_general_ledger(self):
        action = self.env.ref('dynamic_accounts_report.action_general_ledger').read()[0]
        return action
    
    def button_trial_balance(self):
        action = self.env.ref('dynamic_accounts_report.action_trial_balance').read()[0]
        return action
    
    def button_cash_flow(self):
        action = self.env.ref('dynamic_accounts_report.action_cash_flow').read()[0]
        return action
    
    def button_analytic_account(self):
        action = self.env.ref('analytic.action_account_analytic_account_form').read()[0]
        return action
    
    def button_recurring_journal(self):
        action = self.env.ref('equip3_accounting_recurring.recurring_journal_action').read()[0]
        return action
    
    def button_partner_ageing(self):
        action = self.env.ref('dynamic_accounts_report.action_ageing_partner').read()[0]
        return action
    
    def button_customer_statement(self):
        action = self.env.ref('equip3_accounting_reports.action_customer_statement').read()[0]
        return action
    
    def button_financial_ratio(self):
        action = self.env.ref('equip3_accounting_reports.action_financial_ratio').read()[0]
        return action
    
    def button_asset_progress(self):
        action = self.env.ref('equip3_accounting_asset.action_account_asset_cip').read()[0]
        return action
    
    def button_asset(self):
        action = self.env.ref('om_account_asset.action_account_asset_asset_form').read()[0]
        return action
    
    def button_partner_ledger(self):
        action = self.env.ref('dynamic_accounts_report.action_partner_ledger').read()[0]
        return action
    
    def button_equity(self):
        action = self.env.ref('equip3_accounting_reports.action_equity_move').read()[0]
        return action
