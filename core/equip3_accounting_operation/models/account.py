
import pytz
from pytz import timezone, UTC
from odoo import tools, models, fields, api, _
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError, UserError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from lxml import etree
import logging
import requests
import json
import base64
from ast import literal_eval
from ...equip3_general_features.models.email_wa_parameter import EmailParam,waParam

_logger = logging.getLogger(__name__)

headers = {'content-type': 'application/json'}


class AccountMove(models.Model):
    _inherit = "account.move"


    @api.depends('date')
    def _compute_get_period(self):
        for rec in self:
            rec.period_id = False
            if rec.date:
                period = self.env['sh.account.period'].sudo().search(
                    [('date_start', '<=', rec.date), ('date_end', '>=', rec.date), ('company_id', '=', rec.company_id.id)], limit=1)
                if period:
                    rec.period_id = period.id

    def _check_fiscalyear_lock_date(self):
        for move in self:
            lock_date = move.company_id._get_user_fiscal_lock_date()
            if move.date <= lock_date:
                return True
                # if self.user_has_groups('account.group_account_manager'):
                #     message = _("You cannot add/modify entries prior to and inclusive of the lock date %s.", format_date(self.env, lock_date))
                # else:
                #     message = _("You cannot add/modify entries prior to and inclusive of the lock date %s. Check the company settings or ask someone with the 'Adviser' role", format_date(self.env, lock_date))
                # raise UserError(message)
        return True

    @api.model
    def _get_default_invoice_incoterm(self):
        res = super(AccountMove, self)._get_default_invoice_incoterm()
        return res

    @api.model
    def _get_default_journal(self):
        journal = super(AccountMove, self)._get_default_journal()
        return journal
    
    @api.model
    def _get_default_analytic(self):
        analytic_priority_ids = self.env['analytic.priority'].search(
            [], order="priority")
        for analytic_priority in analytic_priority_ids:
            self.env.user.analytic_tag_ids
            if analytic_priority.object_id == 'user' and self.env.user.analytic_tag_ids:
                analytic_tags_ids = self.env['account.analytic.tag'].search(
                    [('id', 'in', self.env.user.analytic_tag_ids.ids), ('company_id', '=', self.env.user.company_id.id)])
                return analytic_tags_ids
                # self.analytic_group_ids = analytic_tags_ids
                # break
            elif analytic_priority.object_id == 'branch' and self.env.user.branch_id.analytic_tag_ids:
                analytic_tags_ids = self.env['account.analytic.tag'].search(
                    [('id', 'in', self.env.user.branch_id.analytic_tag_ids.ids), ('company_id', '=', self.env.user.company_id.id)])
                return analytic_tags_ids
                # self.analytic_group_ids = analytic_tags_ids
                # break

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
    approval_matrix_id = fields.Many2one(
        'approval.matrix.accounting', string="Approval Matrix", compute='_get_approval_matrix')
    is_invoice_approval_matrix = fields.Boolean(
        string="Is Invoice Approval Matrix", compute='_get_approve_button_from_config')
    approved_matrix_ids = fields.One2many(
        'approval.matrix.accounting.lines', 'move_id', string="Approved Matrix")
    approval_matrix_line_id = fields.Many2one(
        'approval.matrix.accounting.lines', string='Approval Matrix Line', compute='_get_approve_button', store=False)
    is_approve_button = fields.Boolean(
        string='Is Approve Button', compute='_get_approve_button', store=False)
    
    state = fields.Selection(selection=[
            ('draft', 'Draft'),
            ('posted', 'Posted'),
            ('to_approve', 'Waiting For Approval'),
            ('cancel', 'Cancelled'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
            ('expired', 'Expired'),
            ('failed', 'Payment Failed')
        ], string='Status', required=True, readonly=True, copy=False, tracking=True,
        default='draft')
    
    
    state1 = fields.Selection(related="state", tracking=False)
    state2 = fields.Selection(related="state", tracking=False)
    is_register_payment_done = fields.Boolean(
        string='Is Register Payment Done')
    analytic_group_ids = fields.Many2many(
        'account.analytic.tag', domain="[('company_id', '=', company_id)]", string="Analytic Group", default=_get_default_analytic, readonly=False)
    invoice_origin_id = fields.Many2one('account.move', string='Invoice No', readonly=True, copy=False, states={'draft': [(
        'readonly', False)]}, domain="[('partner_id','=',partner_id),('move_type','=',(move_type == 'out_refund' and 'out_invoice') or 'in_invoice'),('state','!=','draft')]")
    invoice_origin_date = fields.Date(string='Invoice Date', readonly=True, copy=False, states={
                                      'draft': [('readonly', False)]})
    reason = fields.Char(string="Reason", readonly=True, copy=False, states={
                         'draft': [('readonly', False)]})
    ref_no = fields.Text(string="Ref No", readonly=True, copy=False, states={
                         'draft': [('readonly', False)]})
    request_partner_id = fields.Many2one(
        'res.partner', string="Requested Partner")
    is_fiscal_book_exclude = fields.Boolean(
        string='Exclude on Fiscal Book', default=False)
    received_date = fields.Date(string="Received Date")
    visible_received_date = fields.Boolean(string="Received Date")
    to_approve_state_payment_count = fields.Integer(
        compute='compute_to_approve_state_payment', string='Payment Count (To Approve)')
    show_name_warning = fields.Boolean(store=False, tracking=True)
    date = fields.Date(string='Date', required=True, index=True, readonly=True, states={
                       'draft': [('readonly', False)]}, copy=False, default=fields.Date.context_today, tracking=True)
    narration = fields.Text(string='Terms and Conditions', tracking=True)
    posted_before = fields.Boolean(
        help="Technical field for knowing if the move has been posted before", copy=False, tracking=True)
    to_check = fields.Boolean(string='To Check', default=False, tracking=True,
                              help='If this checkbox is ticked, it means that the user was not sure of all the related information at the time of the creation of the move and that the move needs to be checked again.')
    journal_id = fields.Many2one('account.journal', string='Journal', required=True, readonly=True, states={'draft': [(
        'readonly', False)]}, check_company=True, domain="[('id', 'in', suitable_journal_ids)]", default=_get_default_journal, tracking=True)
    company_currency_id = fields.Many2one(
        string='Company Currency', readonly=True, related='company_id.currency_id', tracking=True)
    line_ids = fields.One2many('account.move.line', 'move_id', string='Journal Items',
                               copy=True, readonly=True, tracking=True, states={'draft': [('readonly', False)]})
    commercial_partner_id = fields.Many2one('res.partner', string='Commercial Entity',
                                            store=True, readonly=True, tracking=True, compute='_compute_commercial_partner_id')
    partner_bank_id = fields.Many2one('res.partner.bank', string='Recipient Bank', tracking=True,
                                      help='Bank Account Number to which the invoice will be paid. A Company bank account if this is a Customer Invoice or Vendor Credit Note, otherwise a Partner bank account number.', check_company=True)
    payment_reference = fields.Char(string='Payment Reference', index=True, copy=False,
                                    tracking=True, help="The payment reference to set on journal items.")
    payment_id = fields.Many2one(index=True, comodel_name='account.payment',
                                 tracking=True, string="Payment", copy=False, check_company=True)
    statement_line_id = fields.Many2one(comodel_name='account.bank.statement.line',
                                        tracking=True, string="Statement Line", copy=False, check_company=True)
    # === Amount fields ===
    amount_tax = fields.Monetary(
        string='Total Taxes', store=True, readonly=True, tracking=True, compute='_compute_amount')
    amount_tax2 = fields.Monetary(
        string='Total Taxes', store=True, compute='_compute_amount2')
    subtotal_amount = fields.Monetary(string='Subtotal', store=True, compute='_compute_amount')
    
    
    amount_total = fields.Monetary(string='Grand Total', store=True, readonly=True,
                                   tracking=True, compute='_compute_amount', inverse='_inverse_amount_total')
    amount_residual = fields.Monetary(
        string='Amount Due', store=True, tracking=True, compute='_compute_amount')
    amount_untaxed_signed = fields.Monetary(string='Untaxed Amount Signed', store=True, readonly=True,
                                            tracking=True, compute='_compute_amount', currency_field='company_currency_id')
    amount_tax_signed = fields.Monetary(string='Tax Signed', store=True, readonly=True,
                                        tracking=True, compute='_compute_amount', currency_field='company_currency_id')
    amount_total_signed = fields.Monetary(string='Total Signed', store=True, readonly=True,
                                          tracking=True, compute='_compute_amount', currency_field='company_currency_id')
    amount_residual_signed = fields.Monetary(
        string='Amount Due Signed', store=True, tracking=True, compute='_compute_amount', currency_field='company_currency_id')
    amount_by_group = fields.Binary(string="Tax amount by group", compute='_compute_invoice_taxes_by_group', help='Edit Tax amounts if you encounter rounding issues.')
    # ==== Cash basis feature fields ====
    tax_cash_basis_rec_id = fields.Many2one('account.partial.reconcile', string='Tax Cash Basis Entry of', tracking=True,
                                            help="Technical field used to keep track of the tax cash basis reconciliation. This is needed when cancelling the source: it will post the inverse journal entry to cancel that part too.")
    tax_cash_basis_move_id = fields.Many2one(comodel_name='account.move', string="Origin Tax Cash Basis Entry",
                                             tracking=True, help="The journal entry from which this tax cash basis journal entry has been created.")
    # ==== Auto-post feature fields ====
    auto_post = fields.Boolean(string='Post Automatically', default=False, copy=False, tracking=True,
                               help='If this checkbox is ticked, this entry will be automatically posted at its date.')
    # ==== Reverse feature fields ====
    reversed_entry_id = fields.Many2one(
        'account.move', string="Reversal of", readonly=True, copy=False, tracking=True, check_company=True)
    reversal_move_id = fields.One2many(
        'account.move', 'reversed_entry_id', tracking=True)
    # =========================================================
    # Invoice related fields
    # =========================================================
    # ==== Business fields ====
    fiscal_position_id = fields.Many2one('account.fiscal.position', string='Fiscal Position', readonly=True, states={'draft': [(
        'readonly', False)]}, check_company=True, tracking=True, domain="[('company_id', '=', company_id)]", ondelete="restrict", help="Fiscal positions are used to adapt taxes and accounts for particular customers or sales orders/invoices. The default value comes from the customer.")
    invoice_date = fields.Date(string='Invoice/Bill Date', readonly=True, index=True,
                               copy=False, tracking=True, states={'draft': [('readonly', False)]})
    invoice_date_due = fields.Date(string='Due Date', readonly=True, index=True,
                                   copy=False, tracking=True, states={'draft': [('readonly', False)]})
    invoice_payment_term_id = fields.Many2one('account.payment.term', string='Payment Terms',
                                              check_company=True, tracking=True, readonly=True, states={'draft': [('readonly', False)]})
    # /!\ invoice_line_ids is just a subset of line_ids.
    invoice_line_ids = fields.One2many('account.move.line', 'move_id', string='Invoice lines', tracking=True, copy=False, readonly=True, domain=[
                                       ('exclude_from_invoice_tab', '=', False)], states={'draft': [('readonly', False)]})
    invoice_incoterm_id = fields.Many2one('account.incoterms', string='Incoterm', tracking=True, default=_get_default_invoice_incoterm,
                                          help='International Commercial Terms are a series of predefined commercial terms used in international transactions.')
    display_qr_code = fields.Boolean(
        string="Display QR-code", related='company_id.qr_code', tracking=True)
    qr_code_method = fields.Selection(string="Payment QR-code", tracking=True, selection=lambda self: self.env['res.partner.bank'].get_available_qr_methods_in_sequence(
    ), help="Type of QR-code to be generated for the payment of this invoice, when printing it. If left blank, the first available and usable method will be used.")
    # ==== Payment widget fields ====
    invoice_outstanding_credits_debits_widget = fields.Text(
        groups="account.group_account_invoice,account.group_account_readonly", compute='_compute_payments_widget_to_reconcile_info')
    invoice_has_outstanding = fields.Boolean(groups="account.group_account_invoice,account.group_account_readonly",
                                             compute='_compute_payments_widget_to_reconcile_info')
    invoice_payments_widget = fields.Text(groups="account.group_account_invoice,account.group_account_readonly",
                                          compute='_compute_payments_widget_reconciled_info')
    # ==== Vendor bill fields ====
    invoice_vendor_bill_id = fields.Many2one('account.move', store=False, tracking=True,
                                             check_company=True, string='Vendor Bill', help="Auto-complete from a past bill.")
    invoice_partner_display_name = fields.Char(
        compute='_compute_invoice_partner_display_info', tracking=True, store=True)
    # ==== Cash rounding fields ====
    invoice_cash_rounding_id = fields.Many2one('account.cash.rounding', string='Cash Rounding Method', tracking=True, readonly=True, states={
                                               'draft': [('readonly', False)]}, help='Defines the smallest coinage of the currency that can be used to pay by cash.')
    # ==== Display purpose fields ====
    invoice_filter_type_domain = fields.Char(compute='_compute_invoice_filter_type_domain', 
                                             help="Technical field used to have a dynamic domain on journal / taxes in the form view.")
    bank_partner_id = fields.Many2one(
        'res.partner', help='Technical field to get the domain on the bank', compute='_compute_bank_partner_id')
    invoice_has_matching_suspense_amount = fields.Boolean(compute='_compute_has_matching_suspense_amount', groups='account.group_account_invoice,account.group_account_readonly',
                                                          help="Technical field used to display an alert on invoices if there is at least a matching amount in any supsense account.")
    tax_lock_date_message = fields.Char(compute='_compute_tax_lock_date_message',
                                        help="Technical field used to display a message when the invoice's accounting date is prior of the tax lock date.")
    # Technical field to hide Reconciled Entries stat button
    has_reconciled_entries = fields.Boolean(
        compute="_compute_has_reconciled_entries")
    show_reset_to_draft_button = fields.Boolean(
        compute='_compute_show_reset_to_draft_button')
    # ==== Hash Fields ====
    restrict_mode_hash_table = fields.Boolean(
        related='journal_id.restrict_mode_hash_table', tracking=True)
    secure_sequence_number = fields.Integer(
        string="Inalteralbility No Gap Sequence #", tracking=True, readonly=True, copy=False)
    inalterable_hash = fields.Char(
        string="Inalterability Hash", tracking=True, readonly=True, copy=False)
    string_to_hash = fields.Char(
        compute='_compute_string_to_hash', readonly=True)
    mr_show_analytic_account = fields.Boolean(
        related='company_id.mr_show_analytic_account')
    journal_entries_template = fields.Many2one(
        'account.move.template', string='Journal Entries Template', readonly=True, copy=False, states={'draft': [('readonly', False)]}, )
    analytic_tag_dynamic = fields.Many2many('account.analytic.tag', compute= 'compute_analytic_tag_dynamic')
    credit_note_expiry_date = fields.Boolean(
        string='Credit Note Expired Date')
    expiry_date = fields.Date(
        string='Expiry Date')
    tax_applies_on = fields.Char(string="Tax Applies to")
    approvers_ids = fields.Many2many('res.users', 'invoice_approvers_rel', string='Approvers List')
    approved_user_ids = fields.Many2many('res.users', 'invoice_approved_user_rel', string='Approved by User')


    @api.depends('analytic_group_ids')
    def compute_analytic_tag_dynamic(self):
        is_analytic_groups_balance_sheet = self.env['ir.config_parameter'].sudo(
        ).get_param('is_analytic_groups_balance_sheet', False)
        for record in self:
            analytic_tag_ids = ()
            if is_analytic_groups_balance_sheet:
                analytic_tag_ids = record.analytic_group_ids.ids
            record.analytic_tag_dynamic = [(6,0, analytic_tag_ids)]

    @api.onchange('analytic_group_ids')
    def onchange_analytic_group(self):
        for record in self:
            for line in record.invoice_line_ids:
                line.analytic_tag_ids = record.analytic_group_ids.ids
    
    @api.onchange('branch_id')
    def _depends_analytic_group_ids(self):
        self._get_default_analytic()

    @api.onchange('journal_entries_template')
    def _compute_journal_entries_template(self):
        data = [(5, 0, 0)]
        for record in self:
            if record.state == 'draft' and record.journal_entries_template:
                journal_entries_template = record.journal_entries_template
                record.approved_matrix_ids = []
                record.approved_matrix_ids = []
                for line in journal_entries_template.line_ids:
                    data.append((0, 0, {
                        'account_id': line.account_id.id or False,
                        'partner_id': line.partner_id.id or False,
                        'name': line.name or False,
                        'debit': line.debit,
                        'credit': line.credit,
                        'tax_tag_ids': [(6, 0, line.tax_tag_ids.ids)],
                    }))
                record.line_ids = data
                record.ref = journal_entries_template.ref or False
                record.date = journal_entries_template.date or False
                record.journal_id = journal_entries_template.journal_id.id or False
                record.to_check = journal_entries_template.to_check or False
                record.narration = journal_entries_template.narration or False

    # Main Function
    # ======================================================================================================

    def write(self, vals):
        move_type = self._context.get('default_move_type')
        if move_type == 'out_invoice':
            for line in self.line_ids:
                if line.date_maturity:
                    line.update({'date_maturity': self.invoice_date_due})
        if move_type == 'entry':
            self._check_balanced()
        res = super(AccountMove, self).write(vals)
        if 'active_model' in self._context:
            return res
        if 'down_payment' in self._context and self._context.get('down_payment'):
            return res        
        return res
    # End Main Function
    # ======================================================================================================

    # Compute Function
    # ======================================================================================================

    @api.depends('amount_total', 'company_id', 'branch_id')
    def _get_approval_matrix(self):
        for record in self:
            matrix_id = False
            if record.move_type == "out_invoice":
                matrix_id = self.env['approval.matrix.accounting'].search([
                    ('company_id', '=', record.company_id.id),
                    ('branch_id', '=', record.branch_id.id),
                    ('min_amount', '<=', record.amount_total),
                    ('max_amount', '>=', record.amount_total),
                    ('approval_matrix_type', '=', 'invoice')
                ], limit=1)
            elif record.move_type == "in_invoice":
                matrix_id = self.env['approval.matrix.accounting'].search([
                    ('company_id', '=', record.company_id.id),
                    ('branch_id', '=', record.branch_id.id),
                    ('min_amount', '<=', record.amount_total),
                    ('max_amount', '>=', record.amount_total),
                    ('approval_matrix_type', '=', 'bill')
                ], limit=1)
            elif record.move_type == "out_refund":
                matrix_id = self.env['approval.matrix.accounting'].search([
                    ('company_id', '=', record.company_id.id),
                    ('branch_id', '=', record.branch_id.id),
                    ('min_amount', '<=', record.amount_total),
                    ('max_amount', '>=', record.amount_total),
                    ('approval_matrix_type', '=', 'credit_note')
                ], limit=1)
            elif record.move_type == "in_refund":
                matrix_id = self.env['approval.matrix.accounting'].search([
                    ('company_id', '=', record.company_id.id),
                    ('branch_id', '=', record.branch_id.id),
                    ('min_amount', '<=', record.amount_total),
                    ('max_amount', '>=', record.amount_total),
                    ('approval_matrix_type', '=', 'refund_approval_matrix')
                ], limit=1)
            record.approval_matrix_id = matrix_id
            record._compute_approving_matrix_lines()

    def _get_approve_button_from_config(self):
        for record in self:
            is_invoice_approval_matrix = False
            if record.move_type == 'out_invoice':
                is_invoice_approval_matrix = self.env['ir.config_parameter'].sudo().get_param('is_invoice_approval_matrix', False)
            elif record.move_type == 'in_invoice':
                is_invoice_approval_matrix = self.env['ir.config_parameter'].sudo().get_param('is_bill_approval_matrix', False)
            elif record.move_type == 'out_refund':
                is_invoice_approval_matrix = self.env['ir.config_parameter'].sudo().get_param('is_credit_note_approval_matrix', False)
            elif record.move_type == 'in_refund':
                is_invoice_approval_matrix = self.env['ir.config_parameter'].sudo().get_param('is_refund_approval_matrix', False)
            record.is_invoice_approval_matrix = is_invoice_approval_matrix

    def _get_approve_button(self):
        for record in self:
            matrix_line = sorted(record.approved_matrix_ids.filtered(
                lambda r: not r.approved), key=lambda r: r.sequence)
            if len(matrix_line) == 0:
                record.is_approve_button = False
                record.approval_matrix_line_id = False
            elif len(matrix_line) > 0:
                matrix_line_id = matrix_line[0]
                if self.env.user.id in matrix_line_id.user_ids.ids and self.env.user.id != matrix_line_id.last_approved.id:
                    record.is_approve_button = True
                    record.approval_matrix_line_id = matrix_line_id.id
                else:
                    record.is_approve_button = False
                    record.approval_matrix_line_id = False
            else:
                record.is_approve_button = False
                record.approval_matrix_line_id = False

    def compute_to_approve_state_payment(self):
        for record in self:
            # count = self.env['account.payment'].search([('ref', '=', self.name), ('state', '=', 'to_approve')]).ids
            count = self.env['account.payment'].search([('ref', '=', self.name), ('state', 'in', ('draft','to_approve'))]).ids
            if not count and record.ref:
               count = self.env['account.payment'].search([('ref', '=', record.ref), ('state', 'in', ('draft','to_approve'))]).ids
            record.to_approve_state_payment_count = len(count)

    # End Compute Function
    # ======================================================================================================

    # API Function
    # ======================================================================================================

    # API Onchange ===========================================================================================

    @api.onchange('invoice_origin_id')
    def _onchange_invoice_origin_id(self):
        for record in self:
            if record.state == 'draft':
                invoice_origin_id = record.invoice_origin_id
                new_invoice_line_ids = [(5, 0, 0)]

                invoice_lines = invoice_origin_id.invoice_line_ids
                for inv_line in invoice_lines:
                    # Fill missing 'account_id and description'.
                    journal = self.env['account.journal'].browse(self._context.get(
                        'default_journal_id') or self._context.get('journal_id') or self.journal_id.id)
                    product = inv_line.product_id

                    values = []
                    if product.partner_ref:
                        values.append(product.partner_ref)
                    if journal.type == 'sale':
                        if product.description_sale:
                            values.append(product.description_sale)
                    elif journal.type == 'purchase':
                        if product.description_purchase:
                            values.append(product.description_purchase)
                    name = '\n'.join(values)

                    new_invoice_line_ids.append((0, 0, {'product_id': inv_line.product_id and inv_line.product_id.id or False,
                                                        'name': inv_line.name or name,
                                                        'account_id': inv_line.account_id.id or (journal and journal.default_account_id.id),
                                                        'quantity': inv_line.quantity or 0.0,
                                                        'price_unit': inv_line.price_unit or 0.0,
                                                        'product_uom_id': inv_line.product_uom_id.id,
                                                        'exclude_from_invoice_tab': inv_line.exclude_from_invoice_tab,
                                                        'tax_ids': [(6, 0, [x.id for x in inv_line.tax_ids])],
                                                        'price_tax': inv_line.price_tax,
                                                        'amount_currency': inv_line.amount_currency,
                                                        'currency_id': inv_line.currency_id.id,
                                                        'debit': inv_line.credit,
                                                        'credit': inv_line.debit,
                                                        }))

                record.invoice_line_ids = new_invoice_line_ids
                record._onchange_invoice_line_ids()
                record.invoice_origin_date = invoice_origin_id and invoice_origin_id.invoice_date or False

    @api.onchange('approval_matrix_id')
    def _compute_approving_matrix_lines(self):
        data = [(5, 0, 0)]
        approver_list = [(5, 0, 0)]
        for record in self:
            if record.state == 'draft' and record.is_invoice_approval_matrix:
                record.approved_matrix_ids = []
                counter = 1
                record.approved_matrix_ids = []
                approver_list = []
                for rec in record.approval_matrix_id:
                    for line in rec.approval_matrix_line_ids:
                        data.append((0, 0, {
                            'sequence': counter,
                            'user_ids': [(6, 0, line.user_ids.ids)],
                            'minimum_approver': line.minimum_approver,
                        }))
                        counter += 1
                        for approvers in line.user_ids:
                            approver_list.append(approvers.id)
                record.approved_matrix_ids = data
                record.approvers_ids = approver_list

    @api.onchange('partner_id', 'attn', 'ref', 'date')
    def branch_domain(self):
        res = {}
        self._get_approve_button_from_config()
        return res

    @api.onchange('branch_id')
    def _onchange_branch_id(self):
        return

    @api.onchange('journal_id')
    def _onchange_journal_id_fs_book(self):
        for sheet in self:
            if sheet.journal_id:
                sheet.is_fiscal_book_exclude = sheet.journal_id.is_fiscal_book_exclude

    @api.onchange('invoice_date', 'received_date')
    def _onchange_invoice_date(self):
        res = super(AccountMove, self)._onchange_invoice_date()
        if self.received_date:
            if not self.invoice_payment_term_id:
                self.invoice_date_due = self.received_date
            # self._recompute_payment_terms_lines()

    @api.onchange('invoice_date_due')
    def _onchange_accounting_invoice_date_due(self):
        if self.credit_note_expiry_date:
           self.expiry_date = self.invoice_date_due

    # End Onchange ===========================================================================================

    # API Model ===========================================================================================
    @api.model
    def default_get(self, fields):
        res = super(AccountMove, self).default_get(fields)
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        received_date_val = IrConfigParam.get_param('Use_received_date', False)
        credit_note_expiry_date = IrConfigParam.get_param('equip3_accounting_masterdata.credit_note_expiry_date', False)        
        # res_config = self.env['ir.config_parameter'].sudo().get_param('bi_sale_purchase_discount_with_tax.tax_discount_policy') or False
        res_config = self.company_id.tax_discount_policy or False        
        tax_information = False
        if res_config:
            if res_config == 'untax':
                tax_information = 'After Discount'
            else:
                tax_information = 'Before Discount'        
        for rec in self:
            if rec.move_type != 'out_refund':
                credit_note_expiry_date = False
            res["visible_received_date"] = received_date_val
            res["credit_note_expiry_date"] = credit_note_expiry_date
            res["tax_applies_on"] = tax_information
            # rec.visible_received_date = received_date_val
            # rec.credit_note_expiry_date = credit_note_expiry_date
            # rec.tax_applies_on = tax_information
        return res

    @api.model
    def _send_bill_notification(self):
        today_date = date.today()
        move_ids = self.search([
            ('invoice_date', '>=', today_date),
            ('move_type', '=', 'in_invoice'),
            ('state', 'in', ('draft', 'posted')),
            ('payment_state', 'in', ('not_paid', 'in_payment', 'partial'))
        ])
        ICP = self.env['ir.config_parameter'].sudo()
        template_id = self.env.ref('equip3_accounting_operation.email_template_bill_due_date_notification')
        whatsapp_template_id = self.env.ref('equip3_accounting_operation.whatsapp_template_pay_bill_reminder')
        reminder_notification_before = ICP.get_param('reminder_notification_before', 1)
        date_last_reminder_bill_before_due_date = datetime.today().date()
        wa_template_submitted = self.env.ref('equip3_accounting_operation.email_template_inv_bill_before_due_date')
        accounting_setting_id = self.env.ref("equip3_accounting_settings.accounting_setting_1").id
        accounting_config_settings =  self.env['accounting.config.settings'].search([('id', '=', accounting_setting_id)])
        invoice_bill_reminder = accounting_config_settings.invoice_bill_reminder
        reminder_interval_before_unit = accounting_config_settings.reminder_interval_before_unit
        reminder_interval_before = accounting_config_settings.reminder_interval_before
        days_bill_before = accounting_config_settings.days_bill_before
        sending_date_bill_before = accounting_config_settings.sending_date_bill_before
        dict_by_branch = {}

        if invoice_bill_reminder:
            for move in move_ids:
                if move.branch_id.id not in dict_by_branch:
                    dict_by_branch[move.branch_id.id] = move.amount_total
                else:
                    dict_by_branch[move.branch_id.id] += move.amount_total

            if reminder_interval_before_unit == "days":
                for move in dict_by_branch:
                    # notification_dates = [move_id.invoice_date]
                    # invoice_date = move_id.invoice_date
                    # for no in range(1, int(reminder_notification_before)):
                    #     invoice_date -= timedelta(days=int(reminder_interval_before))
                    #     notification_dates.append(invoice_date)
                    # if today_date in notification_dates:
                    #     self.send_bill_due_date_notification(move_id, template_id)
                    #     self._send_whatsapp_message_pay_bill(move_id, whatsapp_template_id)

                    notification_dates = []

                    invoice_dates = date_last_reminder_bill_before_due_date
                    try:
                        invoice_dates = datetime.strptime(
                            invoice_dates, "%Y-%m-%d")
                    except:
                        invoice_dates = invoice_dates

                    invoice_date_yesterday = invoice_dates
                    invoice_date = invoice_date_yesterday
                    notification_dates = [invoice_date_yesterday.strftime("%Y-%m-%d")]

                    for no in range(1, int(reminder_notification_before)):
                        invoice_date += timedelta(days=int(reminder_interval_before))
                        invoice_date_str = invoice_date.strftime("%Y-%m-%d")
                        notification_dates.append(invoice_date_str)

                    try:
                        today_date = today_date.strftime("%Y-%m-%d")
                    except:
                        today_date = today_date

                for move in dict_by_branch:
                    if today_date in notification_dates:
                        self.send_invoice_bill_after_due_date_notification(
                            move, dict_by_branch, template_id)
                        self._send_whatsapp_message_bill_after_due_date(
                            move, dict_by_branch, wa_template_submitted)

            elif reminder_interval_before_unit == "weeks":
                # week_days = 7 * int(reminder_interval_before)
                # for move_id in move_ids:
                #     notification_dates = [move_id.invoice_date]
                #     invoice_date = move_id.invoice_date
                #     for no in range(1, int(reminder_notification_before)):
                #         invoice_date -= timedelta(days=week_days)
                #         notification_dates.append(invoice_date)
                #     if today_date in notification_dates:
                #         self.send_bill_due_date_notification(move_id, template_id)
                #         self._send_whatsapp_message_pay_bill(move_id, whatsapp_template_id)

                week_days = 7 * int(reminder_interval_before)
                for move in dict_by_branch:
                    invoice_date = date_last_reminder_bill_before_due_date
                    try:
                        invoice_date = datetime.strptime(invoice_date, "%Y-%m-%d")
                    except:
                        invoice_date = invoice_date

                    # invoice_date = datetime.strptime(invoice_date,"%Y-%m-%d")
                    date_reminder_loop = False
                    for i in range(0, 7):
                        loop_date = invoice_date - timedelta(days=i)
                        loop_date_name = loop_date.strftime('%A')
                        loop_date_name = str(loop_date_name).lower()
                        if days_bill_before == loop_date_name:
                            date_reminder_loop = loop_date

                    loop_notification_dates = [date_reminder_loop.strftime("%Y-%m-%d")]
                    date_reminder_loop1 = date_reminder_loop

                    for no in range(1, 5):
                        date_reminder_loop1 += timedelta(days=int(week_days))
                        invoice_date_str = date_reminder_loop1.strftime("%Y-%m-%d")
                        loop_notification_dates.append(invoice_date_str)

                    today_date = today_date.strftime("%Y-%m-%d")
                    if today_date in loop_notification_dates:
                        self.send_invoice_bill_after_due_date_notification(
                            move, dict_by_branch, template_id)
                        self._send_whatsapp_message_bill_after_due_date(
                            move, dict_by_branch, wa_template_submitted)

                        ICP.set_param(
                            'date_last_reminder_bill_before_due_date', datetime.today().date())

            elif reminder_interval_before_unit == "months":
                for move in dict_by_branch:
                    reminder_interval_before_invoice = 1
                    if len(sending_date_bill_before) == 1:
                        sending_date_bill_before = "0" + sending_date_bill_before
                    reminder_invoice_date_monthly = today_date.strftime('%Y-%m-' + sending_date_bill_before)

                    today_date = today_date.strftime("%Y-%m-%d")
                    if today_date == reminder_invoice_date_monthly:
                        self.send_invoice_bill_after_due_date_notification(
                            move, dict_by_branch, template_id)
                        self._send_whatsapp_message_bill_after_due_date(
                            move, dict_by_branch, wa_template_submitted)
                        ICP.set_param(
                            'date_last_reminder_bill_before_due_date', datetime.today().date())

    @api.model
    def _send_reminder_bill_notification(self):
        today_date = date.today()
        move_ids = self.search([
            ('invoice_date', '<=', today_date),
            ('move_type', '=', 'in_invoice'),
            ('state', '=', 'posted'),
            ('payment_state', 'in', ('not_paid', 'in_payment', 'partial'))
        ])
        ICP = self.env['ir.config_parameter'].sudo()
        template_id = self.env.ref('equip3_accounting_operation.email_template_bill_due_date_reminder_notification')
        whatsapp_template_id = self.env.ref('equip3_accounting_operation.whatsapp_template_pay_bill')
        reminder_notification_after = ICP.get_param('reminder_notification_after', 1)
        date_last_reminder_bill_after_due_date = datetime.today().date()
        wa_template_submitted = self.env.ref('equip3_accounting_operation.email_template_inv_bill_after_due_date')
        accounting_setting_id = self.env.ref("equip3_accounting_settings.accounting_setting_1").id
        accounting_config_settings =  self.env['accounting.config.settings'].search([('id', '=', accounting_setting_id)])
        invoice_bill_reminder = accounting_config_settings.invoice_bill_reminder
        reminder_interval_after_unit = accounting_config_settings.reminder_interval_after_unit
        reminder_interval_after = accounting_config_settings.reminder_interval_after
        days_bill_after = accounting_config_settings.days_bill_after
        sending_date_bill_after = accounting_config_settings.sending_date_bill_after

        dict_data_bybranch = {}
        if invoice_bill_reminder:
            for move in move_ids:
                if move.branch_id.id not in dict_data_bybranch:
                    dict_data_bybranch[move.branch_id.id] = move.amount_total
                    # dict_data_band.append(dict_data_bybranch)
                else:
                    dict_data_bybranch[move.branch_id.id] += move.amount_total

            if reminder_interval_after_unit == "days":
                for move in dict_data_bybranch:
                    # invoice_date = move_id.invoice_date + timedelta(days=int(reminder_interval_after))
                    # notification_dates = [invoice_date]
                    # for no in range(1, int(reminder_notification_after)):
                    #     invoice_date += timedelta(days=int(reminder_interval_after))
                    #     notification_dates.append(invoice_date)
                    # if today_date in notification_dates:
                    #     self.send_bill_due_date_notification(move_id, template_id)
                    #     self._send_whatsapp_message_pay_bill(move_id, whatsapp_template_id)

                    notification_dates = []
                    invoice_dates = date_last_reminder_bill_after_due_date

                    try:
                        invoice_dates = datetime.strptime(
                            invoice_dates, "%Y-%m-%d")
                    except:
                        invoice_dates = invoice_dates

                    invoice_date_yesterday = invoice_dates
                    invoice_date = invoice_date_yesterday
                    notification_dates = [invoice_date_yesterday.strftime("%Y-%m-%d")]
                    for no in range(1, int(reminder_notification_after)):
                        invoice_date += timedelta(days=int(reminder_interval_after))
                        invoice_date_str = invoice_date.strftime("%Y-%m-%d")
                        notification_dates.append(invoice_date_str)

                    try:
                        today_date = today_date.strftime("%Y-%m-%d")
                    except:
                        today_date = today_date

                    if today_date in notification_dates:
                        self.send_invoice_bill_after_due_date_notification(
                            move, dict_data_bybranch, template_id)
                        self._send_whatsapp_message_bill_after_due_date(
                            move, dict_data_bybranch, wa_template_submitted)

                        ICP.set_param(
                            'date_last_reminder_bill_after_due_date', datetime.today().date())

            elif reminder_interval_after_unit == "weeks":
                # week_days = 7 * int(reminder_interval_after)
                # for move_id in move_ids:
                #     invoice_date = move_id.invoice_date + timedelta(days=int(reminder_interval_after))
                #     notification_dates = [invoice_date]
                #     for no in range(1, int(reminder_notification_after)):
                #         invoice_date += timedelta(days=week_days)
                #         notification_dates.append(invoice_date)
                #     if today_date in notification_dates:
                #         self.send_bill_due_date_notification(move_id, template_id)
                #         self._send_whatsapp_message_pay_bill(move_id, whatsapp_template_id)

                week_days = 7 * int(reminder_interval_after)
                for move in dict_data_bybranch:
                    invoice_date = date_last_reminder_bill_after_due_date
                    try:
                        invoice_date = datetime.strptime(invoice_date, "%Y-%m-%d")
                    except:
                        invoice_date = invoice_date

                    # invoice_date = datetime.strptime(invoice_date,"%Y-%m-%d")
                    date_reminder_loop = False
                    for i in range(0, 7):
                        loop_date = invoice_date - timedelta(days=i)
                        loop_date_name = loop_date.strftime('%A')
                        loop_date_name = str(loop_date_name).lower()

                        if days_bill_after == loop_date_name:
                            date_reminder_loop = loop_date

                    loop_notification_dates = [date_reminder_loop.strftime("%Y-%m-%d")]
                    date_reminder_loop1 = date_reminder_loop

                    for no in range(1, 5):
                        date_reminder_loop1 += timedelta(days=int(week_days))
                        invoice_date_str = date_reminder_loop1.strftime("%Y-%m-%d")
                        loop_notification_dates.append(invoice_date_str)

                    today_date = today_date.strftime("%Y-%m-%d")
                    if today_date in loop_notification_dates:
                        self.send_invoice_bill_after_due_date_notification(
                            move, dict_data_bybranch, template_id)
                        self._send_whatsapp_message_bill_after_due_date(
                            move, dict_data_bybranch, wa_template_submitted)

                        ICP.set_param(
                            'date_last_reminder_bill_after_due_date', datetime.today().date())

            elif reminder_interval_after_unit == "months":
                for move in dict_data_bybranch:
                    try:
                        today_date = datetime.strptime(today_date, "%Y-%m-%d")
                    except:
                        today_date = today_date

                    if len(sending_date_bill_after) == 1:
                        sending_date_bill_after = "0" + sending_date_bill_after

                    reminder_bill_date_monthly = today_date.strftime( '%Y-%m-' + sending_date_bill_after)
                    today_date = today_date.strftime("%Y-%m-%d")

                    if today_date == reminder_bill_date_monthly:
                        self.send_invoice_bill_after_due_date_notification(
                            move, dict_data_bybranch, template_id)
                        self._send_whatsapp_message_bill_after_due_date(
                            move, dict_data_bybranch, wa_template_submitted)
                        ICP.set_param(
                            'date_last_reminder_bill_after_due_date', datetime.today().date())

    @api.model
    def _send_invoice_after_notification(self):
        today_date = date.today()
        move_ids = self.search([
            ('invoice_date_due', '<=', today_date),
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('payment_state', 'in', ('not_paid', 'in_payment', 'partial'))
        ])
        ICP = self.env['ir.config_parameter'].sudo()
        template_id = self.env.ref(
            'equip3_accounting_operation.email_template_invoice_reminder_after_notification')
        # reminder_interval_after_invoice = ICP.get_param(
        #     'reminder_interval_after_invoice', 1)
        # eminder_interval_after_unit_invoice = ICP.get_param(
        #     'eminder_interval_after_unit_invoice', 'days')
        reminder_notification_after_invoice = ICP.get_param(
            'reminder_notification_after_invoice', 1)
        # sending_date_invoice_after = ICP.get_param(
        #     'sending_date_invoice_after', 1)
        # days_invoice_after = ICP.get_param('days_invoice_after', 'monday')
        date_last_reminder_after_due_date = datetime.today().date()
        wa_template_submitted = self.env.ref(
            'equip3_accounting_operation.email_template_inv_after_due_date')
        
        accounting_setting_id = self.env.ref("equip3_accounting_settings.accounting_setting_1").id
        accounting_config_settings =  self.env['accounting.config.settings'].search([('id', '=', accounting_setting_id)])
        invoice_bill_reminder = accounting_config_settings.invoice_bill_reminder
        reminder_interval_after_unit_invoice = accounting_config_settings.reminder_interval_after_unit_invoice
        reminder_interval_after_invoice = accounting_config_settings.reminder_interval_after_invoice
        days_invoice_after = accounting_config_settings.days_invoice_after
        sending_date_invoice_after = accounting_config_settings.sending_date_invoice_after

        dict_data_bybranch = {}
        if invoice_bill_reminder:
            for move in move_ids:
                if move.branch_id.id not in dict_data_bybranch:
                    dict_data_bybranch[move.branch_id.id] = move.amount_total
                    # dict_data_band.append(dict_data_bybranch)
                else:
                    dict_data_bybranch[move.branch_id.id] += move.amount_total

            if reminder_interval_after_unit_invoice == "days":
                for move in dict_data_bybranch:
                    notification_dates = []

                    invoice_dates = date_last_reminder_after_due_date
                    try:
                        invoice_dates = datetime.strptime(
                            invoice_dates, "%Y-%m-%d")
                    except:
                        invoice_dates = invoice_dates

                    invoice_date_yesterday = invoice_dates
                    invoice_date = invoice_date_yesterday
                    notification_dates = [invoice_date_yesterday.strftime("%Y-%m-%d")]
                    for no in range(1, int(reminder_notification_after_invoice)):
                        invoice_date += timedelta(days=int(reminder_interval_after_invoice))
                        invoice_date_str = invoice_date.strftime("%Y-%m-%d")
                        notification_dates.append(invoice_date_str)

                    try:
                        today_date = today_date.strftime("%Y-%m-%d")
                    except:
                        today_date = today_date

                    if today_date in notification_dates:
                        self.send_invoice_after_due_date_notification(
                            move, dict_data_bybranch, template_id)
                        self._send_whatsapp_message_after_due_date(
                            move, dict_data_bybranch, wa_template_submitted)

                        ICP.set_param(
                            'date_last_reminder_after_due_date', datetime.today().date())

            elif reminder_interval_after_unit_invoice == "weeks":
                week_days = 7 * int(reminder_interval_after_invoice)
                for move in dict_data_bybranch:
                    invoice_date = date_last_reminder_after_due_date
                    try:
                        invoice_date = datetime.strptime(invoice_date, "%Y-%m-%d")
                    except:
                        invoice_date = invoice_date

                    # invoice_date = datetime.strptime(invoice_date,"%Y-%m-%d")
                    date_reminder_loop = False
                    for i in range(0, 7):
                        loop_date = invoice_date - timedelta(days=i)
                        loop_date_name = loop_date.strftime('%A')
                        loop_date_name = str(loop_date_name).lower()
                        if days_invoice_after == loop_date_name:
                            date_reminder_loop = loop_date

                    loop_notification_dates = [ date_reminder_loop.strftime("%Y-%m-%d")]
                    date_reminder_loop1 = date_reminder_loop

                    for no in range(1, 5):
                        date_reminder_loop1 += timedelta(days=int(week_days))
                        invoice_date_str = date_reminder_loop1.strftime("%Y-%m-%d")
                        loop_notification_dates.append(invoice_date_str)  

                    try:
                        today_date = datetime.strptime(today_date, "%Y-%m-%d")
                    except:
                        today_date = today_date          

                    today_date = today_date.strftime("%Y-%m-%d")
                    if today_date in loop_notification_dates:
                        self.send_invoice_after_due_date_notification(
                            move, dict_data_bybranch, template_id)
                        self._send_whatsapp_message_after_due_date(
                            move, dict_data_bybranch, wa_template_submitted)

                        ICP.set_param(
                            'date_last_reminder_after_due_date', datetime.today().date())

            elif reminder_interval_after_unit_invoice == "months":
                for move in dict_data_bybranch:
                    try:
                        today_date = datetime.strptime(today_date, "%Y-%m-%d")
                    except:
                        today_date = today_date
                    
                    if len(sending_date_invoice_after) == 1:
                        sending_date_invoice_after = "0" + sending_date_invoice_after
                    
                    reminder_interval_after_invoice = 1
                    reminder_invoice_date_monthly = today_date.strftime('%Y-%m-' + sending_date_invoice_after)

                    today_date = today_date.strftime("%Y-%m-%d")
                    if today_date == reminder_invoice_date_monthly:
                        self.send_invoice_after_due_date_notification(
                            move, dict_data_bybranch, template_id)
                        self._send_whatsapp_message_after_due_date(
                            move, dict_data_bybranch, wa_template_submitted)
                        ICP.set_param(
                            'date_last_reminder_after_due_date', datetime.today().date())

    @api.model
    def _send_invoice_before_notification(self):
        today_date = date.today()
        move_ids = self.search([
            ('invoice_date_due', '>=', today_date),
            ('move_type', '=', 'out_invoice'),
            ('state', 'in', ('draft', 'posted')),
            ('payment_state', 'in', ('not_paid', 'in_payment', 'partial'))
        ])

        ICP = self.env['ir.config_parameter'].sudo()
        template_id = self.env.ref(
            'equip3_accounting_operation.email_template_invoice_reminder_before_notification')
        reminder_notification_before_invoice = ICP.get_param(
            'reminder_notification_before_invoice', 1)
        date_last_reminder_due_date = datetime.today().date()
        accounting_setting_id = self.env.ref("equip3_accounting_settings.accounting_setting_1").id
        accounting_config_settings =  self.env['accounting.config.settings'].search([('id', '=', accounting_setting_id)])
        invoice_bill_reminder = accounting_config_settings.invoice_bill_reminder
        reminder_interval_before_unit_invoice = accounting_config_settings.reminder_interval_before_unit_invoice
        reminder_interval_before_invoice = accounting_config_settings.reminder_interval_before_invoice
        days_invoice_before = accounting_config_settings.days_invoice_before
        sending_date_invoice_before = accounting_config_settings.sending_date_invoice_before

        list_data_bybrand = {}
        dict_data_band = []
        if invoice_bill_reminder:
            for move in move_ids:
                if move.branch_id.id not in list_data_bybrand:
                    list_data_bybrand[move.branch_id.id] = move.amount_total
                    dict_data_band.append(list_data_bybrand)
                else:
                    list_data_bybrand[move.branch_id.id] += move.amount_total

            if reminder_interval_before_unit_invoice == "days":
                print(dict_data_band)
                for move in dict_data_band:
                    notification_dates = []

                    invoice_dates = date_last_reminder_due_date
                    try:
                        invoice_dates = datetime.strptime(
                            invoice_dates, "%Y-%m-%d")
                    except:
                        invoice_dates = invoice_dates

                    invoice_date_yesterday = invoice_dates
                    invoice_date = invoice_date_yesterday
                    notification_dates = [
                        invoice_date_yesterday.strftime("%Y-%m-%d")]
                    for no in range(1, int(reminder_notification_before_invoice)):
                        invoice_date += timedelta(days=int(reminder_interval_before_invoice))
                        invoice_date_str = invoice_date.strftime("%Y-%m-%d")
                        notification_dates.append(invoice_date_str)

                    try:
                        today_date = datetime.strptime(today_date, "%Y-%m-%d")
                    except:
                        today_date = today_date

                    today_date = today_date.strftime("%Y-%m-%d")
                    if today_date in notification_dates:
                        self.send_invoice_before_due_date_notification(move, template_id)
                        ICP.set_param('date_last_reminder_due_date',
                                    datetime.today().date())

            elif reminder_interval_before_unit_invoice == "weeks":
                week_days = 7 * int(reminder_interval_before_invoice)
                for move in dict_data_band:
                    invoice_date = date_last_reminder_due_date
                    try:
                        invoice_date = datetime.strptime(invoice_date, "%Y-%m-%d")
                    except:
                        invoice_date = invoice_date

                    # invoice_date = datetime.strptime(invoice_date,"%Y-%m-%d")
                    date_reminder_loop = False
                    for i in range(0, 7):
                        loop_date = invoice_date - timedelta(days=i)
                        loop_date_name = loop_date.strftime('%A')
                        loop_date_name = str(loop_date_name).lower()
                        if days_invoice_before == loop_date_name:
                            date_reminder_loop = loop_date

                    loop_notification_dates = [date_reminder_loop.strftime("%Y-%m-%d")]
                    date_reminder_loop1 = date_reminder_loop

                    for no in range(1, 5):
                        date_reminder_loop1 += timedelta(days=int(week_days))
                        invoice_date_str = date_reminder_loop1.strftime("%Y-%m-%d")
                        loop_notification_dates.append(invoice_date_str)

                    try:
                        today_date = today_date.strftime("%Y-%m-%d")
                    except:
                        today_date = today_date

                    if today_date in loop_notification_dates:
                        self.send_invoice_before_due_date_notification(move, template_id)
                        ICP.set_param('date_last_reminder_due_date',
                                    datetime.today().date())

            elif reminder_interval_before_unit_invoice == "months":
                for move in dict_data_band:
                    try:
                        today_date = datetime.strptime(today_date, "%Y-%m-%d")
                    except:
                        today_date = today_date
                    
                    if len(sending_date_invoice_before) == 1:
                            sending_date_invoice_before = "0" + sending_date_invoice_before

                    reminder_interval_before_invoice = 1
                    reminder_invoice_date_monthly = today_date.strftime('%Y-%m-' + sending_date_invoice_before)

                    today_date = today_date.strftime("%Y-%m-%d")
                    if today_date == reminder_invoice_date_monthly:
                        self.send_invoice_before_due_date_notification(move, template_id)
                        ICP.set_param('date_last_reminder_due_date',
                                    datetime.today().date())

    @api.model
    def _send_automated_followup_invoice(self):
        today_date = date.today()
        template_id = self.env.ref(
            'equip3_accounting_operation.email_template_invoice_followup_notification')
        wa_template_id = self.env.ref(
            'equip3_accounting_operation.wa_template_invoice_followup')
        partner_ids = self.env['res.partner'].search([])
        for partner_id in partner_ids:
            move_ids = self.search([
                ('invoice_date', '<=', today_date),
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
                ('partner_id', 'in', partner_id.ids),
                ('payment_state', 'in',
                 ('not_paid', 'in_payment', 'partial'))
            ])
            if move_ids:
                temp_inv = self.env['followup.invoice.tmp'].create({'partner_id': partner_id.id,
                                                                    'move_id': move_ids,
                                                                    'date': today_date,
                                                                    })
                ctx = {
                    "overdue_template": temp_inv.overdue_template,
                    "email_from": self.env.company.email,
                    "date": date.today(),
                    "email_to": temp_inv.partner_id.email,
                }
                mail_id = template_id.with_context(
                    ctx).send_mail(temp_inv.id, True)
                self._send_whatsapp_message_statement(
                    wa_template_id, partner_id, mail_id, temp_inv.overdue_template)

    @api.model
    def check_expired_date(self):
        today_date = date.today()
        move_ids = self.search([
                ('expiry_date', '<=', today_date),
                ('credit_note_expiry_date', '=', True),
                
                ('move_type', '=', 'out_refund'),
                ('state', '=', 'posted'),
                ('payment_state', 'in',
                 ('not_paid', 'in_payment', 'partial'))
            ])
        print (move_ids,'ffggg')
        if move_ids:
            move_ids.button_draft()
            move_ids.write({'state' : 'expired'})



    @api.model
    def _send_whatsapp_message_pay_bill(self, move, whatsapp_template_id):
        return True
        account_user_reminder_id = self.env['account.user.reminder'].search(
            [('branch_id', '=', move.branch_id.id), ('reminder_type', '=', 'bill')], limit=1)
        user_ids = list(
            set(account_user_reminder_id.account_line_ids.user_ids))
        final_day = str(abs((move.invoice_date - date.today()).days))
        if user_ids:
            if move.currency_id.position == "before":
                amount = move.currency_id.symbol + ' ' + str(move.amount_total)
            else:
                amount = str(move.amount_total) + ' ' + move.currency_id.symbol
            for user in user_ids:
                phone_num = str(user.partner_id.mobile)
                string_test = str(tools.html2plaintext(
                    whatsapp_template_id.body_html))
                if "${date_today}" in string_test:
                    string_test = string_test.replace(
                        "${date_today}", date.today().strftime(DEFAULT_SERVER_DATE_FORMAT))
                if "${user}" in string_test:
                    string_test = string_test.replace("${user}", user.name)
                if "${days}" in string_test:
                    string_test = string_test.replace("${days}", final_day)
                if "${date}" in string_test:
                    string_test = string_test.replace(
                        "${date}", move.invoice_date_due.strftime(DEFAULT_SERVER_DATE_FORMAT))
                if "${amount}" in string_test:
                    string_test = string_test.replace("${amount}", amount)
                if "${vendor}" in string_test:
                    string_test = string_test.replace(
                        "${vendor}", move.partner_id.name)
                if "${br}" in string_test:
                    string_test = string_test.replace("${br}", f"\n")
                if "+" in phone_num:
                    phone_num = phone_num.replace("+", "")
                param = {'body': string_test, 'text': string_test,
                         'phone': phone_num, 'previewBase64': '', 'title': ''}
                domain = self.env['ir.config_parameter'].sudo(
                ).get_param('chat.api.url')
                token = self.env['ir.config_parameter'].sudo(
                ).get_param('chat.api.token')
                try:
                    request_server = requests.post(
                        f'{domain}/sendMessage?token={token}', params=param, headers=headers, verify=True)
                    response = json.loads(request_server.text)
                except ConnectionError:
                    raise ValidationError(
                        "Not connect to API Chat Server. Limit reached or not active")

    @api.model
    def send_bill_due_date_notification(self, move, template_id):
        account_user_reminder_id = self.env['account.user.reminder'].search(
            [('branch_id', '=', move.branch_id.id), ('reminder_type', '=', 'bill')], limit=1)
        user_ids = list(
            set(account_user_reminder_id.account_line_ids.user_ids))
        if user_ids:
            if move.currency_id.position == "before":
                amount = move.currency_id.symbol + ' ' + str(move.amount_total)
            else:
                amount = str(move.amount_total) + ' ' + move.currency_id.symbol
            text = ''
            days = abs((move.invoice_date - date.today()).days)
            if days <= 6:
                text = str(days) + ' days'
            else:
                text = str(int(days / 7)) + ' weeks'
            ctx = {
                "email_from": self.env.company.email,
                "date": date.today(),
                "days": text,
                "amount": amount
            }
            for user in user_ids:
                ctx.update({
                    "email_to": user.partner_id.email,
                    "user": user.name,
                })
                template_id.with_context(ctx).send_mail(
                    move.id
                )
                body_html = (
                    self.env['mail.render.mixin']
                    .with_context(ctx)
                    ._render_template(
                        template_id.body_html,
                        "account.move",
                        move.ids,
                        post_process=True
                    )[move.id]
                )
                message_id = (
                    self.env["mail.message"]
                        .sudo()
                        .create(
                        {
                            "subject": "Reminder to Pay the Bill",
                            "body": body_html,
                            'message_type': 'notification',
                            "model": "account.move",
                            "res_id": move.id,
                            "partner_ids": user.partner_id.ids,
                            "author_id": self.env.user.partner_id.id,
                            "notification_ids": [(0, 0, {
                                'res_partner_id': user.partner_id.id,
                                'notification_type': 'inbox'
                            })]
                        }
                    )
                )

    @api.model
    def send_invoice_due_date_notification(self, move, template_id):
        account_user_reminder_id = self.env['account.user.reminder'].search(
            [('branch_id', '=', move.branch_id.id), ('reminder_type', '=', 'invoice')], limit=1)
        user_ids = list(
            set(account_user_reminder_id.account_line_ids.user_ids))
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        action_invoice_out = self.env.ref(
            'account.action_move_out_invoice_type')
        link_url_invoice = base_url+"/web#id=" + \
            str(move.id)+"&action="+str(action_invoice_out.id)

        if user_ids:
            if move.currency_id.position == "before":
                amount = move.currency_id.symbol + ' ' + str(move.amount_total)
            else:
                amount = str(move.amount_total) + ' ' + move.currency_id.symbol
            days = abs((move.invoice_date_due - date.today()).days)
            text = ''
            if days <= 6:
                text = str(days) + ' days'
            else:
                text = str(int(days / 7)) + ' weeks'
            ctx = {
                "email_from": self.env.company.email,
                "days": text,
                "amount": amount,
                "date": date.today(),
                "link": link_url_invoice,
                "branch": move.branch_id.name,

            }

            for user in user_ids:
                ctx.update({
                    "email_to": user.partner_id.email,
                    "user": user.name,
                })
                template_id.with_context(ctx).send_mail(
                    move.id
                )
                body_html = (
                    self.env['mail.render.mixin']
                    .with_context(ctx)
                    ._render_template(
                        template_id.body_html,
                        "account.move",
                        move.ids,
                        post_process=True
                    )[move.id]
                )
                message_id = (
                    self.env["mail.message"]
                        .sudo()
                        .create(
                        {
                            "subject": "Invoice Reminder",
                            "body": body_html,
                            'message_type': 'notification',
                            "model": "account.move",
                            "res_id": move.id,
                            "partner_ids": user.partner_id.ids,
                            "author_id": self.env.user.partner_id.id,
                            "notification_ids": [(0, 0, {
                                'res_partner_id': user.partner_id.id,
                                'notification_type': 'inbox'
                            })]
                        }
                    )
                )

    @api.model
    def send_invoice_after_due_date_notification(self, branch_id, list_data_bybrand, template_id):
        branchs = self.env['res.branch'].browse(branch_id)
        today_date = date.today()
        move_ids = self.search([
            ('invoice_date_due', '<=', today_date),
            ('move_type', '=', 'out_invoice'),
            ('state', 'in', ('draft', 'posted')),
            ('branch_id', '=', branch_id),
            ('payment_state', 'in', ('not_paid', 'in_payment', 'partial'))
        ])
        account_user_reminder_id = self.env['account.user.reminder'].search(
            [('branch_id', '=', branch_id), ('reminder_type', '=', 'invoice')], limit=1)
        user_ids = list(
            set(account_user_reminder_id.account_line_ids.user_ids))
        if not user_ids:

            user_ids = self.env['res.users'].browse(2)
            user_ids = list(set(user_ids))
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        action_invoice_out = self.env.ref(
            'equip3_accounting_operation.action_move_out_invoice_type_ref2')
        link_url_invoice = base_url+"/web#action="+str(action_invoice_out.id)

        if user_ids:
            amount = "{:0,.2f}".format(float(list_data_bybrand[branch_id]))
            amount = 'Rp' + ' ' + amount

            ctx = {
                "email_from": self.env.company.email,
                "amount": amount,
                "date": date.today(),
                "link": link_url_invoice,
                "branch": branchs.name,

            }

            for user in user_ids:
                ctx.update({
                    "email_to": user.partner_id.email,
                    "user": user.name,
                })
                template_id.with_context(ctx).send_mail(move_ids.ids[0])
                body_html = (
                    self.env['mail.render.mixin']
                    .with_context(ctx)
                    ._render_template(
                        template_id.body_html,
                        "account.move",
                        move_ids.ids,
                        post_process=True
                    )[move_ids.ids[0]]
                )
                message_id = (
                    self.env["mail.message"]
                        .sudo()
                        .create(
                        {
                            "subject": "Invoice Reminder",
                            "body": body_html,
                            'message_type': 'notification',
                            "model": "account.move",
                            "res_id": False,
                            "partner_ids": user.partner_id.ids,
                            "author_id": self.env.user.partner_id.id,
                            "notification_ids": [(0, 0, {
                                'res_partner_id': user.partner_id.id,
                                'notification_type': 'inbox'
                            })]
                        }
                    )
                )

    @api.model
    def send_invoice_bill_after_due_date_notification(self, branch_id, list_data_bybrand, template_id):
        branchs = self.env['res.branch'].browse(branch_id)
        today_date = date.today()
        move_ids = self.search([
            ('invoice_date_due', '<=', today_date),
            ('move_type', '=', 'in_invoice'),
            ('state', 'in', ('draft', 'posted')),
            ('branch_id', '=', branch_id),
            ('payment_state', 'in', ('not_paid', 'in_payment', 'partial'))
        ])

        account_user_reminder_id = self.env['account.user.reminder'].search(
            [('branch_id', '=', branch_id), ('reminder_type', '=', 'invoice')], limit=1)
        user_ids = list(
            set(account_user_reminder_id.account_line_ids.user_ids))
        if not user_ids:

            user_ids = self.env['res.users'].browse(2)
            user_ids = list(set(user_ids))
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        action_invoice_out = self.env.ref(
            'equip3_accounting_operation.action_move_in_invoice_type_ref2')
        link_url_invoice = base_url+"/web#action="+str(action_invoice_out.id)

        if user_ids:
            amount = "{:0,.2f}".format(float(list_data_bybrand[branch_id]))
            amount = 'Rp' + ' ' + amount

            ctx = {
                "email_from": self.env.company.email,
                "amount": amount,
                "date": date.today(),
                "link": link_url_invoice,
                "branch": branchs.name,

            }

            for user in user_ids:
                ctx.update({
                    "email_to": user.partner_id.email,
                    "user": user.name,
                })
                template_id.with_context(ctx).send_mail(move_ids.ids[0])
                body_html = (
                    self.env['mail.render.mixin']
                    .with_context(ctx)
                    ._render_template(
                        template_id.body_html,
                        "account.move",
                        move_ids.ids,
                        post_process=True
                    )[move_ids.ids[0]]
                )
                message_id = (
                    self.env["mail.message"]
                        .sudo()
                        .create(
                        {
                            "subject": "Invoice Reminder",
                            "body": body_html,
                            'message_type': 'notification',
                            "model": "account.move",
                            "res_id": False,
                            "partner_ids": user.partner_id.ids,
                            "author_id": self.env.user.partner_id.id,
                            "notification_ids": [(0, 0, {
                                'res_partner_id': user.partner_id.id,
                                'notification_type': 'inbox'
                            })]
                        }
                    )
                )

    @api.model
    def _send_whatsapp_message_after_due_date(self, branch_id, list_data_bybrand, whatsapp_template_id):
        return True
        account_user_reminder_id = self.env['account.user.reminder'].search(
            [('branch_id', '=', branch_id), ('reminder_type', '=', 'invoice')], limit=1)
        branchs = self.env['res.branch'].browse(branch_id)
        if branchs:
            branch_name = branchs.name
        else:
            branch_name = 'No Branch'
        user_ids = list(
            set(account_user_reminder_id.account_line_ids.user_ids))
        if not user_ids:
            user_ids = self.env['res.users'].browse(2)
            user_ids = list(set(user_ids))
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        action_invoice_out = self.env.ref(
            'equip3_accounting_operation.action_move_out_invoice_type_ref2')
        link_url_invoice = base_url+"/web#action="+str(action_invoice_out.id)
        if user_ids:
            amount = "{:0,.2f}".format(float(list_data_bybrand[branch_id]))
            amount = 'Rp' + ' ' + amount
            for user in user_ids:
                # phone_num = str(user.partner_id.phone or user.partner_id.mobile)
                phone_num = str(user.mobile or user.employee_phone)

                string_test = str(tools.html2plaintext(
                    whatsapp_template_id.body_html))
                if "${user}" in string_test:
                    string_test = string_test.replace("${user}", user.name)
                if "${amount}" in string_test:
                    string_test = string_test.replace("${amount}", amount)
                if "${branch_id}" in string_test:
                    string_test = string_test.replace(
                        "${branch_id}", branch_name)

                if "${link}" in string_test:
                    string_test = string_test.replace(
                        "${link}", link_url_invoice)
                if "${br}" in string_test:
                    string_test = string_test.replace("${br}", f"\n")
                if "+" in phone_num:
                    phone_num = phone_num.replace("+", "")
                param = {'body': string_test, 'text': string_test,
                         'phone': phone_num, 'previewBase64': '', 'title': ''}

                domain = self.env['ir.config_parameter'].sudo(
                ).get_param('chat.api.url')
                token = self.env['ir.config_parameter'].sudo(
                ).get_param('chat.api.token')
                # print (f'{domain}/sendMessage?token={token}')
                # print (param, 'param')
                # print (headers, 'headers')
                # jjj
                try:
                    request_server = requests.post(
                        f'{domain}/sendMessage?token={token}', params=param, headers=headers, verify=True)
                    response = json.loads(request_server.text)

                except ConnectionError:
                    raise ValidationError(
                        "Not connect to API Chat Server. Limit reached or not active")

    @api.model
    def _send_whatsapp_message_bill_after_due_date(self, branch_id, list_data_bybrand, whatsapp_template_id):
        return True
        account_user_reminder_id = self.env['account.user.reminder'].search(
            [('branch_id', '=', branch_id), ('reminder_type', '=', 'invoice')], limit=1)
        branchs = self.env['res.branch'].browse(branch_id)
        if branchs:
            branch_name = branchs.name
        else:
            branch_name = 'No Branch'
        user_ids = list(
            set(account_user_reminder_id.account_line_ids.user_ids))
        if not user_ids:
            user_ids = self.env['res.users'].browse(2)
            user_ids = list(set(user_ids))
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        action_invoice_out = self.env.ref(
            'equip3_accounting_operation.action_move_in_invoice_type_ref2')
        link_url_invoice = base_url+"/web#action="+str(action_invoice_out.id)
        if user_ids:
            amount = "{:0,.2f}".format(float(list_data_bybrand[branch_id]))
            amount = 'Rp' + ' ' + amount
            for user in user_ids:
                # phone_num = str(user.partner_id.phone or user.partner_id.mobile)
                phone_num = str(user.mobile or user.employee_phone)

                string_test = str(tools.html2plaintext(
                    whatsapp_template_id.body_html))
                if "${user}" in string_test:
                    string_test = string_test.replace("${user}", user.name)
                if "${amount}" in string_test:
                    string_test = string_test.replace("${amount}", amount)
                if "${branch_id}" in string_test:
                    string_test = string_test.replace(
                        "${branch_id}", branch_name)

                if "${link}" in string_test:
                    string_test = string_test.replace(
                        "${link}", link_url_invoice)
                if "${br}" in string_test:
                    string_test = string_test.replace("${br}", f"\n")
                if "+" in phone_num:
                    phone_num = phone_num.replace("+", "")
                param = {'body': string_test, 'text': string_test,
                         'phone': phone_num, 'previewBase64': '', 'title': ''}

                domain = self.env['ir.config_parameter'].sudo(
                ).get_param('chat.api.url')
                token = self.env['ir.config_parameter'].sudo(
                ).get_param('chat.api.token')
                try:
                    request_server = requests.post(
                        f'{domain}/sendMessage?token={token}', params=param, headers=headers, verify=True)
                    response = json.loads(request_server.text)
                except ConnectionError:
                    raise ValidationError(
                        "Not connect to API Chat Server. Limit reached or not active")

    @api.model
    def send_invoice_before_due_date_notification(self, move, template_id):
        for m in move:
            branchs = self.env['res.branch'].browse(m)
            today_date = date.today()
            move_ids = self.search([
                ('invoice_date_due', '>=', today_date),
                ('move_type', '=', 'out_invoice'),
                ('state', 'in', ('draft', 'posted')),
                ('branch_id', '=', m),
                ('payment_state', 'in', ('not_paid', 'in_payment', 'partial'))
            ])
            account_user_reminder_id = self.env['account.user.reminder'].search(
                [('branch_id', '=', m), ('reminder_type', '=', 'invoice')], limit=1)
            user_ids = list(
                set(account_user_reminder_id.account_line_ids.user_ids))
            base_url = self.env['ir.config_parameter'].get_param(
                'web.base.url')
            action_invoice_out = self.env.ref(
                'equip3_accounting_operation.action_move_out_invoice_type_ref2')
            link_url_invoice = base_url + \
                "/web#action="+str(action_invoice_out.id)

            if user_ids:
                amount = "{:0,.2f}".format(float(move[m]))
                amount = 'Rp' + ' ' + amount

                ctx = {
                    "email_from": self.env.company.email,
                    "amount": amount,
                    "date": date.today(),
                    "link": link_url_invoice,
                    "branch": branchs.name,

                }

                for user in user_ids:
                    ctx.update({
                        "email_to": user.partner_id.email,
                        "user": user.name,
                    })
                    template_id.with_context(ctx).send_mail(move_ids.ids[0])
                    body_html = (
                        self.env['mail.render.mixin']
                        .with_context(ctx)
                        ._render_template(
                            template_id.body_html,
                            "account.move",
                            move_ids.ids,
                            post_process=True
                        )[move_ids.ids[0]]
                    )
                    message_id = (
                        self.env["mail.message"]
                            .sudo()
                            .create(
                            {
                                "subject": "Invoice Reminder",
                                "body": body_html,
                                'message_type': 'notification',
                                "model": "account.move",
                                "res_id": False,
                                "partner_ids": user.partner_id.ids,
                                "author_id": self.env.user.partner_id.id,
                                "notification_ids": [(0, 0, {
                                    'res_partner_id': user.partner_id.id,
                                    'notification_type': 'inbox'
                                })]
                            }
                        )
                    )

    @api.model
    def _send_whatsapp_message(self, template_id, approver, currency=False, url=False, reason=False):
        wa_sender = waParam()
        # template = self.env.ref('equip3_accounting_operation.wa_template_application_for_invoice_approval')
        for record in self:
            if record.move_type in ['out_invoice', 'in_invoice', 'out_refund', 'in_refund']:
                string_test = str(template_id.message)
                if "${approver_name}" in string_test:
                    string_test = string_test.replace(
                        "${approver_name}", approver.name)
                if "${submitter_name}" in string_test:
                    string_test = string_test.replace(
                        "${submitter_name}", record.request_partner_id.name)
                if "${amount_invoice}" in string_test:
                    string_test = string_test.replace(
                        "${amount_invoice}", str(record.amount_total))
                if "${currency}" in string_test:
                    string_test = string_test.replace("${currency}", currency)
                if "${partner_name}" in string_test:
                    string_test = string_test.replace(
                        "${partner_name}", record.partner_id.name)
                if "${due_date}" in string_test:
                    # string_test = string_test.replace("${due_date}", fields.Datetime.from_string(
                    #     record.invoice_date_due).strftime('%d/%m/%Y'))
                    due_date = fields.Datetime.from_string(record.invoice_date_due)
                    if due_date is not None:
                        string_test = string_test.replace("${due_date}", due_date.strftime('%d/%m/%Y'))
                    else:
                        # Handle the case when due_date is None
                        # You can replace the placeholder with an empty string or any default value
                        string_test = string_test.replace("${due_date}", "")
                
                if "${date_invoice}" in string_test:
                    date_invoice = fields.Datetime.from_string(record.invoice_date)
                    if date_invoice is not None:
                        string_test = string_test.replace("${date_invoice}", date_invoice.strftime('%d/%m/%Y'))
                    else:
                        # Handle the case when date_invoice is None
                        # You can replace the placeholder with an empty string or any default value
                        string_test = string_test.replace("${date_invoice}", "")
                        _logger.error(f"date_invoice is None for record {record.id}")

                    # string_test = string_test.replace("${date_invoice}", fields.Datetime.from_string(
                    #     record.invoice_date).strftime('%d/%m/%Y'))
                if "${create_date}" in string_test:
                    string_test = string_test.replace("${create_date}", fields.Datetime.from_string(
                        record.create_date).strftime('%d/%m/%Y'))
                if "${feedback}" in string_test:
                    string_test = string_test.replace("${feedback}", reason)
                if "${br}" in string_test:
                    string_test = string_test.replace("${br}", f"\n")
                if "${url}" in string_test:
                    string_test = string_test.replace("${url}", url)
                phone_num = str(approver.mobile or approver.employee_phone)
                if "+" in phone_num:
                    phone_num = phone_num.replace("+", "")
                wa_sender.set_wa_string(string_test, template_id._name, template_id=template_id)
                wa_sender.send_wa(phone_num)
                # param = {'body': string_test, 'text': string_test,
                #          'phone': phone_num, 'previewBase64': '', 'title': ''}
                # domain = self.env['ir.config_parameter'].sudo(
                # ).get_param('chat.api.url')
                # token = self.env['ir.config_parameter'].sudo(
                # ).get_param('chat.api.token')
                # try:
                #     request_server = requests.post(
                #         f'{domain}/sendMessage?token={token}', params=param, headers=headers, verify=True)
                #     response = json.loads(request_server.text)
                # except ConnectionError:
                #     raise ValidationError(
                #         "Not connect to API Chat Server. Limit reached or not active")
                    # connector_id.ca_request('post', 'sendMessage', param)

    @api.model
    def _send_whatsapp_message_statement(self, template_id, partner_id, mail_id, overdue_template=False):
        return True
        string_test = str(tools.html2plaintext(template_id.body_html))
        if "${overdue_template}" in string_test:
            string_test = string_test.replace(
                "${overdue_template}", overdue_template)
        if "${br}" in string_test:
            string_test = string_test.replace("${br}", f"\n")
        # if "${url}" in string_test:
        #     string_test = string_test.replace("${url}", url)
        phone_num = str(partner_id.mobile)
        if "+" in phone_num:
            phone_num = phone_num.replace("+", "")
        param = {'body': string_test, 'text': string_test,
                 'phone': phone_num, 'previewBase64': '', 'title': ''}
        # param2 = {'body': }
        domain = self.env['ir.config_parameter'].sudo(
        ).get_param('chat.api.url')
        token = self.env['ir.config_parameter'].sudo(
        ).get_param('chat.api.token')
        try:
            request_server = requests.post(
                f'{domain}/sendMessage?token={token}', params=param, headers=headers, verify=True)
            response = json.loads(request_server.text)
        except ConnectionError:
            raise ValidationError(
                "Not connect to API Chat Server. Limit reached or not active")

        # also send mail attachment to whatsapp
        mail = self.env['mail.mail'].sudo().browse(mail_id)
        for attachment in mail.attachment_ids:
            body = 'data:' + attachment.mimetype + ';base64,' + attachment.datas.decode()
            param = {'body': body, 'filename': attachment.name,
                     'phone': phone_num}
        try:
            request_server = requests.post(
                f'{domain}/sendFile?token={token}', json=param, headers=headers, verify=True)
            response = json.loads(request_server.text)
        except ConnectionError:
            raise ValidationError(
                "Not connect to API Chat Server. Limit reached or not active")

    # End Model ===========================================================================================

    # End API Function
    # ======================================================================================================

    # Button Action Function
    # ======================================================================================================

    def send_request_for_approval(self):
        for record in self:
            if record.move_type == "out_refund":
                action_id = self.env.ref('account.action_move_out_refund_type')
                template_id = self.env.ref(
                    'equip3_accounting_operation.email_template_credit_notes_approval_matrix')
                # wa_template_id = self.env.ref(
                #     'equip3_accounting_operation.email_template_req_credit_note_wa')
                wa_template_id = self.env.ref(
                    'equip3_accounting_operation.wa_template_request_for_credit_note')
            elif record.move_type == "in_refund":
                action_id = self.env.ref('account.action_move_in_refund_type')
                template_id = self.env.ref(
                    'equip3_accounting_operation.email_template_refunds_approval_matrix')
                # wa_template_id = self.env.ref(
                #     'equip3_accounting_operation.email_template_req_refund_wa')
                wa_template_id = self.env.ref(
                    'equip3_accounting_operation.wa_template_request_for_refund')
            elif record.move_type == "in_invoice":
                action_id = self.env.ref('account.action_move_in_invoice_type')
                template_id = self.env.ref(
                    'equip3_accounting_operation.email_template_bill_approval_matrix')
                # wa_template_id = self.env.ref(
                #     'equip3_accounting_operation.email_template_req_bill_wa')
                wa_template_id = self.env.ref(
                    'equip3_accounting_operation.wa_template_request_for_approval_bill')
            else:
                action_id = self.env.ref(
                    'account.action_move_out_invoice_type')
                template_id = self.env.ref(
                    'equip3_accounting_operation.email_template_inv_approval_matrix')
                # wa_template_id = self.env.ref(
                #     'equip3_accounting_operation.email_template_inv_wa')
                wa_template_id = self.env.ref(
                    'equip3_accounting_operation.wa_template_application_for_invoice_approval')
            base_url = self.env['ir.config_parameter'].sudo(
            ).get_param('web.base.url')
            url = base_url + '/web#id=' + \
                str(record.id) + '&action=' + str(action_id.id) + \
                '&view_type=form&model=account.move'
            currency = ''
            invoice_name = 'Draft Invoice' if record.state != 'posted' else record.name
            if record.currency_id.position == 'before':
                currency = record.currency_id.symbol + \
                    ' ' + str(record.amount_total)
            else:
                currency = str(record.amount_total) + ' ' + \
                    record.currency_id.symbol
            record.request_partner_id = self.env.user.partner_id.id
            if record.approved_matrix_ids and len(record.approved_matrix_ids[0].user_ids) > 1:
                for approved_matrix_id in record.approved_matrix_ids[0].user_ids:
                    approver = approved_matrix_id
                    ctx = {
                        'email_from': self.env.user.company_id.email,
                        'email_to': approver.partner_id.email,
                        'approver_name': approver.name,
                        'date': date.today(),
                        'submitter': self.env.user.name,
                        'url': url,
                        'invoice_name': invoice_name,
                        "due_date": record.invoice_date_due,
                        "date_invoice": record.invoice_date,
                        "currency": currency,
                    }
                    template_id.with_context(ctx).send_mail(record.id, True)
                    record._send_whatsapp_message(
                        wa_template_id, approver, currency, url)
            else:
                approver = record.approved_matrix_ids[0].user_ids[0]
                ctx = {
                    'email_from': self.env.user.company_id.email,
                    'email_to': approver.partner_id.email,
                    'approver_name': approver.name,
                    'date': date.today(),
                    'submitter': self.env.user.name,
                    'url': url,
                    'invoice_name': invoice_name,
                    "due_date": record.invoice_date_due,
                    "date_invoice": record.invoice_date,
                    "currency": currency,
                }
                template_id.with_context(ctx).send_mail(record.id, True)
                record._send_whatsapp_message(
                    wa_template_id, approver, currency, url)
            record.write({'state': 'to_approve'})

    def action_request_for_approval(self):
        for record in self:
            record.send_request_for_approval()
            
            # for line in record.approved_matrix_ids:
            #     line.write({'approver_state': 'draft'})

    def action_approve(self):
        for record in self:
            if record.move_type == "out_refund":
                action_id = self.env.ref('account.action_move_out_refund_type')
                template_id = self.env.ref(
                    'equip3_accounting_operation.email_template_credit_notes_approval_matrix')
                template_id_submitter = self.env.ref(
                    'equip3_accounting_operation.email_template_credit_notes_submitter_approval_matrix')
                # wa_template_id = self.env.ref(
                #     'equip3_accounting_operation.email_template_req_credit_note_wa')
                wa_template_id = self.env.ref(
                    'equip3_accounting_operation.wa_template_request_for_credit_note')
                # wa_template_submitted = self.env.ref(
                #     'equip3_accounting_operation.email_template_appr_credit_note_wa')
                wa_template_submitted = self.env.ref(
                    'equip3_accounting_operation.wa_template_approval_credit_note')
            elif record.move_type == "in_refund":
                action_id = self.env.ref('account.action_move_in_refund_type')
                template_id = self.env.ref(
                    'equip3_accounting_operation.email_template_refunds_approval_matrix')
                template_id_submitter = self.env.ref(
                    'equip3_accounting_operation.email_template_refunds_submitter_approval_matrix')
                # wa_template_id = self.env.ref(
                #     'equip3_accounting_operation.email_template_req_refund_wa')
                wa_template_id = self.env.ref(
                    'equip3_accounting_operation.wa_template_request_for_refund')
                # wa_template_submitted = self.env.ref(
                #     'equip3_accounting_operation.email_template_appr_refund_wa')
                wa_template_submitted = self.env.ref(
                    'equip3_accounting_operation.wa_template_approval_refund')
            elif record.move_type == "in_invoice":
                action_id = self.env.ref('account.action_move_in_invoice_type')
                template_id = self.env.ref(
                    'equip3_accounting_operation.email_template_bill_approval_matrix')
                template_id_submitter = self.env.ref(
                    'equip3_accounting_operation.email_template_submitter_bill_approval_matrix')
                # wa_template_id = self.env.ref(
                #     'equip3_accounting_operation.email_template_req_bill_wa')
                wa_template_id = self.env.ref(
                    'equip3_accounting_operation.wa_template_request_for_approval_bill')
                # wa_template_submitted = self.env.ref(
                #     'equip3_accounting_operation.email_template_appr_bill_wa')
                wa_template_submitted = self.env.ref(
                    'equip3_accounting_operation.wa_template_approval_bill')
            else:
                action_id = self.env.ref(
                    'account.action_move_out_invoice_type')
                template_id = self.env.ref(
                    'equip3_accounting_operation.email_template_inv_approval_matrix')
                template_id_submitter = self.env.ref(
                    'equip3_accounting_operation.email_template_submitter_approval_matrix')
                # wa_template_id = self.env.ref(
                #     'equip3_accounting_operation.email_template_inv_wa')
                wa_template_id = self.env.ref(
                    'equip3_accounting_operation.wa_template_application_for_invoice_approval')
                # wa_template_submitted = self.env.ref(
                #     'equip3_accounting_operation.email_template_inv_wa_approval')
                wa_template_submitted = self.env.ref(
                    'equip3_accounting_operation.wa_template_approval_of_invoice')
            base_url = self.env['ir.config_parameter'].sudo(
            ).get_param('web.base.url')
            url = base_url + '/web#id=' + \
                str(record.id) + '&action=' + str(action_id.id) + \
                '&view_type=form&model=account.move'
            user = self.env.user
            currency = ''
            invoice_name = 'Draft Invoice' if record.state != 'posted' else record.name
            if record.currency_id.position == 'before':
                currency = record.currency_id.symbol + str(record.amount_total)
            else:
                currency = str(record.amount_total) + ' ' + \
                    record.currency_id.symbol
            if record.is_approve_button and record.approval_matrix_line_id:
                approval_matrix_line_id = record.approval_matrix_line_id
                if user.id in approval_matrix_line_id.user_ids.ids and \
                        user.id not in approval_matrix_line_id.approved_users.ids:
                    name = approval_matrix_line_id.state_char or ''
                    utc_datetime = datetime.now()
                    local_timezone = pytz.timezone(self.env.user.tz)
                    local_datetime = utc_datetime.replace(tzinfo=pytz.utc)
                    local_datetime = local_datetime.astimezone(
                        local_timezone).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                    if name != '':
                        name += "\n • %s: Approved - %s" % (
                            self.env.user.name, local_datetime)
                    else:
                        name += "• %s: Approved - %s" % (
                            self.env.user.name, local_datetime)

                    approval_matrix_line_id.write({
                        'last_approved': self.env.user.id, 'state_char': name,
                        'approved_users': [(4, user.id)]})
                    record.approved_user_ids = [(4, user.id)]
                    if approval_matrix_line_id.minimum_approver == len(approval_matrix_line_id.approved_users.ids):
                        approval_matrix_line_id.write(
                            {'time_stamp': datetime.now(), 'approved': True})
                        next_approval_matrix_line_id = sorted(record.approved_matrix_ids.filtered(
                            lambda r: not r.approved), key=lambda r: r.sequence)
                        if next_approval_matrix_line_id and len(next_approval_matrix_line_id[0].user_ids) > 1:
                            for approving_matrix_line_user in next_approval_matrix_line_id[0].user_ids:
                                ctx = {
                                    'email_from': self.env.user.company_id.email,
                                    'email_to': approving_matrix_line_user.partner_id.email,
                                    'approver_name': approving_matrix_line_user.name,
                                    'date': date.today(),
                                    'submitter': self.env.user.name,
                                    'url': url,
                                    'invoice_name': invoice_name,
                                    "due_date": record.invoice_date_due,
                                    "date_invoice": record.invoice_date,
                                    "currency": currency,
                                }
                                template_id.sudo().with_context(ctx).send_mail(record.id, True)
                                record._send_whatsapp_message(
                                    wa_template_id, approving_matrix_line_user, currency, url)
                        else:
                            if next_approval_matrix_line_id and next_approval_matrix_line_id[0].user_ids:
                                # approver = record.approved_matrix_ids[0].user_ids[0]
                                ctx = {
                                    'email_from': self.env.user.company_id.email,
                                    'email_to': next_approval_matrix_line_id[0].user_ids[0].partner_id.email,
                                    'approver_name': next_approval_matrix_line_id[0].user_ids[0].name,
                                    'date': date.today(),
                                    'submitter': self.env.user.name,
                                    'url': url,
                                    'invoice_name': invoice_name,
                                    "due_date": record.invoice_date_due,
                                    "date_invoice": record.invoice_date,
                                    "currency": currency,
                                }
                                template_id.sudo().with_context(ctx).send_mail(record.id, True)
                                record._send_whatsapp_message(
                                    wa_template_id, next_approval_matrix_line_id[0].user_ids[0], currency, url)
                    # else:
                    #     approval_matrix_line_id.write({'approver_state': 'pending'})
            if len(record.approved_matrix_ids) == len(record.approved_matrix_ids.filtered(lambda r: r.approved)):
                record.write({'state': 'approved'})
                record.action_post()
                if record.move_type in ("out_refund", "in_refund"):
                    email_to = record.request_partner_id.email
                else:
                    email_to = record.partner_id.email
                ctx = {
                    'email_from': self.env.user.company_id.email,
                    'email_to': email_to,
                    'approver_name': record.name,
                    'date': date.today(),
                    'create_date': record.create_date.date(),
                    'submitter': self.env.user.name,
                    'url': url,
                    'invoice_name': invoice_name,
                    "due_date": record.invoice_date_due,
                    "date_invoice": record.invoice_date,
                    "currency": currency,
                }
                template_id_submitter.sudo().with_context(ctx).send_mail(record.id, True)
                record._send_whatsapp_message(
                    wa_template_submitted, record.request_partner_id.user_ids, currency, url)

    def action_reject(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Accounting Matrix Reject ',
            'res_model': 'accounting.matrix.reject',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
        }

    def action_post(self):
        for rec in self:
            if rec.period_id.id == False:
                raise UserError(
                    "Please define the Fiscal Year and Period first before post any Journal Entry")
            elif rec.period_id.id != False and rec.period_id.state == 'done':
                raise UserError(
                    "You can not post any journal entry already on Closed Period")
            self.with_context(check_move_validity=False)._post(soft=False)
        return 

    # def convert_manual_currency_exchange_rate(self):
    #     for rec in self:
    #         for line in rec.line_ids:
    #             if line.amount_currency > 0:
    #                 debit = line.amount_currency * rec.manual_currency_exchange_inverse_rate
    #                 credit = 0.0
    #                 line.with_context(check_move_validity=False).write({
    #                     'debit': debit,
    #                     'credit': credit,
    #                 })
    #                 print('line.debit', line.debit)
    #             else:
    #                 credit = abs(line.amount_currency) * rec.manual_currency_exchange_inverse_rate
    #                 debit = 0.0
    #                 line.with_context(check_move_validity=False).write({
    #                     'debit': debit,
    #                     'credit': credit,
    #                 })
    #                 print('line.credit', line.credit)
    #     return
    #
    # def write(self, vals):
    #     res = super(AccountMove, self).write(vals)
    #     for rec in self:
    #         if rec.currency_id != rec.company_id.currency_id and rec.move_type in ['out_invoice', 'in_invoice'] and rec.apply_manual_currency_exchange:
    #             if rec.state in ('draft', 'to_approve'):
    #                 rec.convert_manual_currency_exchange_rate()
    #     return res
    
    def button_draft(self):
        if self.payment_state in ('partial', 'paid'):
                raise UserError(
                    "Please unreconcile or cancel the payment associated to this invoice first before resetting to draft.")
        else:
            res = super(AccountMove, self).button_draft()
            for rec in self:
                if rec.period_id.id == False:
                    raise UserError(
                        "Please define the Fiscal Year and Period first before  reset to draft any Journal Entry")
                elif rec.period_id.id != False and rec.period_id.state == 'done':
                    raise UserError(
                        "You can not reset to draft any journal entry already on Closed Period")
                

            AccountMoveLine = self.env['account.move.line']
            excluded_move_ids = []

            if self._context.get('suspense_moves_mode'):
                excluded_move_ids = AccountMoveLine.search(AccountMoveLine._get_suspense_moves_domain(
                ) + [('move_id', 'in', self.ids)]).mapped('move_id').ids

            for move in self:
                if move in move.line_ids.mapped('full_reconcile_id.exchange_move_id'):
                    raise UserError(
                        _('You cannot reset to draft an exchange difference journal entry.'))
                if move.tax_cash_basis_rec_id:
                    raise UserError(
                        _('You cannot reset to draft a tax cash basis journal entry.'))
                if move.restrict_mode_hash_table and move.state == 'posted' and move.id not in excluded_move_ids:
                    raise UserError(
                        _('You cannot modify a posted entry of this journal because it is in strict mode.'))
                # We remove all the analytics entries for this journal
                move.mapped('line_ids.analytic_line_ids').unlink()

            self.mapped('line_ids').remove_move_reconcile()
            self.write({'state': 'draft', 'is_move_sent': False})

        # return super(AccountMove, self).button_draft()
    # End Button Function
    # ======================================================================================================

    # Trigered Function
    # ======================================================================================================

    def open_payments(self):
        action = self.env['ir.actions.act_window']._for_xml_id(
            'account.action_account_payments')
        # ids = self.env['account.payment'].search([('ref', '=', self.name), ('state', '=', 'to_approve')]).ids
        ids = self.env['account.payment'].search([('ref', '=', self.name), ('state', 'in', ('draft', 'to_approve'))]).ids
        if not ids and self.ref:
            ids = self.env['account.payment'].search([('ref', '=', self.ref), ('state', 'in', ('draft','to_approve'))]).ids
        action['context'] = {
            'default_payment_type': 'outbound' if self.move_type in ('in_invoice', 'in_refund') else 'inbound',
            'create': False,
        }
        action['domain'] = [('id', 'in', ids)]
        return action

    def last_day_of_month(self, day):
        next_month = day.replace(day=28) + relativedelta(days=4)
        return next_month - relativedelta(days=next_month.day)

    def _recompute_payment_terms_lines(self):
        res = super(AccountMove, self)._recompute_payment_terms_lines()
        ''' Compute the dynamic payment term lines of the journal entry.'''
        self.ensure_one()
        self = self.with_company(self.company_id)
        in_draft_mode = self != self._origin
        today = fields.Date.context_today(self)
        self = self.with_company(self.journal_id.company_id)

        def _get_payment_terms_computation_date(self):
            ''' Get the date from invoice that will be used to compute the payment terms.
            :param self:    The current account.move record.
            :return:        A datetime.date object.
            '''
            if self.invoice_payment_term_id:
                if self.received_date:
                    return self.received_date
                else:
                    return self.invoice_date or today
            else:
                return self.invoice_date_due or self.invoice_date or today

        def _get_payment_terms_account(self, payment_terms_lines):
            ''' Get the account from invoice that will be set as receivable / payable account.
            :param self:                    The current account.move record.
            :param payment_terms_lines:     The current payment terms lines.
            :return:                        An account.account record.
            '''
            if payment_terms_lines:
                # Retrieve account from previous payment terms lines in order to allow the user to set a custom one.
                return payment_terms_lines[0].account_id
            elif self.partner_id:
                # Retrieve account from partner.
                if self.is_sale_document(include_receipts=True):
                    return self.partner_id.property_account_receivable_id
                else:
                    return self.partner_id.property_account_payable_id
            else:
                # Search new account.
                domain = [
                    ('company_id', '=', self.company_id.id),
                    ('internal_type', '=', 'receivable' if self.move_type in (
                        'out_invoice', 'out_refund', 'out_receipt') else 'payable'),
                ]
                return self.env['account.account'].search(domain, limit=1)

        def _compute_payment_terms(self, date, total_balance, total_amount_currency):
            ''' Compute the payment terms.
            :param self:                    The current account.move record.
            :param date:                    The date computed by '_get_payment_terms_computation_date'.
            :param total_balance:           The invoice's total in company's currency.
            :param total_amount_currency:   The invoice's total in invoice's currency.
            :return:                        A list <to_pay_company_currency, to_pay_invoice_currency, due_date>.
            '''
            if self.invoice_payment_term_id:
                to_compute = self.invoice_payment_term_id.compute(
                    total_balance, date_ref=date, currency=self.company_id.currency_id)
                if self.currency_id == self.company_id.currency_id:
                    # Single-currency.
                    return [(b[0], b[1], b[1]) for b in to_compute]
                else:
                    # Multi-currencies.
                    to_compute_currency = self.invoice_payment_term_id.compute(
                        total_amount_currency, date_ref=date, currency=self.currency_id)
                    return [(b[0], b[1], ac[1]) for b, ac in zip(to_compute, to_compute_currency)]
            else:
                return [(fields.Date.to_string(date), total_balance, total_amount_currency)]

        def _compute_diff_payment_terms_lines(self, existing_terms_lines, account, to_compute):
            ''' Process the result of the '_compute_payment_terms' method and creates/updates corresponding invoice lines.
            :param self:                    The current account.move record.
            :param existing_terms_lines:    The current payment terms lines.
            :param account:                 The account.account record returned by '_get_payment_terms_account'.
            :param to_compute:              The list returned by '_compute_payment_terms'.
            '''
            # As we try to update existing lines, sort them by due date.
            existing_terms_lines = existing_terms_lines.sorted(
                lambda line: line.date_maturity or today)
            existing_terms_lines_index = 0

            # Recompute amls: update existing line or create new one for each payment term.
            new_terms_lines = self.env['account.move.line']
            for date_maturity, balance, amount_currency in to_compute:
                currency = self.journal_id.company_id.currency_id
                if currency and currency.is_zero(balance) and len(to_compute) > 1:
                    continue

                if existing_terms_lines_index < len(existing_terms_lines):
                    # Update existing line.
                    candidate = existing_terms_lines[existing_terms_lines_index]
                    existing_terms_lines_index += 1
                    candidate.update({
                        'date_maturity': date_maturity,
                        'amount_currency': -amount_currency,
                        'debit': balance < 0.0 and -balance or 0.0,
                        'credit': balance > 0.0 and balance or 0.0,
                        'analytic_tag_ids': self.analytic_group_ids.ids,
                    })
                else:
                    # Create new line.
                    create_method = in_draft_mode and self.env[
                        'account.move.line'].new or self.env['account.move.line'].create
                    candidate = create_method({
                        'name': self.payment_reference or '',
                        'debit': balance < 0.0 and -balance or 0.0,
                        'credit': balance > 0.0 and balance or 0.0,
                        'quantity': 1.0,
                        'amount_currency': -amount_currency,
                        'date_maturity': date_maturity,
                        'move_id': self.id,
                        'currency_id': self.currency_id.id,
                        'account_id': account.id,
                        'partner_id': self.commercial_partner_id.id,
                        'analytic_tag_ids': self.analytic_group_ids.ids,
                        'exclude_from_invoice_tab': True,
                    })
                new_terms_lines += candidate
                if in_draft_mode:
                    candidate.update(candidate._get_fields_onchange_balance(
                        force_computation=True))
            return new_terms_lines

        existing_terms_lines = self.line_ids.filtered(
            lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))
        others_lines = self.line_ids.filtered(
            lambda line: line.account_id.user_type_id.type not in ('receivable', 'payable'))
        company_currency_id = (self.company_id or self.env.company).currency_id
        total_balance = sum(others_lines.mapped(
            lambda l: company_currency_id.round(l.balance)))
        total_amount_currency = sum(others_lines.mapped('amount_currency'))

        if not others_lines:
            self.line_ids -= existing_terms_lines
            return

        computation_date = _get_payment_terms_computation_date(self)
        account = _get_payment_terms_account(self, existing_terms_lines)
        to_compute = _compute_payment_terms(
            self, computation_date, total_balance, total_amount_currency)
        new_terms_lines = _compute_diff_payment_terms_lines(
            self, existing_terms_lines, account, to_compute)

        # Remove old terms lines that are no longer needed.
        self.line_ids -= existing_terms_lines - new_terms_lines

        if new_terms_lines:
            self.payment_reference = new_terms_lines[-1].name or ''
            self.invoice_date_due = new_terms_lines[-1].date_maturity

    # End Trigered Function
    # ======================================================================================================
    def action_invoice_sent(self, from_confirmation_wizard=False):
        self.ensure_one()
        customer_availability = self.partner_id.customer_availability
        if customer_availability and not from_confirmation_wizard:
            day_checks = {
                "Monday": self.partner_id.invoiced_at_monday,
                "Tuesday": self.partner_id.invoiced_at_tuesday,
                "Wednesday": self.partner_id.invoiced_at_wednesday,
                "Thursday": self.partner_id.invoiced_at_thursday,
                "Friday": self.partner_id.invoiced_at_friday,
                "Saturday": self.partner_id.invoiced_at_saturday,
                "Sunday": self.partner_id.invoiced_at_sunday,
            }
            today = fields.Date.today()
            day_name = today.strftime("%A")
            if not day_checks[day_name]:
                # Open the confirmation wizard
                wizard = self.env['invoice.confirmation.availability'].create({
                    'message': "You can't send invoice out of customer availability days.",
                    'invoice_id': self.id
                })
                return {
                    'name': 'Confirmation',
                    'type': 'ir.actions.act_window',
                    'res_model': 'invoice.confirmation.availability',
                    'res_id': wizard.id,
                    'view_mode': 'form',
                    'view_type': 'form',
                    'target': 'new',
                    'context': self.env.context,
                }

        res = super(AccountMove, self).action_invoice_sent()
        return res
    
    def invoice_whatsapp(self, from_confirmation_wizard=False):
        self.ensure_one()
        customer_availability = self.partner_id.customer_availability
        if customer_availability and not from_confirmation_wizard:
            day_checks = {
                "Monday": self.partner_id.invoiced_at_monday,
                "Tuesday": self.partner_id.invoiced_at_tuesday,
                "Wednesday": self.partner_id.invoiced_at_wednesday,
                "Thursday": self.partner_id.invoiced_at_thursday,
                "Friday": self.partner_id.invoiced_at_friday,
                "Saturday": self.partner_id.invoiced_at_saturday,
                "Sunday": self.partner_id.invoiced_at_sunday,
            }
            today = fields.Date.today()
            day_name = today.strftime("%A")
            if not day_checks[day_name]:
                # Open the confirmation wizard
                wizard = self.env['invoice.confirmation.availability'].create({
                    'message': "You can't send invoice out of customer availability days.",
                    'invoice_id': self.id,
                    'whatsapp': True
                })
                return {
                    'name': 'Confirmation',
                    'type': 'ir.actions.act_window',
                    'res_model': 'invoice.confirmation.availability',
                    'res_id': wizard.id,
                    'view_mode': 'form',
                    'view_type': 'form',
                    'target': 'new',
                    'context': self.env.context,
                }

        res = super(AccountMove, self).invoice_whatsapp()
        return res

    def _auto_compute_invoice_reference(self):
        ''' Hook to be overridden to set custom conditions for auto-computed invoice references.
            :return True if the move should get a auto-computed reference else False
            :rtype bool
        '''
        self.ensure_one()
        res = super(AccountMove, self)._auto_compute_invoice_reference()
        if self.move_type == 'out_invoice':
            return res
        return self.move_type in ['out_invoice', 'in_invoice'] and not self.payment_reference

class ResCompany(models.Model):
    _inherit = 'res.company'

    mr_show_analytic_account = fields.Boolean(
        compute='_compute_show_analytic_account')

    def _compute_show_analytic_account(self):
        for data in self:
            if data.user_has_groups('analytic.group_analytic_tags'):
                data.mr_show_analytic_account = False
            else:
                data.mr_show_analytic_account = True


class ValidateAccountMove(models.TransientModel):
    _inherit = "validate.account.move"

    def validate_move(self):
        if self._context.get('active_model') == 'account.move':
            domain = [('id', 'in', self._context.get(
                'active_ids', [])), ('state', '=', 'draft')]
        elif self._context.get('active_model') == 'account.journal':
            domain = [('journal_id', '=', self._context.get(
                'active_id')), ('state', '=', 'draft')]
        else:
            raise UserError(_("Missing 'active_model' in context."))

        moves = self.env['account.move'].search(domain).filtered('line_ids')
        if not moves:
            raise UserError(
                _('There are no journal items in the draft state to post.'))
        for move in moves:
            if not move.invoice_date:
                raise UserError("date is null, You can not post any journal entry")
            if move.period_id.id == False:
                raise UserError(
                    "Please define the Fiscal Year and Period first before  reset to draft any Journal Entry")
            elif move.period_id.id != False and move.period_id.state == 'done':
                raise UserError(
                    "You can not reset to draft any journal entry already on Closed Period")
        moves._post(not self.force_post)
        return {'type': 'ir.actions.act_window_close'}


class AccountMoveLine(models.Model):
    _name = "account.move.line"
    _inherit = ['account.move.line', 'mail.thread', 'mail.activity.mixin']

    move_id = fields.Many2one('account.move', string='Journal Entry', index=True, required=True, readonly=True,
                              auto_join=True, ondelete="cascade", check_company=True, tracking=True, help="The move of this entry line.")
    move_name = fields.Char(string='Number', tracking=True,
                            related='move_id.name', store=True, index=True)
    date = fields.Date(related='move_id.date', tracking=True, store=True,
                       readonly=True, index=True, copy=False, group_operator='min')
    ref = fields.Char(related='move_id.ref', tracking=True,
                      store=True, copy=False, index=True, readonly=False)
    parent_state = fields.Selection(
        related='move_id.state', tracking=True, store=True, readonly=True)
    journal_id = fields.Many2one(
        related='move_id.journal_id', tracking=True, store=True, index=True, copy=False)
    company_id = fields.Many2one(related='move_id.company_id', store=True,
                                 tracking=True, readonly=True, default=lambda self: self.env.company)
    company_currency_id = fields.Many2one(related='company_id.currency_id', string='Company Currency',
                                          tracking=True, readonly=True, store=True, help='Utility field to express amount currency')
    tax_fiscal_country_id = fields.Many2one(
        comodel_name='res.country', tracking=True, related='move_id.company_id.account_tax_fiscal_country_id')
    account_id = fields.Many2one('account.account', string='Account', index=True, ondelete="cascade",
                                 domain="[('deprecated', '=', False), ('company_id', '=', 'company_id'),('is_off_balance', '=', False)]", check_company=True, tracking=True)
    account_internal_type = fields.Selection(
        related='account_id.user_type_id.type', tracking=True, string="Internal Type", readonly=True)
    account_internal_group = fields.Selection(
        related='account_id.user_type_id.internal_group', tracking=True, string="Internal Group", readonly=True)
    account_root_id = fields.Many2one(
        related='account_id.root_id', tracking=True, string="Account Root", store=True, readonly=True)
    sequence = fields.Integer(default=10, tracking=True)
    name = fields.Char(string='Label', tracking=True, required=True)
    quantity = fields.Float(string='Quantity', tracking=True, default=1.0, digits='Product Unit of Measure',
                            help="The optional quantity expressed by this line, eg: number of product sold. The quantity is not a legal requirement but is very useful for some reports.")
    price_unit = fields.Float(
        string='Unit Price', tracking=True, digits='Product Price')
    discount = fields.Float(string='Discount (%)',
                            tracking=True, digits='Discount', default=0.0)
    debit = fields.Monetary(string='Debit', tracking=True,
                            default=0.0, currency_field='company_currency_id')
    credit = fields.Monetary(string='Credit', tracking=True,
                             default=0.0, currency_field='company_currency_id')
    balance = fields.Monetary(string='Balance', tracking=True, store=True, currency_field='company_currency_id', compute='_compute_balance',
                              help="Technical field holding the debit - credit in order to open meaningful graph views from reports")
    cumulated_balance = fields.Monetary(string='Cumulated Balance', currency_field='company_currency_id',
                                        compute='_compute_cumulated_balance', help="Cumulated balance depending on the domain and the order chosen in the view.")
    amount_currency = fields.Monetary(string='Amount in Currency', tracking=True, store=True, copy=True,
                                      help="The amount expressed in an optional other currency if it is a multi-currency entry.")
    price_subtotal = fields.Monetary(
        string='Subtotal', tracking=True, store=True, readonly=True, currency_field='currency_id')
    price_total = fields.Monetary(
        string='Total', tracking=True, store=True, readonly=True, currency_field='currency_id')
    reconciled = fields.Boolean(
        compute='_compute_amount_residual', tracking=True, store=True)
    blocked = fields.Boolean(string='No Follow-up', tracking=True, default=False,
                             help="You can check this box to mark this journal item as a litigation with the associated partner")
    date_maturity = fields.Date(string='Due Date', index=True, tracking=True,
                                help="This field is used for payable and receivable journal entries. You can put the limit date for the payment of this line.")
    currency_id = fields.Many2one(
        'res.currency', string='Currency', tracking=True, required=True)
    partner_id = fields.Many2one(
        'res.partner', string='Partner', tracking=True, ondelete='restrict')
    product_uom_id = fields.Many2one('uom.uom', string='Unit of Measure',
                                     tracking=True, domain="[('category_id', '=', product_uom_category_id)]")
    product_id = fields.Many2one(
        'product.product', string='Product', tracking=True, ondelete='restrict')
    product_uom_category_id = fields.Many2one(
        'uom.category', tracking=True, related='product_id.uom_id.category_id')
    # ==== Origin fields ====
    reconcile_model_id = fields.Many2one(
        'account.reconcile.model', string="Reconciliation Model", tracking=True, copy=False, readonly=True, check_company=True)
    payment_id = fields.Many2one('account.payment', index=True, tracking=True, store=True,
                                 string="Originator Payment", related='move_id.payment_id', help="The payment that created this entry")
    statement_line_id = fields.Many2one('account.bank.statement.line', index=True, tracking=True, store=True,
                                        string="Originator Statement Line", related='move_id.statement_line_id', help="The statement line that created this entry")
    statement_id = fields.Many2one(related='statement_line_id.statement_id', tracking=True,
                                   store=True, index=True, copy=False, help="The bank statement used for bank reconciliation")
    # ==== Tax fields ====
    tax_ids = fields.Many2many(comodel_name='account.tax', string="Taxes", context={
                               'active_test': False}, check_company=True, tracking=True, help="Taxes that apply on the base amount")
    tax_line_id = fields.Many2one('account.tax', string='Originator Tax', tracking=True, ondelete='restrict',
                                  store=True, compute='_compute_tax_line_id', help="Indicates that this journal item is a tax line")
    tax_group_id = fields.Many2one(related='tax_line_id.tax_group_id', string='Originator tax group',
                                   readonly=True, tracking=True, store=True, help='technical field for widget tax-group-custom-field')
    tax_base_amount = fields.Monetary(string="Base Amount", store=True,
                                      readonly=True, tracking=True, currency_field='company_currency_id')
    tax_exigible = fields.Boolean(string='Appears in VAT report', default=True, readonly=True, tracking=True,
                                  help="Technical field used to mark a tax line as exigible in the vat report or not (only exigible journal items are displayed). By default all new journal items are directly exigible, but with the feature cash_basis on taxes, some will become exigible only when the payment is recorded.")
    tax_repartition_line_id = fields.Many2one(comodel_name='account.tax.repartition.line', string="Originator Tax Distribution Line", ondelete='restrict',
                                              readonly=True, tracking=True, check_company=True, help="Tax distribution line that caused the creation of this move line, if any")
    tax_tag_ids = fields.Many2many(string="Tags", comodel_name='account.account.tag', ondelete='restrict', tracking=True,
                                   help="Tags assigned to this line by the tax creating it, if any. It determines its impact on financial reports.")
    tax_audit = fields.Char(string="Tax Audit String", compute="_compute_tax_audit", store=True, tracking=True,
                            help="Computed field, listing the tax grids impacted by this line, and the amount it applies to each of them.")
    # ==== Reconciliation fields ====
    amount_residual = fields.Monetary(string='Residual Amount', store=True, currency_field='company_currency_id', tracking=True,
                                      compute='_compute_amount_residual', help="The residual amount on a journal item expressed in the company currency.")
    amount_residual_currency = fields.Monetary(string='Residual Amount in Currency', store=True, tracking=True, compute='_compute_amount_residual',
                                               help="The residual amount on a journal item expressed in its currency (possibly not the company currency).")
    full_reconcile_id = fields.Many2one(
        'account.full.reconcile', string="Matching", copy=False, tracking=True, index=True, readonly=True)
    matched_debit_ids = fields.One2many('account.partial.reconcile', 'credit_move_id', string='Matched Debits',
                                        tracking=True, help='Debit journal items that are matched with this journal item.', readonly=True)
    matched_credit_ids = fields.One2many('account.partial.reconcile', 'debit_move_id', string='Matched Credits',
                                         tracking=True, help='Credit journal items that are matched with this journal item.', readonly=True)
    matching_number = fields.Char(string="Matching #", compute='_compute_matching_number', tracking=True, store=True,
                                  help="Matching number for this line, 'P' if it is only partially reconcile, or the name of the full reconcile if it exists.")
    # ==== Analytic fields ====
    analytic_line_ids = fields.One2many(
        'account.analytic.line', 'move_id', tracking=True, string='Analytic lines')
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account', index=True,
                                          tracking=True, store=True, readonly=False, check_company=True, copy=True)
    analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic Groups')
    # ==== Onchange / display purpose fields ====
    recompute_tax_line = fields.Boolean(store=False, tracking=True, readonly=True,
                                        help="Technical field used to know on which lines the taxes must be recomputed.")
    display_type = fields.Selection([
        ('line_section', 'Section'),
        ('line_note', 'Note')
    ],
        default=False, tracking=True, help="Technical field for UX purpose.")
    is_rounding_line = fields.Boolean(
        help="Technical field used to retrieve the cash rounding line.", tracking=True)
    exclude_from_invoice_tab = fields.Boolean(
        help="Technical field used to exclude some lines from the invoice_line_ids tab in the form view.", tracking=True)
    is_fiscal_book_exclude = fields.Boolean(
        string='Exclude on Fiscal Book', related='move_id.is_fiscal_book_exclude')

    price_tax_discount = fields.Float(string='Product Tax Discount', tracking=True, digits='Product Price')

    is_update_disc_line = fields.Boolean(string='Update Discount')

         
    price_tax = fields.Monetary(string='Tax Amount', currency_field='currency_id',compute='')
    unit_price_fnct = fields.Monetary(string='Total Price', compute='_get_unit_price', currency_field='currency_id')
    disc_percentage_rel = fields.Float(string="Disc Value")

    
    @api.model
    def default_get(self, fields):
        vals = super(AccountMoveLine, self).default_get(fields)
        for line in self:
            if line.move_id:
                if line.move_id.analytic_group_ids:
                    vals['analytic_tag_ids'] = line.move_id.analytic_group_ids
                    vals['journal_id'] = line.move_id.journal_id
        return vals

    def _get_unit_price(self):
        for l in self:
            unit_price_fnct = l.quantity * l.price_unit     
            l.unit_price_fnct = unit_price_fnct

    def calc_discount(self):
        self.ensure_one()
        self.is_update_disc_line = True

    def _inverse_analytic_tag_ids(self):
        pass

    @api.onchange('move_id', 'move_id.analytic_group_ids', 'account_id')
    def _onchange_analytic_account(self):
        for record in self:
            record.analytic_tag_ids = record.move_id.analytic_group_ids

    def _set_price_and_tax_after_fpos(self):
        self.ensure_one()
        # Manage the fiscal position after that and adapt the price_unit.
        # E.g. mapping a price-included-tax to a price-excluded-tax must
        # remove the tax amount from the price_unit.
        # However, mapping a price-included tax to another price-included tax must preserve the balance but
        # adapt the price_unit to the new tax.
        # E.g. mapping a 10% price-included tax to a 20% price-included tax for a price_unit of 110 should preserve
        # 100 as balance but set 120 as price_unit.
        if self.tax_ids and self.move_id.fiscal_position_id and self.move_id.fiscal_position_id.tax_ids:
            price_subtotal = self._get_price_total_and_subtotal(
            )['price_subtotal']
            self.tax_ids = self.move_id.fiscal_position_id.map_tax(
                self.tax_ids._origin, partner=self.move_id.partner_id)
            accounting_vals = self._get_fields_onchange_subtotal(
                price_subtotal=price_subtotal,
                currency=self.move_id.company_currency_id)
            amount_currency = accounting_vals['amount_currency']
            business_vals = self._get_fields_onchange_balance(
                amount_currency=amount_currency)
            if 'price_unit' in business_vals:
                self.price_unit = business_vals['price_unit']


class ApprovalMatrixAccountingLines(models.Model):
    _inherit = "approval.matrix.accounting.lines"

    move_id = fields.Many2one('account.move', string='Move')


class ir_cron(models.Model):
    _inherit = "ir.cron"

    def last_day_of_month(self, day):
        next_month = day.replace(day=28) + relativedelta(days=4)
        return next_month - relativedelta(days=next_month.day)

    def write(self, vals):
        res = super(ir_cron, self).write(vals)
        if 'lastcall' in vals:
            ICP = self.env['ir.config_parameter'].sudo()
            automated_invoice_followup = ICP.get_param(
                'automated_invoice_followup', False)
            followup_sending_date = ICP.get_param('followup_sending_date', 1)
            cekcronjob = self.env.ref(
                'equip3_accounting_operation.cron_automated_followup_invoice')
            if automated_invoice_followup and cekcronjob.id == self.id:
                nextcalldate = self.nextcall
                today = datetime.today()
                if self.interval_type == 'months':
                    if int(followup_sending_date) <= int(self.last_day_of_month(nextcalldate).day):
                        nextcall = datetime(nextcalldate.year, nextcalldate.month, int(
                            followup_sending_date), nextcalldate.hour, nextcalldate.minute, nextcalldate.second)
                    else:
                        nextcall = datetime(nextcalldate.year, nextcalldate.month, int(self.last_day_of_month(
                            nextcalldate).day), nextcalldate.hour, nextcalldate.minute, nextcalldate.second)
                    return self.update({'nextcall': nextcall})
        return res