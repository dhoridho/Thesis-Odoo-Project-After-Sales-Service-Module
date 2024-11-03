# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from lxml import etree
from odoo.addons.point_of_sale.models.pos_payment_method import PosPaymentMethod as PosPaymentMethodOri
from odoo.exceptions import UserError


def write(self, vals):
    allowed = False
    if 'account_journal_id' in vals and len(vals)==1:
        allowed = True
    if self._is_write_forbidden(set(vals.keys())) and not allowed:
        raise UserError('Please close and validate the following open PoS Sessions before modifying this payment method.\n'
                        'Open sessions: %s' % (' '.join(self.open_session_ids.mapped('name')),))
    return super(PosPaymentMethodOri, self).write(vals)

PosPaymentMethodOri.write = write

class PosPayment(models.Model):
    _inherit = "pos.payment"

    voucher_id = fields.Many2one('pos.voucher', 'Voucher')
    voucher_code = fields.Char('Voucher Code')
    pos_branch_id = fields.Many2one('res.branch', string='Branch', default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, domain=lambda self: [('id', 'in', self.env.branches.ids)])
    ref = fields.Char('Ref')
    cheque_owner = fields.Char('Cheque Owner')
    cheque_bank_account = fields.Char('Cheque Bank Account')
    cheque_bank_id = fields.Many2one('res.bank', 'Cheque Bank')
    cheque_check_number = fields.Char('Cheque Check Number')
    cheque_card_name = fields.Char('Cheque Card Name')
    cheque_card_number = fields.Char('Cheque Card Number')
    cheque_card_type = fields.Char('Cheque Card Type')
    priority = fields.Selection([
        ('low','low'),
        ('normal','normal'),
    ], string='priority', default='low')
    payment_card_id = fields.Many2one('card.payment', string="Card Payment")
    card_payment_number = fields.Char('Card Payment Number',copy=False)
    payment_mdr_id = fields.Many2one('pos.payment.method.mdr','Payment MDR')
    mdr_amount = fields.Float("MDR Amount")
    mdr_paid_by = fields.Selection([
        ('Company','Company'),
        ('Customer','Customer'),
    ], string='MDR Paid By', copy=False)
    total_without_mdr = fields.Float('Total Amount Without MDR')
    
    @api.model
    def create(self, vals):
        if not vals.get('pos_branch_id'):
            vals.update({'pos_branch_id': self.env['res.branch'].sudo().get_default_branch()})
        if vals.get('mdr_paid_by') == 'Customer':
            vals['total_without_mdr'] = (vals.get('amount') or 0) - (vals.get('mdr_amount') or 0)
        payment = super(PosPayment, self).create(vals)
        return payment


    @api.model
    def fields_view_get(self, view_id=None, view_type=None, toolbar=False, submenu=False):
        res = super(PosPayment, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)

        user_pos_not_create_edit =  self.env.user.has_group('equip3_pos_masterdata.group_pos_staff') or self.env.user.has_group('equip3_pos_masterdata.group_pos_supervisor') or self.env.user.has_group('equip3_pos_masterdata.group_pos_cashier') or self.env.user.has_group('equip3_pos_masterdata.group_pos_waiter') or self.env.user.has_group('equip3_pos_masterdata.group_pos_cooker')
        user_pos_have_create_edit =  self.env.user.has_group('equip3_pos_masterdata.group_pos_manager')
        if user_pos_not_create_edit and not user_pos_have_create_edit:
            root = etree.fromstring(res['arch'])
            root.set('edit', 'false')
            res['arch'] = etree.tostring(root)
            
        return res

class PosPaymentMethod(models.Model):
    _inherit = "pos.payment.method"

    apply_charges = fields.Boolean("Apply Charges")
    fees_amount = fields.Float("Fees Amount")
    fees_type = fields.Selection(
        selection=[('fixed', 'Fixed'), ('percentage', 'Percentage')],
        string="Fees type",
        default="fixed")
    fees_product_id = fields.Many2one(
        'product.product',
        'Fees Product',
        domain=[('sale_ok', '=', True), ('available_in_pos', '=', True)]
    )
    optional = fields.Boolean("Optional")
    shortcut_key = fields.Char('Shortcut Key')
    jr_use_for = fields.Boolean("Gift Card", default=False)

    fullfill_amount = fields.Boolean(
        'Full fill Amount',
        help='If checked, when cashier click to this Payment Method \n'
             'Payment line auto full fill amount due'
    )

    shortcut_keyboard = fields.Char(
        string='Shortcut Keyboard',
        size=2,
        help='You can input a to z, F1 to F12, Do not set "b", because b is BACK SCREEN'
    )
    cheque_bank_information = fields.Boolean(
        'Cheque Bank Information',
        help='If checked, when cashier select this payment \n'
             'POS automatic popup ask cheque bank information \n'
             'And save information bank of customer to payment lines of Order'
    )
    discount = fields.Boolean('Apply Discount')
    discount_type = fields.Selection([
        ('percent', '%'),
        ('fixed', 'Fixed')
    ], string='Discount Type', default='percent')
    discount_amount = fields.Float('Discount Amount')
    discount_product_id = fields.Many2one(
        'product.product',
        string='Product Discount',
        domain=[('available_in_pos', '=', True)]
    )
    is_bank = fields.Boolean('Bank')

    generate_invoice = fields.Boolean(string="Generate Invoice",default=False)
    invoice_partner_id = fields.Many2one("res.partner", string="Invoice Partner")
    
    able_use_card = fields.Boolean('Able to Use Card')
    is_mdr = fields.Boolean('Card Payment & MDR')
    is_mdr_discount = fields.Boolean('Merchant Discount Rate (MDR)')
    mdr_paid_by = fields.Selection([('Customer','Customer'), ('Company','Company')], string="MDR Paid By")
    mdr_intermediary_account_id = fields.Many2one('account.account',"MDR Intermediary Account")
    mdr_ids = fields.One2many('pos.payment.method.mdr','payment_method_id','MDR Data')
    is_receivables = fields.Boolean('Receivables')
    account_journal_id = fields.Many2one('account.journal', string='Deposit Journal')

    @api.constrains('shortcut_keyboard')
    def check_shortcut_keyboard_no_number(self):
        for data in self:
            if data.shortcut_keyboard and any(char.isdigit() for char in data.shortcut_keyboard):
                raise UserError("Shortcuts cannot contain numbers. Please enter a valid shortcut without numeric characters.")



    @api.onchange('is_cash_count')
    def _onchange_type_is_cash_count(self):
        self.change_type_of_payment_method('is_cash_count')

    @api.onchange('is_bank')
    def _onchange_type_is_bank(self):
        self.change_type_of_payment_method('is_bank')

    @api.onchange('is_receivables')
    def _onchange_type_is_receivables(self):
        self.change_type_of_payment_method('is_receivables')

    def change_type_of_payment_method(self, _field):
        # Only allow to select one of "cash/bank/receivables"
        if _field == 'is_cash_count' and self.is_cash_count == True:
            self.is_bank = False
            self.is_receivables = False
        if _field == 'is_bank' and self.is_bank == True:
            self.is_cash_count = False
            self.is_receivables = False
        if _field == 'is_receivables' and self.is_receivables == True:
            self.is_cash_count = False
            self.is_bank = False


class PosPaymentMethodMDR(models.Model):
    _name = "pos.payment.method.mdr"
    _description = "POS Payment Method MDR"

    payment_method_id = fields.Many2one('pos.payment.method','Payment Method')
    name = fields.Char('Name')
    mdr_type = fields.Selection([
        ('Credit Card','Credit Card'), 
        ('Debit Card','Debit Card'),
        ('QRIS','QRIS'),
        ('Other Debit','Other Debit'),
        ('Other Credit','Other Credit'),
    ], string="Type")
    card_group_ids = fields.Many2many('group.card',string='Card Group')
    card_payment_ids = fields.Many2many('card.payment',string='Card Payment')
    percentage = fields.Float('Percentage (%)')
    surcharge = fields.Float("Surcharge")
    card_group_id = fields.Many2one('group.card','Card Group')
    card_payment_id = fields.Many2one('card.payment','Card Payment')
    card_type = fields.Selection([('Credit','Credit'), ('Debit','Debit')], string="Type")

    @api.onchange('mdr_type')
    def onchange_mdr_type(self):
        card_group_obj = self.env['group.card']
        card_payment_obj = self.env['card.payment']
        card_type = False
        if self.mdr_type:
            if 'Debit' in self.mdr_type:
                card_type = 'Debit'
            if 'Credit' in self.mdr_type:
                card_type = 'Credit'
            if card_type:
                self.card_type = card_type
            self.name = self.mdr_type
            if self.mdr_type=='Other Debit':
                card_groups = card_group_obj.search([])
                if card_groups:
                    for line in self.payment_method_id.mdr_ids:
                        if 'Debit' in line.mdr_type:
                            for cd in line.card_group_ids:
                                data_cd = str(cd.id)
                                try:
                                    data_cd = int(data_cd.replace('NewId_',''))
                                    data_cd = card_group_obj.browse(data_cd)
                                except:
                                    data_cd = card_group_obj.browse(data_cd)
                                if data_cd in card_groups:
                                    card_groups-=data_cd
                self.card_group_ids = card_groups
            elif self.mdr_type=='Other Credit': 
                card_groups = card_group_obj.search([])
                if card_groups:
                    for line in self.payment_method_id.mdr_ids:
                        if 'Credit' in line.mdr_type:
                            for cd in line.card_group_ids:
                                data_cd = str(cd.id)
                                try:
                                    data_cd = int(data_cd.replace('NewId_',''))
                                    data_cd = card_group_obj.browse(data_cd)
                                except:
                                    data_cd = card_group_obj.browse(data_cd)
                                if data_cd in card_groups:
                                    card_groups-=data_cd
                self.card_group_ids = card_groups
            else:
                self.card_group_ids = False
                self.card_payment_ids = False

    @api.onchange('card_group_ids')
    def onchange_card_group_ids(self):
        card_payment_obj = self.env['card.payment']
        if self.card_group_ids and self.mdr_type and self.mdr_type!='QRIS':
            if 'Credit' in self.mdr_type:
                card_type = 'Credit'
            if 'Debit' in self.mdr_type:
                card_type = 'Debit'
            card_payments = card_payment_obj.search([('card_group','in',self.card_group_ids.ids),('card_type','=',card_type)]) 
            self.card_payment_ids = card_payments
        else:
            self.card_payment_ids = False
