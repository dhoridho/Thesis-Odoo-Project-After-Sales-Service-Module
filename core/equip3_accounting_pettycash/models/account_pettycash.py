# -*- coding: utf-8 -*-

from odoo import models, fields, api, _, tools
from odoo.tools import float_compare
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, date, timedelta
from odoo.tools import date_utils
from dateutil.relativedelta import relativedelta

class AccountMove(models.Model):
    _inherit = 'account.move'

    pettycash_id = fields.Many2one('account.pettycash', string='pattycash')
    is_petty_cash_voucher = fields.Boolean(string='Is Petty Cash Voucher')    

    def write(self, vals):
        for move in self:
            if move.pettycash_id:
                pettycash_account_id = move.pettycash_id.journal.default_account_id.id
                for line in move.line_ids:
                    if line.account_id.id == pettycash_account_id and line.credit > 0:
                        if vals.get('amount_total_signed') and vals.get('amount_total_signed') > 0:
                            vals['amount_total_signed'] = -(vals['amount_total_signed'])
                        else:
                            if move.amount_total_signed > 0:
                                vals['amount_total_signed'] = -(move.amount_total_signed)
                            else:
                                vals['amount_total_signed'] = move.amount_total_signed

                if move.reversed_entry_id:
                    for line in move.reversed_entry_id.line_ids:
                        if line.account_id.id == pettycash_account_id and line.credit > 0:
                            if move.reversed_entry_id.amount_total_signed > 0:
                                move.reversed_entry_id.amount_total_signed = -(move.reversed_entry_id.amount_total_signed)

        res = super(AccountMove, self).write(vals)
        for move in self:
            if move.pettycash_id:
                move.pettycash_id.compute_amount()
        return res

class ProductTemplate(models.Model):
    _inherit = 'product.template' 
    
    use_on_petty_cash = fields.Boolean(string='Use on Petty Cash')

class AccountPettycash(models.Model):
    _name = 'account.pettycash'
    _description = "Account Petty Cash"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']

    DAYS_DATA = [('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5'), 
                    ('6', '6'), ('7', '7'), ('8', '8'), ('9', '9'), ('10', '10'), 
                    ('11', '11'), ('12', '12'), ('13', '13'), ('14', '14'), ('15', '15'), 
                    ('16', '16'), ('17', '17'), ('18', '18'), ('19', '19'), ('20', '20'), 
                    ('21', '21'), ('22', '22'), ('23', '23'), ('24', '24'), ('25', '25'), 
                    ('26', '26'), ('27', '27'), ('28', '28 (End of Month)'), ('29', '29 (End of Month)'), ('30', '30 (End of Month)'), 
                    ('31', '31 (End of Month)')
                ]
    WEEK_DATA = [('monday', 'Monday'), 
                    ('tuesday', 'Tuesday'),
                    ('wednesday', 'Wednesday'),
                    ('thursday', 'Thursday'),
                    ('friday', 'Friday'),
                    ('saturday', 'Saturday'),
                    ('sunday', 'Sunday')
                    ]


    @api.model
    def _default_branch(self):
        default_branch_id = self.env.context.get('default_branch_id',False)
        if default_branch_id:
            return default_branch_id
        return self.env.company_branches[0].id if len(self.env.company_branches) == 1 else self.env.user.branch_id.id


    @api.model
    def _domain_branch(self):
        return [('id', 'in', self.env.branches.ids), ('company_id','=', self.env.company.id)]

    @api.model
    def _domain_cash_journal(self):
        return [('type', 'in', ['bank','cash']), ('company_id','=', self.env.company.id)]

    branch_id = fields.Many2one('res.branch', check_company=True, domain=_domain_branch, default = _default_branch, tracking=True, readonly=False, required=True)
    replenish_interval = fields.Selection(string='Replenish Interval', selection=[('week', 'Weeks'), ('month', 'Months')], default="week")
    times = fields.Selection(string='Frequency', selection=[ ('1', 'Once a Month'),  ('2', 'Twice a Month')], default=False)
    replenish_date = fields.Selection(DAYS_DATA,string='Replenish Date')
    replenish_date_2 = fields.Selection(DAYS_DATA,string='Replenish Date 2')
    replenish_week = fields.Selection(WEEK_DATA,string='Replenish Week')
    replenish_intervals = fields.Integer()
    auto_replenish = fields.Boolean(string='Auto Replenishment')
    cash_journal = fields.Many2one('account.journal', domain=_domain_cash_journal, string='Cash Journal', required=True, tracking=True)
    number = fields.Char(string="Number", readonly=True, tracking=True)
    name = fields.Char(string="Name", readonly=True, required=True, tracking=True)
    custodian = fields.Many2one('res.users', string='Custodian', readonly=True, required=True, tracking=True)
    main_cash_account_id = fields.Many2one('account.account', domain="[('user_type_id.type', 'in', ['liquidity'])]", string='Cash Account', readonly=True)
    journal = fields.Many2one('account.journal',domain=_domain_cash_journal , string='Petty Cash Journal', readonly=True, required=True, tracking=True)
    amount = fields.Monetary(string="Fund Amount", required=True, tracking=True)
    balance = fields.Monetary(string="Balance", compute='compute_amount', tracking=True, store=True)
    virtual_balance = fields.Monetary(string="Virtual Balance", compute='compute_amount', tracking=True, store=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company.id, tracking=True, readonly=True)
    effective_date = fields.Date(string="Date", tracking=True)
    create_uid = fields.Many2one('res.users', string='Created by', readonly=True, tracking=True)
    create_date = fields.Datetime(string="Created Date", readonly=True, tracking=True)
    state = fields.Selection(selection=[
            ('draft', 'Draft'),
            ('open', 'Open'),
            ('closed', 'Closed')
        ], string='State', default='draft', tracking=True)
    move_id = fields.One2many('account.move', 'pettycash_id', string='Cash Activity', invisible=True, readonly=True)
    voucher_id = fields.One2many('account.pettycash.voucher.wizard', 'fund', string='Voucher', domain=[('state', '!=', 'posted'),('is_reconcile','=',False)])
    paid_voucher_ids = fields.One2many('account.pettycash.voucher.wizard', 'fund', string='Petty Cash Voucher', domain=[('state', 'in', ('approved', 'posted', 'cancelled', 'rejected'))])
    is_custodian_user = fields.Boolean(compute='_get_custodian_user', string='Custodian User')
    custodian_partner = fields.Many2one('res.partner', related='custodian.partner_id', readonly=True)
    is_replenished = fields.Boolean(compute='_get_replenish', string='Replenished')
    next_execute_date = fields.Date('Next Execute Date')
    expense_amount = fields.Monetary(string="Expenses", compute='compute_amount', store=True)
    analytic_group_ids = fields.Many2many('account.analytic.tag', string="Analytic Group")
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id, required=True)
    currency_rate = fields.Float(string='Currency Rate', default=1.0, required=True)
    apply_manual_currency_exchange = fields.Boolean(string="Apply Manual Currency Exchange")
    manual_currency_exchange_rate = fields.Float(string="Manual Currency Exchange Rate", digits=(12,12))
    manual_currency_exchange_inverse_rate = fields.Float(string="Inverse Rate", digits=(12,12))
    active_manual_currency_rate = fields.Boolean('active Manual Currency', default=False)
    account_date = fields.Date(string="Accounting Date", tracking=True)

    @api.onchange('currency_id')
    def onchange_currency_id(self):
        if self.currency_id:
            if self.company_id.currency_id != self.currency_id:
                if not self.account_date:
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

    def round(self, amount):
        self.ensure_one()
        return tools.float_round(amount, precision_rounding=self.currency_id.rounding)
    
    def _convert(self, amount, date=False):
        for rec in self:
            if rec.currency_id:
                if rec.currency_id != rec.company_id.currency_id:
                    if rec.apply_manual_currency_exchange == False:
                        # convert currency using last rate
                        currency_rate = self.env['res.currency.rate'].search([('currency_id', '=', rec.currency_id.id), ('name', '<=', date or rec.account_date)], limit=1)                    
                        if not currency_rate:
                            raise UserError(_('No currency rate found for the currency %s and the period %s.') % (rec.currency_id.name, date or rec.account_date))
                        res = amount / currency_rate.rate
                    else:
                        res = amount / rec.manual_currency_exchange_rate
                    return rec.round(res)
                return amount
            return amount


    def _get_replenish(self):
        for record in self:
            record.is_replenished = False
            if record.balance == record.amount:
                record.is_replenished = True

    def _get_custodian_user(self):
        for record in self:
            record.is_custodian_user = False
            if record.custodian == self.env.user:
                record.is_custodian_user = True
    
    def download_petty_vouchers(self):
        return self.env.ref('equip3_accounting_pettycash.action_report_petty_cash_vouchers').report_action(None)
    def download_petty_history(self):
        return self.env.ref('equip3_accounting_pettycash.action_report_petty_cash_history').report_action(None)
    def download_petty_activity(self):
        return self.env.ref('equip3_accounting_pettycash.action_report_petty_cash_activity').report_action(None)
    
    @api.depends('amount', 'voucher_id.total', 'move_id.amount_total_signed', 'voucher_id.state')
    def compute_amount(self):
        for rec in self:
            non_rejected = rec.voucher_id.filtered(lambda x: x.state == 'approved')
            total_move_id = rec.move_id.filtered(lambda x: x.state == 'posted')
            sum_move_id = 0
            sum_voucher = 0
            if non_rejected:
                sum_voucher = sum(non_rejected.mapped('total'))
            if total_move_id:
                for move in total_move_id:
                    balance_move = self.env.company.currency_id._convert(move.amount_total_signed, rec.currency_id, self.env.company, move.date)
                    sum_move_id += balance_move
            else:
                sum_move_id = rec.amount

            rec.expense_amount = rec.currency_id.round(sum_move_id)
            rec.balance = rec.currency_id.round(sum_move_id)
            rec.virtual_balance = rec.currency_id.round(sum_move_id - sum_voucher)

    def close_fund(self, date, receivable_account, manual_currency_exchange_inverse_rate=0):
        for fund in self:
            if fund.voucher_id and len(fund.voucher_id) > 0:
                raise ValidationError(_("Petty Cash fund (%s) has un-reconciled vouchers" % (fund.name)))
            desc = _("Close Petty Cash fund (%s)" % (fund.name))
            if fund.balance != 0.00:
                if fund.balance < 0.00:
                    balance = -(fund.balance)
                else:
                    balance = fund.balance

                if fund.currency_id != fund.company_id.currency_id:
                    if manual_currency_exchange_inverse_rate:
                        balance = balance * manual_currency_exchange_inverse_rate
                    else:
                        balance = fund._convert(balance, date)

                    # total_amount = 0
                    # loss_gain = 0
                    # move_ids = fund.move_id.filtered(lambda x: x.state == 'posted')
                    # if move_ids:
                    #     total_amount = sum(move_ids.mapped('amount_total_signed'))                    
                    # loss_gain = total_amount - balance                    
                    # if loss_gain != 0:
                    #     move_vals_exchange = self._prepare_move_line(loss_gain,receivable_account, date, fund)
                    #     AccountMove = self.env['account.move']
                    #     moves = AccountMove.create(move_vals_exchange)
                    #     moves.post()
                    #     if loss_gain < 0:
                    #         moves.amount_total_signed = -(moves.amount_total_signed)

                move = fund.create_receivable_journal_entry(fund, receivable_account.id, date, balance, desc)
                move.amount_total_signed = -(move.amount_total_signed)
                move.write({'pettycash_id': fund.id})
                fund.write({'amount': 0.0, 'balance': 0.0, 'state': 'closed'})
            else:
                fund.write({'amount': 0.0, 'balance': 0.0, 'state': 'closed'})

    def _prepare_move_line(self, loss_gain_amount, account_id, date, fund):
        all_move_vals = []
        journal_id = self.env.company.unrealized_exchange_journal_id
        line_vals_list = []
        line_vals_list.append((0,0,
                                    {                                        
                                        'partner_id': self.custodian.id,
                                        'name': '',
                                        'date_maturity': date,
                                        'debit': abs(-total_balance) if total_balance < 0 else 0.0,
                                        'credit': abs(total_balance) if total_balance > 0 else 0.0,
                                        'account_id': account_id.id,
                                    }))
        line_vals_list.append((0,0,
                                   {
                                        'partner_id': self.custodian.id,
                                        'name': '',
                                        'date_maturity': date,
                                        'debit': abs(total_balance) if total_balance > 0 else 0.0,
                                        'credit': abs(-total_balance) if total_balance < 0 else 0.0,
                                        'account_id': self.env.company.income_unrealized_exchange_account_id.id if loss_gain_amount > 0 else self.env.company.expense_unrealized_exchange_account_id.id,
                                    }))
        move_vals = {
                    'partner_id': self.custodian.id,
                    'ref': '',
                    'date': date,
                    'journal_id': journal_id.id,
                    'line_ids': line_vals_list,
                    'pettycash_id': fund.id,
                    }
        all_move_vals.append(move_vals)
        return all_move_vals

    @api.onchange('company_id')
    def _get_domain(self):
        return {'domain':{'branch_id':f"[('id','in',{self.env.branches.ids}),('company_id','=',{self.env.company.id})]"}}

    @api.onchange('branch_id')
    def _onchange_branch_id(self):
        selected_brach = self.branch_id
        if selected_brach:
            user_id = self.env['res.users'].browse(self.env.uid)
            allowed_branch = user_id.sudo().branch_ids
            if allowed_branch and selected_brach.id not in [ids.id for ids in allowed_branch] :
                raise UserError("Please select active branch only. Other may create the Multi branch issue. \n\ne.g: If you wish to add other branch then Switch branch from the header and set that.")

    @api.model
    def create(self, vals):
        if 'company_id' in vals:
            self = self.with_company(vals['company_id'])
        if vals.get('number', _('New')) == _('New'):
            seq_date = None
            if 'create_date' in vals:
                seq_date = fields.Datetime.context_timestamp(self, fields.Datetime.to_datetime(vals['create_date']))
            vals['number'] = self.env['ir.sequence'].next_by_code('account.pettycash.sequence', sequence_date=seq_date) or _('New')
        result = super(AccountPettycash, self).create(vals)
        return result
    
    @api.constrains('auto_replenish','replenish_interval', 'replenish_week')
    def _check_replenish_week(self):
        for move in self:
            if move.auto_replenish and move.replenish_interval == 'week':
                if not move.replenish_week:
                    raise ValidationError(_('Please set Replenish Week'))

    @api.constrains('auto_replenish','replenish_interval', 'times')
    def _check_replenish_times(self):
        for move in self:
            if move.auto_replenish and move.replenish_interval == 'month':
                if not move.times:
                    raise ValidationError(_('Please set The Frequency'))

    def validate(self):
        if self.amount <= 0:
            raise ValidationError(_('Petty cash fund must be greater than 0'))

        line_ids_det = []
        today_date = date.today()
        amount = self._convert(self.amount)
        line = {
                'date_maturity': today_date,
                'name': 'Petty Cash Plenishment : ' + (self.number),
                'account_id': self.journal.payment_debit_account_id.id,
                'debit': amount,
                'credit': 0.0,
                'analytic_tag_ids': self.analytic_group_ids
                }
        line_ids_det.append((0,0,line))
        line = {
                'date_maturity': today_date,
                'name': 'Petty Cash Plenishment : ' + (self.number),
                'account_id': self.cash_journal.payment_credit_account_id.id,
                'debit':  0.0,
                'credit': amount,
                'analytic_tag_ids': self.analytic_group_ids
                }
        line_ids_det.append((0,0,line))
        
        all_move_vals = {
                'pettycash_id' : self.id,
                'date': today_date,
                'journal_id': self.cash_journal.id,
                'branch_id': self.branch_id.id,
                'line_ids': line_ids_det
            }
                
        AccountMove = self.env['account.move']
        moves = AccountMove.create(all_move_vals)
        moves.post()
        self.update({'state' : 'open',
                    'balance' : self.amount,
                    'virtual_balance' : self.amount})

    @api.onchange("replenish_week","replenish_intervals")
    def onchange_next_execute(self):
        for rec in self:
            if rec.state != 'open':
                rec.next_execute_date = False

    def cron_auto_replenish(self):
        today_date = date.today()
        valid_date = int(today_date.strftime("%d"))
        current_month = date_utils.add(today_date, months=0)
        date_max = date_utils.end_of(current_month, "month")
        petty_cash = self.search([('auto_replenish', '=', True)])
        for pc in petty_cash:
            if pc.auto_replenish and pc.amount != pc.balance:
                if pc.replenish_interval == 'month':
                    if pc.replenish_date not in ('28', '29', '30', '31'):
                        if int(pc.replenish_date) == valid_date:
                            pc.sub_cron_auto_replenish_je(pc)
                    elif pc.replenish_date in ('28', '29', '30', '31'):
                        if today_date == date_max:
                            pc.sub_cron_auto_replenish_je(pc)
                    if pc.times == '2':
                        if pc.replenish_date_2 not in ('28', '29', '30', '31'):
                            if int(pc.replenish_date_2) == valid_date:
                                pc.sub_cron_auto_replenish_je(pc)
                        elif pc.replenish_date_2 in ('28', '29', '30', '31'):
                            if today_date == date_max:
                                pc.sub_cron_auto_replenish_je(pc)
                if pc.replenish_interval == 'week':
                    valid_week = today_date.strftime("%A")
                    valid_week_name = valid_week.upper()
                    rep_week = pc.replenish_week.upper()
                    if valid_week_name == rep_week:
                        if not pc.next_execute_date:
                            interval_week = date.today() + relativedelta(weeks=pc.replenish_intervals)
                            pc.sub_cron_auto_replenish_je(pc)
                            pc.write({'next_execute_date': interval_week})
                        elif pc.next_execute_date and pc.next_execute_date == today_date:
                            interval_week = date.today() + relativedelta(weeks=pc.replenish_intervals)
                            pc.sub_cron_auto_replenish_je(pc)
                            pc.write({'next_execute_date': interval_week})

    def sub_cron_auto_replenish_je(self, obj):
        today_date = date.today()
        date_data = []
        line_ids_det = []
        line = {
                'date_maturity': obj.create_date,
                'name': 'Petty Cash Plenishment : ' + (obj.number),
                'account_id': obj.journal.payment_debit_account_id.id,
                'debit': obj.amount - obj.balance,
                'credit': 0.0
                }
        line_ids_det.append((0,0,line))
        line = {
                'date_maturity': obj.create_date,
                'name': 'Petty Cash Plenishment : ' + (obj.number),
                'account_id': obj.cash_journal.payment_credit_account_id.id,
                'debit':  0.0,
                'credit': obj.amount - obj.balance
                }
        line_ids_det.append((0,0,line))
        all_move_vals = {
                'pettycash_id': obj.id,
                'date': obj.create_date,
                'journal_id': obj.cash_journal.id,
                'branch_id': self.branch_id.id,
                'line_ids': line_ids_det
            }
                
        AccountMove = self.env['account.move']
        moves = AccountMove.create(all_move_vals)
        moves.post()
        obj.update({'state': 'open',
                    'balance': obj.amount,
                    'virtual_balance': obj.amount})


    def cancel(self):
        self.update({'state' : 'draft'})

    def create_voucher(self):
        return {
            'name': _('Create Voucher'),
            'res_model': 'account.pettycash.voucher.wizard',
            'view_mode': 'form',
            'context': {
                'active_model': 'account.pettycash',
                'active_ids': self.id,
                'default_fund': self.id,
                'default_ba_ca_journal_id': self.journal.id
            },
            'target': 'new',
            'type': 'ir.actions.act_window',
        }

    @api.model
    def create_journal_entry_common(self, _type, fnd, account_id, date, amount, desc):
        AccountMove = self.env['account.move']
        # Set debit and credit accounts according to type of entry. Default
        # to payable.
        debit_account = fnd.journal.payment_debit_account_id.id
        credit_account = account_id
        if _type == 'receivable':
            debit_account = account_id
            credit_account = fnd.journal.payment_credit_account_id.id
        # First, create the move
        # move_vals = AccountMove.account_move_prepare(
        #     fnd.journal.id, date=date)
        move_vals = AccountMove.default_get(AccountMove._fields)
        if fnd.journal:
            move_vals.update({'journal_id': fnd.journal.id, 'date': date})
        move_vals.update({'narration': desc, 'branch_id': fnd.branch_id.id,
                          'currency_id': self.env.user.company_id.currency_id.id or self.env.user.currency_id.id or self.env.user.partner_id.currency_id.id,
                          'partner_id': fnd.custodian_partner.id})
        # Create the first line
        move_line1_vals = {
            'name': desc,
            'currency_id': self.env.user.company_id.currency_id.id or self.env.user.currency_id.id or self.env.user.partner_id.currency_id.id,
            'amount_currency': amount,
            'debit': amount,
            'credit': 0.0,
            'account_id': debit_account,
            'journal_id': fnd.journal.id,
            'partner_id': fnd.custodian_partner.id,
            'date': date,
        }
        # Create the second line
        move_line2_vals = {
            'name': desc,
            'currency_id': self.env.user.company_id.currency_id.id or self.env.user.currency_id.id or self.env.user.partner_id.currency_id.id,
            'amount_currency': -amount,
            'debit': 0.0,
            'credit': amount,
            'journal_id': fnd.journal.id,
            'account_id': credit_account,
            'partner_id': fnd.custodian_partner.id,
            'date': date,
        }
        # Update the journal entry and post
        move_vals.update({
            'line_ids': [(0, 0, move_line2_vals), (0, 0, move_line1_vals)]
        })
        move = AccountMove.create(move_vals)
        move.post()
        move.write({'pettycash_id': fnd.id})
        return move

    @api.model
    def create_payable_journal_entry(self, fnd, account_id, date, amount, desc):
        return self.create_journal_entry_common('payable', fnd, account_id, date, amount, desc)

    @api.model
    def create_receivable_journal_entry(self, fnd, account_id, date, amount, desc):
        return self.create_journal_entry_common('receivable', fnd, account_id, date, amount, desc)

    def change_fund_amount(self, new_amount):
        for fund in self:
            # If this is a decrease in funds and there are unreconciled
            # vouchers do not allow the user to proceed.
            diff = float_compare(new_amount, fund.amount, precision_digits=2)
            if diff == -1 and fund.voucher_id and len(fund.voucher_id) > 0:
                raise ValidationError(_("Petty Cash fund (%s) has unreconciled vouchers" % (fund.name)))
            fund.amount = new_amount

    def unlink(self):
        for pettycash in self:
            for move in pettycash.move_id:
                if move.state == 'posted':
                    raise UserError(_('You cannot delete a document that contains posted entries.'))
        return super(AccountPettycash, self).unlink()