# -*- coding: utf-8 -*-

from odoo import models, fields, api

class PosPaymentMethod(models.Model):
    _inherit = "pos.payment.method"

    is_edc_bca = fields.Boolean("EDC BCA")
    is_edc_manual_input = fields.Boolean("EDC Manual Input", help="Manual Input Approval Code")
    edc_port = fields.Char('EDC PORT', default='8100')
    trans_type = fields.Selection([
        ('card','Sale Debit Card'), 
        ('credit_card', 'Sale Credit Card'),
        ('qris','Payment QRIS'),
    ], string='Transaction Type')
    trans_type_code = fields.Char('Transaction Type (Code)', compute='_compute_trans_type_code')
    is_payment_edc = fields.Boolean("Payment EDC", compute='_compute_is_payment_edc', store=True)
    payment_edc_url = fields.Char("Payment EDC Url", default='http://localhost:8100/edc', 
        help='''Production:\n- http://localhost:8100/edc\nTesting:\n- http://localhost:8100/edc/success (Success)\n- http://localhost:8100/edc/cancel (Cancel)\n- http://localhost:8100/edc/gagal (Gagal)
        ''')
    installment_tenor_ids = fields.Many2many(
        'pos.payment.installment.tenor', 
        'pos_payment_method_pos_payment_installment_tenor_rel', 
        'pos_payment_method_id', 
        'pos_payment_installment_tenor_id',
        string='Installment Tenor')
    installment_plan = fields.Char('Installment Plan', default='001')

    @api.depends('is_edc_bca')
    def _compute_is_payment_edc(self):
        for rec in self:
            is_payment_edc = False
            if rec.is_edc_bca:
                is_payment_edc = True
            rec.is_payment_edc = is_payment_edc

    def _compute_trans_type_code(self):
        for rec in self:
            code = ''
            if rec.trans_type == 'card':
                code = '01' 
            if rec.trans_type == 'qris':
                code = '31'
            if rec.trans_type == 'credit_card':
                code = '01'
            rec.trans_type_code = code