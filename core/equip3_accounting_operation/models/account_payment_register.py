
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from lxml import etree
import json
from odoo.addons.base.models.ir_ui_view import (
transfer_field_to_modifiers, transfer_node_to_modifiers, transfer_modifiers_to_node,
)

def setup_modifiers(node, field=None, context=None, in_tree_view=False):
    modifiers = {}
    if field is not None:
        transfer_field_to_modifiers(field, modifiers)
    transfer_node_to_modifiers(
        node, modifiers, context=context)
    transfer_modifiers_to_node(modifiers, node)


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'
    
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(AccountPaymentRegister, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        context = self._context

        doc = etree.XML(res['arch'])
        
        if context.get('move_types','') != 'in_invoice':
            if doc.xpath("//field[@name='administration']"):
                node = doc.xpath("//field[@name='administration']")[0]
                node.set('invisible', '1')
                setup_modifiers(node, res['fields']['administration'])
        res['arch'] = etree.tostring(doc, encoding='unicode')
        
        return res
    
  

    branch_id = fields.Many2one(store=True, readonly=False, domain=lambda self: [('id', 'in', self.env.branches.ids)], compute='_compute_branch_id', required=True)
    receipt_approval_matrix_id = fields.Many2one('approval.matrix.accounting', string="Approval Matrix", compute='_get_receipt_approval_matrix')
    is_receipt_approval_matrix = fields.Boolean(string="Is Receipt Approval Matrix", compute='_get_receipt_approve_button_from_config')
    difference_ids = fields.One2many('account.payment.register.payment.difference.line', 'payment_register_id', string="Difference Accounts")
    payment_difference_amount = fields.Monetary(compute='_compute_payment_difference_amount')
    payment_difference = fields.Monetary(string='Payment Difference', default=0.0, currency_field='company_currency_id')
    difference_amount = fields.Monetary(string='Different Amount', default=0.0, currency_field='company_currency_id')
    available_partner_bank_ids = fields.Many2many(
        comodel_name='res.partner.bank',
    )
    partner_bank_id = fields.Many2one('res.partner.bank', string="Recipient Bank Account",
        readonly=False, store=True,
        compute='_compute_partner_bank_id',
        domain="[('id', 'in', available_partner_bank_ids)]",
        check_company=True)
    
    administration = fields.Boolean('Administration')
    analytic_group_ids = fields.Many2many('account.analytic.tag',domain="[('company_id', '=', company_id)]", string="Analytic Group")
    administration_account = fields.Many2one('account.account', string='Administration Account')
    administration_fee = fields.Monetary('Administration Fee', default=0.0, currency_field='company_currency_id')

  
    @api.depends('difference_ids.payment_amount','payment_difference')
    def _compute_payment_difference_amount(self):
        for wizard in self:
            total = sum([line.payment_amount for line in wizard.difference_ids]) or 0.00
            wizard.payment_difference_amount = total
            wizard.payment_difference = total

    @api.onchange('amount')
    def _onchange_amount(self):
        if self.amount:
            self.payment_difference = self.amount - self.source_amount
            self.difference_amount = self.amount - self.source_amount


    @api.depends('company_id')
    def _compute_branch_id(self):
        context = dict(self.env.context) or {}
        account_invoice_id = self.env['account.move'].browse(context.get('active_ids'))
        if account_invoice_id.branch_id:
            self.branch_id = account_invoice_id.branch_id.id
    
    @api.depends('amount', 'company_id', 'branch_id')
    def _get_receipt_approval_matrix(self):
        for record in self:
            matrix_id = False
            if record.payment_type == 'inbound':
                matrix_id = self.env['approval.matrix.accounting'].search([
                        ('company_id', '=', record.company_id.id),
                        ('branch_id', '=', record.branch_id.id),
                        ('min_amount', '<=', record.amount),
                        ('max_amount', '>=', record.amount),
                        ('approval_matrix_type', '=', 'receipt_approval_matrix')
                    ], limit=1)
            elif record.payment_type == 'outbound':
                matrix_id = self.env['approval.matrix.accounting'].search([
                        ('company_id', '=', record.company_id.id),
                        ('branch_id', '=', record.branch_id.id),
                        ('min_amount', '<=', record.amount),
                        ('max_amount', '>=', record.amount),
                        ('approval_matrix_type', '=', 'payment_approval_matrix')
                    ], limit=1)
            record.receipt_approval_matrix_id = matrix_id

    def _get_receipt_approve_button_from_config(self):
        for record in self:
            is_receipt_approval_matrix = False
            if record.payment_type == 'inbound':
                is_receipt_approval_matrix = self.env['ir.config_parameter'].sudo().get_param('is_receipt_approval_matrix', False)
            elif record.payment_type == 'outbound':
                is_receipt_approval_matrix = self.env['ir.config_parameter'].sudo().get_param('is_payment_approval_matrix', False)
            record.is_receipt_approval_matrix = is_receipt_approval_matrix

    @api.onchange('branch_id')
    def onchange_branch_id(self):
        self._get_receipt_approve_button_from_config()
    
    def request_for_approval(self):
        self.ensure_one()
        if self.is_receipt_approval_matrix and not self.receipt_approval_matrix_id:
            raise ValidationError('Approval Matrix must be filled.')
        
        context = dict(self.env.context) or {}
        batches = self._get_batches()
        edit_mode = self.can_edit_wizard and (len(batches[0]['lines']) == 1 or self.group_payment)

        to_reconcile = []
        if edit_mode:
            payment_vals = self._create_payment_vals_from_wizard()
            payment_vals_list = [payment_vals]
            to_reconcile.append(batches[0]['lines'])
        else:
            # Don't group payments: Create one batch per move.
            if not self.group_payment:
                new_batches = []
                for batch_result in batches:
                    for line in batch_result['lines']:
                        new_batches.append({
                            **batch_result,
                            'lines': line,
                        })
                batches = new_batches

            payment_vals_list = []
            for batch_result in batches:
                payment_vals_list.append(self._create_payment_vals_from_batch(batch_result))
                to_reconcile.append(batch_result['lines'])
        account_invoice_id = self.env['account.move'].browse(context.get('active_ids'))
        total_amount = sum(self.env['account.payment'].search([("approval_invoice_id", '=', account_invoice_id.id), ('state', 'in', ('to_approve', 'approved', 'posted'))]).mapped('amount'))
        # if ((total_amount + self.amount) > account_invoice_id.amount_total):
        #     raise ValidationError('The payment request can not exceed the amount residual of payment request before.')
        payments = self.env['account.payment'].create(payment_vals_list)
        if ((total_amount + self.amount) > account_invoice_id.amount_total):
            diff_payment = self.payment_difference * -1 if self.payment_difference < 0 else self.payment_difference
            invoice_amount = self.amount - diff_payment
            payments_difference_ids = self.difference_ids.filtered(lambda line: line.payment_amount != 0)
            receivable_account_id = account_invoice_id.line_ids.filtered(lambda line: line.account_id.internal_type == 'receivable')
            for line in payments.move_id.line_ids:
                if line.account_id in payments_difference_ids.mapped('account_id'):
                    line.write({'debit' : 0.0, 
                                'credit' : diff_payment})
                # move.line_ids.filtered(lambda x: x.account_id.user_type_id.type in ('receivable', 'payable'))    
                if line.account_id == receivable_account_id.account_id:
                    line.write({'debit' : 0.0, 
                                'credit' : invoice_amount})
                    
        # payments.write({'state': 'to_approve','approval_invoice_id': account_invoice_id.id})
        context.update({'default_payment_type': self.payment_type})
        payments.with_context(context)._compute_approving_matrix_lines()
        payments.write({'state': 'to_approve','approval_invoice_id': account_invoice_id.id, 'invoice_origin_ids': [(6, 0, account_invoice_id.ids)]})
        existing_payment_ids = account_invoice_id.invoice_payment_ids.ids
        new_payment_ids = payments.ids
        all_payment_ids = list(set(existing_payment_ids + new_payment_ids))
        account_invoice_id.write({'invoice_payment_ids': [(6, 0, all_payment_ids)]})
        total_amount = sum(self.env['account.payment'].search([("approval_invoice_id", '=', account_invoice_id.id), ('state', 'in', ('to_approve', 'approved', 'posted'))]).mapped('amount'))
        if total_amount == account_invoice_id.amount_total:
            account_invoice_id.write({'is_register_payment_done': True})

        if self._context.get('dont_redirect_to_payments'):
            return True

        action = {
            'name': _('Payments'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'context': {'create': False},
        }
        if len(payments) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': payments.id,
            })
        else:
            action.update({
                'view_mode': 'tree,form',
                'domain': [('id', 'in', payments.ids)],
            })
        return action
            
           
    def _create_payment_vals_from_wizard(self):
        payment_vals = super(AccountPaymentRegister, self)._create_payment_vals_from_wizard()
        if self.difference_ids:
            multiple_write_off_line_vals = []
            if all(line.payment_amount > 0 for line in self.difference_ids) or all(line.payment_amount < 0 for line in self.difference_ids):
                for line in self.difference_ids:
                    multiple_write_off_line_vals.append({
                        'name': line.name,
                        'amount': line.payment_amount or 0.0,
                        'account_id': line.account_id.id,
                    })
            else:
                for line in self.difference_ids:
                    multiple_write_off_line_vals.append({
                        'name': line.name,
                        'amount': line.payment_amount or 0.0,
                        'account_id': line.account_id.id,
                    })
            payment_vals['multiple_write_off_line_vals'] = multiple_write_off_line_vals
        
        if self.administration:
            payment_vals['administration_fee_vals'] = [{'name' : 'Admnistration Fee', 'amount' : self.administration_fee, 'account_id' : self.administration_account.id}]
            
        payment_vals['branch_id'] = self.branch_id.id

        # Remove the values of write_off_line_vals to prevent creating account.payment
        payment_vals['write_off_line_vals'] = {}

        return payment_vals
    
    def _create_payment_vals_from_batch(self, batch_result):
        payment_vals = super(AccountPaymentRegister, self)._create_payment_vals_from_batch(batch_result)
        payment_vals['branch_id'] = self.branch_id.id
        return payment_vals
    
    
    def action_create_payments(self):
        if self.difference_ids and self.difference_amount != self.payment_difference_amount:
                raise ValidationError(_("Post Difference Amount are not equal to Difference Amount."))
        payment = super(AccountPaymentRegister, self).action_create_payments()
        return payment
    
            
class AccountPaymentRegisterDifferenceLine(models.TransientModel):
    _name = 'account.payment.register.payment.difference.line'
    _description = 'Payment Difference Lines'
    
    name = fields.Char(string='Description', required=True)
    payment_register_id = fields.Many2one('account.payment.register', string='Payment Register')
    account_id = fields.Many2one('account.account', string="Difference Account", copy=False, domain="[('deprecated', '=', False), ('company_id', '=', company_id)]", required=True)
    payment_amount = fields.Monetary(string='Allocation Amount', required=True)
    currency_id = fields.Many2one('res.currency', string='Currency', related='payment_register_id.currency_id', help="The payment's currency.")
    payment_difference = fields.Monetary(compute='_compute_payment_difference')
    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True, default=lambda self: self.env.company)