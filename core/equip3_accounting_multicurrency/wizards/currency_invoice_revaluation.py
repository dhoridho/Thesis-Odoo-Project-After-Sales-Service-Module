from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.misc import format_date
from dateutil.relativedelta import relativedelta
import datetime


class AccountMove(models.Model):
    _inherit = 'account.move'


    currency_revaluation_id = fields.Many2one('account.move', string='Currency Revaluation', ondelete='cascade')
    children_ids = fields.One2many('account.move', 'currency_revaluation_id', string='Children')
    currency_revaluation_ref_id = fields.Many2one('account.move', string='Currency Revaluation Ref')
    currency_revaluation_count = fields.Integer(string="currency revaluation count", default ='0', compute='_compute_currency_revaluation_count')


    @api.depends('currency_revaluation_ref_id')
    def _compute_currency_revaluation_count(self):
        for rec in self:
            count_ref_id = self.env['account.move'].search_count([('currency_revaluation_ref_id', '=', rec.id)])
            rec.currency_revaluation_count = count_ref_id



class CurrencyTaxRate(models.Model):
    _name = "currency.invoice.revaluation"
    _description = "Currency Invoice Revaluation"
    _order = "revaluation_date desc"

    revaluation_period_start = fields.Date(default=str(datetime.date.today() - datetime.timedelta(days=30)), required=True)
    revaluation_period_end = fields.Date(default=fields.Date.context_today, required=True)
    revaluation_date = fields.Date(default=fields.Date.context_today, required=True)    
    journal_id = fields.Many2one(
		string="Unrealized Exchange Journal",
        default=lambda self: self.env.company.unrealized_exchange_journal_id,
        comodel_name='account.journal', 
        required=True)
    income_unrealized_account = fields.Many2one(
        comodel_name="account.account",
        default=lambda self: self.env.company.income_unrealized_exchange_account_id,
        string="Unrealized Gain Account", 
        required=True)        
    expense_unrealized_account = fields.Many2one(
		comodel_name="account.account",
        default=lambda self: self.env.company.expense_unrealized_exchange_account_id,
        string="Unrealized Loss Account", 
        required=True)
    
    def validate(self):        
        if self._context.get('active_ids'):
            active_ids = self._context.get('active_ids')
            move_vals = self.env['account.move'].search([('id', 'in', active_ids)])
        else:           
            move_vals = self.env['account.move'].search([('invoice_date', '>=', self.revaluation_period_start),('invoice_date', '<=', self.revaluation_period_end)])
        moves_ids = move_vals.filtered(lambda line: line.journal_id.type in ['purchase', 'sale'] and line.state == 'posted' and line.payment_state in ['not_paid','partial'])
        AccountMove = self.env['account.move']
        move_id=[]
        for move in moves_ids:
            curr = self.env['res.currency.rate'].search([('name', '<=', self.revaluation_date),('currency_id', '=', move.currency_id.id)],order='name desc')
            if curr:
                rate = curr[0].mr_rate
                if (rate - move.current_rate) != 0:
                    move_line_id = AccountMove.create(self._prepare_move_line(move, rate, move.journal_id.type))
                    move_line_id.post()        
                    move_line_id.write({'currency_revaluation_ref_id' : move.id})    
                    move_id.append(move_line_id.id)
                    move.update({'current_rate' : curr[0].mr_rate,
                                 'current_inverse_rate' : curr[0].conversion,
                                 'currency_revaluation_id' : move_line_id,
                                 'currency_revaluation_count' : move.currency_revaluation_count + 1
                                })
                    domain = [('account_internal_type', 'in', ('receivable', 'payable')), ('reconciled', '=', False)]                    
        return {
                'name':  _('Currency Revaluation'),
                'type': 'ir.actions.act_window',
                'view_mode': 'tree,kanban,form',
                'res_model': 'account.move',
                'views_id': self.env.ref('account.view_move_tree').id,
                'domain': [('id', 'in', move_id)],
                'context' : {'default_move_type': 'entry'}
            }

    def _prepare_move_line(self, move_id, rate,move_type):
        all_move_vals = []        
        if move_id.apply_manual_currency_exchange:
            balance_current_rate = move_id.amount_residual / move_id.manual_currency_exchange_rate
        else:
            balance_current_rate = move_id.currency_id._convert(move_id.amount_residual, self.env.company.currency_id, self.env.company, move_id.invoice_date)
        
        balance_rate = move_id.currency_id._convert(move_id.amount_residual, self.env.company.currency_id, self.env.company, self.revaluation_date)
        total_balance = abs(balance_current_rate) - abs(balance_rate)
        
        loss = False
        if balance_current_rate > balance_rate:
            loss = False
        else:
            loss = True

        if move_id.journal_id.type == 'purchase':
            line_vals_list = []
            line_vals_list.append((0,0,
                                        {                                        
                                            'partner_id': move_id.partner_id.id,
                                            'name': move_id.name,
                                            'date_maturity': self.revaluation_date.strftime("%Y-%m-%d"),
                                            'debit': abs(total_balance) if total_balance > 0 else 0.0,
                                            'credit': abs(-total_balance) if total_balance < 0 else 0.0,
                                            'account_id': move_id.partner_id.property_account_payable_id.id,

                                        }))
            line_vals_list.append((0,0,
                                       {
                                            'partner_id': move_id.partner_id.id,
                                            'name': move_id.name,
                                            'date_maturity': self.revaluation_date.strftime("%Y-%m-%d"),
                                            'debit': abs(-total_balance) if total_balance < 0 else 0.0,
                                            'credit': abs(total_balance) if total_balance > 0 else 0.0,
                                            'account_id': self.income_unrealized_account.id if total_balance > 0 else self.expense_unrealized_account.id,
                                        }))
            move_vals = {
                        'partner_id': move_id.partner_id.id,
                        'ref': move_id.name,
                        'date': self.revaluation_date.strftime("%Y-%m-%d"),
                        'journal_id': self.journal_id.id,
                        'line_ids': line_vals_list,
                        'branch_id': move_id.branch_id.id
                        }
            all_move_vals.append(move_vals)

        elif move_id.journal_id.type == 'sale':
            # balance_current_rate = move_id.currency_id._convert(move_id.amount_residual, self.env.company.currency_id, self.env.company, move_id.invoice_date)
            # balance_rate = move_id.currency_id._convert(move_id.amount_residual, self.env.company.currency_id, self.env.company, self.revaluation_date)
            line_vals_list = []
            line_vals_list.append((0,0,
                                        {
                                            'partner_id': move_id.partner_id.id,
                                            'name': move_id.name,
                                            'date_maturity': self.revaluation_date.strftime("%Y-%m-%d"),
                                            'debit': abs(-total_balance) if total_balance < 0 else 0.0,
                                            'credit': abs(total_balance) if total_balance > 0 else 0.0,
                                            'account_id': move_id.partner_id.property_account_receivable_id.id,
                                            
                                        }))
            line_vals_list.append((0,0,
                                       {
                                            'partner_id': move_id.partner_id.id,
                                            'name': move_id.name,
                                            'date_maturity': self.revaluation_date.strftime("%Y-%m-%d"),
                                            'debit': abs(total_balance) if total_balance > 0 else 0.0,
                                            'credit': abs(-total_balance) if total_balance < 0 else 0.0,                                            
                                            'account_id': self.income_unrealized_account.id if total_balance < 0 else self.expense_unrealized_account.id,
                                        }))
            move_vals = {
                        'partner_id': move_id.partner_id.id,
                        'ref': move_id.name,
                        'date': self.revaluation_date.strftime("%Y-%m-%d"),
                        'journal_id': self.journal_id.id,
                        'line_ids': line_vals_list,
                        'branch_id': move_id.branch_id.id
                        }
            all_move_vals.append(move_vals)
        return all_move_vals

class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    current_rate_id = fields.Float(string='Current Rate', default=lambda self: self.env.company.currency_id.rate, digits=(12, 12))
    current_inverse_rate_id = fields.Float(string='Current Inverse Rate', compute='_compute_current_inverse_rate_id', default=lambda self: self.env.company.currency_id.conversion, store=True)
    is_same_main_currency = fields.Boolean(compute='_compute_check_same_main_currency')
    inverse_rate = fields.Float("Inverse Rate", digits=(12, 12))
    manual_currency_exchange_inverse_rate = fields.Float(string='Inverse Rate', digits=(12, 12))
    manual_currency_exchange_rate = fields.Float(string='Manual Currency Exchange Rate', digits=(12, 12), default=0.0)
    exchange_spot_rate = fields.Float(string='Exchange rate', compute='_oncange_spot_rate', digits=(12, 12))
    
    @api.onchange('manual_currency_exchange_inverse_rate')
    def _oncange_spot_rate(self):
        for rec in self:
            if rec.manual_currency_exchange_inverse_rate:
                if rec.manual_currency_exchange_inverse_rate > 0.0:
                    rec.exchange_spot_rate = rec.amount * rec.manual_currency_exchange_inverse_rate
                else:
                    rec.exchange_spot_rate = 0
            else:
                rec.exchange_spot_rate = 0

    @api.onchange('manual_currency_exchange_inverse_rate')
    def _oncange_rate_conversion(self):
        if self.manual_currency_exchange_inverse_rate:
            self.manual_currency_exchange_rate = 1 / self.manual_currency_exchange_inverse_rate
    
    @api.onchange('manual_currency_exchange_rate')
    def _oncange_rate(self):
        if self.manual_currency_exchange_rate:
            self.manual_currency_exchange_inverse_rate = 1 / self.manual_currency_exchange_rate

    @api.onchange('active_manual_currency_rate')
    def _oncange_active_manual(self):
        self.apply_manual_currency_exchange = self.active_manual_currency_rate

    
    @api.onchange('currency_id', 'payment_date')
    def onchange_currency_id(self):
        if self.currency_id:            
            first_day_of_month = self.payment_date.replace(day=1)
            end_day_of_month = first_day_of_month + relativedelta(months=1, days=-1)
            rate_multicurrency = self.env['res.currency.rate'].search([('currency_id', '=', self.currency_id.id), ('name', '>=', first_day_of_month), ('name', '<=', self.payment_date)], limit=1, order='name desc')
            if rate_multicurrency:
                self.current_rate_id = rate_multicurrency.rate
                self._compute_current_inverse_rate_id()
                self._oncange_spot_rate()
            else:
                if self.env.company.currency_id != self.currency_id:
                    raise UserError(_("There is no currency rate defined for the currency %s on this period %s.") % (self.currency_id.name, first_day_of_month))
                                
    @api.onchange('currency_id')
    def _compute_current_inverse_rate_id(self):
        for each in self:
            each.current_inverse_rate_id = 1 / each.current_rate_id
            each.manual_currency_exchange_rate = each.current_inverse_rate_id
    
    @api.onchange('currency_id')
    def _compute_check_same_main_currency(self):
        for rec in self:
            if rec.company_currency_id == rec.currency_id:
                rec.is_same_main_currency = True
            else:
                rec.is_same_main_currency = False

    def _create_payment_vals_from_wizard(self):
        payment_vals = super(AccountPaymentRegister, self)._create_payment_vals_from_wizard()
        payment_vals['manual_currency_exchange_inverse_rate'] = self.manual_currency_exchange_inverse_rate
        return payment_vals

    def _create_payment_vals_from_batch(self, batch_result):
        payment_vals = super(AccountPaymentRegister, self)._create_payment_vals_from_batch(batch_result)
        payment_vals['manual_currency_exchange_inverse_rate'] = self.manual_currency_exchange_inverse_rate
        payment_vals['apply_manual_currency_exchange'] = self.apply_manual_currency_exchange
        payment_vals['manual_currency_exchange_rate'] = self.manual_currency_exchange_rate
        payment_vals['active_manual_currency_rate'] = self.active_manual_currency_rate
        return payment_vals
    