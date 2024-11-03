from odoo import api, models, fields, _

class ReceivableFlowWizard(models.TransientModel):
    _name = 'receivable.flow.wizard'

    name = fields.Char(string='Name', default='Receivable Flow')

    def button_customers(self):
        action = self.env.ref('account.res_partner_action_customer').read()[0]
        return action
    
    def button_invoice(self):
        action = self.env.ref('account.action_move_out_invoice_type').read()[0] 
        return action
    
    def button_receipt(self):
        action = self.env.ref('account.action_account_payments').read()[0]
        return action
    
    def button_partner_ageing(self):
        action = self.env.ref('dynamic_accounts_report.action_ageing_partner').read()[0]
        return action
    
    def button_customer_statement(self):
        action = self.env.ref('equip3_accounting_reports.action_customer_statement').read()[0]
        return action
    
    def button_currency_receivable(self):
        action = self.env.ref('base.action_currency_form').read()[0]
        return action
    
    def button_credit_note(self):
        action = self.env.ref('account.action_move_out_refund_type').read()[0]
        return action
    
    def button_customer_multi(self):
        action = self.env.ref('equip3_accounting_operation.action_account_multipayment_customer').read()[0]
        return action
    
    def button_other_income(self):
        action = self.env.ref('aos_account_voucher.action_receipt_voucher_list_aos_voucher').read()[0]
        return action
    
    def button_receipt_giro(self):
        action = self.env.ref('equip3_accounting_operation.action_receipt_giro').read()[0]
        return action
    
    def button_revaluation(self):
        action = self.env.ref('equip3_accounting_multicurrency.currency_invoice_revaluation_wizard_action').read()[0]
        return action
    
    def button_ibt(self):
        action = self.env.ref('equip3_accounting_operation.action_account_internal_transfer').read()[0]
        return action
    
    def button_recurring_invoice(self):
        action = self.env.ref('equip3_accounting_recurring.invoice_recurring2_action').read()[0]
        return action
    
    def button_customer_topay(self):
        action = self.env.ref('equip3_accounting_taxoperation.action_invoice_tax_to_pay').read()[0]
        return action
    
    def button_customer_deposit(self):
        action = self.env.ref('equip3_accounting_deposit.action_customer_deposit').read()[0]
        return action