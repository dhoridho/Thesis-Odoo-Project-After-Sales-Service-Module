from odoo import tools, api, fields, models, _
from datetime import datetime, date, timedelta
from odoo.exceptions import ValidationError, UserError


class AccountDebtCollection(models.Model):
    _name = 'account.debt.collection'
    _description = "Debt Collection"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']


    name = fields.Char(string='Number', readonly=True, tracking=True)
    partner_id = fields.Many2one('res.partner', string='Customer', required=True, tracking=True)
    date = fields.Date(string='Date', required=True, tracking=True)
    person_in_charge = fields.Many2one('res.users', string='Person in Charge', default=lambda self: self.env.user, tracking=True)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id, string='Currency', required=True, tracking=True)
    amount = fields.Monetary(string='Total Collection', readonly=True, compute='_compute_amount')
    start_date = fields.Date(string='Invoice Start Date', tracking=True)
    end_date = fields.Date(string='Invoice End Date', required=True, tracking=True)
    deadline_date = fields.Date(string='Collection Deadline Date', required=True, tracking=True)
    branch_id = fields.Many2one('res.branch', string='Branch', 
                                default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else self.env.user.branch_id.id,
                                domain=lambda self: [('id', 'in', self.env.branches.ids)], tracking=True, required=True)
    create_uid = fields.Many2one('res.users', string='Created by', readonly=True, tracking=True)
    create_date = fields.Datetime(string="Created Date", readonly=True, tracking=True)
    line_debt_collection = fields.One2many('account.debt.collection.line', 'debt_collection_id', string='Debt Collection')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('on_progress', 'On Progress'),
        ('wait_for_payment', 'Collection Payment'),
        ('done', 'Done'),
        ('canceled', 'Canceled'),
    ], string='Status', default='draft', tracking=True)
    is_pic = fields.Boolean(string='Is Person in Charge', compute='check_who_is_login')


    @api.constrains('date')
    def _check_date(self):
        for rec in self:
            if rec.date == False:
                raise ValidationError(_("Collection Date cannot be empty"))

    @api.onchange('partner_id', 'end_date')
    def _write_line_detail(self):
        for rec in self:
            list_line = [(5, 0, 0)]
            invoices = self.env['account.move'].search(['&', '&', '&', '&', '&', 
                            ('partner_id', '=', rec.partner_id.id),
                            ('move_type', 'in', ['out_invoice', 'in_refund']),
                            ('state', '=', 'posted'), 
                            ('payment_state', 'in', ['not_paid', 'partial']),
                            ('amount_residual_signed', '!=', 0),
                            ('invoice_date', '<', rec.end_date)
                            ])
            if invoices:
                for invoice in invoices:
                    lines_dict = {
                                    'invoice_id': invoice.id,
                                    'invoice_date': invoice.invoice_date,
                                    # 'amount_invoice': abs(invoice.amount_total_signed),
                                    'amount_invoice': abs(invoice.amount_total),
                                    'amount_residual': abs(invoice.amount_residual_signed)
                                 }
                    list_line.append((0, 0, lines_dict))
            rec.line_debt_collection = list_line

    @api.depends('line_debt_collection.amount')
    def _compute_amount(self):
        for rec in self:
            rec.amount = sum(rec.line_debt_collection.mapped('amount'))

    @api.model
    def check_who_is_login(self):
        logged_in_user = self.env.user
        for rec in self:
            if logged_in_user == rec.person_in_charge:
                rec.is_pic = True
            else:
                rec.is_pic = False

    @api.model
    def update_state_debt_collection(self):
        today = date.today()
        expired_debt_collection = self.env['account.debt.collection'].search([('deadline_date', '<', today), ('state', '=', 'on_progress')])
        for rec in expired_debt_collection:
            line_debt_collection = rec.line_debt_collection
            for line_id in line_debt_collection:
                line_id.write({'state' : 'fail',
                               'journal_id' : False,
                               'date' : False,
                               'amount' : False,
                               'is_full_collect' : False,})
            rec.write({'state' : 'canceled'})
   
                
    def check_duplicate(self):
        for rec in self:
            debt_collection = self.env['account.debt.collection'].search([('partner_id', '=', rec.partner_id.id), ('state', '=', 'on_progress')])
            if debt_collection:
                raise UserError(_("Collection for this partner, already in progress"))
            else:
                seq_date = None
                if rec.date:
                    seq_date = fields.Datetime.context_timestamp(self, fields.Datetime.to_datetime(rec.date))
                rec.write({'state' : 'on_progress',
                           'name'  : self.env['ir.sequence'].next_by_code('debt.collection', sequence_date=seq_date) or _('New')})


    def action_confirm(self):
        cek_duplicate = self.check_duplicate()
        return cek_duplicate


    def action_cancel(self):
        for rec in self:
            line_debt_collection = rec.line_debt_collection
            for line_id in line_debt_collection:
                line_id.write({'state' : 'fail'})
            rec.write({'state' : 'canceled'})

    def action_register_payment(self):
        for rec in self:
            if len(rec.line_debt_collection) > 0:
                for inv in rec.line_debt_collection:
                    if inv.amount > inv.amount_residual:
                        raise UserError(_("Collection Amount cannot be more than the amount due"))
                    if inv.amount < inv.amount_residual:
                        inv.write({'state' : 'partial'})
                    if inv.amount == inv.amount_residual:
                        inv.write({'state' : 'full'})
                    if inv.amount == 0:
                        inv.write({'state' : 'fail'})
                        continue
                    payment = self._create_payments(inv)
                    inv.payment_id = payment.id
            rec.write({'state' : 'done'})
            
    def _create_payments(self, invoices):
        self.ensure_one()
        batches = self._get_batches(invoices.invoice_id)
        edit_mode = True
        to_reconcile = []
        payment_vals = self.prepare_payment_vals(invoices)
        payment_vals_list = [payment_vals]
        to_reconcile.append(batches[0]['lines'])

        payments = self.env['account.payment'].create(payment_vals_list)

        # If payments are made using a currency different than the source one, ensure the balance match exactly in
        # order to fully paid the source journal items.
        # For example, suppose a new currency B having a rate 100:1 regarding the company currency A.
        # If you try to pay 12.15A using 0.12B, the computed balance will be 12.00A for the payment instead of 12.15A.
        if edit_mode:
            for payment, lines in zip(payments, invoices):
                # Batches are made using the same currency so making 'lines.currency_id' is ok.
                if payment.currency_id != lines.currency_id:
                    liquidity_lines, counterpart_lines, writeoff_lines = payment._seek_for_lines()
                    source_balance = abs(sum(lines.mapped('amount_residual')))
                    payment_rate = liquidity_lines[0].amount_currency / liquidity_lines[0].balance
                    source_balance_converted = abs(source_balance) * payment_rate
                    # Translate the balance into the payment currency is order to be able to compare them.
                    # In case in both have the same value (12.15 * 0.01 ~= 0.12 in our example), it means the user
                    # attempt to fully paid the source lines and then, we need to manually fix them to get a perfect
                    # match.
                    payment_balance = abs(sum(counterpart_lines.mapped('balance')))
                    payment_amount_currency = abs(sum(counterpart_lines.mapped('amount_currency')))
                    if not payment.currency_id.is_zero(source_balance_converted - payment_amount_currency):
                        continue

                    delta_balance = source_balance - payment_balance

                    # Balance are already the same.
                    if self.company_currency_id.is_zero(delta_balance):
                        continue

                    # Fix the balance but make sure to peek the liquidity and counterpart lines first.
                    debit_lines = (liquidity_lines + counterpart_lines).filtered('debit')
                    credit_lines = (liquidity_lines + counterpart_lines).filtered('credit')

                    payment.move_id.write({'line_ids': [
                        (1, debit_lines[0].id, {'debit': debit_lines[0].debit + delta_balance}),
                        (1, credit_lines[0].id, {'credit': credit_lines[0].credit + delta_balance}),
                    ]})

        payments.action_post()

        domain = [('account_internal_type', 'in', ('receivable', 'payable')), ('reconciled', '=', False)]
        for payment, lines in zip(payments, to_reconcile):

            # When using the payment tokens, the payment could not be posted at this point (e.g. the transaction failed)
            # and then, we can't perform the reconciliation.
            if payment.state != 'posted':
                continue

            payment_lines = payment.line_ids.filtered_domain(domain)
            for account in payment_lines.account_id:
                (payment_lines + lines) \
                    .filtered_domain([('account_id', '=', account.id), ('reconciled', '=', False)]) \
                    .reconcile()
        return payments


    def _get_batches(self, invoices):
        ''' Group the account.move.line linked to the wizard together.
        :return: A list of batches, each one containing:
            * key_values:   The key as a dictionary used to group the journal items together.
            * moves:        An account.move recordset.
        '''
        self.ensure_one()
        # Keep lines having a residual amount to pay.
        available_lines = self.env['account.move.line']
        for line in invoices.line_ids:
            if line.move_id.state != 'posted':
                raise UserError(_("You can only register payment for posted journal entries."))

            if line.account_internal_type not in ('receivable', 'payable'):
                continue
            if line.currency_id:
                if line.currency_id.is_zero(line.amount_residual_currency):
                    continue
            else:
                if line.company_currency_id.is_zero(line.amount_residual):
                    continue
            available_lines |= line

        # Check.
        if not available_lines:
            raise UserError(
                _("You can't register a payment because there is nothing left to pay on the selected journal items."))
        if len(invoices.line_ids.company_id) > 1:
            raise UserError(_("You can't create payments for entries belonging to different companies."))
        if len(set(available_lines.mapped('account_internal_type'))) > 1:
            raise UserError(
                _("You can't register payments for journal items being either all inbound, either all outbound."))

        # res['line_ids'] = [(6, 0, available_lines.ids)]

        lines = available_lines

        if len(lines.company_id) > 1:
            raise UserError(_("You can't create payments for entries belonging to different companies."))
        if not lines:
            raise UserError(
                _("You can't open the register payment wizard without at least one receivable/payable line."))

        batches = {}
        payments = self.env['account.payment.register']
        for line in lines:
            batch_key = payments._get_line_batch_key(line)

            serialized_key = '-'.join(str(v) for v in batch_key.values())
            batches.setdefault(serialized_key, {
                'key_values': batch_key,
                'lines': self.env['account.move.line'],
            })
            batches[serialized_key]['lines'] += line
        return list(batches.values())


    def prepare_payment_vals(self, invoices):
        acc_id = self.partner_id.property_account_receivable_id
        payment_vals = {
            'date': invoices.date,
            'amount': invoices.amount,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'ref': invoices.invoice_id.name,
            'journal_id': invoices.journal_id.id,
            'currency_id': invoices.currency_id.id,
            'partner_id': self.partner_id.id,
            'partner_bank_id': False,
            'payment_method_id': 1,
            'destination_account_id': acc_id.id,
            'apply_manual_currency_exchange': invoices.invoice_id.apply_manual_currency_exchange,
            'manual_currency_exchange_rate': invoices.invoice_id.manual_currency_exchange_rate,
            'active_manual_currency_rate': invoices.invoice_id.active_manual_currency_rate,
            'branch_id': invoices.invoice_id.branch_id.id,
        }
        return payment_vals

class AccountDebtCollection(models.Model):
    _name = 'account.debt.collection.line'
    _description = "Debt Collection Line"

    debt_collection_id = fields.Many2one('account.debt.collection', string='Debt Collection Line', readonly=True)
    invoice_id = fields.Many2one('account.move', string='Invoice', readonly=True)
    invoice_date = fields.Date(string='Invoice Date', readonly=True)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id, string='Currency', required=True, tracking=True)
    amount_invoice = fields.Monetary(string='Invoice Amount', readonly=True)
    amount_residual = fields.Monetary(string='Debt Amount Due', readonly=True)
    state = fields.Selection([
        ('draft', 'Ready to Collect'),
        ('fail', 'Failed to Collected'),
        ('partial', 'Partially Collected'),
        ('full', 'Full Collected'),
    ], string='Status', default='draft', readonly=True)
    journal_id = fields.Many2one('account.journal', string='Payment Method', domain="[('type', 'in', ['bank','cash'])]")
    date = fields.Date(string='Collection Date', required=True)
    amount = fields.Monetary(string='Collection Amount')
    is_full_collect = fields.Boolean(string='Full Collect')
    payment_id = fields.Many2one('account.payment', string='Payment', readonly=True)
    is_pic_line = fields.Boolean(string='Is Person in Charge', compute='check_pic_line')                       

    @api.onchange('is_full_collect')
    def _onchange_amount_full_collect(self):
        for rec in self:
            if rec.is_full_collect:
                rec.amount = rec.amount_residual
            else:
                rec.amount = False

    @api.depends('debt_collection_id.person_in_charge')
    def check_pic_line(self):
        logged_in_user = self.env.user
        for rec in self:
            if logged_in_user == rec.debt_collection_id.person_in_charge:
                rec.is_pic_line = True
            else:
                rec.is_pic_line = False


