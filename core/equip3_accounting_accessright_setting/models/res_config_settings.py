from odoo import api, fields, models, modules, _
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta


class ResCompany(models.Model):
    _inherit = 'res.company'

    accounting = fields.Boolean(string="Accounting")
    is_inverse_rate = fields.Boolean(string="Use Inverse Rate")
    is_taxes_rate = fields.Boolean(string="Taxes have different exchange rate")

    #Multicurency Config
    unrealized_exchange_journal_id = fields.Many2one(
        comodel_name='account.journal',string="Unrealized Exchange Journal",
        domain="[('company_id', '=', company_id), ('type', '=', 'general')]")
    income_unrealized_exchange_account_id = fields.Many2one(
        comodel_name="account.account",string="Unrealized Gain Account",
        domain=lambda self: "[('internal_type', '=', 'other'), ('deprecated', '=', False), ('company_id', '=', company_id),\
                             ('user_type_id', 'in', %s)]" % [self.env.ref('account.data_account_type_revenue').id,self.env.ref('account.data_account_type_other_income').id])
    expense_unrealized_exchange_account_id = fields.Many2one(
        comodel_name="account.account", string="Unrealized Loss Account",
        domain=lambda self: "[('internal_type', '=', 'other'), ('deprecated', '=', False), ('company_id', '=', company_id),\
                             ('user_type_id', '=', %s)]" % self.env.ref('account.data_account_type_expenses').id)
    
    # tax_discount_policy = fields.Selection([('untax', 'After Discount'), ('tax', 'Before Discount')], string='Tax Applies on')
    tax_discount_policy = fields.Selection(selection_add=[('untax', 'After Discount'), ('tax', 'Before Discount')], string='Tax Applies on')
    sale_account_id = fields.Many2one('account.account', 'Sale Discount Account',
        domain="[('company_id', '=', current_company_id), ('discount_account','=',True), ('user_type_id.internal_group','in',['expense'])]", 
        help="Only set value with string account = Sale Discount")
    purchase_account_id = fields.Many2one('account.account', 'Purchase Discount Account',
        domain="[('company_id', '=', current_company_id), ('discount_account','=',True),('user_type_id.internal_group','in',['income'])]",
        help="Only set value with string account = Purchase Discount")

    interest_income = fields.Many2one('account.account', 
        string="Interest Income Account", 
        domain="[('company_id', '=', current_company_id),('user_type_id.internal_group','in',['income'])]", 
        help="Only set value with string account = Interest Income")
    interest_expense = fields.Many2one('account.account', 
        string="Interest Expense Account",
        domain="[('company_id', '=', current_company_id),('user_type_id.internal_group','in',['expense'])]",
        help="Only set value with string account = Interest Expense")
    deposit_reconcile_journal_id = fields.Many2one('account.journal', 
        string="Reconcile Journal",
        domain="[('company_id', '=', current_company_id)]")
    journal_id = fields.Many2one('account.journal', 
        string="Payment Method",
        domain="[('company_id', '=', current_company_id)]")
    deposit_account_id = fields.Many2one('account.account', domain="[('company_id', '=', current_company_id)]", string="Advance Account")
    post_discount_account = fields.Boolean(string='Post Discount Account')


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    WEEK_DATA = [('monday', 'Monday'), 
                    ('tuesday', 'Tuesday'),
                    ('wednesday', 'Wednesday'),
                    ('thursday', 'Thursday'),
                    ('friday', 'Friday'),
                    ('saturday', 'Saturday'),
                    ('sunday', 'Sunday')
                    ]

    DAYS_DATA = [('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5'), 
                    ('6', '6'), ('7', '7'), ('8', '8'), ('9', '9'), ('10', '10'), 
                    ('11', '11'), ('12', '12'), ('13', '13'), ('14', '14'), ('15', '15'), 
                    ('16', '16'), ('17', '17'), ('18', '18'), ('19', '19'), ('20', '20'), 
                    ('21', '21'), ('22', '22'), ('23', '23'), ('24', '24'), ('25', '25'), 
                    ('26', '26'), ('27', '27'), ('28', '28 (End of Month)'), ('29', '29 (End of Month)'), ('30', '30 (End of Month)'), 
                    ('31', '31 (End of Month)')
                ]

    #Multicurency Config
    currency_exchange_journal_id = fields.Many2one(
        comodel_name='account.journal', related='company_id.currency_exchange_journal_id', readonly=False, 
        string="Currency Exchange Journal Edited", domain="[('company_id', '=', company_id), ('type', '=', 'general')]",
        help='The accounting journal where automatic exchange differences will be registered')
    income_currency_exchange_account_id = fields.Many2one(
        comodel_name="account.account", related="company_id.income_currency_exchange_account_id", string="Gain Account", readonly=False,
        domain=lambda self: "[('internal_type', '=', 'other'), ('deprecated', '=', False), ('company_id', '=', company_id),\
                             ('user_type_id', 'in', %s)]" % [self.env.ref('account.data_account_type_revenue').id,self.env.ref('account.data_account_type_other_income').id])
    expense_currency_exchange_account_id = fields.Many2one(
        comodel_name="account.account", related="company_id.expense_currency_exchange_account_id", string="Loss Account", readonly=False,
        domain=lambda self: "[('internal_type', '=', 'other'), ('deprecated', '=', False), ('company_id', '=', company_id),\
                             ('user_type_id', '=', %s)]" % self.env.ref('account.data_account_type_expenses').id)
    unrealized_exchange_journal_id = fields.Many2one(
        comodel_name='account.journal', related='company_id.unrealized_exchange_journal_id',  readonly=False, string="Unrealized Exchange Journal",
        domain="[('company_id', '=', company_id), ('type', '=', 'general')]")
    income_unrealized_exchange_account_id = fields.Many2one(
        comodel_name="account.account", related="company_id.income_unrealized_exchange_account_id", string="Unrealized Gain Account", readonly=False,
        domain=lambda self: "[('internal_type', '=', 'other'), ('deprecated', '=', False), ('company_id', '=', company_id),\
                             ('user_type_id', 'in', %s)]" % [self.env.ref('account.data_account_type_revenue').id, self.env.ref('account.data_account_type_other_income').id])
    expense_unrealized_exchange_account_id = fields.Many2one(
        comodel_name="account.account", related="company_id.expense_unrealized_exchange_account_id", string="Unrealized Loss Account", readonly=False,
        domain=lambda self: "[('internal_type', '=', 'other'), ('deprecated', '=', False), ('company_id', '=', company_id),\
                             ('user_type_id', '=', %s)]" % self.env.ref('account.data_account_type_expenses').id)

    is_inverse_rate = fields.Boolean(related="company_id.is_inverse_rate", readonly=False)
    is_taxes_rate = fields.Boolean(related="company_id.is_taxes_rate", readonly=False)

    tax_discount_policy = fields.Selection(
        string='Tax Applies on',
        related="company_id.tax_discount_policy",
        readonly=False)
    sale_account_id = fields.Many2one('account.account', 'Sale Discount Account',
        domain="[('company_id', '=', current_company_id), ('discount_account','=',True), ('user_type_id.internal_group','in',['expense'])]", 
        related="company_id.sale_account_id",
        readonly=False,
        help="Only set value with string account = Sale Discount")
    purchase_account_id = fields.Many2one('account.account', 'Purchase Discount Account',
        domain="[('company_id', '=', current_company_id), ('discount_account','=',True),('user_type_id.internal_group','in',['income'])]",
        related="company_id.purchase_account_id",
        readonly=False,
        help="Only set value with string account = Purchase Discount")
    interest_income = fields.Many2one('account.account',
        string="Interest Income Account",
        domain="[('company_id', '=', current_company_id),('user_type_id.internal_group','in',['income'])]",
        related="company_id.interest_income",
        readonly=False,
        help="Only set value with string account = Interest Income")
    interest_expense = fields.Many2one('account.account', 
        string="Interest Expense Account", 
        domain="[('company_id', '=', current_company_id),('user_type_id.internal_group','in',['expense'])]", 
        related="company_id.interest_expense",
        readonly=False,
        help="Only set value with string account = Interest Expense")
    deposit_reconcile_journal_id = fields.Many2one('account.journal', 
        string="Reconcile Journal",
        domain="[('company_id', '=', current_company_id)]",
        related="company_id.deposit_reconcile_journal_id", 
        readonly=False)
    journal_id = fields.Many2one('account.journal', 
        string="Payment Method",
        domain="[('company_id', '=', current_company_id)]",
        related="company_id.journal_id", 
        readonly=False)
    deposit_account_id = fields.Many2one('account.account', 
        string="Advance Account", 
        domain="[('company_id', '=', current_company_id)]",
        related="company_id.deposit_account_id", 
        readonly=False)
    petty_cash_expense_account_id = fields.Many2one('account.account', 
        string="Petty Cash Expense Account", 
        domain="[('user_type_id.name', 'in', ('Expenses', 'Cost of Revenue')),('company_id', '=', current_company_id)]")
    overdue_template = fields.Text(string='Overdue Payments Message')
    tax_rounding_type = fields.Selection([
        ('round_type_up', 'Tax Round Up'),('round_type_down','Tax Round Down'),('round_type_normal','Tax Round Half-up')
    ], string='Tax Rounding Type')

    # Approval Matrix Config
    accounting = fields.Boolean(string="Acccounting", related='company_id.accounting', readonly=False)
    is_credit_note_approval_matrix = fields.Boolean(string='Credit Note Approval Matrix')
    is_refund_approval_matrix = fields.Boolean(string='Refund Approval Matrix')
    is_customer_deposit_approval_matrix = fields.Boolean(string='Customer Deposit Approval Matrix')
    is_vendor_deposit_approval_matrix = fields.Boolean(string='Vendor Deposit Approval Matrix')
    is_receipt_giro_approval_matrix = fields.Boolean(string='Receipt Giro Approval Matrix')
    is_payment_giro_approval_matrix = fields.Boolean(string='Payment Giro Approval Matrix')
    is_internal_transfer_approval_matrix = fields.Boolean(string='Internal Bank/Cash Approval Matrix')
    is_purchase_currency_approval_matrix = fields.Boolean(string='Purchase Currency Approval Matrix')
    is_budget_approval_matrix = fields.Boolean(string='Budget Approval Matrix')
    is_budget_change_req_approval_matrix = fields.Boolean(string='Budget Change Request Approval Matrix')
    is_purchase_budget_approval_matrix = fields.Boolean(string='Purchase Budget Approval Matrix')
    is_purchase_budget_change_req_approval_matrix = fields.Boolean(string='Purchase Budget Change Request Approval Matrix')
    is_internal_transaction = fields.Boolean(string="Use Internal Company Transaction")
    is_analytic_groups_balance_sheet = fields.Boolean(string="Use analytic groups in balance sheet")
    is_assets_approving_matrix = fields.Boolean(string="Assets Approval Matrix")
    is_cash_advance_approving_matrix = fields.Boolean(string="Cash Advance Approval Matrix")
    is_invoice_approval_matrix = fields.Boolean(string="Invoice Approval Matrix")
    is_bill_approval_matrix = fields.Boolean(string="Bill Approval Matrix")
    is_other_income_approval_matrix = fields.Boolean(string="Other Income Approval Matrix")
    is_other_expense_approval_matrix = fields.Boolean(string="Other Expense Approval Matrix")
    is_customer_multi_receipt_approval_matrix = fields.Boolean(string="Customer Multi Receipt Approval Matrix")
    is_vendor_multipayment_approval_matrix = fields.Boolean(string="Vendor Multi Payment Approval Matrix")
    is_receipt_approval_matrix = fields.Boolean(string="Receipt Approval Matrix")
    is_payment_approval_matrix = fields.Boolean(string="Payment Approval Matrix")
    is_payment_voucher_approval_matrix = fields.Boolean(string="Payment Voucher Approval Matrix")    

    group_is_credit_note_approval_matrix = fields.Boolean(string='Group Credit Note Approval Matrix',
        implied_group='equip3_accounting_accessright_setting.group_is_credit_note_approval_matrix')
    group_is_refund_approval_matrix = fields.Boolean(string='Group Refund Approval Matrix',
        implied_group='equip3_accounting_accessright_setting.group_is_refund_approval_matrix')
    group_is_customer_deposit_approval_matrix = fields.Boolean(string='Group Customer Deposit Approval Matrix',
        implied_group='equip3_accounting_accessright_setting.group_is_customer_deposit_approval_matrix')
    group_is_vendor_deposit_approval_matrix = fields.Boolean(string='Group Vendor Deposit Approval Matrix',
        implied_group='equip3_accounting_accessright_setting.group_is_vendor_deposit_approval_matrix')
    group_is_receipt_giro_approval_matrix = fields.Boolean(string='Group Receipt Giro Approval Matrix',
        implied_group='equip3_accounting_accessright_setting.group_is_receipt_giro_approval_matrix')
    group_is_payment_giro_approval_matrix = fields.Boolean(string='Group Payment Giro Approval Matrix',
        implied_group='equip3_accounting_accessright_setting.group_is_payment_giro_approval_matrix')
    group_is_internal_transfer_approval_matrix = fields.Boolean(string='Group Internal Bank/Cash Approval Matrix',
        implied_group='equip3_accounting_accessright_setting.group_is_internal_transfer_approval_matrix')
    group_is_purchase_currency_approval_matrix = fields.Boolean(string='Group Purchase Currency Approval Matrix',
        implied_group='equip3_accounting_accessright_setting.group_is_purchase_currency_approval_matrix')
    group_is_budget_approval_matrix = fields.Boolean(string='Group Budget Approval Matrix',
        implied_group='equip3_accounting_accessright_setting.group_is_budget_approval_matrix')
    group_is_budget_change_req_approval_matrix = fields.Boolean(string='Group Budget Change Request Approval Matrix',
        implied_group='equip3_accounting_accessright_setting.group_is_budget_change_req_approval_matrix')
    group_is_purchase_budget_approval_matrix = fields.Boolean(string='Group Purchase Budget Approval Matrix',
        implied_group='equip3_accounting_accessright_setting.group_is_purchase_budget_approval_matrix')
    group_is_purchase_budget_change_req_approval_matrix = fields.Boolean(string='Group Purchase Budget Change Request Approval Matrix',
        implied_group='equip3_accounting_accessright_setting.group_is_purchase_budget_change_req_approval_matrix')
    group_account_asset_category_fiscal = fields.Boolean(string='Group Fiscal Asset Group',
        implied_group='equip3_accounting_accessright_setting.group_account_asset_category_fiscal')
    group_assets_approving_matrix = fields.Boolean(string='Group Assets Approval Matrix',
        implied_group='equip3_accounting_accessright_setting.group_assets_approving_matrix')
    group_cash_advance_approval_matrix = fields.Boolean(string='Group Cash Advance Approval Matrix',
        implied_group='equip3_accounting_accessright_setting.group_cash_advance_approval_matrix')
    group_is_invoice_approval_matrix = fields.Boolean(string="Group Invoice Approval Matrix",
        implied_group='equip3_accounting_accessright_setting.group_is_invoice_approval_matrix')
    group_is_bill_approval_matrix = fields.Boolean(string="Group Bill Approval Matrix",
        implied_group='equip3_accounting_accessright_setting.group_is_bill_approval_matrix')
    group_is_other_income_approval_matrix = fields.Boolean(string="Group Other Income Approval Matrix",
        implied_group='equip3_accounting_accessright_setting.group_is_other_income_approval_matrix')
    group_is_other_expense_approval_matrix = fields.Boolean(string="Group Other Expense Approval Matrix",
        implied_group='equip3_accounting_accessright_setting.group_is_other_expense_approval_matrix')
    group_is_customer_multi_receipt_approval_matrix = fields.Boolean(string="Group Customer Multi Receipt Approval Matrix",
        implied_group='equip3_accounting_accessright_setting.group_is_customer_multi_receipt_approval_matrix')
    group_is_vendor_multipayment_approval_matrix = fields.Boolean(string="Group Vendor Multi Payment Approval Matrix",
        implied_group='equip3_accounting_accessright_setting.group_is_vendor_multipayment_approval_matrix')
    group_is_receipt_approval_matrix = fields.Boolean(string="Group Receipt Approval Matrix",
        implied_group='equip3_accounting_accessright_setting.group_is_receipt_approval_matrix')
    group_is_payment_approval_matrix = fields.Boolean(string="Group Payment Approval Matrix",
        implied_group='equip3_accounting_accessright_setting.group_is_payment_approval_matrix')
    group_is_payment_voucher_approval_matrix = fields.Boolean(string="Group Payment Voucher Approval Matrix",
        implied_group='equip3_accounting_accessright_setting.group_is_payment_voucher_approval_matrix')
    
    module_om_account_budget = fields.Boolean(string='Budget Management')
    Use_received_date = fields.Boolean(string='Use Received Date')
    customer_availability = fields.Boolean(string='Customer Availability')
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
    reminder_interval_before = fields.Integer(string='Before Due Date')
    reminder_interval_before_unit = fields.Selection([
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months'),
        ], string='')
    reminder_notification_before = fields.Integer(string='')
    reminder_interval_after = fields.Integer(string='After Maturity')
    reminder_interval_after_unit = fields.Selection([
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months'),
        ], string='')
    reminder_notification_after = fields.Integer(string='')
    
    invoice_bill_reminder = fields.Boolean(string='Invoice and Bill Reminder')
    reminder_interval_before_invoice = fields.Integer(string='Before Invoice Due Date')
    reminder_interval_after_invoice = fields.Integer(string='After Invoice Maturity')
    reminder_interval_before_unit_invoice = fields.Selection([('days', 'Days'), ('weeks', 'Weeks'),('months', 'Months')])
    eminder_interval_after_unit_invoice = fields.Selection([('days', 'Days'), ('weeks', 'Weeks'),('months', 'Months')])
    reminder_notification_before_invoice = fields.Integer(string='')
    reminder_notification_after_invoice = fields.Integer(string='')
    days_bill_before  = fields.Selection(WEEK_DATA)
    days_bill_after  = fields.Selection(WEEK_DATA)
    days_invoice_before   = fields.Selection(WEEK_DATA)
    days_invoice_after  = fields.Selection(WEEK_DATA)
    sending_date_bill_before   = fields.Selection(DAYS_DATA)
    sending_date_bill_after  = fields.Selection(DAYS_DATA)
    sending_date_invoice_before    = fields.Selection(DAYS_DATA)
    sending_date_invoice_after   = fields.Selection(DAYS_DATA)
    date_last_reminder_due_date   = fields.Date("Date Last Invoice Send", default=datetime.today().date(),)
    date_last_reminder_after_due_date   = fields.Date("Date Last reminder after due date", default=datetime.today().date(),)
    date_last_reminder_bill_due_date   = fields.Date("Date Last reminder bill due date", default=datetime.today().date(),)
    date_last_reminder_bill_after_due_date   = fields.Date("Date Last reminder bill after due date", default=datetime.today().date(),)
    date_last_reminder_bill_before_due_date   = fields.Date("Date Last reminder bill before due date", default=datetime.today().date(),) 

    is_invoice_cutoff_date = fields.Boolean(string='Multi payment Invoice Cut Off Date')
    invoice_cutoff_date = fields.Selection([
                            ('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5'), 
                            ('6', '6'), ('7', '7'), ('8', '8'), ('9', '9'), ('10', '10'), 
                            ('11', '11'), ('12', '12'), ('13', '13'), ('14', '14'), ('15', '15'), 
                            ('16', '16'), ('17', '17'), ('18', '18'), ('19', '19'), ('20', '20'), 
                            ('21', '21'), ('22', '22'), ('23', '23'), ('24', '24'), ('25', '25'), 
                            ('26', '26'), ('27', '27'), ('28', '28 (End of Month)'), ('29', '29 (End of Month)'), ('30', '30 (End of Month)'), 
                            ('31', '31 (End of Month)')
                            ], string='Cut Off Date')
    post_discount_account = fields.Boolean(string='Post Discount Account',related="company_id.post_discount_account", readonly=False)
           
    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        ICP = self.env['ir.config_parameter'].sudo()
        res.update({
            'overdue_template': ICP.get_param('overdue_template',
                                              'Dear Sir/Madam,\n\nOur records indicate that some payments on your account are still due. \
                                               Please find details below. If the amount has already been paid, please disregard this notice. \
                                               Otherwise, please forward us the total amount stated below. If you have any queries regarding your account, \
                                               please contact us.\n\nThank you in advance for your cooperation.\nBest Regards,'),
            'is_credit_note_approval_matrix': ICP.get_param('is_credit_note_approval_matrix', False),
            'is_refund_approval_matrix': ICP.get_param('is_refund_approval_matrix', False),
            'is_customer_deposit_approval_matrix': ICP.get_param('is_customer_deposit_approval_matrix', False),
            'is_vendor_deposit_approval_matrix': ICP.get_param('is_vendor_deposit_approval_matrix', False),
            'is_receipt_giro_approval_matrix': ICP.get_param('is_receipt_giro_approval_matrix', False),
            'is_payment_giro_approval_matrix': ICP.get_param('is_payment_giro_approval_matrix', False),
            'is_internal_transfer_approval_matrix': ICP.get_param('is_internal_transfer_approval_matrix', False),
            'is_purchase_currency_approval_matrix': ICP.get_param('is_purchase_currency_approval_matrix', False),
            'is_budget_approval_matrix': ICP.get_param('is_budget_approval_matrix', False),
            'is_budget_change_req_approval_matrix': ICP.get_param('is_budget_change_req_approval_matrix', False),
            'is_purchase_budget_approval_matrix': ICP.get_param('is_purchase_budget_approval_matrix', False),
            'is_cash_advance_approving_matrix': ICP.get_param('is_cash_advance_approving_matrix', False),
            'is_assets_approving_matrix': ICP.get_param('is_assets_approving_matrix', False),
            'is_purchase_budget_change_req_approval_matrix': ICP.get_param('is_purchase_budget_change_req_approval_matrix', False),
            'is_internal_transaction': ICP.get_param('is_internal_transaction', False),
            'is_analytic_groups_balance_sheet': ICP.get_param('is_analytic_groups_balance_sheet', False),
            'reminder_interval_before': ICP.get_param('reminder_interval_before', 1),
            'reminder_interval_after': ICP.get_param('reminder_interval_after', 1),
            'reminder_interval_before_unit': ICP.get_param('reminder_interval_before_unit', 'days'),
            'reminder_interval_after_unit': ICP.get_param('reminder_interval_after_unit', 'days'),
            'reminder_notification_before': ICP.get_param('reminder_notification_before', 1),
            'reminder_notification_after': ICP.get_param('reminder_notification_after', 1),
            'petty_cash_expense_account_id': int(ICP.get_param('petty_cash_expense_account_id')),
            'tax_rounding_type': ICP.get_param('tax_rounding_type', False),
            'invoice_bill_reminder': ICP.get_param('invoice_bill_reminder', False),
            'reminder_interval_before_invoice': ICP.get_param('reminder_interval_before_invoice', 1),
            'reminder_interval_after_invoice': ICP.get_param('reminder_interval_after_invoice', 1),
            'reminder_interval_before_unit_invoice': ICP.get_param('reminder_interval_before_unit_invoice',  'days'),
            'eminder_interval_after_unit_invoice': ICP.get_param('eminder_interval_after_unit_invoice','days'),
            'reminder_notification_before_invoice': ICP.get_param('reminder_notification_before_invoice', 1),
            'reminder_notification_after_invoice': ICP.get_param('reminder_notification_after_invoice', 1),
            'days_bill_before' : ICP.get_param('days_bill_before', 'monday'),
            'days_bill_after' : ICP.get_param('days_bill_after', 'monday'),
            'days_invoice_before' : ICP.get_param('days_invoice_before', 'monday'),
            'days_invoice_after' : ICP.get_param('days_invoice_after', 'monday'),
            'sending_date_bill_before' : ICP.get_param('sending_date_bill_before', '1'),
            'sending_date_bill_after' : ICP.get_param('sending_date_bill_after', '1'),
            'sending_date_invoice_before' : ICP.get_param('sending_date_invoice_before', '1'),
            'sending_date_invoice_after' : ICP.get_param('sending_date_invoice_after', '1'),
            'date_last_reminder_due_date' : ICP.get_param('date_last_reminder_due_date', datetime.today().date()),
            'date_last_reminder_after_due_date' : ICP.get_param('date_last_reminder_after_due_date', datetime.today().date()),
            'date_last_reminder_bill_due_date' : ICP.get_param('date_last_reminder_bill_due_date', datetime.today().date()),
            'date_last_reminder_bill_after_due_date' : ICP.get_param('date_last_reminder_bill_after_due_date', datetime.today().date()),
            'date_last_reminder_bill_before_due_date' : ICP.get_param('date_last_reminder_bill_before_due_date', datetime.today().date()),
            'is_invoice_approval_matrix': ICP.get_param('is_invoice_approval_matrix', False),
            'is_bill_approval_matrix': ICP.get_param('is_bill_approval_matrix', False),
            'is_other_income_approval_matrix': ICP.get_param('is_other_income_approval_matrix', False),
            'is_other_expense_approval_matrix': ICP.get_param('is_other_expense_approval_matrix', False),
            'is_payment_voucher_approval_matrix': ICP.get_param('is_payment_voucher_approval_matrix', False),            
            'is_customer_multi_receipt_approval_matrix': ICP.get_param('is_customer_multi_receipt_approval_matrix', False),
            'is_vendor_multipayment_approval_matrix': ICP.get_param('is_vendor_multipayment_approval_matrix', False),
            'is_receipt_approval_matrix': ICP.get_param('is_receipt_approval_matrix', False),
            'is_payment_approval_matrix': ICP.get_param('is_payment_approval_matrix', False),
            'accounting': ICP.get_param('accounting', False),
            'automated_invoice_followup': ICP.get_param('automated_invoice_followup', False),
            'followup_sending_date': ICP.get_param('followup_sending_date', '1'),
            'Use_received_date': ICP.get_param('Use_received_date', False),
            'customer_availability': ICP.get_param('customer_availability', False),
            'is_invoice_cutoff_date': ICP.get_param('is_invoice_cutoff_date', False),
            'invoice_cutoff_date': ICP.get_param('invoice_cutoff_date', '1'),
            'post_discount_account': ICP.get_param('post_discount_account', False),
        })

        if res['automated_invoice_followup']:
            followup_sending_date = ICP.get_param('followup_sending_date', '1')
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
        ISP.set_param('petty_cash_expense_account_id', int(self.petty_cash_expense_account_id.id))
        ISP.set_param('overdue_template', self.overdue_template)
        ISP.set_param('is_credit_note_approval_matrix', self.is_credit_note_approval_matrix)
        ISP.set_param('is_refund_approval_matrix', self.is_refund_approval_matrix)
        ISP.set_param('is_customer_deposit_approval_matrix', self.is_customer_deposit_approval_matrix)
        ISP.set_param('is_vendor_deposit_approval_matrix', self.is_vendor_deposit_approval_matrix)
        ISP.set_param('is_receipt_giro_approval_matrix', self.is_receipt_giro_approval_matrix)
        ISP.set_param('is_payment_giro_approval_matrix', self.is_payment_giro_approval_matrix)
        ISP.set_param('is_internal_transfer_approval_matrix', self.is_internal_transfer_approval_matrix)
        ISP.set_param('is_cash_advance_approving_matrix', self.is_cash_advance_approving_matrix)
        ISP.set_param('is_purchase_currency_approval_matrix', self.is_purchase_currency_approval_matrix)
        ISP.set_param('is_budget_approval_matrix', self.is_budget_approval_matrix)
        ISP.set_param('is_budget_change_req_approval_matrix', self.is_budget_change_req_approval_matrix)
        ISP.set_param('is_purchase_budget_approval_matrix', self.is_purchase_budget_approval_matrix)
        ISP.set_param('is_assets_approving_matrix', self.is_assets_approving_matrix)
        ISP.set_param('is_purchase_budget_change_req_approval_matrix', self.is_purchase_budget_change_req_approval_matrix)
        ISP.set_param('is_internal_transaction', self.is_internal_transaction)
        ISP.set_param('is_analytic_groups_balance_sheet', self.is_analytic_groups_balance_sheet)
        ISP.set_param('reminder_interval_before', self.reminder_interval_before)
        ISP.set_param('reminder_interval_before_unit', self.reminder_interval_before_unit)
        ISP.set_param('reminder_notification_before', self.reminder_notification_before)
        ISP.set_param('reminder_interval_after', self.reminder_interval_after)
        ISP.set_param('reminder_interval_after_unit', self.reminder_interval_after_unit)
        ISP.set_param('reminder_notification_after', self.reminder_notification_after)
        ISP.set_param('tax_rounding_type', self.tax_rounding_type)
        ISP.set_param('invoice_bill_reminder', self.invoice_bill_reminder)
        ISP.set_param('reminder_interval_before_invoice', self.reminder_interval_before_invoice)
        ISP.set_param('reminder_interval_after_invoice', self.reminder_interval_after_invoice)
        ISP.set_param('reminder_interval_before_unit_invoice', self.reminder_interval_before_unit_invoice)
        ISP.set_param('eminder_interval_after_unit_invoice', self.eminder_interval_after_unit_invoice)
        ISP.set_param('reminder_notification_before_invoice', self.reminder_notification_before_invoice)
        ISP.set_param('reminder_notification_after_invoice', self.reminder_notification_after_invoice)
        ISP.set_param('days_bill_before', self.days_bill_before)
        ISP.set_param('days_bill_after', self.days_bill_after)
        ISP.set_param('days_invoice_before', self.days_invoice_before)
        ISP.set_param('days_invoice_after', self.days_invoice_after)
        ISP.set_param('sending_date_bill_before', self.sending_date_bill_before)
        ISP.set_param('sending_date_bill_after', self.sending_date_bill_after)
        ISP.set_param('sending_date_invoice_before', self.sending_date_invoice_before)
        ISP.set_param('sending_date_invoice_after', self.sending_date_invoice_after)
        ISP.set_param('date_last_reminder_due_date', self.date_last_reminder_due_date)
        ISP.set_param('date_last_reminder_after_due_date', self.date_last_reminder_after_due_date)
        ISP.set_param('date_last_reminder_bill_due_date', self.date_last_reminder_bill_due_date)
        ISP.set_param('date_last_reminder_bill_after_due_date', self.date_last_reminder_bill_after_due_date)
        ISP.set_param('date_last_reminder_bill_before_due_date', self.date_last_reminder_bill_before_due_date)
        ISP.set_param('is_invoice_approval_matrix', self.is_invoice_approval_matrix)
        ISP.set_param('is_bill_approval_matrix', self.is_bill_approval_matrix)
        ISP.set_param('is_other_income_approval_matrix', self.is_other_income_approval_matrix)
        ISP.set_param('is_other_expense_approval_matrix', self.is_other_expense_approval_matrix)
        ISP.set_param('is_payment_voucher_approval_matrix', self.is_payment_voucher_approval_matrix)        
        ISP.set_param('is_customer_multi_receipt_approval_matrix', self.is_customer_multi_receipt_approval_matrix)
        ISP.set_param('is_vendor_multipayment_approval_matrix', self.is_vendor_multipayment_approval_matrix)
        ISP.set_param('is_receipt_approval_matrix', self.is_receipt_approval_matrix)
        ISP.set_param('is_payment_approval_matrix', self.is_payment_approval_matrix)
        ISP.set_param('accounting', self.accounting)
        ISP.set_param('automated_invoice_followup', self.automated_invoice_followup)
        ISP.set_param('followup_sending_date', self.followup_sending_date)
        ISP.set_param('Use_received_date', self.Use_received_date)
        ISP.set_param('customer_availability', self.customer_availability)
        ISP.set_param('is_invoice_cutoff_date', self.is_invoice_cutoff_date)
        ISP.set_param('invoice_cutoff_date', self.invoice_cutoff_date)
        ISP.set_param('post_discount_account', self.post_discount_account)
        

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

    @api.onchange('is_credit_note_approval_matrix',
                  'is_refund_approval_matrix',
                  'is_customer_deposit_approval_matrix',
                  'is_vendor_deposit_approval_matrix',
                  'is_receipt_giro_approval_matrix',
                  'is_payment_giro_approval_matrix',
                  'is_internal_transfer_approval_matrix',
                  'is_purchase_currency_approval_matrix',
                  'is_budget_approval_matrix',
                  'is_budget_change_req_approval_matrix',
                  'is_purchase_budget_approval_matrix',
                  'is_purchase_budget_change_req_approval_matrix',
                  'is_assets_approving_matrix',
                  'is_cash_advance_approving_matrix',
                  'is_invoice_approval_matrix',
                  'is_bill_approval_matrix',
                  'is_other_income_approval_matrix',
                  'is_other_expense_approval_matrix',
                  'is_customer_multi_receipt_approval_matrix',
                  'is_vendor_multipayment_approval_matrix',
                  'is_receipt_approval_matrix',
                  'is_payment_approval_matrix',
                  'is_payment_voucher_approval_matrix')
    def onchange_matrix(self):
        self.group_is_credit_note_approval_matrix = self.is_credit_note_approval_matrix
        self.group_is_refund_approval_matrix = self.is_refund_approval_matrix
        self.group_is_customer_deposit_approval_matrix = self.is_customer_deposit_approval_matrix
        self.group_is_vendor_deposit_approval_matrix = self.is_vendor_deposit_approval_matrix
        self.group_is_receipt_giro_approval_matrix = self.is_receipt_giro_approval_matrix
        self.group_is_payment_giro_approval_matrix = self.is_payment_giro_approval_matrix
        self.group_is_internal_transfer_approval_matrix = self.is_internal_transfer_approval_matrix
        self.group_is_purchase_currency_approval_matrix = self.is_purchase_currency_approval_matrix
        self.group_is_budget_approval_matrix = self.is_budget_approval_matrix
        self.group_is_budget_change_req_approval_matrix = self.is_budget_change_req_approval_matrix
        self.group_is_purchase_budget_approval_matrix = self.is_purchase_budget_approval_matrix
        self.group_is_purchase_budget_change_req_approval_matrix = self.is_purchase_budget_change_req_approval_matrix
        self.group_assets_approving_matrix = self.is_assets_approving_matrix
        self.group_cash_advance_approval_matrix = self.is_cash_advance_approving_matrix
        self.group_is_invoice_approval_matrix = self.is_invoice_approval_matrix
        self.group_is_bill_approval_matrix = self.is_bill_approval_matrix
        self.group_is_other_income_approval_matrix = self.is_other_income_approval_matrix
        self.group_is_other_expense_approval_matrix = self.is_other_expense_approval_matrix
        self.group_is_customer_multi_receipt_approval_matrix = self.is_customer_multi_receipt_approval_matrix
        self.group_is_vendor_multipayment_approval_matrix = self.is_vendor_multipayment_approval_matrix
        self.group_is_receipt_approval_matrix = self.is_receipt_approval_matrix
        self.group_is_payment_approval_matrix = self.is_payment_approval_matrix
        self.group_is_payment_voucher_approval_matrix = self.is_payment_voucher_approval_matrix

    @api.onchange('module_om_account_budget')
    def onchange_module_om_account_budget(self):
        if self.module_om_account_budget:
            self.group_analytic_accounting = True

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