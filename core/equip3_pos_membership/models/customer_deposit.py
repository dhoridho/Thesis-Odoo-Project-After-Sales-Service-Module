# -*- coding: utf-8 -*-

from datetime import date

from odoo import fields, models, api
from odoo.exceptions import Warning

class CustomerDeposit(models.Model):
    _inherit = 'customer.deposit'

    is_from_pos = fields.Boolean('Is from POS?')
    pos_order_ids = fields.One2many('pos.order','customer_deposit_id', string='POS Orders')
    create_from_session_id = fields.Many2one('pos.session', string='Create from POS Session', 
        help='When Create member Deposit from POS Frontend, store pos session info')
    origin_create_amount = fields.Float('Origin Create Amount')

    @api.model
    def create(self, vals):
        if vals.get('is_from_pos') == True:
            domain = [('partner_id','=',vals['partner_id']), ('state','in',['draft','post'])]
            deposit = self.env[self._name].search(domain, limit=1)
            if deposit:
                raise Warning('Member already has deposit')

        return super(CustomerDeposit, self).create(vals)

    def action_create_deposit_from_pos(self, vals):
        partner_id = vals['deposit_values']['partner_id']

        domain = [('partner_id','=',partner_id), ('state','in',['draft','post'])]
        deposit = self.env[self._name].search(domain, limit=1)
        if deposit:
            return {
                'status': 'failed', 
                'message': 'Member already has deposit'
            }

        pos_config = self.env['pos.config'].browse(vals['pos_config_id'])
        deposit_account_id = pos_config.customer_deposit_account_id
        deposit_reconcile_journal_id = pos_config.customer_deposit_reconcile_journal_id
        if not deposit_account_id or not deposit_reconcile_journal_id:
            return {
                'status': 'failed', 
                'message': 'Please set Deposit Account/Deposit Reconcile Journal in Point of Sale'
            }

        pos_payment_method = self.env['pos.payment.method'].browse(vals['deposit_values']['payment_method_id'])
        account_journal_id = pos_payment_method.account_journal_id
        if not account_journal_id:
            return {
                'status': 'failed', 
                'message': 'Please set Journal in Payment Method "%s"' % pos_payment_method.name
            }
        amount = vals['deposit_values']['amount']
        deposit_values = {
            'is_from_pos': True,
            'state': 'draft', 
            'name': False, 
            'is_deposit': False, 
            'partner_id': partner_id, 
            'company_id': pos_config.company_id.id, 
            'branch_id': pos_config.pos_branch_id.id, 
            'request_partner_id': False, 
            'amount': amount, 
            'origin_create_amount': amount,
            'payment_date': fields.Date.context_today(self),
            'deposit_reconcile_journal_id': deposit_reconcile_journal_id.id, 
            'deposit_account_id': deposit_account_id.id, 
            'journal_id': account_journal_id.id, 
            'currency_id': pos_config.company_id.currency_id.id, 
            'create_from_session_id': vals['pos_session_id'],
        }
        deposit = self.env['customer.deposit'].create(deposit_values)
        deposit.customer_deposit_post()

        return {'status': 'success', 'message': ''}

    def action_add_deposit_from_pos(self, vals):
        deposit_amount = vals['deposit_amount']
        customer_deposit_id = self.env['customer.deposit'].browse([vals['customer_deposit_id']])
        debit_vals = {
            'debit': abs(deposit_amount),
            'name': customer_deposit_id.journal_id.payment_debit_account_id.name,
            'credit': 0.0,
            'account_id': customer_deposit_id.journal_id.payment_debit_account_id.id,
            'currency_id': customer_deposit_id.currency_id.id,
            'date': date.today(),
        }
        credit_vals = {
            'debit': 0.0,
            'name': customer_deposit_id.deposit_account_id.name,
            'credit': abs(deposit_amount),
            'account_id': customer_deposit_id.deposit_account_id.id,
            'currency_id': customer_deposit_id.currency_id.id,
            'date': date.today(),
        }

        account_journal_id = False
        pos_payment = self.env['pos.payment.method'].search([('id','=', vals.get('payment_method_id', False))])
        if (not pos_payment) or (pos_payment and not pos_payment.account_journal_id):
            return {
                'status': 'failed', 
                'message': 'Please set Journal in Payment Method "%s"' % pos_payment.name
            }
        if pos_payment and pos_payment.account_journal_id:
           account_journal_id = pos_payment.account_journal_id.id

        vals = {
            'ref': 'Add Amount Customer Deposit ' + customer_deposit_id.name,
            'currency_id': customer_deposit_id.currency_id.id,
            'date': date.today(),
            'journal_id': customer_deposit_id.journal_id.id,
            'branch_id': customer_deposit_id.branch_id.id,
            'line_ids': [(0, 0, debit_vals), (0, 0, credit_vals)],
            'deposit_account_journal_id': account_journal_id,
            'create_from_session_id': vals['pos_session_id'],
        }

        move_id = self.env['account.move'].create(vals)
        move_id.post()
        customer_deposit_id.amount += deposit_amount
        customer_deposit_id.remaining_amount += deposit_amount
        customer_deposit_id.deposit_history += move_id
        
        return {'status': 'success', 'message': ''}


    def convert_revenue(self, *args, **kwargs):
        res = super(CustomerDeposit, self).convert_revenue(*args, **kwargs)
        context = res and res.get('context', {}) or {}
        if context and context.get('default_is_from_pos') == True:
            new_context = {}
            for k in context:
                if k == 'form_view_ref' and context[k] == 'equip3_pos_membership.pos_member_deposit_view_form':
                    continue
                if k == 'default_is_from_pos':
                    continue
                new_context[k] = context[k]
            res['context'] = new_context
        return res