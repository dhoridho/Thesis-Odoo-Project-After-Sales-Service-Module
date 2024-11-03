
import pytz
from pytz import timezone, UTC
from odoo import tools, api, fields, models, _
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from odoo.exceptions import UserError, ValidationError
from lxml import etree
import logging
import requests
from ...equip3_general_features.models.email_wa_parameter import EmailParam,waParam

from odoo.addons.base.models.ir_ui_view import (
transfer_field_to_modifiers, transfer_node_to_modifiers, transfer_modifiers_to_node,
)

_logger = logging.getLogger(__name__)
headers = {'content-type': 'application/json'}

def setup_modifiers(node, field=None, context=None, in_tree_view=False):
    modifiers = {}
    if field is not None:
        transfer_field_to_modifiers(field, modifiers)
    transfer_node_to_modifiers(
        node, modifiers, context=context)
    transfer_modifiers_to_node(modifiers, node)

class AccountPayment(models.Model):
    _inherit = "account.payment"

    @api.model
    def _domain_partner_id(self):
        domain = ['|',('parent_id','=',False),('is_company','=',True)]
        partner_type = self._context.get('default_partner_type') or False
        if partner_type:
            if partner_type == 'customer':
                domain += [('is_customer','=',True)]
            elif partner_type == 'supplier':
                domain += [('is_vendor','=',True)]
        return domain

    payment_transaction_credit = fields.One2many('account.multipayment.credit', 'payment_id', string='Children')
    payment_transaction_credit_count = fields.Integer(string="payment transaction count", default='0')
    payment_transaction_debit = fields.One2many('account.multipayment.debit', 'payment_id', string='Children')
    payment_transaction_debit_count = fields.Integer(string="payment transaction count", default='0')
    partner_id = fields.Many2one('res.partner', domain=_domain_partner_id)
    clearing_account_id = fields.Many2one('account.account', string='Clearing Account', tracking=True)
    from_action_clearing = fields.Boolean("From Action Clearing", default=False, copy=False)
    signature_to_confirm = fields.Boolean(related='partner_id.signature_to_confirm',store=True)
    state = fields.Selection(selection=[
            ('draft', 'Draft'),
            ('posted', 'Posted'),
            ('to_approve', 'Waiting For Approval'),
            ('cancel', 'Cancelled'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
            ('expired', 'Expired'),
            ('failed', 'Payment Failed')
        ], string='Status', required=True, readonly=True, copy=False, tracking=True,
        default='draft')
    

    def button_payment_credit(self):
        self.ensure_one()
        action = {
            'name': _("Payments"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.multipayment.credit',
            'context': {'create': False},
        }
        if len(self.payment_transaction_credit) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': self.payment_transaction_credit.id,
            })
        else:
            action.update({
                'view_mode': 'list,form',
                'domain': [('id', 'in', self.payment_transaction_credit.ids)],
            })
        return action

    def button_payment_debit(self):
        self.ensure_one()
        action = {
            'name': _("Payments"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.multipayment.debit',
            'context': {'create': False},
        }
        if len(self.payment_transaction_debit) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': self.payment_transaction_debit.id,
            })
        else:
            action.update({
                'view_mode': 'list,form',
                'domain': [('id', 'in', self.payment_transaction_debit.ids)],
            })
        return action
    
    
    def mark_invoice_as_paid(self):
        self.ensure_one()
        payment_ids = []
        if len(self.line_credit_ids) > 0:
            for rec in self.line_credit_ids:
                if rec.payment_id.id != False:
                    payment_ids.append(rec.payment_id.id)
        if len(self.line_debit_ids) > 0:
            for rec in self.line_debit_ids:
                if rec.payment_id.id != False:
                    payment_ids.append(rec.payment_id.id)
        # if self.state != 'posted':
        #     raise UserError(_("Only a posted payment can be reconciled with an invoice. Trying to reconcile a payment in state %s.") % (self.state,))
        # if self.invoice_ids:
        #     self.invoice_ids.register_payment(self)
        # return True
        
    
# class AccountMoveLine(models.Model):
#     _inherit = "account.move.line"

#     def unlink(self):
#         for rec in self:
#             if rec.payment_id:
#                 raise UserError(_('You cannot delete a journal item that is linked to a payment.'))
#         return super(AccountMoveLine, self).unlink()

                          

class accountmultipayment(models.Model): 
    _name = "account.multipayment"
    _description = "Multipayment"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']

    def _get_street(self, partner):
        self.ensure_one()
        res = {}
        address = ''
        if partner.street:
            address = "%s" % (partner.street)
        if partner.street2:
            address += ", %s" % (partner.street2)
        html_text = str(tools.plaintext2html(address, container_tag=True))
        data = html_text.split('p>')
        if data:
            return data[1][:-2]
        return False

    def _get_address_details(self, partner):
        self.ensure_one()
        res = {}
        address = ''
        if partner.city:
            address = "%s" % (partner.city)
        if partner.state_id.name:
            address += ", %s" % (partner.state_id.name)
        if partner.zip:
            address += ", %s" % (partner.zip)
        if partner.country_id.name:
            address += ", %s" % (partner.country_id.name)
        html_text = str(tools.plaintext2html(address, container_tag=True))
        data = html_text.split('p>')
        if data:
            return data[1][:-2]
        return False
    
    
    @api.model
    def get_state_selection(self):
        context = self._context
        result = [('draft', 'Draft'), 
                  ('to_approve', 'Waiting For Approval'),
                  ('approved', 'Approved'),
                  ('post', 'Received'),
                  ('canceled', 'Cancel'), 
                  ('cleared', 'Cleared'),
                  ('rejected', 'Rejected')]
        return result
    
    @api.model
    def fields_view_get(self, view_id=None, view_type=False, toolbar=False, submenu=False):
        result = super(accountmultipayment, self).fields_view_get(
            view_id, view_type, toolbar=toolbar, submenu=submenu)
        context = self._context
        doc = etree.XML(result['arch'])
        if context.get('default_partner_type') == 'supplier':
            for node in doc.xpath("//field[@name='receive_date']"):
                node.set('string', 'Payment Date')
                setup_modifiers(node, result['fields']['receive_date'])

        result['arch'] = etree.tostring(doc, encoding='unicode')
        return result

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
    def _domain_partner_id(self):
        domain = [('company_id','in',[self.env.company.id, False])]
        partner_type = self._context.get('default_partner_type') or False
        if partner_type:
            if partner_type == 'customer':
                domain += [('is_customer','=',True)]
            elif partner_type == 'supplier':
                domain += [('is_vendor','=',True)]
        return domain
    
    @api.model
    def _domain_journal_id(self):
        active_company = self.env.company
        return [('company_id', '=', active_company.id), ('type', 'in', ['bank','cash'])]

    branch_id = fields.Many2one('res.branch', check_company=True, domain=_domain_branch, default = _default_branch, readonly=False, required=True)
    name = fields.Char(string='Number', readonly=True, tracking=True)
    partner_id = fields.Many2one('res.partner', required=True, tracking=True, domain=_domain_partner_id)
    amount = fields.Monetary(string='Amount', required=True, tracking=True)
    amount_tmp = fields.Monetary(string='Amount', compute='_compute_amount_tmp', store=True, tracking=True)
    journal_id = fields.Many2one('account.journal', 'Payment Method', required=True,
                                 domain=_domain_journal_id, tracking=True)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id, string='Currency',
                                  required=True, tracking=True)
    date = fields.Date(string='Date', required=True, tracking=True)
    ref = fields.Char(string='Reference', tracking=True)
    memo = fields.Char(string='Memo', tracking=True)
    line_credit_ids = fields.One2many('account.multipayment.credit', 'line_id', string='Credits')
    line_debit_ids = fields.One2many('account.multipayment.debit', 'line_id', string='Debits')
    diff_amount = fields.Monetary(string='Payment Difference', compute='_compute_diff_amount', store=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('to_approve', 'Waiting For Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('post', 'Payment'),
        ('canceled', 'Cancel'),
    ], string='Status', default='draft', tracking=True)
    state1 = fields.Selection(related="state")
    state2 = fields.Selection(related="state")
    partner_type = fields.Selection([
        ('customer', 'Customer'),
        ('supplier', 'Vendor')
    ], string='Partner Type', tracking=True)
    total_amount_credit = fields.Monetary(string="Total Amount", compute='_calculate_credit_amount_total', store=True, tracking=True, compute_sudo=True)
    total_amount_debit = fields.Monetary(string="Total Amount", compute='_calculate_credit_amount_total', store=True, tracking=True, compute_sudo=True)
    payment_id_count = fields.Integer(string="Payment", compute='_calculate_credit_amount_total', compute_sudo=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company.id,
                                 tracking=True, readonly=True)
    # branch_id = fields.Many2one('res.branch', string='Branch', default=lambda self: self.env.user.branch_id.id,
    #                             tracking=True, domain="[('company_id', '=', company_id)]")

    
    create_uid = fields.Many2one('res.users', string='Created by', readonly=True, tracking=True)
    create_date = fields.Datetime(string="Created Date", readonly=True, tracking=True)
    different_move_id = fields.Many2one('account.move', string='Different Journal', readonly=True, tracking=True)
    request_partner_id = fields.Many2one('res.partner', string="Requested Partner")

    # deleted field
    payment_method = fields.Many2one('account.journal', 'Payment Method', domain="[('type', 'in', ['bank','cash'])]") 

    multipul_payment_approval_matrix_id = fields.Many2one('approval.matrix.accounting', string="Approval Matrix", compute='_get_multi_payment_approval_matrix')
    is_multi_payment_approval_matrix = fields.Boolean(string="Is Customer and Vendor Approval Matrix", compute='_get_multi_payment_approve_button_from_config')
    is_allowed_to_wa_notification_multi_payment = fields.Boolean(string="Is Allowed to WA Notification", compute='_get_multi_payment_approve_button_from_config')
    is_allowed_to_wa_notification_multi_receipt = fields.Boolean(string="Is Allowed to WA Notification", compute='_get_multi_payment_approve_button_from_config')
    is_approve_button = fields.Boolean(string='Is Approve Button', compute='_get_approve_button_multi_receipt', store=False)
    approved_matrix_ids = fields.One2many('approval.matrix.accounting.lines', 'multi_receipt_id', string="Approved Matrix")
    approval_matrix_line_id = fields.Many2one('approval.matrix.accounting.lines', string='Approval Matrix Line', compute='_get_approve_button_multi_receipt', store=False)

    action_validate_boolean = fields.Boolean(string='Confirm', compute='_get_default_invisible')
    action_draft_boolean = fields.Boolean(string='Reset to Draft', compute='_get_default_invisible')
    action_cancel_boolean = fields.Boolean(string='Cancel', compute='')
    request_for_approval_boolean = fields.Boolean(string='Request For Approval', compute='_get_default_invisible')
    action_approved_rp_boolean = fields.Boolean(string='Approved', compute='_get_default_invisible')
    rp_reject_boolean = fields.Boolean(string='Reject', compute='_get_default_invisible')
    state_boolean = fields.Boolean(string='state', compute='_get_default_invisible')
    state1_boolean = fields.Boolean(string='state1', compute='_get_default_invisible')
    state2_boolean = fields.Boolean(string='state2', compute='_get_default_invisible')
    
    difference_ids = fields.One2many('account.multipayment.difference', 'payment_id', string="Difference Accounts")
    payment_difference_amount = fields.Monetary(compute='_compute_payment_difference_amount')

    #delete this field after xml deleted
    writeoff_account_id = fields.Many2one('account.account', 'Counterpart Account')
    writeoff_label = fields.Char(string='Counterpart Comment')

    payment_type = fields.Selection([
        ('payment', 'Payment'),
        ('giro', 'Giro')
        ], string='Payment Type', tracking=True, default='payment')
    clearing_account_id = fields.Many2one('account.account', string='Clearing Account', tracking=True)
    move_id = fields.Many2one('account.move', string='Clearing Entry', tracking=True, readonly=True)
    due_date = fields.Date(string='Due Date', tracking=True)
    receive_date = fields.Date(string='Receive Date', tracking=True)
    clearing_date = fields.Date(string='Clearing Date', tracking=True)
    is_vendor = fields.Boolean(compute='_compute_partner_type')
    state = fields.Selection(selection= lambda self: self.get_state_selection(), string='Status', default='draft', tracking=True)
    state1 = fields.Selection(related="state")
    state2 = fields.Selection(related="state")
    payment_ids = fields.Many2many('account.payment', string="Payment", compute='_getpayment_ids')
    invoice_cutoff_date = fields.Date(string='Cut Off Date', tracking=True)
    is_cutoff_date = fields.Boolean(string='Is Cut Off Date', compute='_get_cut_off_date_config')


    def unlink(self):
        for rec in self:
            if rec.state not in ('draft', 'canceled'):
                raise UserError(_('You cannot delete a payment that is not draft or canceled.'))
        return super(accountmultipayment, self).unlink()
    
    @api.onchange('date')
    @api.depends('date')
    def set_cutoff_date(self):
        is_cutoff_date = self.env['ir.config_parameter'].sudo().get_param('is_invoice_cutoff_date', False)
        if is_cutoff_date:
            cutoff_date = self.env['ir.config_parameter'].sudo().get_param('invoice_cutoff_date', '1')
            for rec in self:
                if rec.date:
                    if int(cutoff_date) <= int(self.last_day_of_month(rec.date).day):
                        if rec.date.day < int(cutoff_date):
                            rec.invoice_cutoff_date = datetime(rec.date.year, rec.date.month, int(cutoff_date)) - relativedelta(months=1)
                        else:
                            rec.invoice_cutoff_date = datetime(rec.date.year, rec.date.month, int(cutoff_date))
                    else:
                        if rec.date.day < int(cutoff_date):
                            rec.invoice_cutoff_date = datetime(rec.date.year, rec.date.month, int(self.last_day_of_month(rec.date).day)) - relativedelta(months=1)
                        else:
                            rec.invoice_cutoff_date = datetime(rec.date.year, rec.date.month, int(self.last_day_of_month(rec.date).day))

    def last_day_of_month(self, day):
        next_month = day.replace(day=28) + relativedelta(days=4)
        return next_month - relativedelta(days=next_month.day) 
    
    def _get_cut_off_date_config(self):
        for record in self:
            is_cutoff_date = self.env['ir.config_parameter'].sudo().get_param('is_invoice_cutoff_date', False)
            record.is_cutoff_date = is_cutoff_date

    def _getpayment_ids(self):
        payment_ids = []
        if len(self.line_credit_ids) > 0:
            for rec in self.line_credit_ids:
                if rec.payment_id.id != False:
                    payment_ids.append(rec.payment_id.id)
        if len(self.line_debit_ids) > 0:
            for rec in self.line_debit_ids:
                if rec.payment_id.id != False:
                    payment_ids.append(rec.payment_id.id)
        for payment in self:
            payment.payment_ids = [(6, 0, payment_ids)]

    def _compute_partner_type(self):
        if self.partner_type == 'supplier':
            self.is_vendor = True
        else:
            self.is_vendor = False
            

    def action_validate_giro(self):
        for rec in self:
            self.check_closed_period()
            if bool(rec.amount_tmp and rec.amount_tmp <= 0) or bool(not rec.amount_tmp):
                raise ValidationError(_('Amount must be no equals to 0'))
            if len(rec.line_credit_ids) > 0:
                for inv_credit in rec.line_credit_ids:
                    if inv_credit.amount == 0:
                        continue
                    payment = self._create_payments(inv_credit)
                    # payment.move_id.line_ids.filtered(lambda line: line.credit).write({'account_id': rec.clearing_account_id.id})

                    # move_id = payment.move_id
                    # currency_id = rec.currency_id.id if rec.currency_id else None
                    # partner_id = rec.partner_id.id

                    # move_id.write({
                    #     'currency_id': currency_id,
                    #     'partner_id': partner_id,
                    #     'ref': rec.ref,
                    # })

                    rec.receive_date = payment.date
                    rec.due_date = payment.create_date
                    inv_credit.payment_id = payment.id
                    payment.update({'payment_transaction_debit_count' : '1'})
                    payment._action_reconcile_payment(inv_credit)
                    
            if len(rec.line_debit_ids) > 0:
                for inv_debit in rec.line_debit_ids:
                    if inv_debit.amount == 0:
                        continue
                    payment = self._create_payments(inv_debit)
                    # payment.move_id.line_ids.filtered(lambda line: line.debit).write({'account_id': rec.clearing_account_id.id})

                    # move_id = payment.move_id
                    # currency_id = rec.currency_id.id if rec.currency_id else None
                    # partner_id = rec.partner_id.id

                    # move_id.write({
                    #     'currency_id': currency_id,
                    #     'partner_id': partner_id,
                    #     'ref': rec.ref,
                    # })

                    rec.receive_date = payment.date
                    rec.due_date = payment.create_date
                    inv_debit.payment_id = payment.id
                    payment.update({'payment_transaction_debit_count' : '1'})
                    payment._action_reconcile_payment(inv_debit)            

            # payment.action_post()
            if self.diff_amount == 0:
                rec.write({'state': 'post'})
            else:
                moves = self.create_diff_Journal()
                rec.write({'state': 'post', 'different_move_id' : moves.id})
            
    @api.depends('difference_ids.payment_amount','diff_amount')
    def _compute_payment_difference_amount(self):
        for payment in self:
            total = sum([line.payment_amount for line in payment.difference_ids]) or 0.00
            payment.payment_difference_amount = total

    @api.depends('is_multi_payment_approval_matrix', 'state', 'is_approve_button')
    @api.onchange('is_multi_payment_approval_matrix', 'state', 'is_approve_button')
    def _get_default_invisible(self):
        if self.state != 'post':
            self.action_validate_boolean = False
            self.action_draft_boolean = False
        else:
            self.action_validate_boolean = True
            self.action_draft_boolean = True

        if self.is_multi_payment_approval_matrix == True:
            self.action_validate_boolean = True
            self.action_draft_boolean = True
            self.state_boolean = True
        else:
            self.state_boolean = False
        
        if self.is_multi_payment_approval_matrix == True and self.state != 'post':
            self.action_cancel_boolean = True
        else:
            self.action_cancel_boolean = False

        if self.is_multi_payment_approval_matrix == False and self.state != 'draft':
            self.request_for_approval_boolean = True
        else:
            self.request_for_approval_boolean = False

        if self.is_multi_payment_approval_matrix == False and self.is_approve_button == False and self.state != 'to_approve':
            self.action_approved_rp_boolean = True
            self.rp_reject_boolean = True
        else:
            self.action_approved_rp_boolean = False
            self.rp_reject_boolean = False
        if self.state1 == 'rejected':
            self.state1_boolean = True
        else:
            if self.is_multi_payment_approval_matrix == False:
                self.state1_boolean = True
            else:
                self.state1_boolean = False
                self.state_boolean = True

        if self.state2 != 'rejected':
            self.state2_boolean = True
        else:
            if self.is_multi_payment_approval_matrix == False:
                self.state2_boolean = True
            else:
                self.state2_boolean = False
                self.state_boolean = True
    
    def action_rejected(self):
        self.unlink_all_moves()
        self.write({'state': 'rejected'})

    def action_draft(self):
        self.unlink_all_moves()
        if self.different_move_id != False:
            self.update({'different_move_id' : False})
        if self.move_id != False:
            self.update({'move_id' : False})
        self.unlink_payment()
        if len(self.line_credit_ids) > 0:
            for rec in self.line_credit_ids:
                if rec.payment_id.id != False:
                    rec.update({'payment_id' : False})
        if len(self.line_debit_ids) > 0:
            for rec in self.line_debit_ids:
                if rec.payment_id.id != False:
                    rec.update({'payment_id' : False})
        self.write({'state': 'draft'})


    def _clearing_payment(self, moves):
        moves = moves
        payment = moves.payment_id
        payment.update({'move_id' : moves.id})
        return payment


    def action_clearing(self):
        AccountMove = self.env['account.move']
        AccountMoveLine = self.env['account.move.line']
        line_ids_det = []
        partner_type = self.partner_type

        # credit_line_account = partner_type =='supplier' and self.clearing_account_id.id or self.journal_id.default_account_id.id
        # debit_line_account = partner_type =='supplier' and self.journal_id.default_account_id.id or self.clearing_account_id.id

        credit_line_account = partner_type =='supplier' and self.journal_id.default_account_id.id or self.clearing_account_id.id
        debit_line_account = partner_type =='supplier' and self.clearing_account_id.id or self.journal_id.default_account_id.id
        # payment_line = self.line_credit_ids.payment_id or self.line_debit_ids.payment_id
        
        payment_line_ids = self.line_credit_ids.mapped('payment_id') or self.line_debit_ids.mapped('payment_id')

        for payment_line in payment_line_ids:
            debit_line = {
                    'name': '',
                    'account_id': debit_line_account,
                    'credit':  0.0,
                    'debit': self.amount
                    }
            
            credit_line = {
                    'name': '',
                    'account_id': credit_line_account,
                    'credit': self.amount,
                    'debit': 0.0
                    }
            
            line_ids_det.append((0,0, debit_line))
            line_ids_det.append((0,0, credit_line))
            
            
            all_move_vals = {
                    'date': date.today(),
                    'journal_id': self.journal_id.id,
                    'ref': self.ref,
                    'partner_id': self.partner_id.id,
                    'partner_bank_id': self.partner_id.bank_ids and self.partner_id.bank_ids[0].id or False,
                    'payment_id': payment_line.id,
                    'line_ids': line_ids_det
                }
                    
            AccountMove = self.env['account.move']
            moves = AccountMove.create(all_move_vals)
            moves.post()

            # moves.payment_id.write({'move_id' : moves.id})
            # payment_line.with_context(from_action_clearing=True).write({'move_id': moves.id})

        self.update({'state' : 'cleared',
                     'clearing_date' : moves.create_date,
                     'move_id': moves.id})

    def unlink_all_moves(self):
        if self.different_move_id != False:
            self.unlink_diff_journal()
        if self.move_id != False:
            self.unlink_clearing()
        self.unlink_payment()

    def unlink_clearing(self):
        # OVERRIDE to unlink the inherited account.move (move_id field) as well.
        moves = self.with_context(force_delete=True).move_id
        moves.button_draft()
        moves.button_cancel()
        # moves.unlink()
        return moves

    def unlink_diff_journal(self):
        # OVERRIDE to unlink the inherited account.move (move_id field) as well.
        moves = self.with_context(force_delete=True).different_move_id
        moves.button_draft()
        moves.button_cancel()
        # moves.unlink()
        return moves

    def unlink_payment(self):
        payment = self.env['account.payment']
        if len(self.line_credit_ids) > 0:
            for rec in self.line_credit_ids:
                if rec.payment_id.id != False:
                    payment_id = payment.search([('id', '=', rec.payment_id.id)])
                    payment_id.action_draft()
                    payment_id.action_cancel()
                    # payment_id.unlink()
        if len(self.line_debit_ids) > 0:
            for rec in self.line_debit_ids:
                if rec.payment_id.id != False:
                    payment_id = payment.search([('id', '=', rec.payment_id.id)])
                    payment_id.action_draft()
                    payment_id.action_cancel()
                    # payment_id.unlink()
        return payment

    @api.depends('amount', 'company_id', 'branch_id')
    def _get_multi_payment_approval_matrix(self):
        for record in self:
            matrix_id = False
            if record.partner_type == 'customer' and not record.payment_type == 'giro':
                matrix_id = self.env['approval.matrix.accounting'].search([
                        ('company_id', '=', record.company_id.id),
                        ('branch_id', '=', record.branch_id.id),
                        ('min_amount', '<=', record.amount),
                        ('max_amount', '>=', record.amount),
                        ('approval_matrix_type', '=', 'customer_multi_receipt_approval_matrix')
                    ], limit=1)
            elif record.partner_type == 'supplier' and not record.payment_type == 'giro':
                matrix_id = self.env['approval.matrix.accounting'].search([
                        ('company_id', '=', record.company_id.id),
                        ('branch_id', '=', record.branch_id.id),
                        ('min_amount', '<=', record.amount),
                        ('max_amount', '>=', record.amount),
                        ('approval_matrix_type', '=', 'vendor_multi_receipt_approval_matrix')
                    ], limit=1)
            elif record.partner_type == 'customer' and record.payment_type == 'giro':
                matrix_id = self.env['approval.matrix.accounting'].search([
                        ('company_id', '=', record.company_id.id),
                        ('branch_id', '=', record.branch_id.id),
                        ('min_amount', '<=', record.amount),
                        ('max_amount', '>=', record.amount),
                        ('approval_matrix_type', '=', 'receipt_giro_approval_matrix')
                    ], limit=1)
            elif record.partner_type == 'supplier' and record.payment_type == 'giro':
                matrix_id = self.env['approval.matrix.accounting'].search([
                        ('company_id', '=', record.company_id.id),
                        ('branch_id', '=', record.branch_id.id),
                        ('min_amount', '<=', record.amount),
                        ('max_amount', '>=', record.amount),
                        ('approval_matrix_type', '=', 'payment_giro_approval_matrix')
                    ], limit=1)
            record.multipul_payment_approval_matrix_id = matrix_id

    def _get_multi_payment_approve_button_from_config(self):
        for record in self:
            is_multi_payment_approval_matrix = False
            record.is_allowed_to_wa_notification_multi_receipt = False
            record.is_allowed_to_wa_notification_multi_payment = False
            if record.partner_type == 'customer' and not record.payment_type == 'giro':
                # is_multi_payment_approval_matrix = self.env['ir.config_parameter'].sudo().get_param('is_customer_multi_receipt_approval_matrix', False)
                is_multi_payment_approval_matrix = self.env['accounting.config.settings'].search([], limit=1).is_allow_customer_multi_receipt_approval_matrix
                record.is_allowed_to_wa_notification_multi_receipt = self.env['accounting.config.settings'].search([], limit=1).is_allow_customer_multi_receipt_wa_notification
            elif record.partner_type == 'supplier' and not record.payment_type == 'giro':
                # is_multi_payment_approval_matrix = self.env['ir.config_parameter'].sudo().get_param('is_vendor_multipayment_approval_matrix', False)
                is_multi_payment_approval_matrix = self.env['accounting.config.settings'].search([], limit=1).is_allow_vendor_multi_payment_approval_matrix
                record.is_allowed_to_wa_notification_multi_payment = self.env['accounting.config.settings'].search([], limit=1).is_allow_vendor_multi_payment_wa_notification
            elif record.payment_type == 'giro' and record.partner_type == 'customer':
                is_multi_payment_approval_matrix = self.env['ir.config_parameter'].sudo().get_param('is_receipt_giro_approval_matrix', False)
            elif record.payment_type == 'giro' and record.partner_type == 'supplier':
                is_multi_payment_approval_matrix = self.env['ir.config_parameter'].sudo().get_param('is_payment_giro_approval_matrix', False)
            record.is_multi_payment_approval_matrix = is_multi_payment_approval_matrix

    def _get_approve_button_multi_receipt(self):
        for record in self:
            matrix_line = sorted(record.approved_matrix_ids.filtered(lambda r: not r.approved), key=lambda r:r.sequence)
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

    @api.onchange('multipul_payment_approval_matrix_id')
    def _compute_approving_matrix_lines(self):
        data = [(5, 0, 0)]
        for record in self:
            if record.state == 'draft' and record.is_multi_payment_approval_matrix:
                record.approved_matrix_ids = []
                counter = 1
                record.approved_matrix_ids = []
                for rec in record.multipul_payment_approval_matrix_id: 
                    for line in rec.approval_matrix_line_ids:
                        data.append((0, 0, {
                            'sequence' : counter,
                            'user_ids' : [(6, 0, line.user_ids.ids)],
                            'minimum_approver' : line.minimum_approver,
                        }))
                        counter += 1
                record.approved_matrix_ids = data

    def _send_wa_request_for_approval_multi_receipt(self, approver, phone_num, currency, url, submitter):
        wa_template = self.env.ref('equip3_accounting_operation.wa_template_new_request_approval_customer_multi_receipt_1')
        wa_sender = waParam()
        if wa_template:
            if wa_template.broadcast_template_id:
                special_var = [{'variable' : '{approver_name}', 'value' : approver.name},
                               {'variable' : '{submitter_name}', 'value' : submitter},
                                {'variable' : '{url}', 'value' : url},]
                
                wa_sender.set_special_variable(special_var)
                wa_sender.send_wa_qiscuss(wa_template.message_line_ids, self, wa_template, phone_num=str(phone_num))
            else:
                raise ValidationError(_("Broadcast Template not found!"))
    
    def _send_wa_request_for_approval_multi_payment(self, approver, phone_num, currency, url, submitter):
        wa_template = self.env.ref('equip3_accounting_operation.wa_template_new_request_approval_vendor_multi_payment_1')
        wa_sender = waParam()
        if wa_template:
            if wa_template.broadcast_template_id:
                special_var = [{'variable' : '{approver_name}', 'value' : approver.name},
                               {'variable' : '{submitter_name}', 'value' : submitter},
                                {'variable' : '{url}', 'value' : url},]
                
                wa_sender.set_special_variable(special_var)
                wa_sender.send_wa_qiscuss(wa_template.message_line_ids, self, wa_template, phone_num=str(phone_num))
            else:
                raise ValidationError(_("Broadcast Template not found!"))

    def request_for_approval(self):
        self.check_closed_period()
        for record in self:
            if record.partner_type == "supplier":
                action_id = self.env.ref('equip3_accounting_operation.action_payment_giro')
                template_id = self.env.ref('equip3_accounting_operation.email_template_payment_giro_approval_matrix')
                wa_notification = self.is_allowed_to_wa_notification_multi_payment
                # wa_template_id = self.env.ref('equip3_accounting_operation.wa_template_req_payment_giro_wa')
                wa_template_id = self.env.ref('equip3_accounting_operation.wa_template_request_for_approval_payment_giro')
            else:
                action_id = self.env.ref('equip3_accounting_operation.action_receipt_giro')
                template_id = self.env.ref('equip3_accounting_operation.email_template_receipt_giro_approval_matrix')
                wa_notification = self.is_allowed_to_wa_notification_multi_receipt
                # wa_template_id = self.env.ref('equip3_accounting_operation.wa_template_req_receipt_giro_wa')
                wa_template_id = self.env.ref('equip3_accounting_operation.wa_template_request_for_approval_receipt_giro')
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/web#id=' + str(record.id) + '&action='+ str(action_id.id) + '&view_type=form&model=account.multipayment'
            record.request_partner_id = self.env.user.partner_id.id
            currency = ""
            if record.currency_id.position == 'before':
                currency = record.currency_id.symbol + str(record.amount)
            else:
                currency = str(record.amount) + ' ' + record.currency_id.symbol
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
                        "due_date": record.due_date,
                        "date_invoice": record.date,
                        "currency": currency,
                    }
                    template_id.with_context(ctx).send_mail(record.id, True)
                    phone_num = str(approver.mobile or approver.partner_id.mobile)
                    if record.payment_type == 'payment':
                        if wa_notification:
                            if record.partner_type == "customer":
                                record._send_wa_request_for_approval_multi_receipt(approver, phone_num, currency, url, submitter=self.env.user.name)
                            else:
                                record._send_wa_request_for_approval_multi_payment(approver, phone_num, currency, url, submitter=self.env.user.name)
                    else:
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
                    "due_date": record.due_date,
                    "date_invoice": record.date,
                    "currency": currency,
                }
                template_id.with_context(ctx).send_mail(record.id, True)
                phone_num = str(approver.mobile or approver.partner_id.mobile)
                if record.payment_type == 'payment':
                    if wa_notification:
                        if record.partner_type == "customer":
                            record._send_wa_request_for_approval_multi_receipt(approver, phone_num, currency, url, submitter=self.env.user.name)
                        else:
                            record._send_wa_request_for_approval_multi_payment(approver, phone_num, currency, url, submitter=self.env.user.name)
                else:
                    record._send_whatsapp_message(wa_template_id, approver, currency, url)
            record.write({'state': 'to_approve'})

    def _send_wa_reject_multi_receipt(self, submitter, phone_num, created_date, approver = False, reason = False):
        wa_template = self.env.ref('equip3_accounting_operation.wa_template_new_rejection_customer_multi_receipt_1')
        wa_sender = waParam()
        if wa_template:
            if wa_template.broadcast_template_id:
                special_var = [{'variable' : '{submitter_name}', 'value' : submitter},
                                {'variable' : '{approver_name}', 'value' : approver},
                               {'variable' : '{create_date}', 'value' : created_date},
                                 {'variable' : '{feedback}', 'value' : reason}]

                wa_sender.set_special_variable(special_var)
                wa_sender.send_wa_qiscuss(wa_template.message_line_ids, self, wa_template, phone_num=str(phone_num))
            else:
                raise ValidationError(_("Broadcast Template not found!"))

    def _send_wa_reject_multi_payment(self, submitter, phone_num, created_date, approver = False, reason = False):
        wa_template = self.env.ref('equip3_accounting_operation.wa_template_new_rejection_vendor_multi_payment_1')
        wa_sender = waParam()
        if wa_template:
            if wa_template.broadcast_template_id:
                special_var = [{'variable' : '{submitter_name}', 'value' : submitter},
                                {'variable' : '{approver_name}', 'value' : approver},
                               {'variable' : '{create_date}', 'value' : created_date},
                                 {'variable' : '{feedback}', 'value' : reason}]

                wa_sender.set_special_variable(special_var)
                wa_sender.send_wa_qiscuss(wa_template.message_line_ids, self, wa_template, phone_num=str(phone_num))
            else:
                raise ValidationError(_("Broadcast Template not found!"))

    def _send_wa_approval_multi_receipt(self, approver, phone_num, created_date, submitter):
        wa_template = self.env.ref('equip3_accounting_operation.wa_template_new_approval_customer_multi_receipt_1')
        wa_sender = waParam()
        if wa_template:
            if wa_template.broadcast_template_id:
                special_var = [{'variable' : '{approver_name}', 'value' : approver.name},
                               {'variable' : '{submitter_name}', 'value' : submitter},
                                {'variable' : '{create_date}', 'value' : created_date},]
                
                wa_sender.set_special_variable(special_var)
                wa_sender.send_wa_qiscuss(wa_template.message_line_ids, self, wa_template, phone_num=str(phone_num))
            else:
                raise ValidationError(_("Broadcast Template not found!"))
            
    def _send_wa_approval_multi_payment(self, approver, phone_num, created_date, submitter):
        wa_template = self.env.ref('equip3_accounting_operation.wa_template_new_approval_vendor_multi_payment_1')
        wa_sender = waParam()
        if wa_template:
            if wa_template.broadcast_template_id:
                special_var = [{'variable' : '{approver_name}', 'value' : approver.name},
                               {'variable' : '{submitter_name}', 'value' : submitter},
                                {'variable' : '{create_date}', 'value' : created_date},]
                
                wa_sender.set_special_variable(special_var)
                wa_sender.send_wa_qiscuss(wa_template.message_line_ids, self, wa_template, phone_num=str(phone_num))
            else:
                raise ValidationError(_("Broadcast Template not found!"))
            
    def action_approved_rp(self):
        for record in self:
            if record.partner_type == "supplier":
                action_id = self.env.ref('equip3_accounting_operation.action_payment_giro')
                template_id = self.env.ref('equip3_accounting_operation.email_template_payment_giro_approval_matrix')
                template_id_submitter = self.env.ref('equip3_accounting_operation.email_template_payment_giro_submitter_approval_matrix')
                wa_notification = self.is_allowed_to_wa_notification_multi_payment
                # wa_template_id = self.env.ref('equip3_accounting_operation.wa_template_req_payment_giro_wa')
                wa_template_id = self.env.ref('equip3_accounting_operation.wa_template_request_for_approval_payment_giro')
                # wa_template_submitted = self.env.ref('equip3_accounting_operation.wa_template_appr_payment_giro_wa')
                wa_template_submitted = self.env.ref('equip3_accounting_operation.wa_template_approval_for_payment_giro')
            else:
                action_id = self.env.ref('equip3_accounting_operation.action_receipt_giro')
                template_id = self.env.ref('equip3_accounting_operation.email_template_receipt_giro_approval_matrix')
                template_id_submitter = self.env.ref('equip3_accounting_operation.email_template_receipt_giro_submitter_approval_matrix')
                wa_notification = self.is_allowed_to_wa_notification_multi_receipt
                # wa_template_id = self.env.ref('equip3_accounting_operation.wa_template_req_receipt_giro_wa')
                wa_template_id = self.env.ref('equip3_accounting_operation.wa_template_request_for_approval_receipt_giro')
                # wa_template_submitted = self.env.ref('equip3_accounting_operation.wa_template_appr_receipt_giro_wa')
                wa_template_submitted = self.env.ref('equip3_accounting_operation.wa_template_approval_for_receipt_giro')
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/web#id=' + str(record.id) + '&action='+ str(action_id.id) + '&view_type=form&model=account.multipayment'
            created_date = record.create_date.date()
            user = self.env.user
            currency = ''
            if record.currency_id.position == 'before':
                currency = record.currency_id.symbol + str(record.amount)
            else:
                currency = str(record.amount) + ' ' + record.currency_id.symbol
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
                                    "due_date": record.due_date,
                                    "date_invoice": record.date,
                                    "currency": currency,
                                }
                                template_id.sudo().with_context(ctx).send_mail(record.id, True)
                                phone_num = str(approving_matrix_line_user.mobile or approving_matrix_line_user.partner_id.mobile)
                                if record.payment_type == 'payment':
                                    if wa_notification:
                                        if record.partner_type == "customer":
                                            record._send_wa_approval_multi_receipt(approving_matrix_line_user, phone_num, created_date, self.env.user.name)
                                        else:
                                            record._send_wa_approval_multi_payment(approving_matrix_line_user, phone_num, created_date, self.env.user.name)
                                else:
                                    record._send_whatsapp_message(wa_template_id, approving_matrix_line_user, currency, url)
                        else:
                            if next_approval_matrix_line_id and next_approval_matrix_line_id[0].user_ids:
                                # approver = record.approved_matrix_ids[0].user_ids[0]
                                ctx = {
                                    'email_from' : self.env.user.company_id.email,
                                    'email_to' : next_approval_matrix_line_id[0].user_ids[0].partner_id.email,
                                    'approver_name' : next_approval_matrix_line_id[0].user_ids[0].name,
                                    'date': date.today(),
                                    'submitter' : self.env.user.name,
                                    'url' : url,
                                    "due_date": record.due_date,
                                    "date_invoice": record.date,
                                    "currency": currency,
                                }
                                template_id.sudo().with_context(ctx).send_mail(record.id, True)
                                phone_num = str(next_approval_matrix_line_id[0].user_ids[0].mobile or next_approval_matrix_line_id[0].user_ids[0].partner_id.mobile)
                                if record.payment_type == 'payment':
                                    if wa_notification:
                                        if record.partner_type == "customer":
                                            record._send_wa_approval_multi_receipt(next_approval_matrix_line_id[0].user_ids[0], phone_num, created_date, self.env.user.name)
                                        else:
                                            record._send_wa_approval_multi_payment(next_approval_matrix_line_id[0].user_ids[0], phone_num, created_date, self.env.user.name)
                                else:
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
                    "due_date": record.due_date,
                    "date_invoice": record.date,
                    "currency": currency,
                }
                template_id_submitter.sudo().with_context(ctx).send_mail(record.id, True)
                phone_num = str(record.request_partner_id.mobile or record.request_partner_id.partner_id.mobile)
                if record.payment_type == 'payment':
                    if wa_notification:
                        if record.partner_type == "customer":
                            record._send_wa_approval_multi_receipt(record.request_partner_id, phone_num, created_date, self.env.user.name)
                        else:
                            record._send_wa_approval_multi_payment(record.request_partner_id, phone_num, created_date, self.env.user.name)
                else:
                    record._send_whatsapp_message(wa_template_submitted, record.request_partner_id, currency, url)

    def rp_reject(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Approval Marix Reject',
            'res_model': 'multi.receipt.matrix.reject',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
        }

    def _send_whatsapp_message(self, template_id, approver, currency=False, url=False, reason=False):
        wa_sender = waParam()
        for record in self:
            if record.partner_type in ['supplier', 'customer']:
                string_test = str(template_id.message)
                if "${approver_name}" in string_test:
                    string_test = string_test.replace("${approver_name}", approver.name)
                if "${submitter_name}" in string_test:
                    string_test = string_test.replace("${submitter_name}", record.request_partner_id.name)
                if "${amount}" in string_test:
                    string_test = string_test.replace("${amount}", str(record.amount))
                if "${currency}" in string_test:
                    string_test = string_test.replace("${currency}", currency)
                if "${partner_name}" in string_test:
                    string_test = string_test.replace("${partner_name}", record.partner_id.name)
                if "${due_date}" in string_test:
                    if record.due_date :
                        string_test = string_test.replace("${due_date}", fields.Datetime.from_string(
                        record.due_date).strftime('%d/%m/%Y'))
                    else:
                        string_test = string_test.replace("${due_date}", "")

                if "${date}" in string_test:
                    string_test = string_test.replace("${date}", fields.Datetime.from_string(
                        record.date).strftime('%d/%m/%Y'))
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


    @api.depends('line_credit_ids', 'line_debit_ids', 'line_credit_ids.payment_id', 'line_debit_ids.payment_id')
    def _calculate_credit_amount_total(self):
        for rec in self:
            rec.total_amount_credit = sum(rec.line_credit_ids.mapped('amount'))            
            rec.total_amount_debit = sum(rec.line_debit_ids.mapped('amount'))
            payment_count = 0
            if len(rec.line_credit_ids) > 0:
                for record in rec.line_credit_ids:
                    if record.payment_id.id != False:
                        payment_count += 1
            if len(rec.line_debit_ids) > 0:
                for record in rec.line_debit_ids:
                    if record.payment_id.id != False:
                        payment_count += 1
            rec.payment_id_count = payment_count

    @api.onchange('total_amount_credit', 'total_amount_debit')
    def compute_payment_amount(self):
        for rec in self:
            if rec.partner_type == 'customer':
                total = rec.total_amount_debit - rec.total_amount_credit
            else:
                total = rec.total_amount_credit - rec.total_amount_debit
            rec.amount = total

    @api.depends('amount')
    def _compute_amount_tmp(self):
        for rec in self:
            rec.amount_tmp = rec.amount
            if rec.amount < 0:
                raise ValidationError(_('Amount must be greater than 0.'))
            
        # for line in self.line_credit_ids:
        #     if line.amount > line.base_amount:
        #         raise ValidationError(_('Amount must be less than or equal to the original amount'))
            
        # for line in self.line_debit_ids:
        #     if line.amount > line.base_amount:
        #         raise ValidationError(_('Amount must be less than or equal to the original amount'))
            


    @api.depends('amount', 'total_amount_credit', 'total_amount_debit')
    def _compute_diff_amount(self):
        for rec in self:
            if self.partner_type == 'customer':
                rec.diff_amount = rec.amount - (rec.total_amount_debit - rec.total_amount_credit)
            else:
                rec.diff_amount = rec.amount - (rec.total_amount_credit - rec.total_amount_debit)

    @api.model
    def create(self, vals):
        if vals.get('amount', 0) < 0:
            raise ValidationError(_('Amount must be greater than 0.'))
        
        if vals.get('name', _('New')) == _('New'):
            seq_date = None
            if 'date' in vals:
                seq_date = fields.Datetime.context_timestamp(self, fields.Datetime.to_datetime(vals['date']))
            if vals['partner_type'] == 'customer':
                if 'payment_type' in vals:
                    if vals['payment_type'] == 'giro':
                        vals['name'] = self.env['ir.sequence'].next_by_code('receipt.giro', sequence_date=seq_date) or _('New')
                    else:
                        vals['name'] = self.env['ir.sequence'].next_by_code('customer.account.multipayment', sequence_date=seq_date) or _('New')
                else:
                    vals['name'] = self.env['ir.sequence'].next_by_code('customer.account.multipayment', sequence_date=seq_date) or _('New')
            elif vals['partner_type'] == 'supplier':
                if 'payment_type' in vals:
                    if vals['payment_type'] == 'giro':
                        vals['name'] = self.env['ir.sequence'].next_by_code('payment.giro', sequence_date=seq_date) or _('New')
                    else:                    
                        vals['name'] = self.env['ir.sequence'].next_by_code('vendor.account.multipayment', sequence_date=seq_date) or _('New')
                else:                    
                    vals['name'] = self.env['ir.sequence'].next_by_code('vendor.account.multipayment', sequence_date=seq_date) or _('New')
        result = super(accountmultipayment, self).create(vals)
        return result



    @api.onchange('partner_id', 'invoice_cutoff_date','currency_id')
    def _write_line_detail(self):
        for rec in self:
            rec._get_multi_payment_approve_button_from_config()
            list_line_credits = [(5, 0, 0)]
            list_line_debits = [(5, 0, 0)]
            is_cutoff_date = self.env['ir.config_parameter'].sudo().get_param('is_invoice_cutoff_date', False)
            if is_cutoff_date:
                invoices = self.env['account.move'].search(['&', '&', '&', '&', '&', 
                            ('partner_id', '=', rec.partner_id.id), 
                            ('currency_id', '=', rec.currency_id.id),
                            ('move_type', 'in', ['out_invoice', 'in_refund', 'in_invoice', 'out_refund']),
                            ('state', '=', 'posted'), ('payment_state', 'in', ['not_paid', 'partial']),
                            ('amount_residual_signed', '!=', 0),
                            ('invoice_date', '<', rec.invoice_cutoff_date)])
            else:
                invoices = self.env['account.move'].search(['&', '&', '&', '&', 
                            ('partner_id', '=', rec.partner_id.id), 
                            ('currency_id', '=', rec.currency_id.id),
                            ('move_type', 'in', ['out_invoice', 'in_refund', 'in_invoice', 'out_refund']),
                            ('state', '=', 'posted'), ('payment_state', 'in', ['not_paid', 'partial']),
                            ('amount_residual_signed', '!=', 0)])

            if invoices:
                for invoice in invoices:
                    if self.partner_type == 'customer':
                        map_account = ['out_invoice', 'out_refund']
                        map_debit = ['out_invoice', 'in_refund']
                        map_credit = ['in_invoice', 'out_refund']

                        lines_dict = {
                            'invoice_id': invoice.id,
                            'currency_id': invoice.currency_id.id,
                            'account_id': invoice.partner_id.property_account_receivable_id if invoice.move_type in map_account else invoice.partner_id.property_account_payable_id,
                            'invoice_date': invoice.invoice_date,
                            'invoice_date_due': invoice.invoice_date_due,
                            'original_amount': invoice.amount_total,
                            'base_amount': abs(invoice.amount_total_signed),
                            'original_unreconcile': invoice.amount_residual,
                            'base_unreconcile': abs(invoice.amount_residual_signed)
                        }

                        if invoice.move_type in map_credit:
                            list_line_credits.append((0, 0, lines_dict))
                        elif invoice.move_type in map_debit:
                            list_line_debits.append((0, 0, lines_dict))

                    elif self.partner_type == 'supplier':
                        map_account = ['out_invoice', 'out_refund']
                        map_debit = ['out_invoice', 'in_refund']
                        map_credit = ['in_invoice', 'out_refund']

                        lines_dict = {
                            'invoice_id': invoice.id,
                            'currency_id': invoice.currency_id.id,
                            'account_id': invoice.partner_id.property_account_receivable_id if invoice.move_type in map_account else invoice.partner_id.property_account_payable_id,
                            'invoice_date': invoice.invoice_date,
                            'invoice_date_due': invoice.invoice_date_due,
                            'original_amount': invoice.amount_total,
                            'base_amount': abs(invoice.amount_total_signed),
                            'original_unreconcile': invoice.amount_residual,
                            'base_unreconcile': abs(invoice.amount_residual_signed)
                        }

                        if invoice.move_type in map_credit:
                            list_line_credits.append((0, 0, lines_dict))
                        elif invoice.move_type in map_debit:
                            list_line_debits.append((0, 0, lines_dict))

            self.line_credit_ids = list_line_credits
            self.line_debit_ids = list_line_debits

    def prepare_payment_vals(self, invoices):
        payment_type_id = ""
        line_ids_det = []


        if invoices.invoice_id.move_type in ['out_invoice', 'in_refund']:
            payment_type_id = 'inbound'
        elif invoices.invoice_id.move_type in ['in_invoice', 'out_refund']:
            payment_type_id = 'outbound'

        payment_vals = {
            'date': self.date,
            'amount': invoices.amount,
            'payment_type': payment_type_id,
            'partner_type': self.partner_type,
            'ref': invoices.invoice_id.name,
            'journal_id': self.journal_id.id,
            'currency_id': self.currency_id.id,
            'partner_id': self.partner_id.id,
            'partner_bank_id': False,
            'payment_method_id': 1,
            'destination_account_id': invoices.account_id.id,
            'apply_manual_currency_exchange': invoices.invoice_id.apply_manual_currency_exchange,
            'manual_currency_exchange_rate': invoices.invoice_id.manual_currency_exchange_rate,
            'manual_currency_exchange_inverse_rate': invoices.invoice_id.manual_currency_exchange_inverse_rate,            
            'active_manual_currency_rate': invoices.invoice_id.active_manual_currency_rate,
            'branch_id': invoices.invoice_id.branch_id.id,
            'clearing_account_id': self.clearing_account_id.id,
            # 'line_ids': line_ids_det

            
        }


        payment_methods = self.journal_id.outbound_payment_method_ids if self.partner_type == 'customer' else self.journal_id.inbound_payment_method_ids

        payment_difference = invoices.amount - invoices.base_unreconcile

        return payment_vals

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
    

    
    def _create_payments(self, invoices):
        self.ensure_one()
        batches = self._get_batches(invoices.invoice_id)
        edit_mode = True
        to_reconcile = []
        payment_vals = self.prepare_payment_vals(invoices)
        payment_vals_list = [payment_vals]

            
        to_reconcile.append(batches[0]['lines'])

        payments = self.env['account.payment'].create(payment_vals_list)


        # if self.payment_type == 'giro':
        #     # Loop through the payments and update the account_id
        #     for payment in payments:
        #         # Your condition to determine the new account_id value
        #         new_account_id = self.clearing_account_id.id  

        #         # Update the account_id in payment_vals_list
        #         domain_credit = [('account_internal_type', 'in', ('liquidity', 'bank')), ('reconciled', '=', False)]
        #         credit_line = payment.line_ids.filtered_domain(domain_credit)
        #         credit_line.write({'account_id': new_account_id})


        # If payments are made using a currency different than the source one, ensure the balance match exactly in
        # order to fully paid the source journal items.
        # For example, suppose a new currency B having a rate 100:1 regarding the company currency A.
        # If you try to pay 12.15A using 0.12B, the computed balance will be 12.00A for the payment instead of 12.15A.
        if edit_mode:
            for payment, lines in zip(payments, invoices):
                # Batches are made using the same currency so making 'lines.currency_id' is ok.
                if payment.currency_id != lines.currency_id:
                    liquidity_lines, counterpart_lines, writeoff_lines = payment._seek_for_lines()
                    print("Fields in 'lines' object:", lines.fields_get_keys()) 
                
                    # amount_residual = abs(sum(counterpart_lines.mapped('amount_residual')))
                    source_balance = abs(sum(liquidity_lines.mapped('amount_residual')))

                    if liquidity_lines:
                        payment_rate = liquidity_lines[0].amount_currency / liquidity_lines[0].balance
                    else:
                        # Handle the case where liquidity_lines is empty
                        payment_rate = 0  # Or set it to an appropriate default value
                    source_balance_converted = abs(source_balance) * payment_rate
                    # Translate the balance into the payment currency is order to be able to compare them.
                    # In case in both have the same value (12.15 * 0.01 ~= 0.12 in our example), it means the user
                    # attempt to fully paid the source lines and then, we need to manually fix them to get a perfect
                    # match.
                    payment_balance = abs(sum(counterpart_lines.mapped('balance')))
                    payment_amount_currency = abs(sum(counterpart_lines.mapped('amount_currency')))
                    # if not payment.currency_id.is_zero(source_balance_converted - payment_amount_currency):
                    #     continue

                    if payment and len(payment) == 1:
                        payment_currency = self.currency_id
                        print("Fields in 'payment' object:", payment.fields_get_keys())
                        if not payment_currency.is_zero(source_balance_converted - payment_amount_currency):
                            continue
                    else:
                        # Handle the case where payment is not a single record
                        # You may raise an error, log a warning, or handle it based on your requirements
                        print(f"Payment is not a single record: {payment}")
                        continue

                    delta_balance = source_balance - payment_balance

                    # Balance are already the same.
                    if self.company_id.currency_id.is_zero(delta_balance):
                        continue

                    # Fix the balance but make sure to peek the liquidity and counterpart lines first.
                    debit_lines = (liquidity_lines + counterpart_lines).filtered('debit')
                    credit_lines = (liquidity_lines + counterpart_lines).filtered('credit')

                    payment.move_id.write({'line_ids': [
                        (1, debit_lines[0].id, {'debit': debit_lines[0].debit + delta_balance}),
                        (1, credit_lines[0].id, {'credit': credit_lines[0].credit + delta_balance}),
                    ]})

        payments.action_post()

        # if self.payment_type == 'giro':
        #     if self.partner_type == 'supplier':

        #         domain = [('account_internal_type', 'in', ('receivable', 'payable')), ('reconciled', '=', False)]
                
        #         for payment, lines in zip(payments, to_reconcile):

        #             # When using the payment tokens, the payment could not be posted at this point (e.g. the transaction failed)
        #             # and then, we can't perform the reconciliation.
        #             if payment.state != 'posted':
        #                 continue
            
        #             payment_lines = payment.line_ids.filtered_domain(domain)
        #             for account in payment_lines.mapped('account_id'):
        #                 lines_to_reconcile = (payment_lines + lines).filtered(lambda line: line.account_id == account and not line.reconciled)
        #                 if lines_to_reconcile:
        #                     lines_to_reconcile.reconcile()
        #                     # payments.is_reconciled = True

        #                 # if lines_to_reconcile[1].amount_residual == 0 or lines_to_reconcile[1].amount_residual < lines_to_reconcile[0].balance:
        #                 #     payment.is_reconciled = True
        #                 # payment.move_id.write({'ref': lines.invoice_id.name})
                        
        #     elif self.partner_type == 'customer':
        #         domain = [('account_internal_type', 'in', ('receivable', 'payable')), ('reconciled', '=', False)]
                
        #         for payment, lines in zip(payments, to_reconcile):

        #             # When using the payment tokens, the payment could not be posted at this point (e.g. the transaction failed)
        #             # and then, we can't perform the reconciliation.
        #             if payment.state != 'posted':
        #                 continue

        #             payment_lines = payment.line_ids.filtered_domain(domain)
        #             for account in payment_lines.mapped('account_id'):
        #                 lines_to_reconcile = (payment_lines + lines).filtered(lambda line: line.account_id == account and not line.reconciled)
        #                 if lines_to_reconcile:
        #                     lines_to_reconcile.reconcile()
        #                     # payments.is_reconciled = True

        #                 # if lines_to_reconcile[1].amount_residual == 0 or lines_to_reconcile[1].amount_residual < lines_to_reconcile[0].balance:
        #                 #     payment.is_reconciled = True
        #                 # payment.move_id.write({'ref': lines.invoice_id.name})
                            
        #     payment.is_reconciled = True
                    

        return payments


    def _register_payment_multi(self, invoices):
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

        # Create payments.
        payments_vals_list = []
        for batch in batches.values():
            payments_vals_list.append({
                'payment_date': self.date,
                'journal_id': self.journal_id.id,
                'payment_method_id': 1,
                'payment_type': 'inbound' if batch['key_values']['line_type'] == 'customer' else 'outbound',
                        'partner_type': batch['key_values']['partner_type'],
                        'partner_id': batch['key_values']['partner_id'],
                        'amount': batch['key_values']['amount'],
                        'currency_id': batch['key_values']['currency_id'],
                        'payment_date': self.date,
                        'journal_id': self.journal_id.id,
                        'payment_method_id': 1,
                        'payment_type': 'inbound' if batch['key_values']['line_type'] == 'customer' else 'outbound',
                        'invoice_ids': [(6, 0, batch['lines'].mapped('move_id').ids)],
                    })
            self.env['account.payment'].create(payments_vals_list)
        return payments_vals_list

    def mark_invoice_as_paid(self):
        self.ensure_one()
        payment_ids = []
        if len(self.line_credit_ids) > 0:
            for credit in self.line_credit_ids:
                if credit.payment_id.id != False:
                    payment_ids.append(debit.payment_id.id)
        if len(self.line_debit_ids) > 0:
            for debit in self.line_debit_ids:
                if debit.payment_id.id != False:
                    payment_ids.append(debit.payment_id.id)

        # if len(payment_ids) > 0:
        payment = self.payment_ids
        for pay in payment:
            pay.update({'state': 'posted'})
    
    def check_closed_period(self):
        check_periods = self.env['sh.account.period'].search([('company_id', '=', self.company_id.id),('branch_id', '=', self.branch_id.id), ('state', '=', 'done'),('date_start', '<=', self.date),('date_end', '>=', self.date)])
        if check_periods:
            raise UserError(_('You can not post any journal entry already on Closed Period'))

    def action_validate(self):
        self.check_closed_period()
        for rec in self:
            if bool(rec.amount_tmp and rec.amount_tmp <= 0) or bool(not rec.amount_tmp):
                raise ValidationError(_('Amount must be no equals to 0'))
            if rec.is_multi_payment_approval_matrix and rec.payment_type == 'giro':
                rec.action_validate_giro()
            else:
                if len(rec.line_credit_ids) > 0:
                    for inv_credit in rec.line_credit_ids:
                        if inv_credit.amount == 0:
                            continue
                        payment = self._create_payments(inv_credit)
                        inv_credit.payment_id = payment.id
                        payment.update({'payment_transaction_credit_count': '1'})
                        payment._action_reconcile_payment(inv_credit)
                if len(rec.line_debit_ids) > 0:
                    for inv_debit in rec.line_debit_ids:
                        if inv_debit.amount == 0:
                            continue
                        payment = self._create_payments(inv_debit)
                        inv_debit.payment_id = payment.id
                        payment.update({'payment_transaction_debit_count': '1'})
                        payment._action_reconcile_payment(inv_debit)
                if self.diff_amount == 0:
                    rec.write({'state': 'post'})
                    # self.mark_invoice_as_paid()
                    # payment._action_reconcile_payment()
                else:
                    if rec.diff_amount != rec.payment_difference_amount:
                        raise ValidationError(_("Post Difference Amount are not equal to Difference Amount."))
                    moves = self.create_diff_Journal()
                    rec.write({'state': 'post', 'different_move_id': moves.id})


    def create_diff_Journal(self):
        line_ids_det = []
        
        default_line_name = self.env['account.move.line']._get_default_line_name(
                    _("Customer Multi Payment") if self.partner_type == 'customer' else _("Vendor Multi Payment"),
                    abs(self.diff_amount),
                    self.currency_id,
                    self.date,
                    partner=self.partner_id,
                )
        
        if self.partner_type == 'customer':

            line = {
                'name': default_line_name,
                'account_id': self.journal_id.default_account_id.id,
                'debit': self.diff_amount if self.diff_amount > 0.0 else 0.0,
                'credit': -self.diff_amount if self.diff_amount < 0.0 else 0.0,
            }
            line_ids_det.append((0, 0, line))
            
            for diff in self.difference_ids:
                line = {
                    'name':  _("Difference Account - ") + diff.name,
                    'account_id': diff.account_id.id,
                    'debit': -diff.payment_amount if diff.payment_amount < 0.0 else 0.0,
                    'credit': diff.payment_amount if diff.payment_amount > 0.0 else 0.0,
                }
                line_ids_det.append((0, 0, line))
            

        elif self.partner_type == 'supplier':
            line = {
                'name': default_line_name,
                'account_id': self.journal_id.default_account_id.id,
                'debit': -self.diff_amount if self.diff_amount < 0.0 else 0.0,
                'credit': self.diff_amount if self.diff_amount > 0.0 else 0.0,
            }
            line_ids_det.append((0, 0, line))

            for diff in self.difference_ids:
                line = {
                    'name':  _("Difference Account - ") + diff.name,
                    'account_id': diff.account_id.id,
                    'debit': diff.payment_amount if diff.payment_amount > 0.0 else 0.0,
                    'credit': -diff.payment_amount if diff.payment_amount < 0.0 else 0.0,
                }
                line_ids_det.append((0, 0, line))
            
        all_move_vals = {
            'ref': default_line_name,
            'date': self.date,
            'journal_id': self.journal_id.id,
            'branch_id': self.branch_id.id,
            'line_ids': line_ids_det
        }
        AccountMove = self.env['account.move']
        moves = AccountMove.create(all_move_vals)
        moves.post()
        return moves

    def action_cancel(self):
        payment = self.env['account.payment']
        if len(self.line_credit_ids) > 0:
            for rec in self.line_credit_ids:
                if rec.payment_id.id != False:
                    rec.payment_id.action_draft()
                    rec.payment_id.action_cancel()                
        if len(self.line_debit_ids) > 0:
            for rec in self.line_debit_ids:
                if rec.payment_id.id != False:
                    rec.payment_id.action_draft()
                    rec.payment_id.action_cancel()                
        if self.different_move_id:
            self.different_move_id.button_draft()
            self.different_move_id.button_cancel()
        self.write({'state': 'canceled'})

    def action_draft(self):
        payment = self.env['account.payment']
        if len(self.line_credit_ids) > 0:
            for rec in self.line_credit_ids:
                if rec.payment_id.id != False:
                    rec.payment_id.action_draft()
                    rec.payment_id.action_cancel()
                    rec.update({'payment_id' : False})
        if len(self.line_debit_ids) > 0:
            for rec in self.line_debit_ids:
                if rec.payment_id.id != False:
                    rec.payment_id.action_draft()
                    rec.payment_id.action_cancel()
                    rec.update({'payment_id' : False})
        if self.different_move_id:
            self.different_move_id.button_draft()
            self.different_move_id.button_cancel()
            self.update({'different_move_id' : False})
        self.write({'state': 'draft'})

    def button_payment(self):
        self.ensure_one()
        payment_ids = []
        if len(self.line_credit_ids) > 0:
            for rec in self.line_credit_ids:
                if rec.payment_id.id != False:
                    payment_ids.append(rec.payment_id.id)
        if len(self.line_debit_ids) > 0:
            for rec in self.line_debit_ids:
                if rec.payment_id.id != False:
                    payment_ids.append(rec.payment_id.id)
        action = {
            'name': _("Payments"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'context': {'create': False},
        }
        action.update({
            'view_mode': 'list,form',
            'domain': [('id', 'in', payment_ids)],
        })
        return action


class accountmultipaymentcredit(models.Model):
    _name = "account.multipayment.credit"
    _description = ' '

    line_id = fields.Many2one('account.multipayment', string='Detail', readonly=True)
    company_currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id, string='Currency')
    currency_id = fields.Many2one('res.currency', related='line_id.currency_id', string='Currency')
    invoice_id = fields.Many2one('account.move', string='Bill', readonly=True)
    account_id = fields.Many2one('account.account', string='Account', readonly=True)
    invoice_date = fields.Date(string='Date', readonly=True)
    invoice_date_due = fields.Date(string='Due Date', readonly=True)
    original_amount = fields.Monetary(string='Original Currency Amount', currency_field='currency_id', readonly=True)
    base_amount = fields.Monetary(string='Base Currency Amount', currency_field='company_currency_id', readonly=True)
    original_unreconcile = fields.Monetary(string='Original Open Balance', currency_field='currency_id', readonly=True)
    base_unreconcile = fields.Monetary(string='Base Currency Open Balance', currency_field='company_currency_id', readonly=True)
    is_full_reconcile = fields.Boolean(string='Full Reconcile')
    amount = fields.Monetary(string='Amount', currency_field='currency_id')
    payment_id = fields.Many2one('account.payment', string='Payment')

    @api.onchange('is_full_reconcile')
    def calculate_credit_amount_base(self):
        for rec in self:
            if rec.is_full_reconcile:
                # balance = rec.company_currency_id._convert(rec.base_unreconcile, rec.currency_id, self.env.company, rec.line_id.date or fields.Date.context_today(self))
                # rec.amount = balance
                rec.amount = rec.original_unreconcile
            else:
                rec.amount = False


class accountmultipaymentdebit(models.Model):
    _name = "account.multipayment.debit"
    _description = ' '

    line_id = fields.Many2one('account.multipayment', string='Detail', readonly=True)
    company_currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id, string='Currency')
    currency_id = fields.Many2one('res.currency', related='line_id.currency_id', string='Currency')
    invoice_id = fields.Many2one('account.move', string='Invoice', readonly=True)
    account_id = fields.Many2one('account.account', string='Account', readonly=True)
    invoice_date = fields.Date(string='Date', readonly=True)
    invoice_date_due = fields.Date(string='Due Date', readonly=True)
    original_amount = fields.Monetary(string='Original Currency Amount', currency_field='currency_id', readonly=True)
    base_amount = fields.Monetary(string='Base Currency Amount', currency_field='company_currency_id', readonly=True)
    original_unreconcile = fields.Monetary(string='Original Open Balance', currency_field='currency_id', readonly=True)
    base_unreconcile = fields.Monetary(string='Base Currency Open Balance', currency_field='company_currency_id', readonly=True)
    is_full_reconcile = fields.Boolean(string='Full Reconcile')
    amount = fields.Monetary(string='Amount', currency_field='currency_id')
    payment_id = fields.Many2one('account.payment', string='Payment')

    @api.onchange('is_full_reconcile')
    def calculate_debit_amount_base(self):
        for rec in self:
            if rec.is_full_reconcile:
                # balance = rec.company_currency_id._convert(rec.base_unreconcile, rec.currency_id, self.env.company, rec.line_id.date or fields.Date.context_today(self))
                # rec.amount = balance
                rec.amount = rec.original_unreconcile
            else:
                rec.amount = False

class ApprovalMatrixAccountingLines(models.Model):
    _inherit = "approval.matrix.accounting.lines"

    multi_receipt_id = fields.Many2one('account.multipayment', string='Multipul Receipt Payment')
    
    
class AccountMultipaymentDifference(models.Model):
    _name = 'account.multipayment.difference'
    _description = 'Payment Difference Lines'
    
    name = fields.Char(string='Description', required=True)
    payment_id = fields.Many2one('account.multipayment', string='Payment')
    account_id = fields.Many2one('account.account', string="Difference Account", copy=False, domain="[('deprecated', '=', False), ('company_id', '=', company_id)]", required=True)
    payment_amount = fields.Monetary(string='Allocation Amount', required=True)
    currency_id = fields.Many2one('res.currency', string='Currency', related='payment_id.currency_id', help="The payment's currency.")
    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True, default=lambda self: self.env.company)
