from odoo import api , fields , models, _
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta

class ResCompany(models.Model):
    _inherit = 'res.company'

    accounting = fields.Boolean(string="Accounting")

class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    is_invoice_approval_matrix = fields.Boolean(string="Invoice Approval Matrix")
    is_bill_approval_matrix = fields.Boolean(string="Bill Approval Matrix")
    is_other_income_approval_matrix = fields.Boolean(string="Other Income Approval Matrix")
    is_other_expense_approval_matrix = fields.Boolean(string="Other Expense Approval Matrix")

    is_customer_multi_receipt_approval_matrix = fields.Boolean(string="Customer Multi Receipt Approval Matrix")
    is_vendor_multipayment_approval_matrix = fields.Boolean(string="Vendor Multi Payment Approval Matrix")
    is_receipt_approval_matrix = fields.Boolean(string="Receipt Approval Matrix")
    is_payment_approval_matrix = fields.Boolean(string="Payment Approval Matrix")
    is_payment_voucher_approval_matrix = fields.Boolean(string="Payment Voucher Approval Matrix")

    accounting = fields.Boolean(string="Acccounting", related='company_id.accounting', readonly=False)

    is_cost_price_per_warehouse = fields.Boolean(string="Cost Price Per Warehouse")

    group_is_invoice_approval_matrix = fields.Boolean(string="Invoice Approval Matrix",
        implied_group='equip3_accounting_accessright_setting.group_is_invoice_approval_matrix')
    group_is_bill_approval_matrix = fields.Boolean(string="Bill Approval Matrix",
        implied_group='equip3_accounting_accessright_setting.group_is_bill_approval_matrix')
    group_is_other_income_approval_matrix = fields.Boolean(string="Other Income Approval Matrix",
        implied_group='equip3_accounting_accessright_setting.group_is_other_income_approval_matrix')
    group_is_other_expense_approval_matrix = fields.Boolean(string="Other Expense Approval Matrix",
        implied_group='equip3_accounting_accessright_setting.group_is_other_expense_approval_matrix')
    group_is_customer_multi_receipt_approval_matrix = fields.Boolean(string="Customer Multi Receipt Approval Matrix",
        implied_group='equip3_accounting_accessright_setting.group_is_customer_multi_receipt_approval_matrix')
    group_is_vendor_multipayment_approval_matrix = fields.Boolean(string="Vendor Multi Payment Approval Matrix",
        implied_group='equip3_accounting_accessright_setting.group_is_vendor_multipayment_approval_matrix')
    group_is_receipt_approval_matrix = fields.Boolean(string="Receipt Approval Matrix",
        implied_group='equip3_accounting_accessright_setting.group_is_receipt_approval_matrix')
    group_is_payment_approval_matrix = fields.Boolean(string="Payment Approval Matrix",
        implied_group='equip3_accounting_accessright_setting.group_is_payment_approval_matrix')
    group_is_payment_voucher_approval_matrix = fields.Boolean(string="Payment Voucher Approval Matrix",
        implied_group='equip3_accounting_accessright_setting.group_is_payment_voucher_approval_matrix')
    
    module_om_account_budget = fields.Boolean(string='Budget Management')
    Use_received_date = fields.Boolean(string='Use Received Date')

    automated_invoice_followup = fields.Boolean(string='Automated Invoice Follow-Up')
    followup_sending_date = fields.Selection([
                            ('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5'), 
                            ('6', '6'), ('7', '7'), ('8', '8'), ('9', '9'), ('10', '10'), 
                            ('11', '11'), ('12', '12'), ('13', '13'), ('14', '14'), ('15', '15'), 
                            ('16', '16'), ('17', '17'), ('18', '18'), ('19', '19'), ('20', '20'), 
                            ('21', '21'), ('22', '22'), ('23', '23'), ('24', '24'), ('25', '25'), 
                            ('26', '26'), ('27', '27'), ('28', '28 (End of Month)'), ('29', '29 (End of Month)'), ('30', '30 (End of Month)'), 
                            ('31', '31 (End of Month)')
                            ], string='Follow-Up Sending Date')



    @api.onchange('module_om_account_budget')
    def onchange_module_om_account_budget(self):
        if self.module_om_account_budget:
            self.group_analytic_accounting = True
    @api.onchange('group_om_account_budget')
    def _onchange_group_analytic_tags(self):
        if self.group_om_account_budget:
            self.group_analytic_tags = True
            self.group_analytic_accounting = False
            self.module_product_margin = False
    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        res.update({
            'is_invoice_approval_matrix': IrConfigParam.get_param('is_invoice_approval_matrix', False),
            'is_bill_approval_matrix': IrConfigParam.get_param('is_bill_approval_matrix', False),
            'is_other_income_approval_matrix': IrConfigParam.get_param('is_other_income_approval_matrix', False),
            'is_other_expense_approval_matrix': IrConfigParam.get_param('is_other_expense_approval_matrix', False),
            'is_payment_voucher_approval_matrix': IrConfigParam.get_param('is_payment_voucher_approval_matrix', False),
            'is_cost_price_per_warehouse': IrConfigParam.get_param('is_cost_price_per_warehouse', False),

            'is_customer_multi_receipt_approval_matrix': IrConfigParam.get_param('is_customer_multi_receipt_approval_matrix', False),
            'is_vendor_multipayment_approval_matrix': IrConfigParam.get_param('is_vendor_multipayment_approval_matrix', False),
            'is_receipt_approval_matrix': IrConfigParam.get_param('is_receipt_approval_matrix', False),
            'is_payment_approval_matrix': IrConfigParam.get_param('is_payment_approval_matrix', False),
            'accounting': IrConfigParam.get_param('accounting', False),

            'automated_invoice_followup': IrConfigParam.get_param('automated_invoice_followup', False),
            'followup_sending_date': IrConfigParam.get_param('followup_sending_date', '1'),
            'Use_received_date': IrConfigParam.get_param('Use_received_date', False),


        })
        if res['automated_invoice_followup']:
            followup_sending_date = IrConfigParam.get_param('followup_sending_date', '1')
            cronjob = self.env.ref('equip3_accounting_operation.cron_automated_followup_invoice')
            nextcalldate = cronjob.nextcall
            if cronjob.interval_type == 'months':
                if  int(followup_sending_date) <= int(self.last_day_of_month(nextcalldate).day):
                    nextcall = datetime(nextcalldate.year, nextcalldate.month, int(followup_sending_date), nextcalldate.hour, nextcalldate.minute, nextcalldate.second)
                else:
                    nextcall = datetime(nextcalldate.year, nextcalldate.month, int(self.last_day_of_month(nextcalldate).day), nextcalldate.hour, nextcalldate.minute, nextcalldate.second)
                cronjob.update({'nextcall' : nextcall}) 
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        ISP = self.env['ir.config_parameter'].sudo()
        ISP.set_param('is_invoice_approval_matrix', self.is_invoice_approval_matrix)
        ISP.set_param('is_bill_approval_matrix', self.is_bill_approval_matrix)
        ISP.set_param('is_other_income_approval_matrix', self.is_other_income_approval_matrix)
        ISP.set_param('is_other_expense_approval_matrix', self.is_other_expense_approval_matrix)
        ISP.set_param('is_payment_voucher_approval_matrix', self.is_payment_voucher_approval_matrix)
        ISP.set_param('is_cost_price_per_warehouse', self.is_cost_price_per_warehouse)

        ISP.set_param('is_customer_multi_receipt_approval_matrix', self.is_customer_multi_receipt_approval_matrix)
        ISP.set_param('is_vendor_multipayment_approval_matrix', self.is_vendor_multipayment_approval_matrix)
        ISP.set_param('is_receipt_approval_matrix', self.is_receipt_approval_matrix)
        ISP.set_param('is_payment_approval_matrix', self.is_payment_approval_matrix)
        ISP.set_param('accounting', self.accounting)

        ISP.set_param('automated_invoice_followup', self.automated_invoice_followup)
        ISP.set_param('followup_sending_date', self.followup_sending_date)
        ISP.set_param('Use_received_date', self.Use_received_date)

        if self.automated_invoice_followup:
            followup_sending_date = self.followup_sending_date
            cronjob = self.env.ref('equip3_accounting_operation.cron_automated_followup_invoice')
            nextcalldate = cronjob.nextcall
            if cronjob.interval_type == 'months':
                if  int(followup_sending_date) <= int(self.last_day_of_month(nextcalldate).day):
                    nextcall = datetime(nextcalldate.year, nextcalldate.month, int(followup_sending_date), nextcalldate.hour, nextcalldate.minute, nextcalldate.second)
                else:
                    nextcall = datetime(nextcalldate.year, nextcalldate.month, int(self.last_day_of_month(nextcalldate).day), nextcalldate.hour, nextcalldate.minute, nextcalldate.second)
                cronjob.update({'nextcall' : nextcall})

    
    @api.onchange('is_invoice_approval_matrix',
                  'is_bill_approval_matrix',
                  'is_other_income_approval_matrix',
                  'is_other_expense_approval_matrix',
                  'is_customer_multi_receipt_approval_matrix',
                  'is_vendor_multipayment_approval_matrix',
                  'is_receipt_approval_matrix',
                  'is_payment_approval_matrix',
                  'is_payment_voucher_approval_matrix')
    def onchange_aproval_matrix_bool(self):
        self.group_is_invoice_approval_matrix = self.is_invoice_approval_matrix
        self.group_is_bill_approval_matrix = self.is_bill_approval_matrix
        self.group_is_other_income_approval_matrix = self.is_other_income_approval_matrix
        self.group_is_other_expense_approval_matrix = self.is_other_expense_approval_matrix
        self.group_is_customer_multi_receipt_approval_matrix = self.is_customer_multi_receipt_approval_matrix
        self.group_is_vendor_multipayment_approval_matrix = self.is_vendor_multipayment_approval_matrix
        self.group_is_receipt_approval_matrix = self.is_receipt_approval_matrix
        self.group_is_payment_approval_matrix = self.is_payment_approval_matrix
        self.group_is_payment_voucher_approval_matrix = self.is_payment_voucher_approval_matrix

    @api.onchange('accounting')
    def onchange_aproval_matrix(self):
        if self.accounting == False:
            self.is_invoice_approval_matrix = False
            self.is_bill_approval_matrix = False
            self.is_other_income_approval_matrix = False
            self.is_other_expense_approval_matrix = False
            self.is_customer_multi_receipt_approval_matrix = False
            self.is_vendor_multipayment_approval_matrix = False
            self.is_receipt_approval_matrix = False
            self.is_payment_approval_matrix = False
            self.is_payment_voucher_approval_matrix = False
            self.is_credit_note_approval_matrix = False
            self.is_refund_approval_matrix = False
            self.is_customer_deposit_approval_matrix = False
            self.is_vendor_deposit_approval_matrix = False
            self.is_receipt_giro_approval_matrix = False
            self.is_payment_giro_approval_matrix = False
            self.is_internal_transfer_approval_matrix = False
            self.is_purchase_currency_approval_matrix = False
            self.is_budget_approval_matrix = False
            self.is_budget_change_req_approval_matrix = False
            self.is_purchase_budget_approval_matrix = False
            self.is_purchase_budget_change_req_approval_matrix = False
            self.is_assets_approving_matrix = False
            self.is_cash_advance_approving_matrix = False

    def last_day_of_month(self, day):
        next_month = day.replace(day=28) + relativedelta(days=4)
        return next_month - relativedelta(days=next_month.day)

