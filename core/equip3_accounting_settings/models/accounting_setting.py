from datetime import datetime
from odoo import models,fields,api


class accountingSetting(models.Model):
    _name = 'accounting.config.settings'
    
    
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
        
    name = fields.Char()
    invoice_bill_reminder = fields.Boolean()
    reminder_interval_before_unit = fields.Selection([
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months'),
        ], string='',default='days')
    reminder_interval_before = fields.Integer(string='Before Due Date')
    days_bill_before  = fields.Selection(WEEK_DATA)
    sending_date_bill_before   = fields.Selection(DAYS_DATA)
    reminder_interval_after_unit = fields.Selection([
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months'),
        ], string='',default='days')
    reminder_interval_after = fields.Integer(string='After Maturity')
    days_bill_after  = fields.Selection(WEEK_DATA)
    sending_date_bill_after  = fields.Selection(DAYS_DATA)
    reminder_interval_before_unit_invoice = fields.Selection([('days', 'Days'), ('weeks', 'Weeks'),('months', 'Months')],default='days')
    reminder_interval_before_invoice = fields.Integer(string='Before Invoice Due Date')
    days_invoice_before   = fields.Selection(WEEK_DATA)
    sending_date_invoice_before    = fields.Selection(DAYS_DATA)
    date_last_reminder_due_date   = fields.Date("Date Last Invoice Send", default=datetime.today().date(),)
    reminder_interval_after_unit_invoice = fields.Selection([('days', 'Days'), ('weeks', 'Weeks'),('months', 'Months')],default='days')
    reminder_interval_after_invoice = fields.Integer(string='After Invoice Maturity')
    days_invoice_after  = fields.Selection(WEEK_DATA)
    sending_date_invoice_after   = fields.Selection(DAYS_DATA)
    
    is_allow_budget_approval_matrix = fields.Boolean(string="Allow Budget Approval Matrix")
    is_allow_budget_wa_notification = fields.Boolean(string="Enable Budget Whatsapp Notification", default=False)

    is_allow_customer_deposit_approval_matrix = fields.Boolean(string="Allow Customer Deposit Approval Matrix")
    is_allow_customer_deposit_wa_notification = fields.Boolean(string="Enable Customer Deposit Whatsapp Notification", default=False)

    is_allow_vendor_deposit_approval_matrix = fields.Boolean(string="Allow Vendor Deposit Approval Matrix")
    is_allow_vendor_deposit_wa_notification = fields.Boolean(string="Enable Vendor Deposit Whatsapp Notification", default=False)

    is_allow_customer_multi_receipt_approval_matrix = fields.Boolean(string="Allow Customer Multi Receipt Approval Matrix")
    is_allow_customer_multi_receipt_wa_notification = fields.Boolean(string="Enable Customer Multi Receipt Whatsapp Notification", default=False)

    is_allow_vendor_multi_payment_approval_matrix = fields.Boolean(string="Allow Vendor Multi Payment Approval Matrix")
    is_allow_vendor_multi_payment_wa_notification = fields.Boolean(string="Enable Vendor Multi Payment Whatsapp Notification", default=False)

    is_allow_budget_change_req_approval_matrix = fields.Boolean(string="Allow Budget Change Request Approval Matrix")
    is_allow_budget_change_req_wa_notification = fields.Boolean(string="Enable Budget Change Request Whatsapp Notification", default=False)

    is_allow_purchase_budget_approval_matrix = fields.Boolean(string="Allow Purchase Budget Approval Matrix")
    is_allow_purchase_budget_wa_notification = fields.Boolean(string="Enable Purchase Budget Whatsapp Notification", default=False)

    is_allow_purchase_budget_change_req_approval_matrix = fields.Boolean(string="Allow Purchase Change Request Approval Matrix")
    is_allow_purchase_budget_change_req_wa_notification = fields.Boolean(string="Enable Purchase Change Request Whatsapp Notification", default=False)

    is_allow_cash_advance_approval_matrix = fields.Boolean(string="Allow Cash Advance Approval Matrix")
    is_allow_cash_advance_wa_notification = fields.Boolean(string="Enable Cash Advance Whatsapp Notification", default=False)

    is_allow_other_income_approval_matrix = fields.Boolean(string="Allow Other Income Approval Matrix")
    is_allow_other_income_wa_notification = fields.Boolean(string="Enable Other Income Whatsapp Notification", default=False)

    is_allow_other_expense_approval_matrix = fields.Boolean(string="Allow Other Expense Approval Matrix")
    is_allow_other_expense_wa_notification = fields.Boolean(string="Enable Other Expense Whatsapp Notification", default=False)

    @api.onchange('is_allow_budget_approval_matrix')
    def onchange_is_allow_budget_approval_matrix(self):
        if not self.is_allow_budget_approval_matrix:
            self.is_allow_budget_wa_notification = False

    @api.onchange('is_allow_customer_deposit_approval_matrix')
    def onchange_is_allow_customer_deposit_approval_matrix(self):
        if not self.is_allow_customer_deposit_approval_matrix:
            self.is_allow_customer_deposit_wa_notification = False

    @api.onchange('is_allow_vendor_deposit_approval_matrix')
    def onchange_is_allow_vendor_deposit_approval_matrix(self):
        if not self.is_allow_vendor_deposit_approval_matrix:
            self.is_allow_vendor_deposit_wa_notification = False

    @api.onchange('is_allow_customer_multi_receipt_approval_matrix')
    def onchange_is_allow_customer_multi_receipt_approval_matrix(self):
        if not self.is_allow_customer_multi_receipt_approval_matrix:
            self.is_allow_customer_multi_receipt_wa_notification = False

    @api.onchange('is_allow_vendor_multi_payment_approval_matrix')
    def onchange_is_allow_vendor_multi_payment_approval_matrix(self):
        if not self.is_allow_vendor_multi_payment_approval_matrix:
            self.is_allow_vendor_multi_payment_wa_notification = False

    @api.onchange('is_allow_budget_change_req_approval_matrix')
    def onchange_is_allow_budget_change_req_approval_matrix(self):
        if not self.is_allow_budget_change_req_approval_matrix:
            self.is_allow_budget_change_req_wa_notification = False

    @api.onchange('is_allow_purchase_budget_approval_matrix')
    def onchange_is_allow_purchase_budget_approval_matrix(self):
        if not self.is_allow_purchase_budget_approval_matrix:
            self.is_allow_purchase_budget_wa_notification = False

    @api.onchange('is_allow_purchase_budget_change_req_approval_matrix')
    def onchange_is_allow_purchase_budget_change_req_approval_matrix(self):
        if not self.is_allow_purchase_budget_change_req_approval_matrix:
            self.is_allow_purchase_budget_change_req_wa_notification = False

    @api.onchange('is_allow_cash_advance_approval_matrix')
    def onchange_is_allow_cash_advance_approval_matrix(self):
        if not self.is_allow_cash_advance_approval_matrix:
            self.is_allow_cash_advance_wa_notification = False


    @api.depends('is_allow_budget_approval_matrix', 'is_allow_customer_deposit_approval_matrix', 'is_allow_vendor_deposit_approval_matrix', 'is_allow_customer_multi_receipt_approval_matrix', 'is_allow_vendor_multi_payment_approval_matrix',\
                'is_allow_budget_change_req_approval_matrix', 'is_allow_purchase_budget_approval_matrix', 'is_allow_purchase_budget_change_req_approval_matrix', 'is_allow_cash_advance_approval_matrix', 'is_allow_other_income_approval_matrix', 'is_allow_other_expense_approval_matrix')
    def _compute_group_membership(self):
        # Get users in the accountant group / Accounting Manager
        accountant_group_id = self.env.ref('equip3_accounting_accessright_setting.group_accountant_staff').id
        user_ids = []
        self.env.cr.execute("""
                    SELECT u.id
                    FROM res_users u
                    JOIN res_groups_users_rel g_rel ON u.id = g_rel.uid
                    WHERE g_rel.gid = %s
                """, (accountant_group_id,))
        user_ids = [row[0] for row in self.env.cr.fetchall()]

        group_budget = self.env.ref('equip3_accounting_accessright_setting.group_is_budget_approval_matrix')
        for record in self:
            if record.is_allow_budget_approval_matrix:
                # Write these users to the group
                group_budget.sudo().write({'users': [(6, 0, user_ids)]})
            else:
                # Remove all users from the group
                group_budget.sudo().write({'users': [(5, 0, 0)]})

        group_customer_deposit = self.env.ref('equip3_accounting_accessright_setting.group_is_customer_deposit_approval_matrix')
        for record in self:
            if record.is_allow_customer_deposit_approval_matrix:
                # Write these users to the group
                group_customer_deposit.sudo().write({'users': [(6, 0, user_ids)]})
            else:
                # Remove all users from the group
                group_customer_deposit.sudo().write({'users': [(5, 0, 0)]})

        group_vendor_deposit = self.env.ref('equip3_accounting_accessright_setting.group_is_vendor_deposit_approval_matrix')    
        for record in self:
            if record.is_allow_vendor_deposit_approval_matrix:
                # Write these users to the group
                group_vendor_deposit.sudo().write({'users': [(6, 0, user_ids)]})
            else:
                # Remove all users from the group
                group_vendor_deposit.sudo().write({'users': [(5, 0, 0)]})

        group_customer_multi_receipt = self.env.ref('equip3_accounting_accessright_setting.group_is_customer_multi_receipt_approval_matrix')
        for record in self:
            if record.is_allow_customer_multi_receipt_approval_matrix:
                # Write these users to the group
                group_customer_multi_receipt.sudo().write({'users': [(6, 0, user_ids)]})
            else:
                # Remove all users from the group
                group_customer_multi_receipt.sudo().write({'users': [(5, 0, 0)]})

        group_vendor_multi_payment = self.env.ref('equip3_accounting_accessright_setting.group_is_vendor_multipayment_approval_matrix')
        for record in self:
            if record.is_allow_vendor_multi_payment_approval_matrix:
                # Write these users to the group
                group_vendor_multi_payment.sudo().write({'users': [(6, 0, user_ids)]})
            else:
                # Remove all users from the group
                group_vendor_multi_payment.sudo().write({'users': [(5, 0, 0)]})

        group_budget_change_req = self.env.ref('equip3_accounting_accessright_setting.group_is_budget_change_req_approval_matrix')
        for record in self:
            if record.is_allow_budget_change_req_approval_matrix:
                # Write these users to the group
                group_budget_change_req.sudo().write({'users': [(6, 0, user_ids)]})
            else:
                # Remove all users from the group
                group_budget_change_req.sudo().write({'users': [(5, 0, 0)]})

        group_purchase_budget = self.env.ref('equip3_accounting_accessright_setting.group_is_purchase_budget_approval_matrix')
        for record in self:
            if record.is_allow_purchase_budget_approval_matrix:
                # Write these users to the group
                group_purchase_budget.sudo().write({'users': [(6, 0, user_ids)]})
            else:
                # Remove all users from the group
                group_purchase_budget.sudo().write({'users': [(5, 0, 0)]})


        group_purchase_change_req = self.env.ref('equip3_accounting_accessright_setting.group_is_purchase_budget_change_req_approval_matrix')
        for record in self:
            if record.is_allow_purchase_budget_change_req_approval_matrix:
                # Write these users to the group
                group_purchase_change_req.sudo().write({'users': [(6, 0, user_ids)]})
            else:
                # Remove all users from the group
                group_purchase_change_req.sudo().write({'users': [(5, 0, 0)]})

        group_cash_advance = self.env.ref('equip3_accounting_accessright_setting.group_cash_advance_approval_matrix')
        for record in self:
            if record.is_allow_cash_advance_approval_matrix:
                # Write these users to the group
                group_cash_advance.sudo().write({'users': [(6, 0, user_ids)]})
            else:
                # Remove all users from the group
                group_cash_advance.sudo().write({'users': [(5, 0, 0)]})

        group_other_income = self.env.ref('equip3_accounting_accessright_setting.group_is_other_income_approval_matrix')
        for record in self:
            if record.is_allow_other_income_approval_matrix:
                # Write these users to the group
                group_other_income.sudo().write({'users': [(6, 0, user_ids)]})
            else:
                # Remove all users from the group
                group_other_income.sudo().write({'users': [(5, 0, 0)]})

        group_other_expense = self.env.ref('equip3_accounting_accessright_setting.group_is_other_expense_approval_matrix')
        for record in self:
            if record.is_allow_other_expense_approval_matrix:
                # Write these users to the group
                group_other_expense.sudo().write({'users': [(6, 0, user_ids)]})
            else:
                # Remove all users from the group
                group_other_expense.sudo().write({'users': [(5, 0, 0)]})

                
        # for record in self:
        #     if record.is_allow_budget_approval_matrix:
        #         group_budget.sudo().write({'users': [(4, record.env.uid)]})
        #     else:
        #         group_budget.sudo().write({'users': [(3, record.env.uid)]})

   

    # @api.model
    # def create(self, vals):
    #     record = super(accountingSetting, self).create(vals)
    #     record._compute_group_membership()
    #     return record

    def write(self, vals):
        res = super(accountingSetting, self).write(vals)
        self._compute_group_membership()
        return res
    

    
    
    