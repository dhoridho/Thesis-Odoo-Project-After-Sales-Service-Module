
import time
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DSDF


class BankAccRecStatement(models.Model):
    _name = "bank.acc.rec.statement"
    _description = "Bank Account Statement Balance"

    def check_group(self):
        """Check group.

        Check if following security constraints are implemented for groups:
        Bank Statement Preparer - they can create, view and delete any of the
        Bank Statements provided the Bank Statement is not in the DONE state,
        or the Ready for Review state.
        Bank Statement Verifier - they can create, view, edit, and delete
        any of the Bank Statements information at any time.
        NOTE: DONE Bank Statements  are only allowed to be deleted by a Bank
        Statement Verifier.
        """
        user = self.env.user
        is_user = user.has_group('sg_bank_reconcile.group_bank_stmt_verifier')
        for statement in self:
            if statement.state != 'draft' and not is_user:
                raise UserError(_(
                    "User Error !\nOnly a member of Bank Statement "
                    "Verifier group may delete/edit bank statements when "
                    "not in draft state!"))

    def copy(self, default={}):
        """Override this method to set blank fields."""
        default.update({'name': ''})
        return super(BankAccRecStatement, self).copy(default=default)

    def write(self, vals):
        """Write.

        This method override to check whether current logged in user has a
        group to change state.
        """
        for rec in self:
            rec.check_group()
        return super(BankAccRecStatement, self).write(vals)

    def unlink(self):
        """Unlink.

        Reset the related account.move.line to be re-assigned later to
        statement.
        """
        self.check_group()
        for statement in self:
            if statement.state == 'done':
                raise UserError(_("You cannot delete an entry which has"
                                  " been 'Done' once."))
            statement_lines = statement.credit_move_line_ids + \
                statement.debit_move_line_ids
            statement_lines.unlink()
        return super(BankAccRecStatement, self).unlink()

    def check_difference_balance(self):
        """Check if difference balance is zero or not."""
        for statement in self:
            if statement.difference != 0.0:
                raise UserError(_(
                    "Prior to reconciling a statement, all "
                    "differences must be accounted for and the "
                    "Difference balance "
                    "must be zero.Please review and make necessary changes."))

    def action_cancel(self):
        """Cancel the the statement."""
        for rec in self:
            rec.write({'state': 'cancel'})

    def action_review(self):
        """Change the status of statement from 'draft' to 'to_be_reviewed'."""
        # If difference balance not zero prevent further processing
        for rec in self:
            rec.check_difference_balance()
            rec.write({'state': 'to_be_reviewed'})
        return True

    def action_process(self):
        """Action process.

        Set the account move lines as 'Cleared' and Assign 'Bank Acc Rec
        Statement ID' for the statement lines which are marked as 'Cleared'.
        """
        self.check_difference_balance()
        for statement in self:
            statement_lines = statement.credit_move_line_ids + \
                statement.debit_move_line_ids
            for statement_line in statement_lines:
                if statement_line.move_line_id:
                    vals = {'cleared_bank_account':
                            statement_line.cleared_bank_account,
                            'bank_acc_rec_statement_id': statement.id or False}
                    statement_line.move_line_id.write(vals)
            statement.write({'state': 'done',
                             'verified_by_user_id': self._uid,
                             'verified_date': time.strftime('%Y-%m-%d')})

    def action_cancel_draft(self):
        """Reset the statement to draft and perform resetting operations."""
        for statement in self:
            statement_lines = statement.credit_move_line_ids + \
                statement.debit_move_line_ids
            for statement_line in statement_lines:
                if statement_line:
                    statement_line.write({'cleared_bank_account': False,
                                          'research_required': False})
                if statement_line.move_line_id:
                    line_vals = {'cleared_bank_account': False,
                                 'bank_acc_rec_statement_id': False}
                    statement_line.move_line_id.write(line_vals)
            statement.write({'state': 'draft',
                             'verified_by_user_id': False,
                             'verified_date': False})

    def action_select_all(self):
        """Mark all the statement lines as 'Cleared'."""
        for statement in self:
            statement_lines = statement.credit_move_line_ids + \
                statement.debit_move_line_ids
            statement_lines.write({'cleared_bank_account': True})

    def action_unselect_all(self):
        """Reset 'Cleared' in all the statement lines."""
        for statement in self:
            statement_lines = statement.credit_move_line_ids + \
                statement.debit_move_line_ids
            statement_lines.write({'cleared_bank_account': False})

    @api.depends('credit_move_line_ids',
                 'credit_move_line_ids.cleared_bank_account',
                 'debit_move_line_ids',
                 'debit_move_line_ids.cleared_bank_account')
    def _compute_balance(self):
        account_precision = self.env['decimal.precision'].precision_get(
            'Account')
        for statement in self:
            sum_of_credits = 0.0
            sum_of_debits = 0.0
            cleared_balance = 0.0
            difference = 0.0
            sum_of_credits_lines = 0
            sum_of_debits_lines = 0
            for line in statement.credit_move_line_ids:
                sum_of_credits += line.cleared_bank_account and \
                    round(line.amount, account_precision) or 0.0
                sum_of_credits_lines += line.cleared_bank_account and 1 or 0
            for line in statement.debit_move_line_ids:
                sum_of_debits += line.cleared_bank_account and \
                    round(line.amount, account_precision) or 0.0
                sum_of_debits_lines += line.cleared_bank_account and 1 or 0
            cleared_balance = round((sum_of_debits - sum_of_credits),
                                    account_precision)
            difference = round((statement.ending_balance -
                                statement.starting_balance) - cleared_balance,
                               account_precision)
            statement.sum_of_credits = sum_of_credits
            statement.sum_of_debits = sum_of_debits
            statement.cleared_balance = cleared_balance
            statement.difference = difference
            statement.sum_of_credits_lines = sum_of_credits_lines
            statement.sum_of_debits_lines = sum_of_debits_lines

    def _get_move_line_write(self, line, multi_currency):
        amount = 0.0
        if multi_currency:
            amount = line and line.amount_currency or 0.0
        else:
            amount = line.credit or line.debit or 0.0
        res = {'ref': line.ref,
               'date': line.date,
               'partner_id': line.partner_id.id,
               'currency_id': line.currency_id.id,
               'amount': abs(amount),
               'name': line.name,
               'move_line_id': line.id,
               'type': line.credit and 'cr' or 'dr'}
        return res

    def _get_exits_move_line(self, mv_line_rec):
        domain = [('move_line_id', '=', mv_line_rec.id),
                  ('statement_id', 'in', self.ids)]
        res = {}
        statemen_line_obj = self.env['bank.acc.rec.statement.line']
        statmnt_mv_line_ids = statemen_line_obj.search(domain)
        for statement_line in statmnt_mv_line_ids:
            res.update({'cleared_bank_account':
                        statement_line.cleared_bank_account,
                        'ref': statement_line.ref or '',
                        'date': statement_line.date or False,
                        'partner_id': statement_line.partner_id.id or False,
                        'currency_id': statement_line.currency_id.id or False,
                        'amount': abs(statement_line.amount) or 0.0,
                        'name': statement_line.name or '',
                        'move_line_id':
                        statement_line.move_line_id.id or False,
                        'type': statement_line.type})
        return res

    def refresh_record(self):
        """Refresh Record."""
        to_write = {'credit_move_line_ids': [],
                    'debit_move_line_ids': [],
                    'multi_currency': False}
        for obj in self:
            if not obj.account_id:
                continue
            account_curr_id = obj.account_id.currency_id
            cmpny_curr_id = obj.account_id.company_id.currency_id
            if account_curr_id and cmpny_curr_id and \
                    account_curr_id.id != cmpny_curr_id.id:
                to_write['multi_currency'] = True
            move_line_ids = [
                line.move_line_id.id
                for line in obj.credit_move_line_ids + obj.debit_move_line_ids
                if line.move_line_id]
            domain = [
                ('id', 'not in', move_line_ids),
                ('account_id', '=', obj.account_id.id),
                ('move_id.state', '=', 'posted'),
                ('cleared_bank_account', '=', False),
                ('journal_id.type', '!=', 'situation')]
            if not obj.suppress_ending_date_filter:
                domain += [('date', '<=', obj.ending_date)]
            lines = self.env['account.move.line'].search(domain)
            for line in lines:
                if obj.keep_previous_uncleared_entries:
                    if not line.is_b_a_r_s_state_done():
                        continue
                res = (0, 0,
                       self._get_move_line_write(line,
                                                 to_write['multi_currency']))
                if line.credit:
                    to_write['credit_move_line_ids'].append(res)
                else:
                    to_write['debit_move_line_ids'].append(res)
            to_write.pop('multi_currency')
            obj.write(to_write)

    def _get_last_reconciliation(self, account_id):
        res = self.search([('account_id', '=', account_id),
                           ('state', '!=', 'cancel')],
                          order="ending_date desc", limit=1)
        return res

    @api.onchange('account_id', 'ending_date', 'suppress_ending_date_filter',
                  'keep_previous_uncleared_entries')
    def onchange_account_id(self):
        """Onchange account."""
        val = {'value': {'credit_move_line_ids': [],
                         'debit_move_line_ids': [],
                         'multi_currency': False,
                         'company_currency_id': False,
                         'account_currency_id': False, }}
        if self.account_id:
            last_rec = self._get_last_reconciliation(self.account_id.id)
            if last_rec and last_rec.ending_date:
                e_date = (last_rec.ending_date +
                          timedelta(days=1)).strftime(DSDF)
                val['value']['exchange_date'] = e_date
            elif self.ending_date:
                dt_ending = self.ending_date + timedelta(days=-1)
                if dt_ending.month == 1:
                    dt_ending = dt_ending.replace(year=dt_ending.year - 1,
                                                  month=12)
                else:
                    prev_month = (dt_ending.replace(day=1) -
                                  timedelta(days=1))
                    if dt_ending.day <= prev_month.day:
                        dt_ending = dt_ending.replace(
                            month=dt_ending.month - 1)
                    else:
                        dt_ending = prev_month
                val['value']['exchange_date'] = dt_ending.strftime(DSDF)
            move_line_ids = []
            acc_curr_id = self.account_id.currency_id
            cmpny_curr_id = self.account_id.company_id.currency_id
            if acc_curr_id and cmpny_curr_id and \
                    acc_curr_id.id != cmpny_curr_id.id:
                val['value']['multi_currency'] = True
            for statement in self:
                statement_lines = statement.credit_move_line_ids + \
                    statement.debit_move_line_ids
                move_line_ids = [line.move_line_id.id
                                 for line in statement_lines
                                 if line.move_line_id]
            domain = [('account_id', '=', self.account_id.id),
                      ('move_id.state', '=', 'posted'),
                      ('cleared_bank_account', '=', False),
                      ('journal_id.type', '!=', 'situation')]
            if not self.keep_previous_uncleared_entries:
                domain += [('draft_assigned_to_statement', '=', False)]
            if not self.suppress_ending_date_filter:
                domain += [('date', '<=', self.ending_date)]
            line_ids = self.env['account.move.line'].search(domain)
            for line in line_ids:
                if line.id not in move_line_ids:
                    res = self._get_move_line_write(
                        line,
                        val['value']['multi_currency'])
                else:
                    res = self._get_exits_move_line(line)
                if res.get('type') == 'cr':
                    val['value']['credit_move_line_ids'] = [(0, 0, res)]
                else:
                    val['value']['debit_move_line_ids'] = [(0, 0, res)]
        return val

    def is_b_a_r_s_state_done(self):
        """Check bank account reconcile statement is done or not."""
        statement_line_obj = self.env['bank.acc.rec.statement.line']
        for rec in self:
            statement_line_ids = statement_line_obj.search([('move_line_id',
                                                             '=', rec.id)])
            for state_line in statement_line_ids:
                if state_line.statement_id.state not in ("done", "cancel"):
                    return False
            return True

    name = fields.Char(
        'Name', required=True,
        states={'done': [('readonly', True)]},
        help="This is a unique name identifying the "
        "statement (e.g. Bank X January 2012).")
    account_id = fields.Many2one(
        'account.account', 'Account', required=True,
        states={'done': [('readonly', True)]},
        domain="[('company_id', '=', company_id)]",
        help="The Bank/Gl Account that is being reconciled.")
    ending_date = fields.Date('Ending Date', required=True,
                              states={'done': [('readonly', True)]},
                              default=time.strftime('%Y-%m-%d'),
                              help="The ending date of your bank statement.")
    starting_balance = fields.Float(
        'Starting Balance', required=True,
        digits='Account',
        help="The Starting Balance on your bank statement.",
        states={'done': [('readonly', True)]})
    ending_balance = fields.Float(
        'Ending Balance', required=True,
        digits='Account',
        help="The Ending Balance on your bank statement.",
        states={'done': [('readonly', True)]})
    company_id = fields.Many2one(
        'res.company', 'Company',
        required=True, readonly=True,
        help="The Company for which the deposit ticket is made to",
        default=lambda self: self.env.user.company_id)
    notes = fields.Text('Notes')
    verified_date = fields.Date(
        'Verified Date',
        states={'done': [('readonly', True)]},
        help="Date in which Deposit Ticket was verified.")
    verified_by_user_id = fields.Many2one(
        'res.users', 'Verified By',
        states={'done': [('readonly', True)]},
        help="Entered automatically by the "
        "'last user' who saved it. System generated.")
    credit_move_line_ids = fields.One2many('bank.acc.rec.statement.line',
                                           'statement_id', 'Credits',
                                           domain=[('type', '=', 'cr')],
                                           context={'default_type': 'cr'},
                                           states={'done': [('readonly',
                                                             True)]})
    debit_move_line_ids = fields.One2many('bank.acc.rec.statement.line',
                                          'statement_id', 'Debits',
                                          domain=[('type', '=', 'dr')],
                                          context={'default_type': 'dr'},
                                          states={'done': [('readonly',
                                                            True)]})
    suppress_ending_date_filter = fields.Boolean(
        'Remove Ending Date Filter',
        help="If this is checked then the Statement End Date"
        " filter on the transactions below will not occur."
        " All transactions would come over.")
    keep_previous_uncleared_entries = fields.Boolean(
        'Keep Previous Uncleared Entries',
        help=("If this is checked then the previous uncleared entries "
              "will be include."))
    state = fields.Selection([('draft', 'Draft'),
                              ('to_be_reviewed', 'Ready for Review'),
                              ('process', 'Process'), ('done', 'Done'),
                              ('cancel', 'Cancel')], 'State',
                             index=True, readonly=True, default='draft')
    cleared_balance = fields.Float(
        compute='_compute_balance',
        string='Cleared Balance',
        digits='Account',
        help="Total Sum of the Deposit Amount "
        "Cleared - Total Sum of Checks, Withdrawals, "
        "Debits, and Service Charges Amount Cleared")
    difference = fields.Float(
        compute='_compute_balance',
        string='Difference',
        digits='Account',
        help="(Ending Balance - Beginning Balance) - Cleared Balance.")
    sum_of_credits = fields.Float(
        compute='_compute_balance',
        string='Checks, Withdrawals, Debits, and Service Charges Amount',
        digits='Account',
        help="Total SUM of Amts of lines with Cleared = True")
    sum_of_debits = fields.Float(
        compute='_compute_balance',
        string='Deposits, Credits, and Interest Amount',
        digits='Account',
        help="Total SUM of Amts of lines with Cleared = True")
    sum_of_credits_lines = fields.Integer(
        compute='_compute_balance',
        string='Checks, Withdrawals, Debits, and Service Charges # of Items',
        help="Total of number of lines with Cleared = True")
    sum_of_debits_lines = fields.Integer(
        compute='_compute_balance',
        string='Deposits, Credits, and Interest # of Items',
        help="Total of number of lines with Cleared = True")

    _order = "ending_date desc"
    _sql_constraints = [
        ('name_company_uniq', 'unique (name, company_id, account_id)',
         'The name of the statement must be unique per company '
         'and G/L account!')]

    def clear_bank_statement_line(self):
        """Clear bank statement line.

        Method used to remove unclear statement lines from credit & debit of
        move lines.
        @self: Object Pointer
        @return : True
        """
        credit_debit_ids = []
        for bank_rec_statmnt_rec in self:
            for debit_mv_lines in bank_rec_statmnt_rec.debit_move_line_ids:
                if not debit_mv_lines.cleared_bank_account:
                    credit_debit_ids.append(debit_mv_lines.id)
            for credit_mv_lines in bank_rec_statmnt_rec.credit_move_line_ids:
                if not credit_mv_lines.cleared_bank_account:
                    credit_debit_ids.append(credit_mv_lines.id)
        if credit_debit_ids:
            statement_line_obj = self.env['bank.acc.rec.statement.line']
            del_bnk_line_brw = statement_line_obj.browse(credit_debit_ids)
            del_bnk_line_brw.unlink()
        self.write({'state': 'process'})


class BankAccRecStatementLine(models.Model):
    _name = "bank.acc.rec.statement.line"
    _description = "Statement Line"

    name = fields.Char('Name',
                       help="Derived from the related Journal Item.",
                       required=True)
    ref = fields.Char('Reference',
                      help="Derived from related Journal Item.")
    partner_id = fields.Many2one('res.partner', string='Partner',
                                 help="Derived from related Journal Item.")
    amount = fields.Float(
        'Amount',
        digits='Account',
        help="Derived from the 'debit' amount from related Journal Item.")
    date = fields.Date('Date', required=True,
                       help="Derived from related Journal Item.")
    statement_id = fields.Many2one('bank.acc.rec.statement', 'Statement',
                                   required=True, ondelete='cascade')
    move_line_id = fields.Many2one('account.move.line', 'Journal Item',
                                   help="Related Journal Item.")
    cleared_bank_account = fields.Boolean(
        'Cleared? ',
        help='Check if the transaction has cleared from the bank')
    research_required = fields.Boolean(
        'Research Required? ',
        help='Check if the transaction should be '
        'researched by Accounting personal')
    currency_id = fields.Many2one(
        'res.currency', 'Currency',
        help="The optional other currency if it is a multi-currency entry.")
    type = fields.Selection([('dr', 'Debit'), ('cr', 'Credit')], 'Cr/Dr')

    @api.model
    def create(self, vals):
        """Update the draft assigned statement when create statement line."""
        if not vals.get('move_line_id', False):
            raise UserError(_(
                'You cannot add any new bank statement line '
                'manually as of this revision!'))
        move_line_obj = self.env['account.move.line']
        account_move_line_brw = move_line_obj.browse(vals['move_line_id'])
        account_move_line_brw.write({'draft_assigned_to_statement': True})
        return super(BankAccRecStatementLine, self).create(vals)

    def unlink(self):
        """Update moveline before delete the statement line."""
        move_line_ids = [stamnt_line.move_line_id.id for stamnt_line in self if stamnt_line.move_line_id]
        if move_line_ids:
            move_line_obj = self.env['account.move.line']
            account_move_line_brw = move_line_obj.browse(move_line_ids)
            account_move_line_brw.write({'draft_assigned_to_statement': False,
                                         'cleared_bank_account': False,
                                         'bank_acc_rec_statement_id': False})
        return super(BankAccRecStatementLine, self).unlink()
