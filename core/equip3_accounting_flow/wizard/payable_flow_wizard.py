from odoo import api, models, fields, _

class PayableFlowWizard(models.TransientModel):
    _name = 'payable.flow.wizard'

    name = fields.Char(string='Name', default='Payable Flow')

    def button_vendors(self):
        action = self.env.ref('account.res_partner_action_supplier').read()[0]
        return action
    
    def button_bills(self):
        action = self.env.ref('account.action_move_in_invoice_type').read()[0]
        return action
    
    def button_payments(self):
        action = self.env.ref('account.action_account_payments_payable').read()[0]
        return action
    
    def button_partner_ageing(self):
        action = self.env.ref('dynamic_accounts_report.action_ageing_partner').read()[0]
        return action
    
    def button_currency(self):
        action = self.env.ref('base.action_currency_form').read()[0]
        return action
    
    def button_vendor_refunds(self):
        action = self.env.ref('account.action_move_in_refund_type').read()[0]
        return action
    
    def button_vendor_multi(self):
        action = self.env.ref('equip3_accounting_operation.action_account_multipayment_vendor').read()[0]
        return action
    
    def button_other_expense(self):
        action = self.env.ref('aos_account_voucher.action_review_voucher_list_aos_voucher').read()[0]
        return action
    
    def button_payment_voucher(self):
        action = self.env.ref('equip3_accounting_operation.vendor_voucher_payment_action').read()[0]
        return action
    
    def button_revaluation(self):
        action = self.env.ref('equip3_accounting_multicurrency.currency_invoice_revaluation_wizard_action').read()[0]
        return action
    
    def button_ibt(self):
        action = self.env.ref('equip3_accounting_operation.action_account_internal_transfer').read()[0]
        return action
    
    def button_recurring_bills(self):
        action = self.env.ref('equip3_accounting_recurring.recurring_bill_action').read()[0]
        return action
    
    def button_payment_giro(self):
        action = self.env.ref('equip3_accounting_operation.action_payment_giro').read()[0]
        return action
    
    def button_vendor_deposit(self):
        action = self.env.ref('equip3_accounting_deposit.action_vendor_deposit').read()[0]
        return action
    
    def button_bill_topay(self):
        action = self.env.ref('equip3_accounting_taxoperation.action_bill_invoice_tax_to_pay').read()[0]
        return action