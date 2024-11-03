# -*- coding: utf-8 -*-

from odoo import api, fields, models

class PosPaymentEdc(models.Model):
    _name = "pos.payment.edc"
    _description = "Pos Payment EDC"
    _order = "create_date desc"

    name = fields.Char('Description')
    payment_state = fields.Selection([('success','Success'), ('cancel', 'Cancel'),('failed','Failed')], string='Payment Status')
    payment_type = fields.Selection([('card','Debit/Credit Card'), ('qris','Qris')], string='Payment Type') # 01: Card, 31: Qris, 32: Check Payment Qris
    invoice_number = fields.Char('Invoice Number')
    order_number = fields.Char('Order Number')
    resp_data = fields.Text('Response Data')
    pos_order_id = fields.Many2one('pos.order', 'POS Order')
    edc_type = fields.Selection([('bca','BCA')], string='EDC Type')

    version = fields.Char('Version')
    trans_type = fields.Char('Trans Type')
    trans_amount = fields.Char('Trans Amount')
    other_amount = fields.Char('Other Amount')
    pan = fields.Char('PAN')
    expiry_date = fields.Char('Expiry Date')
    resp_code = fields.Char('Resp Code')
    rrn = fields.Char('RRN')
    approval_code = fields.Char('Approval Code')
    date = fields.Char('Date')
    time = fields.Char('Time')
    merchant_id = fields.Char('Merchant ID')
    terminal_id = fields.Char('Terminal ID')
    offline_flag = fields.Char('Offline Flag')
    cardholder_name = fields.Char('Cardholder Name')
    pan_cashier_card = fields.Char('Pan Cashier Card')
    invoice_number = fields.Char('Invoice Number')
    batch_number = fields.Char('Batch Number')
    issuer_id = fields.Char('Issuer ID')
    installment_flag = fields.Char('Installment Flag')
    dcc_flag = fields.Char('DCC Flag')
    reedem_flag = fields.Char('Reedem Flag')
    info_amount = fields.Char('Info Amount')
    dcc_decimal_place = fields.Char('DCC Decimal Place')
    dcc_currency_name = fields.Char('DCC Currency Name')
    dcc_exchange_rate = fields.Char('DCC Exchange Rate')
    coupon_flag = fields.Char('Coupon Flag')
    filler = fields.Char('Filler')
    pos_branch_id = fields.Many2one('res.branch', string='Branch', related='pos_order_id.pos_branch_id')
    company_id = fields.Many2one('res.company', string='Company', related='pos_order_id.company_id')

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        context = self._context
        if 'ctx_limit' in context:
            limit = context['ctx_limit']
        if 'ctx_order_by' in context:
            order = context['ctx_order_by']
        return super(PosPaymentEdc, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)

    def get_payment(self, vals):
        # TODO: search with sudo to avoid branch & company rules
        domain = vals.get('domain',[])
        fields = vals.get('fields',[])
        offset = vals.get('offset',0)
        limit = vals.get('offset',None)
        order = vals.get('order',None)
        return self.env['pos.payment.edc'].sudo().search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)