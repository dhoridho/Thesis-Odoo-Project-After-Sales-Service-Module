# -*- coding: utf-8 -*-

from odoo import models, fields, api, _, tools
from odoo.exceptions import UserError, ValidationError
from ...equip3_general_features.models.email_wa_parameter import waParam
import json


class AccountPettycashVoucherhWizard(models.Model):
    _name = 'account.pettycash.voucher.wizard'
    _description = "Account Petty Cash Voucher Wizard"

    name = fields.Char(string='Number', readonly=True, required=True, copy=False, default='New')
    number = fields.Char(string="Number", readonly=True, required=True, copy=False, default='New')
    fund = fields.Many2one('account.pettycash', string='Fund', readonly=True, domain=[('state', '!=', ('closed'))])
    partner_id = fields.Many2one('res.users', string='Partner')
    date = fields.Date(string="Date", required=True, default=fields.Date.context_today)
    ba_ca_journal_id = fields.Many2one(related="fund.journal", string='Bank/Cash Journal', readonly=True, store=True)
    payment_reference = fields.Char(string="Payment Reference")
    submitter_id = fields.Many2one('res.users', string='Submitter', default=lambda self: self.env.user)
    attachment = fields.Binary()
    currency_id = fields.Many2one('res.currency', string='Currency', related='fund.currency_id',
                                  readonly=True, store=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company.id,
                                 readonly=True, store=True)
    state = fields.Selection(selection=[
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('waiting_for_approval', 'Waiting for Approval'),
        ('approved', 'Confirmed'),
        ('rejected', 'Rejected'),
        ('posted', 'Posted'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', readonly=True)
    voucher_line = fields.One2many('account.pettycash.voucher.wizard.line', 'line_id', string='Voucher Line')
    total = fields.Monetary(string='Total', store=True, readonly=True, compute='_compute_amount')
    is_pettycash_voucher_approved = fields.Boolean('Petty Cash Voucher Approved')
    move_id = fields.Many2one('account.move', 'Journal Entry', copy=False)
    narration = fields.Text('Notes', readonly=True, states={'draft': [('readonly', False)]})
    voucher_type = fields.Selection([
        ('sale', 'Receipt'),
        ('purchase', 'Payment')
    ], string='Type', readonly=True, states={'draft': [('readonly', False)]}, oldname="type", default='sale')
    tax_amount = fields.Monetary(readonly=True, store=True, compute='_compute_total')
    expense_account_state = fields.Selection(selection=[
        ('filled', 'Expense Account is Filled'),
        ('null', 'Expense Account is not Filled'),
    ], string='Expense Account Status', default='null', compute = 'compute_expense_account_state')
    apply_manual_currency_exchange = fields.Boolean(string="Apply Manual Currency Exchange")
    manual_currency_exchange_rate = fields.Float(string="Manual Currency Exchange Rate", digits=(12,12))
    manual_currency_exchange_inverse_rate = fields.Float(string="Inverse Rate", digits=(12,12))
    active_manual_currency_rate = fields.Boolean('active Manual Currency')
    is_reconcile = fields.Boolean('Reconcile', default=False)

    @api.onchange('currency_id')
    def onchange_currency_id(self):
        if self.currency_id:
            if self.company_id.currency_id != self.currency_id:
                if not self.date:
                    raise UserError(_('Please set Accounting Date first'))
                self.active_manual_currency_rate = True
                
            else:
                self.active_manual_currency_rate = False
        else:
            self.active_manual_currency_rate = False

    @api.onchange('manual_currency_exchange_inverse_rate')
    def _oncange_rate_conversion(self):
        if self.manual_currency_exchange_inverse_rate:
            self.manual_currency_exchange_rate = 1 / self.manual_currency_exchange_inverse_rate

    @api.onchange('manual_currency_exchange_rate')
    def _oncange_rate(self):
        if self.manual_currency_exchange_rate:
            self.manual_currency_exchange_inverse_rate = 1 / self.manual_currency_exchange_rate
    
    @api.depends('voucher_line', 'voucher_line.expense_account_state')
    def compute_expense_account_state(self):
        for record in self:
            null_states= len(record.voucher_line.filtered(lambda v : v.expense_account_state == 'null'))
            filled_states= len(record.voucher_line.filtered(lambda v : v.expense_account_state == 'filled'))
            if null_states:
                record.expense_account_state = 'null'
            else:
                record.expense_account_state= 'filled'

    def action_request_for_approval(self):
        exceeding_lines = []
        for record in self:
            for line in record.voucher_line:
                if line.expense_budget != 0:
                    subtotal_cost_same_budget = 0
                    for line2 in record.voucher_line:
                        if line2.crossovered_budget_line_id.id == line.crossovered_budget_line_id.id:
                            subtotal_cost_same_budget += (line2.price_unit * line2.quantity)

                    if subtotal_cost_same_budget > line.expense_budget:
                        exceeding_lines.append(line)

        if exceeding_lines:
            wizard = self.env['expense.request.warning'].create({
                'warning_line_ids': [
                    (0, 0, {
                        'product_id': line.product_id.id,
                        'budgetary_position_id': line.crossovered_budget_line_id.general_budget_id.id,
                        'account_id': line.expense_account.id,
                        'planned_budget': line.crossovered_budget_line_id.budget_amount,
                        'expense_budget': line.expense_budget,
                        'realized_amount': (line.price_unit * line.quantity),
                    }) for line in exceeding_lines
                ]
            })
            return {
                'name': 'Warning',
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'expense.request.warning',
                'res_id': wizard.id,
                'target': 'new',
            }
        else:
            self.send_request_for_approval()

    def send_request_for_approval(self):
        for record in self:
            record.write({'state': 'waiting_for_approval'})
            for line in record.voucher_line:
                if line.expense_account:
                    line.expense_account_state = 'filled'
            
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            action_id = self.env.ref('equip3_accounting_pettycash.action_account_pettycash')
            url = base_url + '/web#id=' + \
                str(record.fund.id) + '&action=' + str(action_id.id) + \
                '&view_type=form&model=account.pettycash'
            mail_template = self.env.ref('equip3_accounting_pettycash.mail_template_petty_cash_voucher_approval')
            ctx = {
                'email_from': self.env.user.company_id.email,
                'email_to': record.submitter_id.partner_id.email,
                'custodian_name': record.fund.custodian.name,
                'submitter_name': record.submitter_id.name,
                'total_amount': str(record.total),
                'fund_name': record.fund.name,
                'voucher_date': record.date,
                "voucher_name": record.name,
                "url": url,
            }
            mail_template.with_context(ctx).send_mail(record.id, True)

            whatsapp_template = self.env.ref('equip3_accounting_pettycash.wa_template_petty_cash_voucher_approval')
            phone_number = str(record.fund.custodian.mobile or record.fund.custodian.phone)
            record._send_whatsapp_message(whatsapp_template, phone_number, url)

    @api.model
    def create(self, vals):
        if 'company_id' in vals:
            self = self.with_company(vals['company_id'])
        if vals.get('name', _('New')) == _('New'):
            seq_date = None
            if 'date' in vals:
                seq_date = fields.Datetime.context_timestamp(self, fields.Datetime.to_datetime(vals['date']))
            vals['name'] = self.env['ir.sequence'].next_by_code('account.pettycash.voucher.wizard.seq',
                                                                sequence_date=seq_date) or _('New')
        result = super(AccountPettycashVoucherhWizard, self).create(vals)
        return result

    @api.depends('voucher_line', 'voucher_line.amount')
    def _compute_total(self):
        tax_calculation_rounding_method = self.env.user.company_id.tax_calculation_rounding_method
        for voucher in self:
            total = 0
            tax_amount = 0
            tax_lines_vals_merged = {}
            for line in voucher.voucher_line:
                tax_info = line.tax_ids.compute_all(line.price_unit, voucher.currency_id, line.quantity,
                                                    line.product_id, voucher.partner_id)
                if tax_calculation_rounding_method == 'round_globally':
                    total += tax_info.get('total_excluded', 0.0)
                    for t in tax_info.get('taxes', False):
                        key = (
                            t['id'],
                            t['account_id'],
                        )
                        if key not in tax_lines_vals_merged:
                            tax_lines_vals_merged[key] = t.get('amount', 0.0)
                        else:
                            tax_lines_vals_merged[key] += t.get('amount', 0.0)
                else:
                    total += tax_info.get('total_included', 0.0)
                    tax_amount += sum([t.get('amount', 0.0) for t in tax_info.get('taxes', False)])
            if tax_calculation_rounding_method == 'round_globally':
                tax_amount = sum([voucher.currency_id.round(t) for t in tax_lines_vals_merged.values()])
            voucher.tax_amount = tax_amount

    def account_move_get(self):
        for record in self:
            if not record.number or record.number == '/':
                seq_date = fields.Datetime.context_timestamp(self, fields.Datetime.to_datetime(record.date))
                new_number = self.env['ir.sequence'].next_by_code('account.voucher', sequence_date=seq_date) or _('New')
            else:
                new_number = record.number
            record.number = new_number
            move = {
                'journal_id': record.ba_ca_journal_id.id,
                'narration': record.narration,
                'date': record.date,
                'ref': record.payment_reference,
                'branch_id': record.fund.branch_id.id,
            }
            return move

    def download_petty(self):
        return self.env.ref('equip3_accounting_pettycash.action_report_petty_cash_voucher').report_action(None)
    

    # def _convert(self, amount):
    #     for voucher in self:
    #         return voucher.currency_id._convert(amount, voucher.company_id.currency_id, voucher.company_id,
    #                                             voucher.date)

    def round(self, amount):
        self.ensure_one()
        return tools.float_round(amount, precision_rounding=self.currency_id.rounding)
    
    def _convert(self, amount):
        for rec in self:
            if rec.currency_id == rec.company_id.currency_id:
                return rec.currency_id._convert(amount, rec.company_id.currency_id, rec.company_id, rec.date or fields.Date.context_today(rec), round=False)
            else:
                if self.apply_manual_currency_exchange == False:
                    currency_rate = self.env['res.currency.rate'].search([('currency_id', '=', rec.currency_id.id), ('name', '<=', rec.date)], limit=1)                    
                    if not currency_rate:
                        raise UserError(_('No currency rate found for the currency %s and the period %s.') % (rec.currency_id.name, rec.date))
                    res = amount / currency_rate.rate
                else:
                    res = amount / self.manual_currency_exchange_rate                
            return self.round(res)

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = dict(self.env.context) or {}
        user = self.env.user
        domain.append(('submitter_id', '=', user.id))
        return super(AccountPettycashVoucherhWizard, self).search_read(domain=domain, fields=fields, offset=offset,
                                                                       limit=limit, order=order)

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        context = dict(self.env.context) or {}
        user = self.env.user
        domain.append(('submitter_id', '=', user.id))
        return super(AccountPettycashVoucherhWizard, self).read_group(domain=domain, fields=fields, groupby=groupby,
                                                                      offset=offset, limit=limit,
                                                                      orderby=orderby, lazy=lazy)

    def first_move_line_get(self, move_id, company_currency, current_currency):
        debit = credit = 0.0
        if (self.voucher_type == 'sale' and self._convert(self.total) < 0.0) or (
                self.voucher_type == 'purchase' and self._convert(self.total) > 0.0):
            debit = self._convert(self.total)
        elif (self.voucher_type == 'sale' and self._convert(self.total) > 0.0) or (
                self.voucher_type == 'purchase' and self._convert(self.total) < 0.0):
            credit = self._convert(self.total)
        if debit < 0.0: debit = 0.0
        if credit < 0.0: credit = 0.0
        sign = debit - credit < 0 and -1 or 1
        # set the first line of the voucher

        analytic_tag_ids = False
        for line in self.voucher_line:
            if line.analytic_group_ids:
                analytic_tag_ids = line.analytic_group_ids
                break

        move_line = {
            'name': '/',
            'debit': debit,
            'credit': credit,
            'account_id': self.fund.journal.default_account_id.id,
            'move_id': move_id,
            'journal_id': self.ba_ca_journal_id.id,
            'partner_id': self.partner_id.commercial_partner_id.id,
            'currency_id': company_currency != current_currency and current_currency or False,
            'amount_currency': (sign * abs(self.total)  # amount < 0 for refunds
                                if company_currency != current_currency else 0.0),
            'date': self.date,
            'analytic_tag_ids': analytic_tag_ids
        }

        # if company_currency != current_currency:
        #     ctx = {}
        #     if self.date:
        #         ctx['date'] = self.date
        #     move_line['amount_currency'] = self._convert(self.total)
        return move_line

    def action_move_line_create(self):
        ''' PAY NOW IS DIRECT JOURNAL NON ACTIVE RECONCILED BEHAVIOUR
        Confirm the vouchers given in ids and create the journal entries for each of them
        '''
        for voucher in self:
            local_context = dict(self._context)
            if voucher.move_id:
                continue
            company_currency = voucher.ba_ca_journal_id.company_id.currency_id.id
            current_currency = voucher.currency_id.id or company_currency
            # we select the context to use accordingly if it's a multicurrency case or not
            # But for the operations made by _convert, we always need to give the date in the context
            ctx = local_context.copy()
            ctx['date'] = voucher.date
            ctx['check_move_validity'] = False
            # Create the account move record.
            move = self.env['account.move'].create(voucher.account_move_get())

            # Get the name of the account_move just created
            # Create the first line of the voucher
            move_line = self.env['account.move.line'].with_context(ctx).create(
                voucher.with_context(ctx).first_move_line_get(move.id, company_currency, current_currency))
            line_total = move_line.debit - move_line.credit
            if voucher.voucher_type == 'sale':
                line_total = line_total - voucher._convert(voucher.tax_amount)
            elif voucher.voucher_type == 'purchase':
                line_total = line_total + voucher._convert(voucher.tax_amount)

            # Create one move line per voucher line where amount is not 0.0
            line_total = voucher.with_context(ctx).voucher_move_line_create(line_total, move.id, company_currency, current_currency)

            # # Add tax correction to move line if any tax correction specified
            # if voucher.tax_correction != 0.0:
            #     tax_move_line = self.env['account.move.line'].search([('move_id', '=', move.id), ('tax_line_id', '!=', False)], limit=1)
            #     if len(tax_move_line):
            #         tax_move_line.write({'debit': tax_move_line.debit + voucher.tax_correction if tax_move_line.debit > 0 else 0,
            #             'credit': tax_move_line.credit + voucher.tax_correction if tax_move_line.credit > 0 else 0})
            # move.line_ids.filtered(lambda line: not line.reconciled and line.account_id == voucher.fund.journal.default_account_id).reconcile()

            move.post()
            voucher.write({
                'name': move.name,
                'move_id': move.id,
                'state': 'posted',
            })
        return True

    def _prepare_voucher_move_line(self, line, amount, move_id, company_currency, current_currency):
        line_subtotal = line.amount
        # line_subtotal = self._convert(line.amount)
        if self.voucher_type == 'sale':
            line_subtotal = -1 * self._convert(line.amount)

        if (self.voucher_type == 'sale' and amount > 0.0) or (self.voucher_type == 'purchase' and amount < 0.0):
            debit = abs(amount)
            # debit = self._convert(abs(amount))
            credit = 0.0
        elif (self.voucher_type == 'sale' and amount < 0.0) or (self.voucher_type == 'purchase' and amount > 0.0):
            debit = 0.0
            # credit = self._convert(abs(amount))
            credit = abs(amount)

        move_line = {
            'journal_id': self.ba_ca_journal_id.id,
            'name': '/',
            'account_id': line.expense_account.id,
            'move_id': move_id,
            'quantity': line.quantity,
            'product_id': line.product_id.id,
            'partner_id': self.partner_id.commercial_partner_id.id,
            'credit': abs(amount) if credit > 0.0 else 0.0,
            'debit': abs(amount) if debit > 0.0 else 0.0,
            'date': self.date,
            'tax_ids': [(4, t.id) for t in line.tax_ids],
            'amount_currency': line_subtotal if current_currency != company_currency else 0.0,
            'currency_id': company_currency != current_currency and current_currency or False,
            'payment_id': self._context.get('payment_id'),
            'analytic_tag_ids': line.analytic_group_ids,
        }

        if company_currency != current_currency:
            ctx = {}
            if self.date:
                ctx['date'] = self.date
            move_line['amount_currency'] = amount
        return move_line

    def voucher_move_line_create(self, line_total, move_id, company_currency, current_currency):
        for line in self.voucher_line:
            if not line.amount:
                continue
            amount = (line.price_unit * line.quantity)
            # amount = self._convert(line.price_unit * line.quantity)
            move_line = self._prepare_voucher_move_line(line, amount, move_id, company_currency, current_currency)

            if (line.tax_ids):
                tax_group = line.tax_ids.compute_all(line.price_unit, line.currency_id, line.quantity, line.product_id,
                                                     self.partner_id)
                if move_line['debit']: move_line['debit'] = tax_group['total_excluded']
                if move_line['credit']: move_line['credit'] = tax_group['total_excluded']
                
                for tax_vals in tax_group['taxes']:
                    if tax_vals['amount']:
                        tax = self.env['account.tax'].browse([tax_vals['id']])
                        if not tax_vals['account_id']:
                            raise UserError(_('You have to setup account taxes for %s.' % tax_vals['name']))
                        account_id = (amount > 0 and tax_vals['account_id'])
                        if not account_id:
                            account_id = line.account_id.id
                        temp = {
                            'account_id': account_id,
                            'name': tax_vals['name'],
                            'tax_line_id': tax_vals['id'],
                            'move_id': move_id,
                            'date': self.date,
                            'partner_id': self.partner_id.id,
                            'debit': self.voucher_type == 'sale' and self._convert(tax_vals['amount']) or 0.0,
                            'credit': self.voucher_type != 'sale' and self._convert(tax_vals['amount']) or 0.0,
                            'analytic_tag_ids': line.analytic_group_ids
                        }
                        
                        if company_currency != current_currency:
                            ctx = {}
                            if self.date:
                                ctx['date'] = self.date
                            temp['currency_id'] = current_currency
                            temp['amount_currency'] = tax_vals['amount']
                            # # Convert tax_vals['amount'] to company currency if needed
                            # converted_amount = self._convert(tax_vals['amount'])
                            # # Adjust sign based on debit or credit
                            # temp['amount_currency'] = converted_amount if temp.get('debit', 0.0) > 0 else -converted_amount
                            # temp['amount_currency'] = self._convert(tax_vals['amount'], current_currency,
                            #                                                     line.company_id,
                            #                                                     self.date or fields.Date.today(),
                            #                                                     round=True)
                        else:
                            # When currencies are the same, ensure amount_currency matches the debit/credit amount exactly
                            temp['amount_currency'] = temp.get('debit', 0.0) - temp.get('credit', 0.0)
                        self.env['account.move.line'].create(temp)
            move_line['debit'] = self._convert(amount)
            self.env['account.move.line'].create(move_line)
        return line_total

    def proforma_voucher(self):
        self.action_move_line_create()

    #add warning 'Fill the expense account!' when field expense account is empty
    def action_approved(self):
        for rec in self:
            for line in rec.voucher_line:
                if not line.expense_account:
                    raise ValidationError('Fill the expense account!')
            rec.state = 'approved'
            rec.expense_account_state = 'filled'
    
            mail_template = self.env.ref('equip3_accounting_pettycash.mail_template_petty_cash_voucher_approved')
            ctx = {
                'email_from': self.env.user.company_id.email,
                'email_to': rec.submitter_id.partner_id.email,
                'submitter_name': rec.submitter_id.name,
                'voucher_date': rec.date,
            }
            mail_template.with_context(ctx).send_mail(rec.id, True)

            whatsapp_template = self.env.ref('equip3_accounting_pettycash.wa_template_petty_cash_voucher_approved')
            phone_number = str(rec.submitter_id.mobile or rec.submitter_id.phone)
            rec._send_whatsapp_message(whatsapp_template, phone_number)
    
    #add warning 'Fill the expense account!' when field expense account is empty
    def button_approved(self):
        for move in self:
            for line in move.voucher_line:
                if not line.expense_account:
                    raise ValidationError('Fill the expense account please!')
            move.expense_account_state = 'filled'
            move.state = 'approved'   

            mail_template = self.env.ref('equip3_accounting_pettycash.mail_template_petty_cash_voucher_approved')
            ctx = {
                'email_from': self.env.user.company_id.email,
                'email_to': move.submitter_id.partner_id.email,
                'submitter_name': move.submitter_id.name,
                'voucher_date': move.date,
            }
            mail_template.with_context(ctx).send_mail(move.id, True)

            whatsapp_template = self.env.ref('equip3_accounting_pettycash.wa_template_petty_cash_voucher_approved')
            phone_number = str(move.submitter_id.mobile or move.submitter_id.phone)
            move._send_whatsapp_message(whatsapp_template, phone_number)

    def action_create_voucher(self):
        if self._context.get('dont_redirect'):
            return True

    @api.depends('voucher_line.amount')
    def _compute_amount(self):
        for rec in self:
            total = 0.0
            for line in rec.voucher_line:
                total += line.amount
            rec.total = total
    
    def action_rejected(self):
        for rec in self:
            rec.state = 'rejected'

            mail_template = self.env.ref('equip3_accounting_pettycash.mail_template_petty_cash_voucher_rejected')
            ctx = {
                'email_from': self.env.user.company_id.email,
                'email_to': rec.submitter_id.partner_id.email,
                'submitter_name': rec.submitter_id.name,
                'voucher_date': rec.date,
            }
            mail_template.with_context(ctx).send_mail(rec.id, True)

            whatsapp_template = self.env.ref('equip3_accounting_pettycash.wa_template_petty_cash_voucher_rejected')
            phone_number = str(rec.submitter_id.mobile or rec.submitter_id.phone)
            rec._send_whatsapp_message(whatsapp_template, phone_number)
    
    @api.model
    def _send_whatsapp_message(self, template_id, phone_number, url=False):
        wa_sender = waParam()
        for record in self:
            if not template_id.broadcast_template_id:
                raise ValidationError(_("Broadcast Template must be set first in Whatsapp Template!"))
            string_test = str(template_id.message)
            if "${custodian_name}" in string_test:
                string_test = string_test.replace("${custodian_name}", record.fund.custodian.name)
            if "${submitter_name}" in string_test:
                string_test = string_test.replace("${submitter_name}", record.submitter_id.name)
            if "${total_amount}" in string_test:
                string_test = string_test.replace("${total_amount}", str(record.total))
            if "${fund_name}" in string_test:
                string_test = string_test.replace("${fund_name}", record.fund.name)
            if "${voucher_name}" in string_test:
                string_test = string_test.replace("${voucher_name}", record.name)
            if "${voucher_date}" in string_test:
                string_test = string_test.replace("${voucher_date}", fields.Datetime.from_string(
                    record.date).strftime('%d/%m/%Y'))
            if "${url}" in string_test:
                string_test = string_test.replace("${url}", url)
            phone_num = phone_number
            if "+" in phone_num:
                phone_num = phone_num.replace("+", "")
            wa_sender.set_wa_string(string_test, template_id._name, template_id=template_id)
            wa_sender.send_wa(phone_num)

    def action_cancel(self):
        for record in self:
            record.write({'state':'cancelled'})

class AccountPettycashVoucherhWizardLine(models.Model):
    _name = 'account.pettycash.voucher.wizard.line'
    _description = "Account Petty Cash Voucher Wizard Line"

    def _default_analytic_group_ids(self):
        active_id = self._context.get('active_id')
        return self.env['account.pettycash'].browse(active_id).analytic_group_ids

    line_id = fields.Many2one('account.pettycash.voucher.wizard', string='Voucher Line', readonly=True, store=True)
    product_id = fields.Many2one('product.product', string='Product', domain="[('use_on_petty_cash','=',True)]")
    name = fields.Char(string="Description")
    expense_account = fields.Many2one('account.account', string='Expense Account')
    quantity = fields.Float(string='Quantity', default=1)
    price_unit = fields.Float(string="Unit Price")
    tax_ids = fields.Many2one('account.tax', string='Tax', domain="[('type_tax_use','=','purchase')]")
    taxes = fields.Monetary(string="Taxes", readonly=True, store=True)
    price_total = fields.Monetary(string="price total", readonly=True, store=True)
    amount = fields.Monetary(string="Amount", readonly=True, store=True)
    currency_id = fields.Many2one('res.currency', related='line_id.currency_id')
    company_id = fields.Many2one('res.company', related='line_id.company_id')
    partner_id = fields.Many2one('res.users', related='line_id.partner_id')
    expense_account_state = fields.Selection(selection=[
        ('filled', 'Expense Account is Filled'),
        ('null', 'Expense Account is not Filled'),
    ], string='Expense Account Status', default='null')
    analytic_group_ids = fields.Many2many('account.analytic.tag', string="Analytic Group", default=_default_analytic_group_ids)
    analytic_group_ids_domain = fields.Char(string='Analytic Group Domain', compute='_compute_analytic_group_ids_domain')
    expense_budget = fields.Monetary(string="Expense Budget", compute='_compute_amount_budget')
    crossovered_budget_line_id = fields.Many2one('crossovered.budget.lines', string='Budget Line')
    crossovered_budget_id = fields.Many2one('crossovered.budget', related='crossovered_budget_line_id.crossovered_budget_id')
    date = fields.Date(related='line_id.date')
    general_budget_id = fields.Many2one('account.budget.post', string='Budgetary Position')
    state = fields.Selection(related='line_id.state')


    @api.depends('expense_account','analytic_group_ids','line_id.date')
    def _compute_amount_budget(self):
        for line in self:
            budget_lines = self.env['crossovered.budget.lines'].search([
                ('crossovered_budget_id.state', '=', 'validate'),
                ('date_from', '<=', line.line_id.date), 
                ('date_to', '>=', line.line_id.date),
            ])

            expense_budget = 0
            for budget in budget_lines:
                acc_ids = budget.general_budget_id.account_ids.ids
                if line.expense_account.id in acc_ids and any(item in line.analytic_group_ids.ids for item in budget.account_tag_ids.ids):
                    expense_budget_amount = budget.budget_amount - (budget.child_purchase_amount + budget.reserve_amount_2 + budget.practical_budget_amount)
                    expense_budget = expense_budget_amount
                    line.crossovered_budget_line_id = budget.id
                    line.general_budget_id = budget.general_budget_id.id

                    # voucher_line = self.search([
                    #     ('crossovered_budget_line_id', '=',line.crossovered_budget_line_id.id),
                    #     ('line_id.state', '=', 'approved')
                    # ])
                    # for voucher in voucher_line:
                    #     expense_budget -= (voucher.price_unit * voucher.quantity)

            line.expense_budget = expense_budget

    @api.depends('line_id.fund.analytic_group_ids')
    def _compute_analytic_group_ids_domain(self):
        self.analytic_group_ids_domain = json.dumps([('id','in',self.line_id.fund.analytic_group_ids.ids)])

    # def button_approved(self):
    #     for move in self:
    #         for line in move.voucher_line:
    #             if not line.expense_account:
    #                 raise ValidationError('Fill the expense account please!')
    #         move.expense_account_state = 'filled'
    #         move.state = 'approved'

    @api.onchange('product_id')
    def _onchange_product_id(self):
        for line in self:
            line.name = line._get_computed_name()
            line.expense_account = line._get_computed_account()
            taxes = line._get_computed_taxes()
            line.tax_ids = taxes
            # line.expense_account = line._get_expense_account()

    @api.onchange('quantity', 'price_unit', 'tax_ids')
    def _onchange_price_subtotal(self):
        for line in self:
            line.update(line._get_price_total_and_subtotal())

    def _get_computed_name(self):
        self.ensure_one()
        if not self.product_id:
            return ''

        if self.partner_id.lang:
            product = self.product_id.with_context(lang=self.partner_id.lang)
        else:
            product = self.product_id

        values = []
        if product.partner_ref:
            values.append(product.partner_ref)
        if product.description_purchase:
            values.append(product.description_purchase)
        return '\n'.join(values)

    def _get_computed_account(self):
        self.ensure_one()
        self = self.with_company(self.line_id.ba_ca_journal_id.company_id)
        
        if self.product_id:
            accounts = self.product_id.product_tmpl_id.property_account_expense_id
            return accounts or self.expense_account

        else:
            expense = int(self._get_config_value('petty_cash_expense_account_id')) if self._get_config_value(
            'petty_cash_expense_account_id') else False
            return expense or self.expense_account

    # def _get_expense_account(self):
    #     self.ensure_one()
    #     expense_account = int(self._get_config_value('petty_cash_expense_account_id')) if self._get_config_value(
    #         'petty_cash_expense_account_id') else False
    #     return expense_account

    def _get_computed_taxes(self):
        self.ensure_one()

        if self.product_id.supplier_taxes_id:
            tax_ids = self.product_id.supplier_taxes_id.filtered(lambda tax: tax.company_id == self.line_id.company_id)
        elif self.expense_account.tax_ids:
            tax_ids = self.expense_account.tax_ids
        else:
            tax_ids = self.env['account.tax']

        if not tax_ids:
            tax_ids = self.line_id.company_id.account_purchase_tax_id

        if self.company_id and tax_ids:
            tax_ids = tax_ids.filtered(lambda tax: tax.company_id == self.company_id)

        return tax_ids

    def _get_price_total_and_subtotal(self, price_unit=None, quantity=None, currency=None, product=None, partner=None,
                                      taxes=None):
        self.ensure_one()
        return self._get_price_total_and_subtotal_model(
            price_unit=price_unit or self.price_unit,
            quantity=quantity or self.quantity,
            currency=currency or self.currency_id,
            product=product or self.product_id,
            partner=partner or self.partner_id,
            taxes=taxes or self.tax_ids,
        )

    @api.model
    def _get_price_total_and_subtotal_model(self, price_unit, quantity, currency, product, partner, taxes):
        res = {}
        # Compute 'price_subtotal'.
        line_discount_price_unit = price_unit
        subtotal = quantity * line_discount_price_unit
        # Compute 'price_total'.
        if taxes:
            force_sign = 1
            taxes_res = taxes._origin.with_context(force_sign=force_sign).compute_all(line_discount_price_unit,
                                                                                      quantity=quantity,
                                                                                      currency=currency,
                                                                                      product=product, partner=partner)
            res['price_total'] = taxes_res['total_excluded']
            res['amount'] = taxes_res['total_included']
            res['taxes'] = taxes_res['total_included'] - taxes_res['total_excluded']
        else:
            res['amount'] = res['price_total'] = subtotal
            res['taxes'] = 0

        if currency:
            res = {k: currency.round(v) for k, v in res.items()}
        return res

    def _get_config_value(self, para):
        value = self.env['ir.config_parameter'].sudo().get_param(para)
        return value
