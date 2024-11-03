# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import fields, models, api, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError, ValidationError
from num2words import num2words
from lxml import etree
import logging
_logger = logging.getLogger(__name__)


class AccountVoucher(models.Model):
    _name = 'account.voucher'
    _description = 'Accounting Voucher'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "date desc, id desc"

#     @api.model
#     def _default_journal(self):
#         #voucher_type = self._context.get('voucher_type', 'sale')
#         company_id = self._context.get('company_id', self.env.user.company_id.id)
#         domain = [
#             ('type', '=', ('cash','bank','general')),
#             ('company_id', '=', company_id),
#         ]
#         return self.env['account.journal'].search(domain, limit=1)


    @api.model
    def _default_journal(self):
        voucher_type = self._context.get('voucher_type', 'sale')
        company_id = self._context.get('company_id', self.env.user.company_id.id)
        domain = [
            ('type', '=', voucher_type),
            ('company_id', '=', company_id),
        ]
        return self.env['account.journal'].search(domain, limit=1)
    
    @api.model
    def _default_payment_journal(self):
        company_id = self._context.get('company_id', self.env.user.company_id.id)
        domain = [
            ('type', 'in', ('bank', 'cash')),
            ('company_id', '=', company_id),
        ]
        return self.env['account.journal'].search(domain, limit=1)
    
    def _compute_voucher_docs_count(self):
        Attachment = self.env['ir.attachment']
        for voucher in self:
            voucher.doc_count = Attachment.search_count([
                ('res_model', '=', 'account.voucher'), ('res_id', '=', voucher.id)
            ])
    
    doc_count = fields.Integer(compute='_compute_voucher_docs_count', string="Number of documents attached")
    voucher_type = fields.Selection([
        ('sale', 'Receipt'),
        ('purchase', 'Payment')
        ], string='Type', readonly=True, states={'draft': [('readonly', False)]}, oldname="type")
    #name = fields.Char('Payment Memo',
    #    readonly=True, states={'draft': [('readonly', False)]}, default='',copy=False)
    number = fields.Char(copy=False, readonly=False, index=True, tracking=True)
    name = fields.Char(string='Entries Number')
    date = fields.Date("Bill Date", readonly=True,
        index=True, states={'draft': [('readonly', False)]},
        copy=False, default=fields.Date.context_today)
    account_date = fields.Date("Accounting Date",
        readonly=True, index=True, states={'draft': [('readonly', False)]},
        help="Effective date for accounting entries", copy=False, default=fields.Date.context_today)
    journal_id = fields.Many2one('account.journal', 'Journal',
        required=True, readonly=True, states={'draft': [('readonly', False)]}, default=_default_journal,
        domain="[('type', 'in', {'sale': ['sale'], 'purchase': ['purchase']}.get(voucher_type, [])), ('company_id', '=', company_id)]")
    payment_journal_id = fields.Many2one('account.journal', string='Payment Method', readonly=True,
        states={'draft': [('readonly', False)]}, domain="[('type', 'in', ['cash', 'bank'])]", default=_default_payment_journal)
    fiscal_position_id = fields.Many2one('account.fiscal.position', string='Fiscal Position')
#     account_id = fields.Many2one('account.account', 'Account',
#         required=True, readonly=True, states={'draft': [('readonly', False)]},
#         domain="[('deprecated', '=', False), ('internal_type','=', (voucher_type == 'purchase' and 'payable' or 'receivable'))]")
    line_ids = fields.One2many('account.voucher.line', 'voucher_id', 'Voucher Lines',
        readonly=True, copy=True,
        states={'draft': [('readonly', False)]})
    narration = fields.Text('Notes', readonly=True, states={'draft': [('readonly', False)]})
    currency_id = fields.Many2one('res.currency', compute='_get_journal_currency',
        string='Currency', readonly=True, store=True, default=lambda self: self._get_currency())
    company_id = fields.Many2one('res.company', 'Company',
        readonly=True, states={'draft': [('readonly', False)]},
        default=lambda self: self._get_company())
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('cancel', 'Cancelled'),
        ('proforma', 'Pro-forma'),
        ('posted', 'Posted')
        ], 'Status', readonly=True, track_visibility='onchange', copy=False, default='draft',
        help=" * The 'Draft' status is used when a user is encoding a new and unconfirmed Voucher.\n"
             " * The 'Pro-forma' status is used when the voucher does not have a voucher number.\n"
             " * The 'Posted' status is used when user create voucher,a voucher number is generated and voucher entries are created in account.\n"
             " * The 'Cancelled' status is used when user cancel voucher.")
    reference = fields.Char('Bill Reference', readonly=True, states={'draft': [('readonly', False)]},
                                 help="The partner reference of this document.", copy=False)
    amount = fields.Monetary(string='Total', store=True, readonly=True, compute='_compute_total')
    tax_amount = fields.Monetary(readonly=True, store=True, compute='_compute_total')
    tax_correction = fields.Monetary(readonly=True, states={'draft': [('readonly', False)]},
        help='In case we have a rounding problem in the tax, use this field to correct it')
    #number = fields.Char(readonly=True, copy=False)
    move_id = fields.Many2one('account.move', 'Journal Entry', copy=False)
    partner_id = fields.Many2one('res.partner', 'Partner', change_default=1, readonly=True, states={'draft': [('readonly', False)]})
    paid = fields.Boolean(compute='_check_paid', help="The Voucher has been totally paid.")
    pay_now = fields.Selection([
            ('pay_now', 'Pay Directly'),
            ('pay_later', 'Pay Later'),
        ], 'Payment', index=True, readonly=True, states={'draft': [('readonly', False)]}, default='pay_later')
    date_due = fields.Date('Due Date', readonly=True, index=True, states={'draft': [('readonly', False)]})
    
    user_id = fields.Many2one('res.users', string='Responsible', index=True, track_visibility='onchange', track_sequence=2, default=lambda self: self.env.user)
    account_id = fields.Many2one('account.account', 'Account', required=True, readonly=True, states={'draft': [('readonly', False)]},  domain="[('deprecated', '=', False)]")
    transaction_type = fields.Selection([
                                         #('expedition', 'Expedition'), 
                                         ('regular', 'Regular'),
                                         #('disposal','Asset Disposal')
                                         ], string='Transaction Type', default='regular', readonly=True, states={'draft': [('readonly', False)]})
    
    
    # @api.onchange('account_date')
    # def _onchange_account_date(self):
    #     check_periods = self.env['sh.account.period'].search([('date_start', '<=', self.account_date), ('date_end', '>=', self.account_date), ('company_id', '=', self.company_id.id), ('branch_id', '=', self.branch_id.id), ('state', '=', 'done')])
    #     if check_periods:
    #         raise UserError(_('You can not post any journal entry already on Closed Period'))

    
    def _valid_field_parameter(self, field, name):
        return name == "oldname" or name == "track_sequence" or name == "track_visibility" or super()._valid_field_parameter(field, name)

    def _get_report_base_filename(self):
        return self._get_move_display_name()

    def _get_move_display_name(self, show_ref=False):
        ''' Helper to get the display name of an invoice depending of its type.
        :param show_ref:    A flag indicating of the display name must include or not the journal entry reference.
        :return:            A string representing the invoice.
        '''
        self.ensure_one()
        draft_name = ''
        if self.state == 'draft':
            draft_name = _('Draft Voucher')
            if not self.number or self.number == '/':
                draft_name = ' (* %s)' % str(self.id)
            else:
                draft_name = ' ' + self.number
        return (draft_name or self.number) + (show_ref and self.reference and ' (%s%s)' % (self.reference[:50], '...' if len(self.reference) > 50 else '') or '')
    
    # @api.depends('state', 'journal_id', 'payment_journal_id', 'date')
    # def _compute_name(self):
    #     # def journal_key(move):
    #     #     return (move.journal_id, move.payment_journal_id.refund_sequence and move.move_type)
    #     #
    #     # def date_key(move):
    #     #     return (move.date.year, move.date.month)
    #     #
    #     # grouped = defaultdict(  # key: journal_id, move_type
    #     #     lambda: defaultdict(  # key: first adjacent (date.year, date.month)
    #     #         lambda: {
    #     #             'records': self.env['account.move'],
    #     #             'format': False,
    #     #             'format_values': False,
    #     #             'reset': False
    #     #         }
    #     #     )
    #     # )
    #     self = self.sorted(lambda m: (m.date, m.reference or '', m.id))
    #     highest_name = self[0]._get_last_sequence() if self else False
    #     print ('===s===',highest_name)
        # Group the moves by journal and month
        # for move in self:
        #     move._constrains_date_sequence()
            # if not highest_name and move == self[0] and not move.posted_before:
            #     # In the form view, we need to compute a default sequence so that the user can edit
            #     # it. We only check the first move as an approximation (enough for new in form view)
            #     pass
            # elif (move.name and move.name != '/') or move.state != 'posted':
            #     try:
            #         if not move.posted_before:
            #             move._constrains_date_sequence()
            #         # Has already a name or is not posted, we don't add to a batch
            #         continue
            #     except ValidationError:
            #         # Has never been posted and the name doesn't match the date: recompute it
            #         pass
            # group = grouped[journal_key(move)][date_key(move)]
            # if not group['records']:
            #     # Compute all the values needed to sequence this whole group
            #     move._set_next_sequence()
            #     group['format'], group['format_values'] = move._get_sequence_format_param(move.name)
            #     group['reset'] = move._deduce_sequence_number_reset(move.name)
            # group['records'] += move

        # Fusion the groups depending on the sequence reset and the format used because `seq` is
        # the same counter for multiple groups that might be spread in multiple months.
        # final_batches = []
        # for journal_group in grouped.values():
        #     for date_group in journal_group.values():
        #         if (
        #             not final_batches
        #             or final_batches[-1]['format'] != date_group['format']
        #             or dict(final_batches[-1]['format_values'], seq=0) != dict(date_group['format_values'], seq=0)
        #         ):
        #             final_batches += [date_group]
        #         elif date_group['reset'] == 'never':
        #             final_batches[-1]['records'] += date_group['records']
        #         elif (
        #             date_group['reset'] == 'year'
        #             and final_batches[-1]['records'][0].date.year == date_group['records'][0].date.year
        #         ):
        #             final_batches[-1]['records'] += date_group['records']
        #         else:
        #             final_batches += [date_group]

        # Give the name based on previously computed values
        # for batch in final_batches:
        #     for move in batch['records']:
        #         move.name = batch['format'].format(**batch['format_values'])
        #         batch['format_values']['seq'] += 1
        #     batch['records']._compute_split_sequence()

        # self.filtered(lambda m: not m.name).name = '/'
        
    def _convert_num2words(self):
        #check_amount_in_words = currency.amount_to_text(math.floor(amount), lang='en', currency='')
        check_amount_in_words = (num2words(self.amount, lang='id') + ' ' + (self.currency_id.name or '')).upper()
        return check_amount_in_words
    
    def print_payment_voucher(self):
        line_ids = self.mapped('line_ids')
        if not line_ids:
            raise UserError(_('Nothing to print.'))
        return self.env.ref('aos_account_voucher.action_report_account_voucher').report_action(self)
    
    
    def attachment_voucher_view(self):
        self.ensure_one()
        domain = [
            ('res_model', '=', 'account.voucher'), ('res_id', 'in', self.ids)]
        return {
            'name': _('Attachments'),
            'domain': domain,
            'res_model': 'ir.attachment',
            'type': 'ir.actions.act_window',
            'view_id': False,
            'view_mode': 'kanban,tree,form',
            'view_type': 'form',
            'help': _('''<p class="oe_view_nocontent_create">
                        Documents are attached to the purchase order.</p><p>
                        Send messages or log internal notes with attachments to link
                        documents to your property contract.
                    </p>'''),
            'limit': 80,
            'context': "{'default_res_model': '%s','default_res_id': %d}" % (self._name, self.id)
        }

    @api.depends('move_id.line_ids.reconciled', 'move_id.line_ids.account_id.internal_type')
    def _check_paid(self):
        self.paid = any([((line.account_id.internal_type, 'in', ('receivable', 'payable')) and line.reconciled) for line in self.move_id.line_ids])

    @api.model
    def _get_currency(self):
        journal = self.env['account.journal'].browse(self.env.context.get('default_journal_id', False))
        if journal.currency_id:
            return journal.currency_id.id
        return self.env.user.company_id.currency_id.id

    @api.model
    def _get_company(self):
        return self._context.get('company_id', self.env.user.company_id.id)

    @api.constrains('company_id', 'currency_id')
    def _check_company_id(self):
        for voucher in self:
            if not voucher.company_id:
                raise ValidationError(_("Missing Company"))
            if not voucher.currency_id:
                raise ValidationError(_("Missing Currency"))

    @api.depends('name', 'number')
    def name_get(self):
        return [(r.id, (r.number or _('Voucher'))) for r in self]

    @api.depends('journal_id', 'company_id')
    def _get_journal_currency(self):
        self.currency_id = self.journal_id.currency_id.id or self.company_id.currency_id.id

    @api.depends('tax_correction', 'line_ids.price_subtotal')
    def _compute_total(self):
        tax_calculation_rounding_method = self.env.user.company_id.tax_calculation_rounding_method
        for voucher in self:
            total = 0
            tax_amount = 0
            tax_lines_vals_merged = {}
            for line in voucher.line_ids:
                tax_info = line.tax_ids.compute_all(line.price_unit, voucher.currency_id, line.quantity, line.product_id, voucher.partner_id)
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
                voucher.amount = total + tax_amount + voucher.tax_correction
            else:
                voucher.amount = total + voucher.tax_correction
            voucher.tax_amount = tax_amount

    @api.onchange('date')
    def onchange_date(self):
        self.account_date = self.date

    # @api.model
    # def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
    #     res = super(AccountVoucher, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
    #     if view_type == 'form':
    #         doc = etree.XML(res['arch'])
    #         for node in doc.xpath("//field[@name='account_id']"):
    #             # Assuming 'voucher_type' is stored and accessible in the context or through the default record data
    #             voucher_type = self._context.get('default_voucher_type')  # You might need a more reliable way to get this value
    #             domain = [('deprecated', '=', False)]
    #             if voucher_type == 'sale':
    #                 excluded_user_types = self.env['account.account.type'].search([('name', 'in', ['Expenses', 'Other Expense'])])
    #                 excluded_user_types_ids = excluded_user_types.ids
    #                 # return {'domain': {'account_id': [('user_type_id', 'not in', excluded_user_types_ids)]}}
    #                 domain.append(('user_type_id.name', 'not in', excluded_user_types.mapped('name')))
    #             elif voucher_type == 'purchase':
    #                 excluded_user_types = self.env['account.account.type'].search([('name', 'in', ['Expenses', 'Other Expense'])])
    #                 excluded_user_types_ids = excluded_user_types.ids
    #                 domain.append(('user_type_id.name', 'not in', excluded_user_types.mapped('name')))
    #             node.set('domain', str(domain))
    #         res['arch'] = etree.tostring(doc)
        
    #     return res


    @api.onchange('voucher_type', 'partner_id', 'pay_now', 'journal_id', 'payment_journal_id')
    def onchange_partner_id(self):
        pay_journal_domain = [('type', 'in', ['cash', 'bank'])]
        domain = [
            ('company_id', '=', self.company_id.id),
        ]

        if self.partner_id:
            if self.pay_now == 'pay_now':
                self.account_id = self.payment_journal_id.default_account_id \
                    if self.voucher_type == 'sale' else self.payment_journal_id.default_account_id
            else:
                self.account_id = self.partner_id.property_account_receivable_id \
                    if self.voucher_type == 'sale' else self.partner_id.property_account_payable_id  
                
                
        else:            
            if self.pay_now == 'pay_now':
                self.account_id = self.payment_journal_id.default_account_id \
                    if self.voucher_type == 'sale' else self.payment_journal_id.default_account_id
            else:
                self.account_id = self.env['account.account'].search(domain+[('internal_type', '=', 'receivable' if self.voucher_type == 'sale' else 'payable')], limit=1)
            if self.voucher_type == 'purchase':
                self.journal_id = self.env['account.journal'].search(domain+[('type','=','purchase')], limit=1)
                pay_journal_domain.append(('outbound_payment_method_ids', '!=', False))
            else:
                self.journal_id = self.env['account.journal'].search(domain+[('type','=','sale')], limit=1)
                pay_journal_domain.append(('inbound_payment_method_ids', '!=', False))
        return {'domain': {'payment_journal_id': pay_journal_domain}}

#     @api.onchange('partner_id', 'pay_now', 'journal_id')
#     def onchange_partner_id(self):
#         #print "==onchange_partner_id==",self.pay_now,self.voucher_type
#         if self.pay_now == 'pay_now':
#             if self.journal_id.type in ('sale','purchase'):
#                 liq_journal = self.env['account.journal'].search([('type','not in',['sale','purchase'])], limit=1)
#                 self.account_id = liq_journal.default_account_id \
#                     if self.voucher_type == 'sale' else liq_journal.default_account_id
#             else:
#                 self.account_id = self.journal_id.default_account_id \
#                     if self.voucher_type == 'sale' else self.journal_id.default_account_id
#         else:
#             if self.partner_id:
#                 self.account_id = self.partner_id.property_account_receivable_id \
#                     if self.voucher_type == 'sale' else self.partner_id.property_account_payable_id
#             elif self.journal_id.type not in ('sale','purchase'):
#                 self.account_id = False
#             else:
#                 self.account_id = self.journal_id.default_account_id \
#                     if self.voucher_type == 'sale' else self.journal_id.default_account_id
            

    def action_post(self):
        return self.action_move_line_create()
        # self.action_move_line_create()

    def action_cancel_draft(self):
        self.write({'state': 'draft'})

    def check_closed_period(self):
        check_periods = self.env['sh.account.period'].search([('company_id', '=', self.company_id.id), ('date_start', '<=', self.account_date), ('date_end', '>=', self.account_date), ('state', '=', 'done'), ('branch_id', '=', self.branch_id.id)])
        if check_periods:
            raise UserError(_('You can not post any journal entry already on Closed Period'))

    def proforma_voucher(self):
        self.check_closed_period()
        exceeding_lines = []
        for line in self.line_ids:
            subtotal_without_tax = line.price_unit * line.quantity
            if line.expense_budget != 0 and subtotal_without_tax > line.expense_budget:
                exceeding_lines.append(line)  # Append the line record itself

        # Step 2: The list comprehension now works correctly with line records
        if exceeding_lines:
            wizard = self.env['expense.request.warning'].create({
                'warning_line_ids': [
                    (0, 0, {
                        'product_id': line.product_id.id,
                        'budgetary_position_id': line.budgetary_position_id.id,
                        'account_id': line.account_id.id,
                        'expense_budget': round(line.expense_budget, 2),
                        'planned_budget': round(line.planned_budget, 2),
                        'realized_amount': round((line.price_unit * line.quantity), 2),
                    }) for line in exceeding_lines
                ]
            })
            return {
                'name': 'Expense Request Warning',
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'expense.request.warning',
                'res_id': wizard.id,
                'target': 'new',
            }
        else:
            self.write({'state': 'confirmed'})

    def cancel_voucher(self):
        for voucher in self:
            voucher.move_id.button_draft()
            voucher.move_id.button_cancel()
            voucher.move_id.with_context(force_delete=True).unlink()
        self.write({'state': 'cancel', 'move_id': False})

    def unlink(self):
        for voucher in self:
            if voucher.state not in ('draft', 'cancel'):
                raise UserError(_('Cannot delete voucher(s) which are already opened or paid.'))
        return super(AccountVoucher, self).unlink()


    def first_move_line_get(self, move_id, company_currency, current_currency):
        debit = credit = 0.0
        if self.voucher_type == 'purchase':
            credit = self._convert(self.amount)
        elif self.voucher_type == 'sale':
            debit = self._convert(self.amount)
        if debit < 0.0: debit = 0.0
        if credit < 0.0: credit = 0.0
        sign = debit - credit < 0 and -1 or 1
        #set the first line of the voucher
        move_line = {
                'name': self.name or '/',
                'debit': debit,
                'credit': credit,
                'account_id': self.account_id.id,
                'move_id': move_id,
                'journal_id': self.payment_journal_id.id if self.pay_now == 'pay_now' else self.journal_id.id,
                'partner_id': self.partner_id.commercial_partner_id.id,
                'currency_id': company_currency != current_currency and current_currency or False,
                'amount_currency': (sign * abs(self.amount)  # amount < 0 for refunds
                    if company_currency != current_currency else 0.0),
                'date': self.account_date,
                'date_maturity': self.date_due,
            }
        return move_line


    def account_move_get(self):
        for record in self:
            if not record.number or record.number == '/':
                seq_date = fields.Datetime.context_timestamp(self, fields.Datetime.to_datetime(record.date))
                new_number = self.env['ir.sequence'].next_by_code('account.voucher', sequence_date=seq_date) or _('New')
            else:
                new_number = record.number
            #print ('===new_number==',new_number)
            record.number = new_number
            # highest_name = self[0]._get_last_sequence() if self else False
            # if record.number:
            #     new_number = record.number
            # else:
            #     new_number = record._set_next_sequence()
            # elif self.pay_now == 'pay_now':
            #     if self.payment_journal_id.id:
            #         if not self.payment_journal_id.secure_sequence_id.active:
            #             raise UserError(_('Please activate the sequence of selected journal !'))
            #     name = self.payment_journal_id.secure_sequence_id.with_context(ir_sequence_date=self.date).next_by_id()
            # elif self.pay_now == 'pay_later':
            #     if self.journal_id.secure_sequence_id:
            #         if not self.journal_id.secure_sequence_id.active:
            #             raise UserError(_('Please activate the sequence of selected journal !'))
            #     name = self.journal_id.secure_sequence_id.with_context(ir_sequence_date=self.date).next_by_id()
            # else:
            #     raise UserError(_('Please define a sequence on the journal.'))
            # if not record.number or record.number != '/':
            #     seq_date = fields.Datetime.context_timestamp(self, fields.Datetime.to_datetime(record.date))
            #     new_number = self.env['ir.sequence'].next_by_code('account.voucher', sequence_date=seq_date) or _('New')
            # else:
            #     new_number = record.number
            move = {
                # 'name': new_number,
                'journal_id': record.payment_journal_id.id if record.pay_now == 'pay_now' else record.journal_id.id,
                'narration': record.narration,
                'date': record.account_date,
                'ref': record.reference,
            }
            return move


    def _convert(self, amount):
        '''
        This function convert the amount given in company currency. It takes either the rate in the voucher (if the
        payment_rate_currency_id is relevant) either the rate encoded in the system.
        :param amount: float. The amount to convert
        :param voucher: id of the voucher on which we want the conversion
        :param context: to context to use for the conversion. It may contain the key 'date' set to the voucher date
            field in order to select the good rate to use.
        :return: the amount in the currency of the voucher's company
        :rtype: float
        '''
        for voucher in self:
            return voucher.currency_id._convert(amount, voucher.company_id.currency_id, voucher.company_id, voucher.account_date)


#     def voucher_pay_now_payment_create(self):
#         if self.voucher_type == 'sale':
#             payment_methods = self.journal_id.inbound_payment_method_ids
#             payment_type = 'inbound'
#             partner_type = 'customer'
#             sequence_code = 'account.payment.customer.invoice'
#         else:
#             payment_methods = self.journal_id.outbound_payment_method_ids
#             payment_type = 'outbound'
#             partner_type = 'supplier'
#             sequence_code = 'account.payment.supplier.invoice'
#         return {
#             'payment_type': payment_type,
#             'payment_method_id': payment_methods and payment_methods[0].id or False,
#             'partner_type': partner_type,
#             'partner_id': self.partner_id.commercial_partner_id.id,
#             'amount': self.amount,
#             'currency_id': self.currency_id.id,
#             'payment_date': self.date,
#             'journal_id': self.payment_journal_id.id,
#             'communication': self.name,
#         }
    
    def _prepare_voucher_move_line(self, line, amount, move_id, company_currency, current_currency):
        line_subtotal = line.price_subtotal
        if self.voucher_type == 'sale':
            line_subtotal = -1 * line.price_subtotal
        # convert the amount set on the voucher line into the currency of the voucher's company
        #amount = self._convert(line.price_unit*line.quantity)
        #===================================================================
        # ALLOW DEBIT AND CREDIT BASED ON MINUS OR PLUS
        #===================================================================
        if (self.voucher_type == 'sale' and amount > 0.0) or (self.voucher_type == 'purchase' and amount < 0.0):
            debit = 0.0
            credit = abs(amount)
        elif (self.voucher_type == 'sale' and amount < 0.0) or (self.voucher_type == 'purchase' or amount > 0.0):
            debit = abs(amount)
            credit = 0.0
        move_line = {
            'journal_id': self.journal_id.id,
            'name': line.name or '/',
            'account_id': line.account_id.id,
            'move_id': move_id,
            'quantity': line.quantity,
            'product_id': line.product_id.id,
            'partner_id': self.partner_id.commercial_partner_id.id,
            'analytic_account_id': line.account_analytic_id and line.account_analytic_id.id or False,
            'analytic_tag_ids': [(6, 0, line.analytic_tag_ids.ids)],
            #===================================================================     
            'credit': abs(amount) if credit > 0.0 else 0.0,
            'debit': abs(amount) if debit > 0.0 else 0.0,
            #===================================================================
            'date': self.account_date,
            'tax_ids': [(4,t.id) for t in line.tax_ids],
            'amount_currency': line_subtotal if current_currency != company_currency else 0.0,
            'currency_id': company_currency != current_currency and current_currency or False,
            'payment_id': self._context.get('payment_id'),
        }
        return move_line
    
    def voucher_move_line_create(self, line_total, move_id, company_currency, current_currency):
        '''
        Create one account move line, on the given account move, per voucher line where amount is not 0.0.
        It returns Tuple with tot_line what is total of difference between debit and credit and
        a list of lists with ids to be reconciled with this format (total_deb_cred,list_of_lists).
 
        :param voucher_id: Voucher id what we are working with
        :param line_total: Amount of the first line, which correspond to the amount we should totally split among all voucher lines.
        :param move_id: Account move wher those lines will be joined.
        :param company_currency: id of currency of the company to which the voucher belong
        :param current_currency: id of currency of the voucher
        :return: Tuple build as (remaining amount not allocated on voucher lines, list of account_move_line created in this method)
        :rtype: tuple(float, list of int)
        '''
        for line in self.line_ids:
            #create one move line per voucher line where amount is not 0.0
            if not line.price_subtotal:
                continue
#             line_subtotal = line.price_subtotal
#             if self.voucher_type == 'sale':
#                 line_subtotal = -1 * line.price_subtotal
#             # convert the amount set on the voucher line into the currency of the voucher's company
            amount = self._convert(line.price_unit*line.quantity)
#             #===================================================================
#             # ALLOW DEBIT AND CREDIT BASED ON MINUS OR PLUS
#             #===================================================================
#             if (self.voucher_type == 'sale' and amount > 0.0) or (self.voucher_type == 'purchase' and amount < 0.0):
#                 debit = 0.0
#                 credit = abs(amount)
#             elif (self.voucher_type == 'sale' and amount < 0.0) or (self.voucher_type == 'purchase' or amount > 0.0):
#                 debit = abs(amount)
#                 credit = 0.0
            #===================================================================
            move_line = self._prepare_voucher_move_line(line, amount, move_id, company_currency, current_currency)          
#             move_line = {
#                 'journal_id': self.journal_id.id,
#                 'name': line.name or '/',
#                 'account_id': line.account_id.id,
#                 'move_id': move_id,
#                 'quantity': line.quantity,
#                 'product_id': line.product_id.id,
#                 'partner_id': self.partner_id.commercial_partner_id.id,
#                 'analytic_account_id': line.account_analytic_id and line.account_analytic_id.id or False,
#                 'analytic_tag_ids': [(6, 0, line.analytic_tag_ids.ids)],
#                 #===================================================================     
#                 'credit': abs(amount) if credit > 0.0 else 0.0,
#                 'debit': abs(amount) if debit > 0.0 else 0.0,
#                 #===================================================================
#                 'date': self.account_date,
#                 'tax_ids': [(4,t.id) for t in line.tax_ids],
#                 'amount_currency': line_subtotal if current_currency != company_currency else 0.0,
#                 'currency_id': company_currency != current_currency and current_currency or False,
#                 'payment_id': self._context.get('payment_id'),
#             }
            # Create one line per tax and fix debit-credit for the move line if there are tax included
            if (line.tax_ids):
                tax_group = line.tax_ids.compute_all(line.price_unit, line.currency_id, line.quantity, line.product_id, self.partner_id)
                if move_line['debit']: move_line['debit'] = tax_group['total_excluded']
                if move_line['credit']: move_line['credit'] = tax_group['total_excluded']
                for tax_vals in tax_group['taxes']:
                    if tax_vals['amount']:
                        tax = self.env['account.tax'].browse([tax_vals['id']])
                        #print ('===tax_vals==',tax_vals)
                        if not tax_vals['account_id']:
                            raise UserError(_('You have to setup account taxes for %s.' % tax_vals['name']))
                        account_id = (amount > 0 and tax_vals['account_id'])
                        if not account_id: account_id = line.account_id.id
                        temp = {
                            'account_id': account_id,
                            'name': line.name + ' ' + tax_vals['name'],
                            'tax_line_id': tax_vals['id'],
                            'move_id': move_id,
                            'date': self.account_date,
                            'partner_id': self.partner_id.id,
                            'debit': self.voucher_type != 'sale' and tax_vals['amount'] or 0.0,
                            'credit': self.voucher_type == 'sale' and tax_vals['amount'] or 0.0,
                            'analytic_account_id': line.account_analytic_id and line.account_analytic_id.id or False,
                        }
                        if company_currency != current_currency:
                            ctx = {}
                            if self.account_date:
                                ctx['date'] = self.account_date
                            temp['currency_id'] = current_currency.id
                            temp['amount_currency'] = company_currency._convert(tax_vals['amount'], current_currency, line.company_id, self.account_date or fields.Date.today(), round=True)
                        self.env['account.move.line'].create(temp)
 
            self.env['account.move.line'].create(move_line)
        return line_total
        

#     def voucher_move_line_create(self, line_total, move_id, company_currency, current_currency):
#         '''
#         Create one account move line, on the given account move, per voucher line where amount is not 0.0.
#         It returns Tuple with tot_line what is total of difference between debit and credit and
#         a list of lists with ids to be reconciled with this format (total_deb_cred,list_of_lists).
#  
#         :param voucher_id: Voucher id what we are working with
#         :param line_total: Amount of the first line, which correspond to the amount we should totally split among all voucher lines.
#         :param move_id: Account move wher those lines will be joined.
#         :param company_currency: id of currency of the company to which the voucher belong
#         :param current_currency: id of currency of the voucher
#         :return: Tuple build as (remaining amount not allocated on voucher lines, list of account_move_line created in this method)
#         :rtype: tuple(float, list of int)
#         '''
#         for line in self.line_ids:
#             #create one move line per voucher line where amount is not 0.0
#             if not line.price_subtotal:
#                 continue
#             line_subtotal = line.price_subtotal
#             if self.voucher_type == 'sale':
#                 line_subtotal = -1 * line.price_subtotal
#             # convert the amount set on the voucher line into the currency of the voucher's company
#             amount = self._convert(line.price_unit*line.quantity)
#             #===================================================================
#             # ALLOW DEBIT AND CREDIT BASED ON MINUS OR PLUS
#             #===================================================================
#             if (self.voucher_type == 'sale' and amount > 0.0) or (self.voucher_type == 'purchase' and amount < 0.0):
#                 debit = 0.0
#                 credit = abs(amount)
#             elif (self.voucher_type == 'sale' and amount < 0.0) or (self.voucher_type == 'purchase' or amount > 0.0):
#                 debit = abs(amount)
#                 credit = 0.0
#             #===================================================================            
#             move_line = {
#                 'journal_id': self.journal_id.id,
#                 'name': line.name or '/',
#                 'account_id': line.account_id.id,
#                 'move_id': move_id,
#                 'quantity': line.quantity,
#                 'product_id': line.product_id.id,
#                 'partner_id': self.partner_id.commercial_partner_id.id,
#                 'analytic_account_id': line.account_analytic_id and line.account_analytic_id.id or False,
#                 'analytic_tag_ids': [(6, 0, line.analytic_tag_ids.ids)],
#                 #===================================================================     
#                 'credit': abs(amount) if credit > 0.0 else 0.0,
#                 'debit': abs(amount) if debit > 0.0 else 0.0,
#                 #===================================================================
#                 'date': self.account_date,
#                 'tax_ids': [(4,t.id) for t in line.tax_ids],
#                 'amount_currency': line_subtotal if current_currency != company_currency else 0.0,
#                 'currency_id': company_currency != current_currency and current_currency or False,
#                 'payment_id': self._context.get('payment_id'),
#             }
#             # Create one line per tax and fix debit-credit for the move line if there are tax included
#             if (line.tax_ids):
#                 tax_group = line.tax_ids.compute_all(line.price_unit, line.currency_id, line.quantity, line.product_id, self.partner_id)
#                 if move_line['debit']: move_line['debit'] = tax_group['total_excluded']
#                 if move_line['credit']: move_line['credit'] = tax_group['total_excluded']
#                 for tax_vals in tax_group['taxes']:
#                     if tax_vals['amount']:
#                         tax = self.env['account.tax'].browse([tax_vals['id']])
#                         account_id = (amount > 0 and tax_vals['account_id'] or tax_vals['refund_account_id'])
#                         if not account_id: account_id = line.account_id.id
#                         temp = {
#                             'account_id': account_id,
#                             'name': line.name + ' ' + tax_vals['name'],
#                             'tax_line_id': tax_vals['id'],
#                             'move_id': move_id,
#                             'date': self.account_date,
#                             'partner_id': self.partner_id.id,
#                             'debit': self.voucher_type != 'sale' and tax_vals['amount'] or 0.0,
#                             'credit': self.voucher_type == 'sale' and tax_vals['amount'] or 0.0,
#                             'analytic_account_id': line.account_analytic_id and line.account_analytic_id.id or False,
#                         }
#                         if company_currency != current_currency:
#                             ctx = {}
#                             if self.account_date:
#                                 ctx['date'] = self.account_date
#                             temp['currency_id'] = current_currency.id
#                             temp['amount_currency'] = company_currency._convert(tax_vals['amount'], current_currency, line.company_id, self.account_date or fields.Date.today(), round=True)
#                         self.env['account.move.line'].create(temp)
#  
#             self.env['account.move.line'].create(move_line)
#         return line_total
     

    def action_move_line_create(self):
        ''' PAY NOW IS DIRECT JOURNAL NON ACTIVE RECONCILED BEHAVIOUR
        Confirm the vouchers given in ids and create the journal entries for each of them
        '''
        for voucher in self:
            local_context = dict(self._context)
            if voucher.move_id:
                continue
            company_currency = voucher.journal_id.company_id.currency_id.id
            current_currency = voucher.currency_id.id or company_currency
            # we select the context to use accordingly if it's a multicurrency case or not
            # But for the operations made by _convert, we always need to give the date in the context
            ctx = local_context.copy()
            ctx['date'] = voucher.account_date
            ctx['check_move_validity'] = False
            # Create the account move record.
            move = self.env['account.move'].create(voucher.account_move_get())
            #print ('===s===',move.name)
            # Get the name of the account_move just created
            # Create the first line of the voucher
            move_line = self.env['account.move.line'].with_context(ctx).create(voucher.with_context(ctx).first_move_line_get(move.id, company_currency, current_currency))
            line_total = move_line.debit - move_line.credit
            if voucher.voucher_type == 'sale':
                line_total = line_total - voucher._convert(voucher.tax_amount)
            elif voucher.voucher_type == 'purchase':
                line_total = line_total + voucher._convert(voucher.tax_amount)
            #print ('===ctx===',ctx)
            # Create one move line per voucher line where amount is not 0.0
            line_total = voucher.with_context(ctx).voucher_move_line_create(line_total, move.id, company_currency, current_currency)

 
            # Create a payment to allow the reconciliation when pay_now = 'pay_now'.
#===============================================================================
#             if voucher.pay_now == 'pay_now':
#                 payment_id = (self.env['account.payment']
#                     .with_context(force_counterpart_account=voucher.account_id.id)
#                     .create(voucher.voucher_pay_now_payment_create()))
#                 payment_id.post()
# 
#                 # Reconcile the receipt with the payment
#                 lines_to_reconcile = (payment_id.move_line_ids + move.line_ids).filtered(lambda l: l.account_id == voucher.account_id)
#                 lines_to_reconcile.reconcile()
#===============================================================================
 
            # Add tax correction to move line if any tax correction specified
            if voucher.tax_correction != 0.0:
                tax_move_line = self.env['account.move.line'].search([('move_id', '=', move.id), ('tax_line_id', '!=', False)], limit=1)
                if len(tax_move_line):
                    tax_move_line.write({'debit': tax_move_line.debit + voucher.tax_correction if tax_move_line.debit > 0 else 0,
                        'credit': tax_move_line.credit + voucher.tax_correction if tax_move_line.credit > 0 else 0})
 
            # if not voucher.number or voucher.number != '/':
            #     seq_date = fields.Datetime.context_timestamp(self, fields.Datetime.to_datetime(voucher.date))
            #     new_number = self.env['ir.sequence'].next_by_code('account.voucher', sequence_date=seq_date) or _('New')
            # else:
            #     new_number = record.number
            # We post the voucher.
            #print ('mooo',move.name)
            move._post()
            voucher.write({
                'name': move.name,
                'move_id': move.id,
                'state': 'posted',
            })
        # return True
#===============================================================================
#     ASLI
#===============================================================================
#     @api.multi
#     def voucher_move_line_create(self, line_total, move_id, company_currency, current_currency):
#         '''
#         Create one account move line, on the given account move, per voucher line where amount is not 0.0.
#         It returns Tuple with tot_line what is total of difference between debit and credit and
#         a list of lists with ids to be reconciled with this format (total_deb_cred,list_of_lists).
# 
#         :param voucher_id: Voucher id what we are working with
#         :param line_total: Amount of the first line, which correspond to the amount we should totally split among all voucher lines.
#         :param move_id: Account move wher those lines will be joined.
#         :param company_currency: id of currency of the company to which the voucher belong
#         :param current_currency: id of currency of the voucher
#         :return: Tuple build as (remaining amount not allocated on voucher lines, list of account_move_line created in this method)
#         :rtype: tuple(float, list of int)
#         '''
#         tax_calculation_rounding_method = self.env.user.company_id.tax_calculation_rounding_method
#         tax_lines_vals = []
#         for line in self.line_ids:
#             #create one move line per voucher line where amount is not 0.0
#             if not line.price_subtotal:
#                 continue
#             line_subtotal = line.price_subtotal
#             if self.voucher_type == 'sale':
#                 line_subtotal = -1 * line.price_subtotal
#             # convert the amount set on the voucher line into the currency of the voucher's company
#             amount = self._convert(line.price_unit*line.quantity)
#             move_line = {
#                 'journal_id': self.journal_id.id,
#                 'name': line.name or '/',
#                 'account_id': line.account_id.id,
#                 'move_id': move_id,
#                 'quantity': line.quantity,
#                 'product_id': line.product_id.id,
#                 'partner_id': self.partner_id.commercial_partner_id.id,
#                 'analytic_account_id': line.account_analytic_id and line.account_analytic_id.id or False,
#                 'analytic_tag_ids': [(6, 0, line.analytic_tag_ids.ids)],
#                 'credit': abs(amount) if self.voucher_type == 'sale' else 0.0,
#                 'debit': abs(amount) if self.voucher_type == 'purchase' else 0.0,
#                 'date': self.account_date,
#                 'tax_ids': [(4,t.id) for t in line.tax_ids],
#                 'amount_currency': line_subtotal if current_currency != company_currency else 0.0,
#                 'currency_id': company_currency != current_currency and current_currency or False,
#                 'payment_id': self._context.get('payment_id'),
#             }
#             # Create one line per tax and fix debit-credit for the move line if there are tax included
#             if (line.tax_ids and tax_calculation_rounding_method == 'round_per_line'):
#                 tax_group = line.tax_ids.compute_all(self._convert(line.price_unit), self.company_id.currency_id, line.quantity, line.product_id, self.partner_id)
#                 if move_line['debit']: move_line['debit'] = tax_group['total_excluded']
#                 if move_line['credit']: move_line['credit'] = tax_group['total_excluded']
#                 Currency = self.env['res.currency']
#                 company_cur = Currency.browse(company_currency)
#                 current_cur = Currency.browse(current_currency)
#                 for tax_vals in tax_group['taxes']:
#                     if tax_vals['amount']:
#                         tax = self.env['account.tax'].browse([tax_vals['id']])
#                         account_id = (amount > 0 and tax_vals['account_id'] or tax_vals['refund_account_id'])
#                         if not account_id: account_id = line.account_id.id
#                         temp = {
#                             'account_id': account_id,
#                             'name': line.name + ' ' + tax_vals['name'],
#                             'tax_line_id': tax_vals['id'],
#                             'move_id': move_id,
#                             'date': self.account_date,
#                             'partner_id': self.partner_id.id,
#                             'debit': self.voucher_type != 'sale' and tax_vals['amount'] or 0.0,
#                             'credit': self.voucher_type == 'sale' and tax_vals['amount'] or 0.0,
#                             'analytic_account_id': line.account_analytic_id and line.account_analytic_id.id or False,
#                         }
#                         if company_currency != current_currency:
#                             ctx = {}
#                             sign = temp['credit'] and -1 or 1
#                             amount_currency = company_cur._convert(tax_vals['amount'], current_cur, line.company_id,
#                                                  self.account_date or fields.Date.today(), round=True)
#                             if self.account_date:
#                                 ctx['date'] = self.account_date
#                             temp['currency_id'] = current_currency
#                             temp['amount_currency'] = sign * abs(amount_currency)
#                         self.env['account.move.line'].create(temp)
# 
#             # When global rounding is activated, we must wait until all tax lines are computed to
#             # merge them.
#             if tax_calculation_rounding_method == 'round_globally':
#                 # _apply_taxes modifies the dict move_line in place to account for included/excluded taxes
#                 tax_lines_vals += self.env['account.move.line'].with_context(round=False)._apply_taxes(
#                     move_line,
#                     move_line.get('debit', 0.0) - move_line.get('credit', 0.0)
#                 )
#                 # rounding False means the move_line's amount are not rounded
#                 currency = self.env['res.currency'].browse(company_currency)
#                 move_line['debit'] = currency.round(move_line['debit'])
#                 move_line['credit'] = currency.round(move_line['credit'])
#             self.env['account.move.line'].create(move_line)
# 
#         # When round globally is set, we merge the tax lines
#         if tax_calculation_rounding_method == 'round_globally':
#             tax_lines_vals_merged = {}
#             for tax_line_vals in tax_lines_vals:
#                 key = (
#                     tax_line_vals['tax_line_id'],
#                     tax_line_vals['account_id'],
#                     tax_line_vals['analytic_account_id'],
#                 )
#                 if key not in tax_lines_vals_merged:
#                     tax_lines_vals_merged[key] = tax_line_vals
#                 else:
#                     tax_lines_vals_merged[key]['debit'] += tax_line_vals['debit']
#                     tax_lines_vals_merged[key]['credit'] += tax_line_vals['credit']
#             currency = self.env['res.currency'].browse(company_currency)
#             for vals in tax_lines_vals_merged.values():
#                 vals['debit'] = currency.round(vals['debit'])
#                 vals['credit'] = currency.round(vals['credit'])
#                 self.env['account.move.line'].create(vals)
#         return line_total
# 
#     @api.multi
#     def action_move_line_create(self):
#         '''
#         Confirm the vouchers given in ids and create the journal entries for each of them
#         '''
#         for voucher in self:
#             local_context = dict(self._context, force_company=voucher.journal_id.company_id.id)
#             if voucher.move_id:
#                 continue
#             company_currency = voucher.journal_id.company_id.currency_id.id
#             current_currency = voucher.currency_id.id or company_currency
#             # we select the context to use accordingly if it's a multicurrency case or not
#             # But for the operations made by _convert, we always need to give the date in the context
#             ctx = local_context.copy()
#             ctx['date'] = voucher.account_date
#             ctx['check_move_validity'] = False
#             # Create the account move record.
#             move = self.env['account.move'].create(voucher.account_move_get())
#             # Get the name of the account_move just created
#             # Create the first line of the voucher
#             move_line = self.env['account.move.line'].with_context(ctx).create(voucher.with_context(ctx).first_move_line_get(move.id, company_currency, current_currency))
#             line_total = move_line.debit - move_line.credit
#             if voucher.voucher_type == 'sale':
#                 line_total = line_total - voucher._convert(voucher.tax_amount)
#             elif voucher.voucher_type == 'purchase':
#                 line_total = line_total + voucher._convert(voucher.tax_amount)
#             # Create one move line per voucher line where amount is not 0.0
#             line_total = voucher.with_context(ctx).voucher_move_line_create(line_total, move.id, company_currency, current_currency)
# 
#             # Create a payment to allow the reconciliation when pay_now = 'pay_now'.
#             if voucher.pay_now == 'pay_now':
#                 payment_id = (self.env['account.payment']
#                     .with_context(force_counterpart_account=voucher.account_id.id)
#                     .create(voucher.voucher_pay_now_payment_create()))
#                 payment_id.post()
# 
#                 # Reconcile the receipt with the payment
#                 lines_to_reconcile = (payment_id.move_line_ids + move.line_ids).filtered(lambda l: l.account_id == voucher.account_id)
#                 lines_to_reconcile.reconcile()
# 
#             # Add tax correction to move line if any tax correction specified
#             if voucher.tax_correction != 0.0:
#                 tax_move_line = self.env['account.move.line'].search([('move_id', '=', move.id), ('tax_line_id', '!=', False)], limit=1)
#                 if len(tax_move_line):
#                     tax_move_line.write({'debit': tax_move_line.debit + voucher.tax_correction if tax_move_line.debit > 0 else 0,
#                         'credit': tax_move_line.credit + voucher.tax_correction if tax_move_line.credit > 0 else 0})
# 
#             # We post the voucher.
#             voucher.write({
#                 'move_id': move.id,
#                 'state': 'posted',
#                 'number': move.name
#             })
#             move.post()
#         return True

#     def _track_subtype(self, init_values):
#         self.ensure_one()
#         if 'state' in init_values:
#             return 'aos_account_voucher.mt_voucher_state_change'
#         return super(AccountVoucher, self)._track_subtype(init_values)
    
    
#     def _track_subtype(self, init_values):
#         # OVERRIDE to add custom subtype depending of the state.
#         self.ensure_one()
# 
#         if not self.is_invoice(include_receipts=True):
#             return super(AccountMove, self)._track_subtype(init_values)
# 
#         if 'payment_state' in init_values and self.payment_state == 'paid':
#             return self.env.ref('account.mt_invoice_paid')
#         elif 'state' in init_values and self.state == 'posted' and self.is_sale_document(include_receipts=True):
#             return self.env.ref('account.mt_invoice_validated')
#         return super(AccountMove, self)._track_subtype(init_values)


class AccountVoucherLine(models.Model):
    _name = 'account.voucher.line'
    _description = 'Accounting Voucher Line'

    def _get_default_uom_id(self):
        return self.env['uom.uom'].search([], limit=1, order='id').id
    
    name = fields.Text(string='Description', required=True)
    sequence = fields.Integer(default=10,
        help="Gives the sequence of this line when displaying the voucher.")
    voucher_id = fields.Many2one('account.voucher', 'Voucher', required=1, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product',
        ondelete='set null', index=True)
    uom_id = fields.Many2one('uom.uom', default=_get_default_uom_id, string='Unit of Measure', required=True)
    account_id = fields.Many2one('account.account', string='Account',
        required=True,
        help="The income or expense account related to the selected product.")
    # account_id = fields.Many2one('account.account', string='Account',
    #     required=True, compute='_compute_account_id', readonly=False,
    #     help="The income or expense account related to the selected product.")
    price_unit = fields.Float(string='Unit Price', required=True, digits=dp.get_precision('Product Price'), oldname='amount')
    price_subtotal = fields.Monetary(string='Amount',
        store=True, readonly=True, compute='_compute_subtotal')
    quantity = fields.Float(digits=dp.get_precision('Product Unit of Measure'),
        required=True, default=1)
    account_analytic_id = fields.Many2one('account.analytic.account', 'Analytic Account')
    analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic Tags')
    company_id = fields.Many2one('res.company', related='voucher_id.company_id', string='Company', store=True, readonly=True)
    tax_ids = fields.Many2many('account.tax', string='Tax', help="Only for tax excluded from price")
    currency_id = fields.Many2one('res.currency', related='voucher_id.currency_id', readonly=False)
    company_currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id, string='Company Currency', readonly=True)
    expense_budget = fields.Monetary(string='Expense Budget', readonly=True, compute='_get_expense_budget_id')
    planned_budget = fields.Monetary(string='Planned Budget', readonly=True, compute='_get_expense_budget_id')
    used_budget = fields.Monetary(string='Used Budget', readonly=True, compute='_get_expense_budget_id')
    budgetary_position_id = fields.Many2one('account.budget.post', string='Budgetary Position')
    crossovered_budget_line_id = fields.Many2one('crossovered.budget.lines', string='Budget Line')
    crossovered_budget_id = fields.Many2one('crossovered.budget', related='crossovered_budget_line_id.crossovered_budget_id')
    account_date = fields.Date(related='voucher_id.account_date')
    state = fields.Selection(related='voucher_id.state')
    price_untaxed = fields.Float(string='Untaxed Amount', store=True, readonly=True, compute='_compute_subtotal')


    # @api.onchange('voucher_id')
    # def _onchange_partner_id(self):
    #     for line in self:
    #         if line.voucher_id.partner_id:
    #             if line.voucher_id.voucher_type == 'sale':
    #                 excluded_user_types = self.env['account.account.type'].search([('name', 'in', ['Expenses', 'Other Expense'])])
    #                 excluded_user_types_ids = excluded_user_types.ids
    #                 return {'domain': {'account_id': [('user_type_id.name', 'not in', excluded_user_types_ids)]}}
    #             elif line.voucher_id.voucher_type == 'purchase':
    #                 excluded_user_types = self.env['account.account.type'].search([('name', 'in', ['Income', 'Other Income'])])
    #                 excluded_user_types_ids = excluded_user_types.ids
    #                 return {'domain': {'account_id': [('user_type_id.name', 'not in', excluded_user_types_ids)]}}

    # @api.depends('voucher_id.partner_id', 'voucher_id.voucher_type')
    # def _compute_account_id(self):
    #     if self.voucher_id.voucher_type == 'sale':
    #         return {'domain': {'account_id': [('user_type_id.name', 'in', ['Income', 'Other Income'])]}}
    #     elif self.voucher_id.voucher_type == 'purchase':
    #         return {'domain': {'account_id': [('user_type_id.name', 'in', ['Expenses'])]}}
            

  
    def _convert_amount_budget(self, currency_id, amount):
        return self.voucher_id.company_id.currency_id._convert(amount, currency_id, self.voucher_id.company_id, self.voucher_id.account_date)

    @api.depends('product_id', 'account_id', 'analytic_tag_ids', 'currency_id', 'voucher_id.account_date')
    def _get_expense_budget_id(self):
        for line in self:
            if line.voucher_id.voucher_type == 'purchase':
                expense_budget = 0.0
                line.expense_budget = expense_budget
                # account_domain = []
                crossovered_budget_lines = self.env['crossovered.budget.lines'].search([
                    ('company_id', '=', line.company_id.id),
                    ('account_tag_ids', 'in', line.analytic_tag_ids.ids),
                    ('date_from', '<=', line.voucher_id.account_date),
                    ('date_to', '>=', line.voucher_id.account_date),
                    ('crossovered_budget_id.state', '=', 'validate'),
                    ])
                # if line.voucher_id.voucher_type == 'sale':
                #     excluded_user_types = self.env['account.account.type'].search([('name', 'in', ['Expenses', 'Other Expense'])])
                #     excluded_user_types_ids = excluded_user_types.ids
                #     account_domain.append(('user_type_id', 'not in', excluded_user_types_ids))
                # elif line.voucher_id.voucher_type == 'purchase':
                #     excluded_user_types = self.env['account.account.type'].search([('name', 'in', ['Income', 'Other Income'])])
                #     excluded_user_types_ids = excluded_user_types.ids
                #     account_domain.append(('user_type_id', 'not in', excluded_user_types_ids))
                for budget_line in crossovered_budget_lines:
                    line.planned_budget = 0
                    line.used_budget = 0
                    if line.account_id.id in budget_line.general_budget_id.account_ids.ids:
                        if budget_line.remaining_amount is not None:
                            line.budgetary_position_id = budget_line.general_budget_id.id
                            expense_budget_amount = budget_line.budget_amount - (budget_line.child_purchase_amount + budget_line.reserve_amount_2 + budget_line.practical_budget_amount)
                            line.expense_budget = line._convert_amount_budget(line.currency_id, expense_budget_amount)
                            line.planned_budget = line._convert_amount_budget(line.currency_id, budget_line.budget_amount)
                            line.used_budget = line._convert_amount_budget(line.currency_id, budget_line.practical_amount)
                            line.crossovered_budget_line_id = budget_line.id
                            break

                if not crossovered_budget_lines:
                    line.budgetary_position_id = False
                    line.expense_budget = 0.0
                    line.planned_budget = 0.0
                    line.used_budget = 0.0
            else:
                line.budgetary_position_id = False
                line.expense_budget = 0.0
                line.planned_budget = 0.0
                line.used_budget = 0.0
            # total_remaining_amount = sum(remaining_amounts)
            # line.expense_budget_id = total_remaining_amount

            # return {'domain': {'account_id': account_domain}}

    @api.onchange('analytic_tag_ids')
    def _onchange_analytic_tag_ids(self):
        for line in self:
            if line.analytic_tag_ids:
                if self.voucher_id.voucher_type == 'sale':
                    excluded_user_types = self.env['account.account.type'].search([('name', 'in', ['Expenses', 'Other Expense'])])
                    excluded_user_types_ids = excluded_user_types.ids
                    return {'domain': {'account_id': [('user_type_id', 'not in', excluded_user_types_ids)]}}
                elif self.voucher_id.voucher_type == 'purchase':
                    excluded_user_types = self.env['account.account.type'].search([('name', 'in', ['Income', 'Other Income'])])
                    excluded_user_types_ids = excluded_user_types.ids
                    return {'domain': {'account_id': [('user_type_id', 'not in', excluded_user_types_ids)]}}
                

    def _valid_field_parameter(self, field, name):
        return name == "oldname" or name == "tracking" or super()._valid_field_parameter(field, name)

    @api.depends('price_unit', 'tax_ids', 'quantity', 'product_id', 'voucher_id.currency_id')
    def _compute_subtotal(self):
        """
        Compute the amounts of the SO line.
        """
        for line in self:
            #price_subtotal = line.quantity * line.price_unit
            taxes = line.tax_ids.compute_all(line.price_unit, line.voucher_id.currency_id, line.quantity, product=line.product_id, partner=line.voucher_id.partner_id)
            line.update({
                'price_subtotal': taxes['total_excluded'],
                'price_untaxed': taxes['total_excluded'],
            })
            
    @api.onchange('product_id', 'voucher_id', 'price_unit', 'company_id')
    def _onchange_line_details(self):
        if not self.voucher_id or not self.product_id:# or not self.voucher_id.partner_id:
            return
        onchange_res = self.product_id_change(
            self.product_id.id,
            self.voucher_id.partner_id.id,
            self.price_unit,
            self.company_id.id,
            self.voucher_id.currency_id.id,
            self.voucher_id.voucher_type)
        for fname, fvalue in onchange_res['value'].items():
            setattr(self, fname, fvalue)

    def _get_account(self, product, fpos, type):
        accounts = product.product_tmpl_id.get_product_accounts(fpos)
        if type == 'sale':
            return accounts['income']
        return accounts['expense']

    def product_id_change(self, product_id, partner_id=False, price_unit=False, company_id=None, currency_id=None, type=None):
        # TDE note: mix of old and new onchange badly written in 9, multi but does not use record set
        context = self._context
        company_id = company_id if company_id is not None else context.get('company_id', False)
        company = self.env['res.company'].browse(company_id)
        currency = self.env['res.currency'].browse(currency_id)
        #if not partner_id:
        #    raise UserError(_("You must first select a partner."))
        part = self.env['res.partner'].browse(partner_id)
        if not part:
            part = company.partner_id
        if part.lang:
            self = self.with_context(lang=part.lang)

        product = self.env['product.product'].browse(product_id)
        fpos = part.property_account_position_id
        account = self._get_account(product, fpos, type)
        values = {
            'name': product.partner_ref,
            'account_id': account.id,
        }

        if type == 'purchase':
            values['price_unit'] = price_unit or product.standard_price
            taxes = product.supplier_taxes_id or account.tax_ids
            if product.description_purchase:
                values['name'] += '\n' + product.description_purchase
        else:
            values['price_unit'] = price_unit or product.lst_price
            taxes = product.taxes_id or account.tax_ids
            if product.description_sale:
                values['name'] += '\n' + product.description_sale

        values['tax_ids'] = taxes.ids
        values['uom_id'] = product.uom_id.id
        if company and currency:
            if company.currency_id != currency:
                if type == 'purchase':
                    values['price_unit'] = price_unit or product.standard_price
                values['price_unit'] = values['price_unit'] * currency.rate

        return {'value': values, 'domain': {}}
    
class AccountPayment(models.Model):
    _inherit = 'account.payment'

    # Allows to force the destination account
    # for receivable/payable
    #
    # @override
    def _get_counterpart_move_line_vals(self, invoice=False):
        values = super(AccountPayment, self)._get_counterpart_move_line_vals(invoice)

        if self._context.get('force_counterpart_account'):
            values['account_id'] = self._context['force_counterpart_account']

        return values
