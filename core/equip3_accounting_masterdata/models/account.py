from odoo import api, fields, models, _
from odoo.osv import expression
from odoo.tools import remove_accents
from odoo.addons.base.models.res_bank import sanitize_account_number
from odoo.exceptions import UserError, ValidationError
from dateutil.relativedelta import relativedelta
from odoo.osv.expression import get_unaccent_wrapper
import logging
from collections import defaultdict
from math import copysign
import re

_logger = logging.getLogger(__name__)

class AccountAccount(models.Model):
    _name = "account.account"
    _inherit = ['account.account', 'mail.thread', 'mail.activity.mixin']

    name = fields.Char(tracking=True)
    currency_id = fields.Many2one(tracking=True)
    code = fields.Char(tracking=True)
    deprecated = fields.Boolean(tracking=True)
    used = fields.Boolean(tracking=True)
    user_type_id = fields.Many2one(tracking=True)
    internal_type = fields.Selection(tracking=True)
    internal_group = fields.Selection(tracking=True)    
    reconcile = fields.Boolean(tracking=True)
    tax_ids = fields.Many2many(tracking=True)
    note = fields.Text(tracking=True)
    company_id = fields.Many2one(tracking=True)
    tag_ids = fields.Many2many(tracking=True)
    group_id = fields.Many2one(tracking=True)
    root_id = fields.Many2one(tracking=True)
    allowed_journal_ids = fields.Many2many(tracking=True)
    opening_debit = fields.Monetary(tracking=True)
    opening_credit = fields.Monetary(tracking=True)
    opening_balance = fields.Monetary(tracking=True)
    is_off_balance = fields.Boolean(tracking=True)

    def init(self):
        bank_parent_account_id = False
        try:
            bank_parent_account_id = self.env.ref('equip3_accounting_masterdata.data_account_asset_bank_and_cash_parent')
        except:
            bank_parent_account_id = False
        if bank_parent_account_id:
            bank_parent_account_id = self.env.ref('equip3_accounting_masterdata.data_account_asset_bank_and_cash_parent').id 
            if bank_parent_account_id:
                self.env.cr.execute("""update account_account set parent_id = %s where id in \
                                        (select id from account_account where user_type_id in \
                                        (select id from account_account_type where name in ('Bank and Cash','Petty Cash')))""", (bank_parent_account_id,))

            receiveable_parent_account_id = self.env.ref('equip3_accounting_masterdata.data_account_asset_receivable_parent').id 
            if receiveable_parent_account_id:
                self.env.cr.execute("""update account_account set parent_id = %s where id in \
                                        (select id from account_account where user_type_id in \
                                        (select id from account_account_type where name in ('Receivable')))""", (receiveable_parent_account_id,))

            inventory_parent_account_id = self.env.ref('equip3_accounting_masterdata.data_account_asset_inventory_parent').id 
            if inventory_parent_account_id:
                self.env.cr.execute("""update account_account set parent_id = %s where id in \
                                        (select id from account_account where user_type_id in \
                                        (select id from account_account_type where name in ('Inventory')))""", (inventory_parent_account_id,))

            current_asset_parent_account_id = self.env.ref('equip3_accounting_masterdata.data_account_asset_current_asset_parent').id 
            if current_asset_parent_account_id:
                self.env.cr.execute("""update account_account set parent_id = %s where id in \
                                        (select id from account_account where user_type_id in \
                                        (select id from account_account_type where name in ('Current Assets','Outstanding Receipt','Supplies','Other Receivable')))""", (current_asset_parent_account_id,))

            fixed_asset_parent_account_id = self.env.ref('equip3_accounting_masterdata.data_account_fixed_asset_parent').id 
            if fixed_asset_parent_account_id:
                self.env.cr.execute("""update account_account set parent_id = %s where id in \
                                        (select id from account_account where user_type_id in \
                                        (select id from account_account_type where name in ('Fixed Assets','Building','Vehicle','Equipment','Property')))""", (fixed_asset_parent_account_id,))

            non_current_asset_parent_account_id = self.env.ref('equip3_accounting_masterdata.data_account_non_current_asset_child').id 
            if non_current_asset_parent_account_id:
                self.env.cr.execute("""update account_account set parent_id = %s where id in \
                                        (select id from account_account where user_type_id in \
                                        (select id from account_account_type where \
                                        name in ('Non-current Assets','Prepayments')))""", (non_current_asset_parent_account_id,))

            current_liability_parent_account_id = self.env.ref('equip3_accounting_masterdata.data_account_current_liability_parent').id 
            if current_liability_parent_account_id:
                self.env.cr.execute("""update account_account set parent_id = %s where id in \
                                        (select id from account_account where user_type_id in \
                                        (select id from account_account_type where \
                                        name in ('Payable','Credit Card','Current Liabilities','Trade Payable','Other Payable')))""", (current_liability_parent_account_id,))

            non_current_liability_parent_account_id = self.env.ref('equip3_accounting_masterdata.data_account_non_current_liability_parent').id 
            if non_current_liability_parent_account_id:
                self.env.cr.execute("""update account_account set parent_id = %s where id in \
                                        (select id from account_account where user_type_id in \
                                        (select id from account_account_type where \
                                        name in ('Non-current Liabilities','Long Term Liability')))""", (non_current_liability_parent_account_id,))

            equity_parent_account_id = self.env.ref('equip3_accounting_masterdata.data_account_equity_grand_parent').id 
            if equity_parent_account_id:
                self.env.cr.execute("""update account_account set parent_id = %s where id in \
                                        (select id from account_account where user_type_id in \
                                        (select id from account_account_type where \
                                        name in ('Equity','Current Year Earnings','Prive','Retained Earnings')))""", (equity_parent_account_id,))

            profit_and_loss_parent_account_id = self.env.ref('equip3_accounting_masterdata.data_account_profit_and_loss_grand_parent').id 
            if profit_and_loss_parent_account_id:
                self.env.cr.execute("""update account_account set parent_id = %s where id in \
                                        (select id from account_account where user_type_id in \
                                        (select id from account_account_type where \
                                        name in ('Income')))""", (profit_and_loss_parent_account_id,))

            other_income_parent_account_id = self.env.ref('equip3_accounting_masterdata.data_account_other_income_grand_parent').id 
            if other_income_parent_account_id:
                self.env.cr.execute("""update account_account set parent_id = %s where id in \
                                        (select id from account_account where user_type_id in \
                                        (select id from account_account_type where \
                                        name in ('Other Income','Return Order','Discount Voucher','Discount Item')))""", (other_income_parent_account_id,))

            expense_parent_account_id = self.env.ref('equip3_accounting_masterdata.data_account_expense_grand_parent').id 
            if expense_parent_account_id:
                self.env.cr.execute("""update account_account set parent_id = %s where id in \
                                        (select id from account_account where user_type_id in \
                                        (select id from account_account_type where \
                                        name in ('Expenses','Cost of Revenue')))""", (expense_parent_account_id,))


            other_expense_parent_account_id = self.env.ref('equip3_accounting_masterdata.data_account_other_expense_grand_parent').id 
            if other_expense_parent_account_id:
                self.env.cr.execute("""update account_account set parent_id = %s where id in \
                                        (select id from account_account where user_type_id in \
                                        (select id from account_account_type where \
                                        name in ('Depreciation','Interest','Tax','Amortization','Interest Expense')))""", (other_expense_parent_account_id,))
                

class AccountTax(models.Model):
    _name = 'account.tax'
    _inherit = ['account.tax', 'mail.thread', 'mail.activity.mixin']

    name = fields.Char(tracking=True)
    type_tax_use = fields.Selection(tracking=True)
    tax_scope = fields.Selection(tracking=True)
    amount_type = fields.Selection(tracking=True)
    active = fields.Boolean(tracking=True)
    company_id = fields.Many2one(tracking=True)
    children_tax_ids = fields.Many2many(tracking=True)
    sequence = fields.Integer(tracking=True)
    amount = fields.Float(tracking=True)
    description = fields.Char(tracking=True)
    price_include = fields.Boolean(tracking=True)
    include_base_amount = fields.Boolean(tracking=True)
    analytic = fields.Boolean(tracking=True)
    tax_group_id = fields.Many2one(tracking=True)
    hide_tax_exigibility = fields.Boolean(tracking=True)
    tax_exigibility = fields.Selection(tracking=True)
    cash_basis_transition_account_id = fields.Many2one(tracking=True)
    invoice_repartition_line_ids = fields.One2many(tracking=True)
    refund_repartition_line_ids = fields.One2many(tracking=True)
    tax_fiscal_country_id = fields.Many2one(tracking=True)
    country_code = fields.Char(tracking=True)


class AccountJournal(models.Model):
    _name = 'account.journal'
    _inherit = ['account.journal', 'mail.thread', 'mail.activity.mixin']

    name = fields.Char(tracking=True)
    code = fields.Char(tracking=True)
    active = fields.Boolean(tracking=True)
    type = fields.Selection(tracking=True)
    type_control_ids = fields.Many2many(tracking=True)
    account_control_ids = fields.Many2many(tracking=True)
    default_account_type = fields.Many2one(tracking=True)
    default_account_id = fields.Many2one(tracking=True)
    payment_debit_account_id = fields.Many2one(tracking=True)
    payment_credit_account_id = fields.Many2one(tracking=True)
    suspense_account_id = fields.Many2one(tracking=True)
    restrict_mode_hash_table = fields.Boolean(tracking=True)
    sequence = fields.Integer(tracking=True)
    invoice_reference_type = fields.Selection(tracking=True)
    invoice_reference_model = fields.Selection(tracking=True)
    currency_id = fields.Many2one(tracking=True)
    company_id = fields.Many2one(tracking=True)
    country_code = fields.Char(tracking=True)
    refund_sequence = fields.Boolean(tracking=True)
    sequence_override_regex = fields.Text(tracking=True)
    inbound_payment_method_ids = fields.Many2many(tracking=True)
    outbound_payment_method_ids = fields.Many2many(tracking=True)
    at_least_one_inbound = fields.Boolean(tracking=True)
    at_least_one_outbound = fields.Boolean(tracking=True)
    profit_account_id = fields.Many2one(tracking=True)
    loss_account_id = fields.Many2one(tracking=True)
    company_partner_id = fields.Many2one(tracking=True)
    bank_statements_source = fields.Selection(tracking=True)
    bank_acc_number = fields.Char(tracking=True)
    bank_id = fields.Many2one(tracking=True)
    sale_activity_type_id = fields.Many2one(tracking=True)
    sale_activity_user_id = fields.Many2one(tracking=True)
    sale_activity_note = fields.Text(tracking=True)
    alias_id = fields.Many2one(tracking=True)
    alias_domain = fields.Char(tracking=True)
    alias_name = fields.Char(tracking=True)
    journal_group_ids = fields.Many2many(tracking=True)
    secure_sequence_id = fields.Many2one(tracking=True)
    use_reconcile = fields.Boolean(string='Use Bank Reconcile?', default=False)
    # allowed_company_ids = fields.Many2many('res.company', string='Allowed Companies')
    # allowed_branch_ids = fields.Many2many('your.branch.model', string='Allowed Branches')


    # @api.model
    # def search(self, args, offset=0, limit=None, order=None, count=False):
    #     # Define args if not already defined
    #     args = args or []

    #     # Add company and branch filters to the domain
    #     if self.env.context.get('allowed_company_ids'):
    #         args += [('company_id', 'in', self.env.context.get('allowed_company_ids'))]
    #     if self.env.context.get('allowed_branch_ids'):
    #         args += ['|', ('branch_id', 'in', self.env.context.get('allowed_branch_ids')), ('branch_id', '=', False)]

    #     # Call the original search method
    #     return super(AccountJournal, self).search(args, offset=offset, limit=limit, order=order)
    
    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context
        _logger.info(f"Context: {context}")
        
        if self.env.context.get('allowed_company_ids'):
            domain += [('company_id', 'in', self.env.context.get('allowed_company_ids'))]
        if self.env.context.get('allowed_branch_ids'):
            domain += ['|',('branch_id', 'in', self.env.context.get('allowed_branch_ids')),('branch_id', '=', False)]

        _logger.info("allowed_company_ids: %s", self.env.context.get('allowed_company_ids'))

        result = super(AccountJournal, self).search_read(
            domain=domain, fields=fields, offset=offset, limit=limit, order=order
        )

        return result
    
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        context = self.env.context
        # domain.extend([('company_id', '=', self.env.company.id)])
        if context.get('allowed_company_ids'):
            domain.extend([('company_id', 'in', self.env.companies.ids)])
        if context.get('allowed_branch_ids'):
            domain.extend(['|',('branch_id', 'in', self.env.context.get('allowed_branch_ids')),('branch_id', '=', False)])
        return super(AccountJournal, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)

    
    @api.onchange('default_account_id')
    def onchange_default_account_id(self):
        account_id = self.default_account_id
        if self.default_account_id:
            self.payment_credit_account_id = account_id
            self.payment_debit_account_id = account_id

    @api.onchange('use_reconcile','default_account_id')
    def onchange_use_reconcile(self):
        account_id = self.default_account_id
        if self.use_reconcile:
            self.payment_credit_account_id = False
            self.payment_debit_account_id = False
        else:
            self.payment_credit_account_id = account_id
            self.payment_debit_account_id = account_id

    @api.model
    def check_invoice_sequence_on_install(self):
        invoices = self.env['account.journal'].search([('sequence_id', '!=', '0')])
        for invoice in invoices:
            invoice.create_journal_sequence()
        return True


class AccountType(models.Model):
    _name = 'account.account.type'
    _inherit = ['account.account.type', 'mail.thread', 'mail.activity.mixin']

    name = fields.Char(tracking=True)
    include_initial_balance = fields.Boolean(tracking=True)
    type = fields.Selection(selection_add=[('view', 'View')], tracking=True)
    internal_group = fields.Selection(tracking=True)
    note = fields.Text(tracking=True)


class AccountReconcile(models.Model):
    _name = 'account.reconcile.model'
    _inherit = ['account.reconcile.model', 'mail.thread', 'mail.activity.mixin']

    active = fields.Boolean(tracking=True)
    name = fields.Char(tracking=True)
    sequence = fields.Integer(tracking=True)
    company_id = fields.Many2one(tracking=True)
    rule_type = fields.Selection(tracking=True)
    auto_reconcile = fields.Boolean(tracking=True)
    to_check = fields.Boolean(tracking=True)
    matching_order = fields.Selection(tracking=True)
    match_text_location_label = fields.Boolean(tracking=True)
    match_text_location_note = fields.Boolean(tracking=True)
    match_text_location_reference = fields.Boolean(tracking=True)
    match_journal_ids = fields.Many2many(tracking=True)
    match_nature = fields.Selection(tracking=True)
    match_amount = fields.Selection(tracking=True)
    match_amount_min = fields.Float(tracking=True)
    match_amount_max = fields.Float(tracking=True)
    match_label = fields.Selection(tracking=True)
    match_label_param = fields.Char(tracking=True)
    match_note = fields.Selection(tracking=True)
    match_note_param = fields.Char(tracking=True)
    match_transaction_type = fields.Selection(tracking=True)
    match_transaction_type_param = fields.Char(tracking=True)
    match_same_currency = fields.Boolean(tracking=True)
    match_total_amount = fields.Boolean(tracking=True)
    match_total_amount_param = fields.Float(tracking=True)
    match_partner = fields.Boolean(tracking=True)
    match_partner_ids = fields.Many2many(tracking=True)
    match_partner_category_ids = fields.Many2many(tracking=True)
    line_ids = fields.One2many(tracking=True)
    partner_mapping_line_ids = fields.One2many(tracking=True)
    past_months_limit = fields.Integer(tracking=True)
    decimal_separator = fields.Char(tracking=True)
    show_decimal_separator = fields.Boolean(tracking=True)
    number_entries = fields.Integer(tracking=True)


class AccountPaymentTerm(models.Model):
    _name = 'account.payment.term'
    _inherit = ['account.payment.term', 'mail.thread', 'mail.activity.mixin']

    name = fields.Char(tracking=True)
    active = fields.Boolean(tracking=True)
    note = fields.Text(tracking=True)
    line_ids = fields.One2many(tracking=True)
    company_id = fields.Many2one(tracking=True)
    sequence = fields.Integer(tracking=True)