from odoo import tools, models, fields, api, _
from datetime import date, datetime, timedelta
import pytz
from pytz import timezone, UTC
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from odoo.exceptions import UserError
from lxml import etree
import logging
import requests
from ...equip3_general_features.models.email_wa_parameter import EmailParam,waParam

_logger = logging.getLogger(__name__)
headers = {'content-type': 'application/json'}

class AccountInternalTransfer(models.Model):
    _name = "account.internal.transfer"
    _description = "Account Internal Transfer"
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

    branch_id = fields.Many2one('res.branch', check_company=True, domain=_domain_branch, default = _default_branch, readonly=False, required=True)
    name = fields.Char(readonly=True, )
    request_partner_id = fields.Many2one('res.partner', string="Requested Partner")
    bank_from_journal_id = fields.Many2one('account.journal', domain="[('type', 'in', ('bank', 'cash'))]",
                                           string="Bank From", tracking=True)
    bank_to_journal_id = fields.Many2one('account.journal', domain="[('type', 'in', ('bank', 'cash'))]",
                                         string="Bank To", tracking=True)
    transfer_in_transit = fields.Boolean(string='Transfer in Transit', tracking=True)
    account_in_transit = fields.Many2one('account.account', string="Transit Account", tracking=True)
    transfer_desc = fields.Text(string="Description", tracking=True)
    transfer_amount = fields.Monetary(string="Amount", currency_field='currency_id', tracking=True)
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True, tracking=True)
    transfer_date = fields.Date(string="Transfer Date", tracking=True)
    create_date = fields.Datetime('Create Date', tracking=True, readonly=True)
    create_uid = fields.Many2one('res.users', 'Created by', tracking=True, readonly=True)
    company_id = fields.Many2one('res.company', string='Company', tracking=True,
                                 default=lambda self: self.env.company.id)
    # branch_id = fields.Many2one('res.branch', string='Branch', tracking=True,
    #                             default=lambda self: self.env.user.branch_id.id)
    
    state = fields.Selection(selection=[
        ('draft', 'Draft'),
        ('to_approve', 'Waiting For Approval'),
        ('approved', 'Approved'),
        ('in_progress', 'In Progress'),
        ('done', 'Completed'),
        ('rejected', 'Rejected')
    ], string='State', default='draft', tracking=True)
    filter_branch_ids = fields.Many2many('res.branch', string="Branch", compute='_compute_branch_ids')

    administration = fields.Boolean(string='Administration', default=False, tracking=True)
    # show when administration = true – mandatory
    administration_account = fields.Many2one('account.account', string="Administration Account", tracking=True)
    administration_fee = fields.Monetary(string="Amount", currency_field='currency_id', tracking=True)
    has_reconciled_entries = fields.Boolean(string='reconciled Entries', default=False, tracking=True)
    approval_matrix_id = fields.Many2one('approval.matrix.accounting', string="Approval Matrix",
                                         compute='_get_approval_matrix')
    is_internal_approval_matrix = fields.Boolean(string="Is Internal Approval Matrix",
                                                 compute='_get_approve_button_from_config')
    approved_matrix_ids = fields.One2many('approval.matrix.accounting.lines', 'acc_internal_transfer_id',
                                          string="Approved Matrix")
    approval_matrix_line_id = fields.Many2one('approval.matrix.accounting.lines', string='Approval Matrix Line',
                                              compute='_get_approve_button', store=False)
    is_approve_button = fields.Boolean(string='Is Approve Button', compute='_get_approve_button', store=False)
    state1 = fields.Selection(related="state", tracking=False)
    state2 = fields.Selection(related="state", tracking=False)
    analytic_group_ids = fields.Many2many('account.analytic.tag', domain="[('company_id', '=', company_id)]",
                                          string="Analytic Group",
                                          default=lambda self: self.env.user.analytic_tag_ids.ids)

    apply_manual_currency_exchange = fields.Boolean(string="Apply Manual Currency Exchange")
    manual_currency_exchange_rate = fields.Float(string="Manual Currency Exchange Rate", digits=(12,12))
    manual_currency_exchange_inverse_rate = fields.Float(string="Inverse Rate", digits=(12,12))


    @api.onchange('branch_id')
    def _depends_analytic_group_ids(self):
        for rec in self:
            rec.analytic_group_ids =  rec.branch_id.analytic_tag_ids

    def unlink(self):
        for record in self:
            if record.state not in ('draft', 'rejected'):
                raise UserError(_('You can not delete this record because the state is not draft or rejected'))
        return super(AccountInternalTransfer, self).unlink()    

    @api.model
    def create(self, vals):
        if 'company_id' in vals:
            self = self.with_company(vals['company_id'])
        if vals.get('name', _('New')) == _('New'):
            seq_date = None
            if 'transfer_date' in vals:
                seq_date = fields.Datetime.context_timestamp(self, fields.Datetime.to_datetime(vals['transfer_date']))
            vals['name'] = self.env['ir.sequence'].next_by_code('account.internal.transfer',
                                                                sequence_date=seq_date) or _('New')
        result = super(AccountInternalTransfer, self).create(vals)
        return result

    @api.onchange('bank_to_journal_id')
    def currency(self):
        self._get_approve_button_from_config()
        for rec in self:
            if rec.bank_to_journal_id:
                rec.currency_id = rec.bank_to_journal_id.currency_id

    @api.onchange('branch_id')
    def onchange_branch_id(self):
        self._compute_branch_ids()

    def _compute_branch_ids(self):
        user = self.env.user 
        branch_ids = user.branch_ids + user.branch_id
        for rec in self:
            rec.filter_branch_ids = [(6, 0, branch_ids.ids)]

    def action_validate(self):
        # res =super(AccountInternalTransfer, self).action_validate()
        for record in self:
            self.warning_message(abs(record.transfer_amount))
            ref = ''
            name = ''
            if record.type_curr == 'bank_cash':
                ref = 'Internal Transfer' + ' ' + (record.transfer_desc or '')
                name = 'Internal Transfer' +' ' + (record.name or '')
            elif record.type_curr == 'purchase_currency':
                ref = 'Purchase Currency' + ' ' + (record.transfer_desc or '')
                name = 'Purchase Currency' +' ' + (record.name or '')

            counterpart_transfer_amount = abs(record.transfer_amount)
            counterpart_administration_fee = abs(record.administration_fee)
            counterpart_amount = counterpart_transfer_amount + counterpart_administration_fee
            company_currency = record.company_id.currency_id

            # Manage currency.
            if record.currency_id == company_currency:
                # Single-currency.
                balance_transfer_amount = counterpart_transfer_amount
                balance_administration_fee = counterpart_administration_fee
                balance = counterpart_amount
                counterpart_transfer_amount = 0.0
                counterpart_administration_fee = 0.0
                counterpart_amount = 0.0
                currency_id = False
            else:
                # Multi-currencies.
                if record.apply_manual_currency_exchange == True:
                    balance_transfer_amount = counterpart_transfer_amount/record.manual_currency_exchange_rate
                    balance_administration_fee = counterpart_administration_fee/record.manual_currency_exchange_rate
                    balance = balance_transfer_amount + balance_administration_fee
                else:
                    balance_transfer_amount = record.currency_id._convert(counterpart_transfer_amount, company_currency, record.company_id, record.transfer_date)
                    balance_administration_fee = record.currency_id._convert(counterpart_administration_fee, company_currency, record.company_id, record.transfer_date)
                    balance = record.currency_id._convert(counterpart_amount, company_currency, record.company_id, record.transfer_date)

                currency_id = record.currency_id.id
            
            if record.transfer_in_transit == True and record.administration == True:                
                credit_vals = {
                        'name': name,
                        'amount_currency': -counterpart_amount,
                        'currency_id': currency_id,
                        'debit': 0.0,
                        'credit': abs(balance),
                        'date_maturity': record.transfer_date,
                        'account_id': record.bank_from_journal_id.payment_credit_account_id.id,
                        'analytic_tag_ids': [(6, 0, record.analytic_group_ids.ids)],
                    }

                debit_vals1 = {
                        'name': name,
                        'amount_currency': counterpart_transfer_amount,
                        'currency_id': currency_id,
                        'debit': abs(balance_transfer_amount),
                        'credit': 0.0,
                        'date_maturity': record.transfer_date,
                        'account_id': record.account_in_transit.id,
                        'analytic_tag_ids': [(6, 0, record.analytic_group_ids.ids)],
                    }

                debit_vals2 = {
                        'name': name,
                        'amount_currency': counterpart_administration_fee,
                        'currency_id': currency_id,
                        'debit': abs(balance_administration_fee),
                        'credit': 0.0,
                        'date_maturity': record.transfer_date,
                        'account_id': record.administration_account.id,
                        'analytic_tag_ids': [(6, 0, record.analytic_group_ids.ids)],
                    }
                vals = {
                    'ref': ref,
                    'date': record.transfer_date,
                    'internal_tf_id': record.id,
                    'journal_id': record.bank_from_journal_id.id,
                    'branch_id': record.branch_id.id,
                    'analytic_group_ids': [(6, 0, record.analytic_group_ids.ids)],
                    'line_ids': [(0, 0, credit_vals),(0, 0, debit_vals1),(0, 0, debit_vals2)]
                }
                
                move_id = self.env['account.move'].create(vals)
                move_id.post()
                record.write({'state': 'in_progress'})

            elif record.transfer_in_transit == True and record.administration == False:
                credit_vals = {
                        'name': name,
                        'amount_currency': -counterpart_transfer_amount,
                        'currency_id': currency_id,
                        'debit': 0.0,
                        'credit': abs(balance_transfer_amount),
                        'date_maturity': record.transfer_date,
                        'account_id': record.bank_from_journal_id.payment_credit_account_id.id,
                        'analytic_tag_ids': [(6, 0, record.analytic_group_ids.ids)],
                    }

                debit_vals1 = {
                        'name': name,
                        'amount_currency': counterpart_transfer_amount,
                        'currency_id': currency_id,
                        'debit': abs(balance_transfer_amount),
                        'credit': 0.0,
                        'date_maturity': record.transfer_date,
                        'account_id': record.account_in_transit.id,
                        'analytic_tag_ids': [(6, 0, record.analytic_group_ids.ids)],
                    }
                vals = {
                    'ref': ref,
                    'date': record.transfer_date,
                    'internal_tf_id': record.id,
                    'journal_id': record.bank_from_journal_id.id,
                    'branch_id': record.branch_id.id,
                    'analytic_group_ids': [(6, 0, record.analytic_group_ids.ids)],
                    'line_ids': [(0, 0, credit_vals),(0, 0, debit_vals1)]
                }

                move_id = self.env['account.move'].create(vals)
                move_id.post()
                record.write({'state': 'in_progress'})

            elif record.transfer_in_transit == False and record.administration == True:
                credit_vals = {
                        'name': name,
                        'amount_currency': -counterpart_amount,
                        'currency_id': currency_id,
                        'debit': 0.0,
                        'credit': abs(balance),
                        'date_maturity': record.transfer_date,
                        'account_id': record.bank_from_journal_id.payment_credit_account_id.id,
                        'analytic_tag_ids': [(6, 0, record.analytic_group_ids.ids)],
                    }

                debit_vals1 = {
                        'name': name,
                        'amount_currency': counterpart_transfer_amount,
                        'currency_id': currency_id,
                        'debit': abs(balance_transfer_amount),
                        'credit': 0.0,
                        'date_maturity': record.transfer_date,
                        'account_id': record.bank_to_journal_id.payment_debit_account_id.id,
                        'analytic_tag_ids': [(6, 0, record.analytic_group_ids.ids)],
                    }

                debit_vals2 = {
                        'name': name,
                        'amount_currency': counterpart_administration_fee,
                        'currency_id': currency_id,
                        'debit': abs(balance_administration_fee),
                        'credit': 0.0,
                        'date_maturity': record.transfer_date,
                        'account_id': record.administration_account.id,
                        'analytic_tag_ids': [(6, 0, record.analytic_group_ids.ids)],
                    }
                vals = {
                    'ref': ref,
                    'date': record.transfer_date,
                    'internal_tf_id': record.id,
                    'journal_id': record.bank_from_journal_id.id,
                    'branch_id': record.branch_id.id,
                    'analytic_group_ids': [(6, 0, record.analytic_group_ids.ids)],
                    'line_ids': [(0, 0, credit_vals),(0, 0, debit_vals1),(0, 0, debit_vals2)]
                }

                move_id = self.env['account.move'].create(vals)
                move_id.post()
                record.write({'state': 'done'})

            else:
                credit_vals = {
                        'name': name,
                        'amount_currency': -counterpart_transfer_amount,
                        'currency_id': currency_id,
                        'debit': 0.0,
                        'credit': abs(balance_transfer_amount),
                        'date_maturity': record.transfer_date,
                        'account_id': record.bank_from_journal_id.payment_credit_account_id.id,
                        'analytic_tag_ids': [(6, 0, record.analytic_group_ids.ids)],
                    }
                debit_vals = {
                        'name': name,
                        'amount_currency': counterpart_transfer_amount,
                        'currency_id': currency_id,
                        'debit': abs(balance_transfer_amount),
                        'credit': 0.0,
                        'date_maturity': record.transfer_date,
                        'account_id': record.bank_to_journal_id.payment_debit_account_id.id,
                        'analytic_tag_ids': [(6, 0, record.analytic_group_ids.ids)],
                    }
                vals = {
                    'ref': ref,
                    'date': record.transfer_date,
                    'internal_tf_id': record.id,
                    'journal_id': record.bank_from_journal_id.id,
                    'branch_id': record.branch_id.id,
                    'analytic_group_ids': [(6, 0, record.analytic_group_ids.ids)],
                    'line_ids': [(0, 0, debit_vals), (0, 0, credit_vals)]
                }

                move_id = self.env['account.move'].create(vals)
                move_id.post()
                record.write({'state': 'done'})
        # return res


    def action_complete(self):
        for record in self:
            ref = 'Internal Transfer' + ' ' + (record.transfer_desc or '')
            name = 'Internal Transfer' + ' ' + (record.name or '')

            # Manage currency.
            counterpart_transfer_amount = abs(record.transfer_amount)
            company_currency = record.company_id.currency_id

            if record.currency_id == company_currency:
                # Single-currency.
                balance_transfer_amount = counterpart_transfer_amount
                counterpart_transfer_amount = 0.0
                currency_id = False
            else:
                # Multi-currencies.
                balance_transfer_amount = record.currency_id._convert(counterpart_transfer_amount, company_currency,
                                                                      record.company_id, record.transfer_date)
                currency_id = record.currency_id.id

            credit_vals = {
                'name': name,
                'amount_currency': -counterpart_transfer_amount,
                'currency_id': currency_id,
                'debit': 0.0,
                'credit': abs(balance_transfer_amount),
                'date_maturity': date.today(),
                'account_id': record.account_in_transit.id,
                'analytic_tag_ids':  [(6, 0, record.analytic_group_ids.ids)] or False,
            }

            debit_vals = {
                'name': name,
                'amount_currency': counterpart_transfer_amount,
                'currency_id': currency_id,
                'debit': abs(balance_transfer_amount),
                'credit': 0.0,
                'date_maturity': date.today(),
                'account_id': record.bank_to_journal_id.payment_debit_account_id.id,
                'analytic_tag_ids': [(6, 0, record.analytic_group_ids.ids)] or False,
            }
            vals = {
                'ref': ref,
                'date': date.today(),
                'journal_id': record.bank_to_journal_id.id,
                'branch_id': record.branch_id.id,
                'analytic_group_ids': [(6, 0, record.analytic_group_ids.ids)],
                'line_ids': [(0, 0, credit_vals), (0, 0, debit_vals)]
            }

            move_id = self.env['account.move'].create(vals)
            move_id.post()
            record.write({'state': 'done', 'has_reconciled_entries': True})

            domain = [('account_id', '=', self.account_in_transit.id), ('reconciled', '=', False),
                      ('name', 'like', '%' + name)]
            bank_to_reconcile = move_id.line_ids.filtered_domain(domain)
            move_to_reconcile = self.env['account.move.line'].search(domain)
            for account in move_to_reconcile.account_id:
                (move_to_reconcile + bank_to_reconcile) \
                    .filtered_domain([('account_id', '=', self.account_in_transit.id), ('reconciled', '=', False),
                                      ('name', 'like', '%' + name)]) \
                    .reconcile()

    def _reconciled_lines(self):
        ids = []
        name = 'Internal Transfer' + ' ' + self.name
        domain = [('account_id', '=', self.account_in_transit.id), ('name', 'like', '%' + name),
                  ('reconciled', '=', True)]
        move_to_reconcile = self.env['account.move.line'].search(domain)
        for aml in move_to_reconcile:
            ids.extend(
                [r.debit_move_id.id for r in aml.matched_debit_ids] if aml.credit > 0 else [r.credit_move_id.id for r in
                                                                                            aml.matched_credit_ids])
            ids.append(aml.id)
        return ids

    def open_reconcile_view(self):
        action = self.env['ir.actions.act_window']._for_xml_id('account.action_account_moves_all_a')
        ids = self._reconciled_lines()
        action['domain'] = [('id', 'in', ids)]
        return action

    def open_internal_journal_view(self):
        action = self.env['ir.actions.act_window']._for_xml_id('account.action_account_moves_all_a')
        # action['domain'] = [('name', 'ilike', self.name)]
        move_ids = self.env['account.move'].search([('internal_tf_id', '=', self.id)])
        action['domain'] = [('move_id', 'in', move_ids.ids)]

        return action


    # def action_complete(self):
    #     for record in self:
    #         ref = 'Internal Transfer ' + (record.transfer_desc or '')
    #         name = 'Internal Transfer  ' + (record.name or '')
    #         debit_vals = {
    #                 'debit': abs(record.transfer_amount),
    #                 'date': date.today(),
    #                 'name': name,
    #                 'credit': 0.0,
    #                 'account_id': record.bank_to_journal_id.payment_debit_account_id.id,
    #             }
    #         credit_vals = {
    #                 'debit': 0.0,
    #                 'date': date.today(),
    #                 'name': name,
    #                 'credit': abs(record.transfer_amount),
    #                 'account_id': record.account_in_transit.id if record.transfer_in_transit else record.bank_from_journal_id.payment_credit_account_id.id,
    #             }
    #         vals = {
    #             'ref': ref,
    #             'date': date.today(),
    #             'journal_id': record.bank_to_journal_id.id,
    #             'line_ids': [(0, 0, debit_vals), (0, 0, credit_vals)]
    #         }
    #         move_id = self.env['account.move'].create(vals)
    #         move_id.post()
    #         record.write({'state': 'done'})

    def action_request_for_approval(self):
        for record in self:
            action_id = self.env.ref('equip3_accounting_operation.action_account_internal_transfer')
            template_id = self.env.ref('equip3_accounting_operation.email_template_internal_cb_approval_matrix')
            # wa_template_id = self.env.ref('equip3_accounting_operation.wa_template_req_internal_transfer_wa')
            wa_template_id = self.env.ref('equip3_accounting_operation.wa_template_request_for_approval_internal_transfer')
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/web#id=' + str(record.id) + '&action='+ str(action_id.id) + '&view_type=form&model=account.internal.transfer'
            currency = ''
            if record.company_id.currency_id.position == 'before':
                currency = record.company_id.currency_id.symbol + str(record.transfer_amount)
            else:
                currency = str(record.transfer_amount) + ' ' + record.company_id.currency_id.symbol
            record.request_partner_id = self.env.user.partner_id.id
            if record.approved_matrix_ids and len(record.approved_matrix_ids[0].user_ids) > 1:
                for approved_matrix_id in record.approved_matrix_ids[0].user_ids:
                    approver = approved_matrix_id
                    ctx = {
                        'email_from' : self.env.user.company_id.email,
                        'email_to' : approver.partner_id.email,
                        'approver_name' : approver.name,
                        'date': date.today(),
                        'submitter' : self.env.user.name,
                        'url' : url,
                        "due_date": record.transfer_date,
                        "date_invoice": record.create_date,
                        "currency": currency,
                    }
                    template_id.with_context(ctx).send_mail(record.id, True)
                    record._send_whatsapp_message(wa_template_id, approver, currency, url)
            else:
                approver = record.approved_matrix_ids[0].user_ids[0]
                ctx = {
                    'email_from' : self.env.user.company_id.email,
                    'email_to' : approver.partner_id.email,
                    'approver_name' : approver.name,
                    'date': date.today(),
                    'submitter' : self.env.user.name,
                    'url' : url,
                    "due_date": record.transfer_date,
                    "date_invoice": record.create_date,
                    "currency": currency,
                }
                template_id.with_context(ctx).send_mail(record.id, True)
                record._send_whatsapp_message(wa_template_id, approver, currency, url)
            record.write({'state': 'to_approve'})

    def action_approve(self):
        for record in self:
            action_id = self.env.ref('equip3_accounting_operation.action_account_internal_transfer')
            template_id = self.env.ref('equip3_accounting_operation.email_template_internal_cb_approval_matrix')
            template_id_submitter = self.env.ref('equip3_accounting_operation.email_template_internal_cb_submitter_approval_matrix')
            # wa_template_id = self.env.ref('equip3_accounting_operation.wa_template_req_internal_transfer_wa')
            wa_template_id = self.env.ref('equip3_accounting_operation.wa_template_request_for_approval_internal_transfer')
            # wa_template_submitted = self.env.ref('equip3_accounting_operation.wa_template_appr_internal_transfer_wa')
            wa_template_submitted = self.env.ref('equip3_accounting_operation.wa_template_approval_for_internal_transfer')
            user = self.env.user
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/web#id=' + str(record.id) + '&action='+ str(action_id.id) + '&view_type=form&model=account.internal.transfer'
            currency = ''
            if record.company_id.currency_id.position == 'before':
                currency = record.company_id.currency_id.symbol + str(record.transfer_amount)
            else:
                currency = str(record.transfer_amount) + ' ' + record.company_id.currency_id.symbol
            if record.is_approve_button and record.approval_matrix_line_id:
                approval_matrix_line_id = record.approval_matrix_line_id
                if user.id in approval_matrix_line_id.user_ids.ids and \
                        user.id not in approval_matrix_line_id.approved_users.ids:
                    name = approval_matrix_line_id.state_char or ''
                    utc_datetime = datetime.now()
                    local_timezone = pytz.timezone(self.env.user.tz)
                    local_datetime = utc_datetime.replace(tzinfo=pytz.utc)
                    local_datetime = local_datetime.astimezone(local_timezone).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                    if name != '':
                        name += "\n • %s: Approved - %s" % (self.env.user.name, local_datetime)
                    else:
                        name += "• %s: Approved - %s" % (self.env.user.name, local_datetime)

                    approval_matrix_line_id.write({
                        'last_approved': self.env.user.id, 'state_char': name,
                        'approved_users': [(4, user.id)]})
                    if approval_matrix_line_id.minimum_approver == len(approval_matrix_line_id.approved_users.ids):
                        approval_matrix_line_id.write({'time_stamp': datetime.now(), 'approved': True})
                        next_approval_matrix_line_id = sorted(record.approved_matrix_ids.filtered(lambda r: not r.approved), key=lambda r:r.sequence)
                        if next_approval_matrix_line_id and len(next_approval_matrix_line_id[0].user_ids) > 1:
                            for approving_matrix_line_user in next_approval_matrix_line_id[0].user_ids:
                                ctx = {
                                    'email_from' : self.env.user.company_id.email,
                                    'email_to' : approving_matrix_line_user.partner_id.email,
                                    'approver_name' : approving_matrix_line_user.name,
                                    'date': date.today(),
                                    'submitter' : self.env.user.name,
                                    'url' : url,
                                    "due_date": record.transfer_date,
                                    "date_invoice": record.create_date,
                                    "currency": currency,
                                }
                                template_id.sudo().with_context(ctx).send_mail(record.id, True)
                                record._send_whatsapp_message(wa_template_id, approving_matrix_line_user, currency, url)
                        else:
                            if next_approval_matrix_line_id and next_approval_matrix_line_id[0].user_ids:
                                ctx = {
                                    'email_from' : self.env.user.company_id.email,
                                    'email_to' : next_approval_matrix_line_id[0].user_ids[0].partner_id.email,
                                    'approver_name' : next_approval_matrix_line_id[0].user_ids[0].name,
                                    'date': date.today(),
                                    'submitter' : self.env.user.name,
                                    'url' : url,
                                    "due_date": record.transfer_date,
                                    "date_invoice":record.create_date,
                                    "currency": currency,
                                }
                                template_id.sudo().with_context(ctx).send_mail(record.id, True)
                                record._send_whatsapp_message(wa_template_id, approving_matrix_line_user, currency, url)
            if len(record.approved_matrix_ids) == len(record.approved_matrix_ids.filtered(lambda r:r.approved)):
                record.write({'state': 'approved'})
                record.action_validate()
                ctx = {
                    'email_from' : self.env.user.company_id.email,
                    'email_to' : record.request_partner_id.email,
                    'approver_name' : record.name,
                    'date': date.today(),
                    'create_date': record.create_date.date(),
                    'submitter' : self.env.user.name,
                    'url' : url,
                    "due_date": record.transfer_date,
                    "currency": currency,
                }
                template_id_submitter.sudo().with_context(ctx).send_mail(record.id, True)
                record._send_whatsapp_message(wa_template_submitted, record.request_partner_id.user_ids, currency, url)

    def action_reject(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Internal Cash / Bank Transfer Marix Reject ',
            'res_model': 'internal.matrix.reject',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
        }

    def _send_whatsapp_message(self, template_id, approver, currency=False, url=False, reason=False):
        for record in self:
            wa_sender = waParam()
            # string_test = str(tools.html2plaintext(template_id.body_html))
            string_test = str(template_id.message)
            if "${approver_name}" in string_test:
                string_test = string_test.replace("${approver_name}", approver.name)
            if "${submitter_name}" in string_test:
                string_test = string_test.replace("${submitter_name}", record.request_partner_id.name)
            if "${amount}" in string_test:
                string_test = string_test.replace("${amount}", str(record.amount))
            if "${currency}" in string_test:
                string_test = string_test.replace("${currency}", currency)
            if "${bank_from}" in string_test:
                string_test = string_test.replace("${bank_from}", record.bank_from_journal_id.name)
            if "${bank_to}" in string_test:
                string_test = string_test.replace("${bank_to}", record.bank_to_journal_id.name)
            if "${transfer_date}" in string_test:
                string_test = string_test.replace("${transfer_date}", fields.Datetime.from_string(
                    record.transfer_date).strftime('%d/%m/%Y'))
            if "${create_date}" in string_test:
                string_test = string_test.replace("${create_date}", fields.Datetime.from_string(
                    record.create_date).strftime('%d/%m/%Y'))
            if "${feedback}" in string_test:
                string_test = string_test.replace("${feedback}", reason)
            if "${br}" in string_test:
                string_test = string_test.replace("${br}", f"\n")
            if "${url}" in string_test:
                string_test = string_test.replace("${url}", url)
            phone_num = str(approver.phone or approver.mobile or approver.employee_phone)
            if "+" in phone_num:
                phone_num = phone_num.replace("+", "")
            wa_sender.set_wa_string(string_test, template_id._name, template_id=template_id)
            wa_sender.send_wa(phone_num)
            # param = {'body': 'test', 'text': string_test, 'phone': phone_num, 'previewBase64': '', 'title': ''}
            # domain = self.env['ir.config_parameter'].sudo().get_param('chat.api.url')
            # token = self.env['ir.config_parameter'].sudo().get_param('chat.api.token')
            # try:
            #     request_server = requests.post(f'{domain}/sendLink?token={token}', params=param, headers=headers, verify=True)
            # except ConnectionError:
            #     raise ValidationError("Not connect to API Chat Server. Limit reached or not active")

    @api.depends('transfer_amount', 'company_id', 'branch_id')
    def _get_approval_matrix(self):
        for record in self:
            matrix_id = False
            if record.type_curr == "bank_cash":
                matrix_id = self.env['approval.matrix.accounting'].search([
                    ('company_id', '=', record.company_id.id),
                    ('branch_id', '=', record.branch_id.id),
                    ('min_amount', '<=', record.transfer_amount),
                    ('max_amount', '>=', record.transfer_amount),
                    ('approval_matrix_type', '=', 'inter_bank_cash_approval_matrix')
                ], limit=1)
            record.approval_matrix_id = matrix_id
            record._compute_approving_matrix_lines()

    def _get_approve_button_from_config(self):
        for record in self:
            is_internal_approval_matrix = False
            if record.type_curr == 'bank_cash':
                is_internal_approval_matrix = self.env['ir.config_parameter'].sudo().get_param(
                    'is_internal_transfer_approval_matrix', False)
            record.is_internal_approval_matrix = is_internal_approval_matrix

    def _get_approve_button(self):
        for record in self:
            matrix_line = sorted(record.approved_matrix_ids.filtered(lambda r: not r.approved),
                                 key=lambda r: r.sequence)
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

    @api.onchange('approval_matrix_id')
    def _compute_approving_matrix_lines(self):
        data = [(5, 0, 0)]
        for record in self:
            if record.state == 'draft' and record.is_internal_approval_matrix:
                record.approved_matrix_ids = []
                counter = 1
                record.approved_matrix_ids = []
                for rec in record.approval_matrix_id:
                    for line in rec.approval_matrix_line_ids:
                        data.append((0, 0, {
                            'sequence': counter,
                            'user_ids': [(6, 0, line.user_ids.ids)],
                            'minimum_approver': line.minimum_approver,
                        }))
                        counter += 1
                record.approved_matrix_ids = data


class ApprovalMatrixAccountingLines(models.Model):
    _inherit = "approval.matrix.accounting.lines"

    acc_internal_transfer_id = fields.Many2one('account.internal.transfer', string='Account Internal Transfer')
