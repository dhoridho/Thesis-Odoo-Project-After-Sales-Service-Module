from odoo import models, fields, api, _, tools
from odoo.exceptions import UserError
import datetime
from lxml import etree

from odoo.addons.base.models.ir_ui_view import (
transfer_field_to_modifiers, transfer_node_to_modifiers, transfer_modifiers_to_node,
)


def setup_modifiers(node, field=None, context=None, in_tree_view=False):
    modifiers = {}
    if field is not None:
        transfer_field_to_modifiers(field, modifiers)
    transfer_node_to_modifiers(
        node, modifiers, context=context)
    transfer_modifiers_to_node(modifiers, node)
     

class AccountReceipPayment(models.Model):
    _name = 'receipt.payment'
    _description = "Receipt Payment"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']

    @api.model
    def _default_branch(self):
        default_branch_id = self.env.context.get('default_branch_id',False)
        if default_branch_id:
            return default_branch_id
        return self.env.company_branches[0].id if len(self.env.company_branches) == 1 else self.env.user.branch_id.id




    @api.model
    def _domain_branch(self):
        return [('id', 'in', self.env.branches.ids), ('company_id','=', self.env.company.id)]

    branch_id = fields.Many2one('res.branch', check_company=True, domain=_domain_branch, default=_default_branch, readonly=False, required=True)
    name = fields.Char(string='Number', readonly=True, tracking=True)
    partner_id = fields.Many2one('res.partner', readonly=True, string='Customer', required=True, tracking=True)
    amount = fields.Monetary(string='Paid Amount', readonly=True, store=True, compute='compute_payment_amount', tracking=True)
    journal_id = fields.Many2one('account.journal', string='Payment Method', required=True, tracking=True)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id.id, readonly=True, store=True, required=True, tracking=True)
    clearing_account_id = fields.Many2one('account.account', string='Clearing Account', required=True, tracking=True)
    move_id = fields.Many2one('account.move', string='Clearing Entry', tracking=True, readonly=True)
    date = fields.Date(string='Date', required=True, tracking=True)
    payment_ref = fields.Char(string='Payment Ref', tracking=True)
    memo = fields.Char(string='memo', tracking=True)
    due_date = fields.Datetime(string='Due Date', tracking=True)
    receive_date = fields.Datetime(string='Receive Date', tracking=True)
    clearing_date = fields.Datetime(string='Clearing Date', tracking=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company.id, tracking=True, readonly=True)
    # branch_id = fields.Many2one('res.branch', string='Branch', default=lambda self: self.env.user.branch_id.id, tracking=True, domain="[('company_id', '=', company_id)]")
    
    diff_amount = fields.Monetary(string='Difference Amount', readonly=True, tracking=True)
    writeoff_acc_id = fields.Many2one('account.account', string='Counterpart Account', domain=[('deprecated','=',False)], tracking=True)
    naration = fields.Text(string='Notes', tracking=True)
    create_uid = fields.Many2one('res.users', string='Created by', readonly=True, tracking=True)
    create_date = fields.Datetime(string="Created Date", readonly=True, tracking=True)
    partner_type = fields.Selection([
        ('customer', 'Customer'),
        ('supplier', 'Vendor')
        ], string='Partner Type', tracking=True)
    line_credit_ids = fields.One2many('receipt.payment.line.credit', 'line_id', string='Credits')
    line_debit_ids = fields.One2many('receipt.payment.line.debit', 'line_id', string='Debits')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('open', 'Open'),
        ('post', 'Posted'),
        ('cancel', 'Cancelled'),
        ('cleared', 'Cleared'),
        ('rejected', 'Rejected'),
        ], string='State', default='draft', tracking=True)
    total_amount_credit = fields.Monetary(string="Total Amount", compute='_calculate_credit_amount_total', store=True, tracking=True, compute_sudo=True)
    total_amount_debit = fields.Monetary(string="Total Amount", compute='_calculate_credit_amount_total', store=True, tracking=True, compute_sudo=True)
    payment_id_count = fields.Integer(string="Payment", compute='_calculate_credit_amount_total', compute_sudo=True)

class ReceiptPaymentLineCredit(models.Model):
    _name = "receipt.payment.line.credit"
    _description = ' '

    line_id = fields.Many2one('receipt.payment', string='Detail', readonly=True)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id, string='Currency')
    invoice_id = fields.Many2one('account.move', string='Invoice', readonly=True)
    account_id = fields.Many2one('account.account', string='Account', readonly=True)
    invoice_date = fields.Date(string='Date', readonly=True)
    invoice_date_due = fields.Date(string='Due Date', readonly=True)
    original_amount = fields.Monetary(string='Original Currency Amount', readonly=True)
    base_amount = fields.Monetary(string='Base Currency Amount', readonly=True)
    original_unreconcile = fields.Monetary(string='Original Open Balance', readonly=True)
    base_unreconcile = fields.Monetary(string='Base Currency Open Balance', readonly=True)
    is_full_reconcile = fields.Boolean(string='Full Reconcile')
    amount = fields.Monetary(string='Amount')
    payment_id = fields.Many2one('account.payment', string='Payment')    

    @api.onchange('is_full_reconcile')
    def calculate_credit_amount_base(self):
        for rec in self:
            if rec.is_full_reconcile:
                rec.amount = rec.base_unreconcile
            else:
                rec.amount = False

class ReceiptPaymentLineDebit(models.Model):
    _name = "receipt.payment.line.debit"
    _description = ' '

    line_id = fields.Many2one('receipt.payment', string='Detail', readonly=True)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id, string='Currency')
    invoice_id = fields.Many2one('account.move', string='Invoice', readonly=True)
    account_id = fields.Many2one('account.account', string='Account', readonly=True)
    invoice_date = fields.Date(string='Date', readonly=True)
    invoice_date_due = fields.Date(string='Due Date', readonly=True)
    original_amount = fields.Monetary(string='Original Currency Amount', readonly=True)
    base_amount = fields.Monetary(string='Base Currency Amount', readonly=True)
    original_unreconcile = fields.Monetary(string='Original Open Balance', readonly=True)
    base_unreconcile = fields.Monetary(string='Base Currency Open Balance', readonly=True)
    is_full_reconcile = fields.Boolean(string='Full Reconcile')
    amount = fields.Monetary(string='Amount')
    payment_id = fields.Many2one('account.payment', string='Payment')
    
    @api.onchange('is_full_reconcile')
    def calculate_debit_amount_base(self):
        for rec in self:
            if rec.is_full_reconcile:
                rec.amount = rec.base_unreconcile
            else:
                rec.amount = False
      
    

    

    