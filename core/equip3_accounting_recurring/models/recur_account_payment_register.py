
from odoo import models, fields, api, _
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError, ValidationError

class ReccuringMoveLineInherit(models.Model):
    _inherit = 'recurring.move.line'

    account_id = fields.Many2one('account.account', required = True)
    analytic_group_ids = fields.Many2many('account.analytic.tag', string='Analytic Groups')

    @api.onchange('account_id')
    def set_account_sh_move_line_tag(self):
        for line in self:
            line.update({'analytic_group_ids': [(6, 0, line.recurring_id.analytic_group_ids.ids)],})

class AccountPaymentRegIng(models.TransientModel):
    _inherit = 'account.payment.register'

    is_prepayment = fields.Boolean(string='Prepayment')
    prepayment_journal_id = fields.Many2one(comodel_name='account.journal')
    start_date = fields.Date(string='Start Date', default=fields.Datetime.now)
    end_date = fields.Date(string='End Date', compute='_onchange_stop_recurring_interval')
    recurring_interval = fields.Integer(string='Interval', default=1)
    recurring_interval_unit = fields.Selection([('days', 'Days'), ('weeks','Weeks'), ('months','Months'), ('years','Years')], default='days')
    stop_recurring_interval = fields.Integer(string='Stop After', default=0)
    stop_recurring_interval_unit = fields.Selection([('days', 'Days'), ('weeks','Weeks'), ('months','Months'), ('years','Years')])
    revenue_account = fields.Many2one(comodel_name='account.account')
    move_type = fields.Char(string='tab', default=lambda self: self._context.get('move_types',False))
    is_show_prepayment = fields.Boolean(string='Is Prepayment', compute='_compute_is_show_prepayment', store=False)

    @api.depends('line_ids')
    def _compute_is_show_prepayment(self):
        for record in self:
            record.is_show_prepayment = True
            move_ids = record.line_ids.mapped('move_id')
            if any(move.is_prepayment for move in move_ids):
                record.is_show_prepayment = False

    @api.depends('stop_recurring_interval',
                  'recurring_interval_unit', 'start_date')
    
    def _onchange_stop_recurring_interval(self):
        for rec in self:
            rec.stop_recurring_interval_unit = rec.recurring_interval_unit
            if rec.start_date:
                if self.stop_recurring_interval > 0:
                    end_date = False
                    st_date = fields.Date.from_string(rec.start_date)
                    if rec.recurring_interval_unit == 'days':
                        end_date = st_date + \
                            relativedelta(days=rec.stop_recurring_interval - 1)
                    elif rec.recurring_interval_unit == 'weeks':
                        end_date = st_date + \
                            relativedelta(weeks=rec.stop_recurring_interval - 1)
                    elif rec.recurring_interval_unit == 'months':
                        end_date = st_date + \
                            relativedelta(months=rec.stop_recurring_interval - 1)
                    elif rec.recurring_interval_unit == 'years':
                        end_date = st_date + \
                            relativedelta(years=rec.stop_recurring_interval - 1)

                    if end_date:
                        rec.end_date = end_date
                else:
                    self.end_date = False

    @api.onchange('partner_type')
    def _onchange_domain(self):
        self.ensure_one()
        res={}
        if self.partner_type == "customer":
            domain_line = "[('user_type_id.name', 'in', ['Income','Other Income'])]"
        else:
            domain_line = "[('user_type_id.name', 'in', ['Expenses','Depreciation','Cost of Revenue'])]"
        res['domain'] = {'revenue_account' : domain_line}
        return res

    @api.onchange('is_prepayment')
    def _giveme_default(self):
        if self.is_prepayment == True:
            company_id = self.company_id
            val = self.env['account.journal'].search([('type','in',('general','bank','cash')),('company_id','=',company_id.id)])
            domain = [('id', 'in', val.ids)]
            return {'domain': {'prepayment_journal_id': domain}}
        else:
            return {'domain': {'prepayment_journal_id': []}}

        # val = self.env['account.journal'].search([('type','in',('general','bank','cash'))])
        # self.prepayment_journal_id = val[0]

    # @api.model
    # def _set_tomove(self):
    #     for rec in self:
    #         if rec.is_prepayment:
    #             move = self.env['account.move'].search([('name','=',rec.communication)])

    def detail_prepayment(self,payments_id):
        recurring_line = []
        for res in self:
            payment = self.env['account.payment'].search([('id', '=', payments_id.id)])
            if payment.state == 'to_approve':
                invoice_ids = self.env['account.move'].search([('name', '=', payment.ref)])
            else:
                if len(payment.reconciled_invoice_ids) > 0:
                    invoice_ids = payment.reconciled_invoice_ids
                else:
                    invoice_ids = payment.reconciled_bill_ids
            product = []
            type_move = ''
            partner_id = ''
            for inv_id in invoice_ids:
                for inv in inv_id:
                    type_move = inv.move_type
                    partner_id = inv.partner_id
                    for result in inv.invoice_line_ids:                                        
                        product.append(result)
            move_line = self.move_line_create(product,partner_id,type_move)    
            # raise UserError('Kode transaksi 08 is only for non VAT subject items.')
            if res.is_prepayment == True:
                for rec in move_line:
                    if type_move in ['out_invoice', 'out_refund', 'out_receipt']:
                        recuring_inv = self.env['invoice.recurring'].with_context(default_partner_id=1, default_prepayment_journal='customer')
                        prepayment_journal = 'customer'                
                    else:
                        recuring_inv = self.env['invoice.recurring'].with_context(default_partner_id=1, default_prepayment_journal='vendor')
                        prepayment_journal = 'vendor'

                    detail_recuring = {'journal_id' : res.prepayment_journal_id.id, 
                                       'start_date' : res.start_date,
                                       'end_date' : res.end_date,
                                       'recurring_interval' : res.recurring_interval,
                                       'recurring_interval_unit' : res.recurring_interval_unit,
                                       'stop_recurring_interval' : res.stop_recurring_interval,
                                       'stop_recurring_interval_unit' : res.stop_recurring_interval_unit,
                                       'type' : 'entry',
                                       'prepayment_journal' : prepayment_journal,
                                       'branch_id' : res.branch_id.id,
                                       'sh_move_line' : rec
                                       }

                    recurring_line.append(recuring_inv.create(detail_recuring))
        return recurring_line

    def move_line_create(self,product,partner_id,move_type):
        result=[]
        for rec in product:
            line_ids = []
            if self.recurring_interval >= 1 :
                interval = self.recurring_interval
            else :
                interval = 1
            
            if self.stop_recurring_interval == 0 or self.stop_recurring_interval == False:
                amount = 0
            else:
                amount = (rec.quantity * rec.price_unit) / (self.stop_recurring_interval / interval)
            if move_type in ['out_invoice', 'out_refund', 'out_receipt']:
                line = {'account_id': self.revenue_account.id,
                        'partner_id': partner_id.id,
                        'name': rec.name,
                        'debit': 0.0,
                        'credit': amount,
                        }
                line_ids.append((0, 0, line))
                line = {'account_id': rec.account_id.id,
                        'partner_id': partner_id.id,
                        'name': rec.name,
                        'debit': amount,
                        'credit': 0.0,
                        }
                line_ids.append((0, 0, line))
            elif move_type in ['in_invoice', 'in_refund', 'in_receipt']:
                line = {'account_id': rec.account_id.id,
                        'partner_id': partner_id.id,
                        'name': rec.name,
                        'debit': 0.0,
                        'credit': amount,
                        }
                line_ids.append((0, 0, line))
                line = {'account_id': self.revenue_account.id,
                        'partner_id': partner_id.id,
                        'name': rec.name,
                        'debit': amount,
                        'credit': 0.0,
                        }
                line_ids.append((0, 0, line))
            result.append(line_ids)
        return result

    # def move_line_create(self,product,partner_id,move_type):
    #     result=[]
    #     for rec in product:
    #         line_ids = []
    #         if self.stop_recurring_interval == 0 or self.stop_recurring_interval == False:
    #             amount = 0
    #         else:
    #             amount = (rec.quantity * rec.price_unit) / self.stop_recurring_interval
    #         if move_type in ['out_invoice', 'out_refund', 'out_receipt']:
    #             line = {'account_id': self.revenue_account.id,
    #                     'partner_id': partner_id.id,
    #                     'name': rec.name,
    #                     'debit': 0.0,
    #                     'credit': amount,
    #                     }
    #             line_ids.append((0, 0, line))
    #             line = {'account_id': rec.account_id.id,
    #                     'partner_id': partner_id.id,
    #                     'name': rec.name,
    #                     'debit': amount,
    #                     'credit': 0.0,
    #                     }
    #             line_ids.append((0, 0, line))
    #         elif move_type in ['in_invoice', 'in_refund', 'in_receipt']:
    #             line = {'account_id': rec.account_id.id,
    #                     'partner_id': partner_id.id,
    #                     'name': rec.name,
    #                     'debit': 0.0,
    #                     'credit': amount,
    #                     }
    #             line_ids.append((0, 0, line))
    #             line = {'account_id': self.revenue_account.id,
    #                     'partner_id': partner_id.id,
    #                     'name': rec.name,
    #                     'debit': amount,
    #                     'credit': 0.0,
    #                     }
    #             line_ids.append((0, 0, line))
    #         result.append(line_ids)
    #     return result

    
    def action_create_payments(self):
        context = dict(self.env.context) or {}
        if "dont_redirect_to_payments" in context:
            if context['dont_redirect_to_payments'] == True:
                context.update({'dont_redirect_to_payments' : False})
                self.env.context = context
                action = super(AccountPaymentRegIng, self).action_create_payments()
                if 'res_id' in action:
                    payments = self.env['account.payment'].search([('id', '=', action['res_id'])])
                    detail = self.detail_prepayment(payments)
                    payments.update({'is_prepayment' : self.is_prepayment,
                                     'prepayment_journal_id' : self.prepayment_journal_id,
                                     'start_date' : self.start_date,
                                     'end_date' : self.end_date,
                                     'recurring_interval' : self.recurring_interval,
                                     'recurring_interval_unit' : self.recurring_interval_unit,
                                     'stop_recurring_interval' : self.stop_recurring_interval,
                                     'stop_recurring_interval_unit' : self.stop_recurring_interval_unit,
                                     'revenue_account' : self.revenue_account})
                    move_ids = self.line_ids.mapped('move_id')
                    for move in move_ids:
                        move.is_prepayment = self.is_prepayment
                    return True
        return super(AccountPaymentRegIng, self).action_create_payments()

    def request_for_approval(self):
        context = dict(self.env.context) or {}
        if "dont_redirect_to_payments" in context:
            if context['dont_redirect_to_payments'] == True:
                context.update({'dont_redirect_to_payments' : False})
                self.env.context = context
                action = super(AccountPaymentRegIng, self).request_for_approval()
                if 'res_id' in action:
                    payments = self.env['account.payment'].search([('id', '=', action['res_id'])])
                    detail = self.detail_prepayment(payments)
                    payments.update({'is_prepayment' : self.is_prepayment,
                                     'prepayment_journal_id' : self.prepayment_journal_id,
                                     'start_date' : self.start_date,
                                     'end_date' : self.end_date,
                                     'recurring_interval' : self.recurring_interval,
                                     'recurring_interval_unit' : self.recurring_interval_unit,
                                     'stop_recurring_interval' : self.stop_recurring_interval,
                                     'stop_recurring_interval_unit' : self.stop_recurring_interval_unit,
                                     'revenue_account' : self.revenue_account})
                    move_ids = self.line_ids.mapped('move_id')
                    for move in move_ids:
                        move.is_prepayment = self.is_prepayment
                    return True
        return super(AccountPaymentRegIng, self).request_for_approval()

class AccountMove(models.Model):
    _inherit = "account.move"

    def action_register_payment(self):
        for rec in self:
            ''' Open the account.payment.register wizard to pay the selected journal entries.
            :return: An action opening the account.payment.register wizard.
            '''
            return {
                'name': _('Register Payment'),
                'res_model': 'account.payment.register',
                'view_mode': 'form',
                'context': {
                    'active_model': 'account.move',
                    'active_ids': self.ids,
                    'move_types' : rec.move_type,
                },
                'target': 'new',
                'type': 'ir.actions.act_window',
            }

