from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from json import dumps
import json

class AccountPayment(models.Model):
    _inherit = "account.payment"

    reconcile_invisible = fields.Boolean(string='reconcile', compute='_check_invisible_reconcile', default = True)

    @api.depends('state','is_reconciled')
    def _check_invisible_reconcile(self):
        self.ensure_one()
        if self.state == 'posted' and self.is_reconciled == False:
            self.reconcile_invisible = False
        else:
            self.reconcile_invisible = True

    def action_reconcile_payment(self):
        name=''
        if self.payment_type:
            if self.payment_type == 'outbound':
                name = 'Reconcile Bill'
            else:
                name = 'Reconcile Invoice'

        return {
                'name':  _(name),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'account.payment.reconcile',
                'views_id': self.env.ref('equip3_accounting_operation.view_form_reconcile_payment').id,
                'domain': [('payment_id', '=', self.id)],
                'context': {'default_date_reconcile': self.date, 'default_payment_id': self.id},
                'target': 'new'
                }

class AccountPaymentReconcile(models.Model):
    _name = "account.payment.reconcile"
    _description = ' '

    payment_id = fields.Many2one('account.payment', string='Payment')
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, readonly=True, related='payment_id.currency_id')
    payment_type = fields.Selection([
        ('outbound', 'Send Money'),
        ('inbound', 'Receive Money'),
    ], string='Payment Type', related='payment_id.payment_type', required=True)
    partner_id = fields.Many2one('res.partner', string='Partner', related='payment_id.partner_id')    
    date_reconcile = fields.Date(string='Date')
    allocation_line_ids = fields.One2many('account.payment.reconcile.line', 'reconcile_line_id', string='Account Move reconcile')
    payment_amount = fields.Monetary(string='total Amount', compute='_payment_amount', readonly = True)
    limit_amount = fields.Monetary(string='Limit Amount', compute='_payment_limit', readonly = True)    
    

    def button_reconcille_payment(self):
        check_periods = self.env['sh.account.period'].search([('company_id', '=', self.env.company.id), ('date_start', '<=', self.date_reconcile), ('date_end', '>=', self.date_reconcile), ('state', '=', 'done')])
        if check_periods:
            raise UserError(_('You can not post any journal entry already on Closed Period'))
        if self.limit_amount < 0:
            raise ValidationError(_('Total Allocation can not bigger than Remaining Amount'))
        move_obj = self.env['account.move']
        for rec in self.allocation_line_ids:
            if rec.allocation_amount == 0:
                continue
            
            # if self.payment_id.payment_type == 'inbound':
            #     diff_amount = rec.allocation_amount - rec.amount_due
            # else:
            #     diff_amount = rec.allocation_amount + rec.amount_due
            
            # allocation_amount = rec.allocation_amount
            # if allocation_amount < 0:
            #     allocation_amount = allocation_amount*-1

            # amount_due = rec.amount_due
            # if amount_due < 0:
            #     amount_due = amount_due*-1

            # diff_amount = allocation_amount - amount_due
            # full_reconcile = diff_amount <= 0

            allocation_amount = abs(rec.allocation_amount)
            amount_due = abs(rec.amount_due)
            diff_amount = allocation_amount - amount_due
            full_reconcile = diff_amount <= 0

            if full_reconcile:
                # line_id = []
                amount_currency = rec.allocation_amount
                balance = self.payment_id.currency_id._convert(amount_currency, self.env.company.currency_id, self.env.company , self.date_reconcile or fields.Date.context_today(self))
                payment_ref = self.payment_id.ref + ' ' if self.payment_id.ref else ''
                
                if self.payment_id.payment_type == 'inbound':
                    to_reconcile = rec.invoice_id.line_ids.filtered(lambda r:r.account_id.id == self.partner_id.property_account_receivable_id.id)
                else:
                    to_reconcile = rec.invoice_id.line_ids.filtered(lambda r:r.account_id.id == self.payment_id.destination_account_id.id)
                
                domain = [('account_internal_type', 'in', ('receivable', 'payable')), ('reconciled', '=', False)]
                payment_lines = self.payment_id.line_ids.filtered_domain(domain)
                for account in payment_lines.account_id:
                    lines = payment_lines
                    lines += to_reconcile.filtered_domain([('account_id', '=', account.id), ('reconciled', '=', False)])
                    lines.reconcile()

                    if self.payment_id.payment_type == 'inbound':
                        if len(lines) > 1 and lines[1].amount_residual == 0:
                            rec.invoice_id.write({'payment_state' : 'paid'})
                        elif lines[1].amount_residual < lines[1].balance:
                            rec.invoice_id.write({'payment_state' : 'partial'})
                        else:
                            rec.invoice_id.write({'payment_state' : 'not_paid'})
                    else:
                        if len(lines) > 1 and lines[1].amount_residual == 0:
                            rec.invoice_id.write({'payment_state' : 'paid'})
                        elif lines[1].amount_residual > lines[1].balance:
                            rec.invoice_id.write({'payment_state' : 'partial'})
                        else:
                            rec.invoice_id.write({'payment_state' : 'not_paid'})

            else :
                line_id = []
                amount_currency = rec.allocation_amount
                balance = self.payment_id.currency_id._convert(amount_currency, self.env.company.currency_id, self.env.company , self.date_reconcile or fields.Date.context_today(self)) 
                move_line1 = {
                        'name'              : 'Customer Reconcile' if self.payment_id.payment_type == 'inbound' else 'Vendor Reconcile',
                        'account_id'        : self.payment_id.journal_id.default_account_id.id if self.payment_id.payment_type == 'outbound' else self.payment_id.destination_account_id.id,
                        # 'account_id'        : self.partner_id.property_account_receivable_id.id if self.payment_id.payment_type == 'inbound' else self.payment_id.destination_account_id.id,
                        'currency_id'       : self.currency_id.id,
                        'amount_currency'   : -rec.allocation_amount,
                        'debit'             : 0,
                        'credit'            : balance,
                        'partner_id'        : self.partner_id.id,
                    }
                line_id.append((0,0,move_line1))
                move_line2 = {
                        'name'              : 'Customer Reconcile' if self.payment_id.payment_type == 'inbound' else 'Vendor Reconcile',
                        'account_id'        : self.payment_id.destination_account_id.id if self.payment_id.payment_type == 'outbound' else self.payment_id.journal_id.default_account_id.id,
                        # 'account_id'        : self.partner_id.property_account_receivable_id.id if self.payment_id.payment_type == 'inbound' else self.payment_id.destination_account_id.id,
                        'currency_id'       : self.currency_id.id,
                        'amount_currency'   : rec.allocation_amount,
                        'debit'             : balance,
                        'credit'            : 0,
                        'partner_id'        : self.partner_id.id,
                    }
                line_id.append((0,0,move_line2))
                move_vals = {'journal_id'    : self.payment_id.journal_id.id,
                            'currency_id'   : self.currency_id.id,
                            'date'          : self.date_reconcile,
                            'partner_id'    : self.partner_id.id,
                            'branch_id'     : self.payment_id.branch_id.id,
                            'ref'           : rec.invoice_id.name,
                            'line_ids'      : line_id,
                    }
                reconcile_move_id = move_obj.create(move_vals)
                payment_ref = self.payment_id.ref + ' ' if self.payment_id.ref else ''
                reconcile_move_id.action_post()
                batches = self._get_batches(rec.invoice_id)
                to_reconcile = []
                to_reconcile.append(batches[0]['lines'])
                
                
                # if self.payment_id.payment_type == 'outbound':
                domain = [('account_internal_type', 'in', ('receivable', 'payable')), ('reconciled', '=', False)]
                for lines in to_reconcile:
                    payment_lines = reconcile_move_id.line_ids.filtered_domain(domain)
                    for account in payment_lines.account_id:
                        (payment_lines + lines).filtered_domain([('account_id', '=', account.id), ('reconciled', '=', False)]).reconcile()

                    # if self.payment_id.payment_type == 'inbound':
                    #     if len(lines) > 1 and lines[1].amount_residual == 0:
                    #         rec.invoice_id.write({'payment_state' : 'paid'})
                    #     elif lines[1].amount_residual < lines[1].balance:
                    #         rec.invoice_id.write({'payment_state' : 'partial'})
                    #     else:
                    #         rec.invoice_id.write({'payment_state' : 'not_paid'})
                    # else:
                    #     if len(lines) > 1 and lines[1].amount_residual == 0:
                    #         rec.invoice_id.write({'payment_state' : 'paid'})
                    #     elif lines[1].amount_residual > lines[1].balance:
                    #         rec.invoice_id.write({'payment_state' : 'partial'})
                    #     else:
                    #         rec.invoice_id.write({'payment_state' : 'not_paid'})

                
                # lines = payment_lines
                # lines += to_reconcile.filtered_domain([('account_id', '=', account.id), ('reconciled', '=', False)])
                # lines += reconcile_move_id.line_ids.filtered(lambda line: line.account_id == lines[0].account_id and not line.reconciled)
                # lines.reconcile()
            
            if self.payment_id.reconciled_invoice_ids:
                self.payment_id.update({'ref' : payment_ref + self._get_batch(self.payment_id.reconciled_invoice_ids)})
            if self.payment_id.reconciled_bill_ids:
                self.payment_id.update({'ref' : payment_ref + self._get_batch(self.payment_id.reconciled_bill_ids)})
            if self.payment_id.reconciled_statement_ids:
                self.payment_id.update({'ref' : payment_ref + self._get_batch(self.payment_id.reconciled_statement_ids)})

        existing_payment_ids = rec.invoice_id.invoice_payment_ids.ids
        new_payment_ids = [self.payment_id.id]  # Convert to list
        all_payment_ids = list(set(existing_payment_ids + new_payment_ids))
        rec.invoice_id.write({'invoice_payment_ids': [(6, 0, all_payment_ids)]})
        
        invoice_origin_ids = self.payment_id.reconciled_invoice_ids.ids
        bill_origin_ids = self.payment_id.reconciled_bill_ids.ids

        if self.payment_id.payment_type == 'inbound':
            if not invoice_origin_ids:
                invoice_origin_ids = self.allocation_line_ids.mapped('invoice_id').ids
            self.payment_id.update({'invoice_origin_ids' : [(6, 0, invoice_origin_ids)]})
        elif self.payment_id.payment_type == 'outbound':
            if not bill_origin_ids:
                bill_origin_ids = self.allocation_line_ids.mapped('invoice_id').ids
            self.payment_id.update({'invoice_origin_ids' : [(6, 0, bill_origin_ids)]})
        


    def _get_batch(self, invoice):
        labels = set(line.name for line in invoice)
        return ' '.join(sorted(labels))
                
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
        
    @api.depends('payment_id')
    def _payment_amount(self):
        for line in self:
            amount = 0
            if line.payment_id:
                domain = [('account_internal_type', 'in', ('receivable', 'payable')), ('reconciled', '=', False)]
                lines = line.payment_id.move_id.line_ids.filtered_domain(domain)
                amount_residual = lines.amount_residual
                balance = self.env.company.currency_id._convert(amount_residual, line.payment_id.currency_id, self.env.company , line.date_reconcile or fields.Date.context_today(self))
                if line.payment_id.payment_type == 'inbound':
                    amount = balance*-1
                else:
                    amount = balance
            line.payment_amount = amount

    @api.depends('allocation_line_ids.invoice_id')
    def _payment_limit(self):
        for line in self:
            total = 0
            for allocation_line in line.allocation_line_ids:
                total = total + allocation_line.allocation_amount
            subtotal = line.payment_amount
            line.limit_amount = subtotal - total
              
    
class AccountPaymentReconcileLine(models.Model):
    _name = "account.payment.reconcile.line"
    _description = ' '

    reconcile_line_id = fields.Many2one('account.payment.reconcile', string='reconcile line', ondelete="cascade",)    
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, readonly=True, related='reconcile_line_id.currency_id')
    payment_type = fields.Selection([
        ('outbound', 'Send Money'),
        ('inbound', 'Receive Money'),
    ], string='Payment Type', related='reconcile_line_id.payment_id.payment_type', required=True)
    partner_id = fields.Many2one('res.partner', string='Partner', related='reconcile_line_id.partner_id')
    amount_due = fields.Monetary(string='Amount Due Signed', related='invoice_id.amount_residual_signed')
    # amount_due = fields.Monetary(string='Amount Due Signed')
    invoice_id = fields.Many2one('account.move', string='Invoice')
    allocation_amount = fields.Monetary(string='Allocation Amount')
    # allocation_amount = fields.Float(string='Allocation Amount', compute='_compute_inverse_amount', inverse='_compute_inverse_amount')

    @api.onchange('invoice_id')
    def _onchange_invoice_id(self):   
        for line in self:
            if line.invoice_id:
                amount_residual_signed = line.invoice_id.amount_residual_signed
                balance = line.invoice_id.company_currency_id._convert(amount_residual_signed, line.invoice_id.currency_id, line.invoice_id.company_id , line.invoice_id.invoice_date or fields.Date.context_today(self))
                amount_currency = line.invoice_id.currency_id._convert(balance, line.reconcile_line_id.payment_id.currency_id, line.reconcile_line_id.payment_id.company_id, line.reconcile_line_id.date_reconcile or fields.Date.context_today(self))
                line.amount_due = amount_currency

    @api.onchange('payment_type')
    def _onchange_domain(self):   
        res={}
        if self.payment_type:
            if self.payment_type == 'outbound':
                domain_line = [('state', '=', 'posted'), ('payment_state', 'in', ['not_paid','partial']),('partner_id', '=', self.partner_id.id), ('journal_id.type', '=', 'purchase')]
            else:
                domain_line = [('state', '=', 'posted'), ('payment_state', 'in', ['not_paid','partial']),('partner_id', '=', self.partner_id.id), ('journal_id.type', '=', 'sale')]
        res['domain'] = {'invoice_id' : domain_line}
        return res

    @api.onchange('amount_due')
    def _compute_inverse_amount(self):
        if self.amount_due:
            amount = self.amount_due*-1 if self.amount_due < 0 else self.amount_due
            self.allocation_amount = self.reconcile_line_id.limit_amount if amount > self.reconcile_line_id.limit_amount else amount
