# -*- coding: utf-8 -*-

import json

import odoo
from odoo import http
from odoo.http import request

def check_params(data, req_fields):
    for field in req_fields:
        if field not in data:
            return False
    return True

class PosEdcController(http.Controller):

    @http.route(['/api-pos-edc/payment'], type='json', auth='public', csrf=False, methods=['GET','POST'])
    def api_payment(self, **kw):
        PosPaymentEdc = request.env['pos.payment.edc']
        data = kw
        if not data:
            data = json.loads(request.httprequest.data)

        pass_check = check_params(data, ['data'])
        if not pass_check:
            response = { "message": "Missing required field ~" }
        if pass_check:
            response = {}
            domain = [('order_number','=', data.get('order_number'))]
            payment = PosPaymentEdc.sudo().search_read(domain, ['id', 'name'], limit=1)
            if payment:
                response = { "message": "Data received ID:" + str(payment[0]['id']) }
            if not payment:
                payment_data = self.prepare_payment_data(data)
                payment = PosPaymentEdc.sudo().create(payment_data)
                response = { "message": "New Data received ID:" + str(payment.id) }
            
        return response

    def prepare_payment_data(self, vals):
        data = vals['data']
        order_number = vals.get('order_number', '-1')

        status = vals.get('status')
        if not status:
            status = vals.get('Status')
        status = str(status).lower()
        if status in ['canceled']:
            status = 'cancel'

        pos_order_id = False
        domain = [('pos_reference', '=', order_number)]
        pos_order = request.env['pos.order'].sudo().search(domain, limit=1)
        if pos_order:
            pos_order_id = pos_order.id
        
        display_order_number = order_number
        order_numbers = order_number.split('-D-')
        if len(order_numbers) == 2:
            display_order_number = order_numbers[0]
            
        values = {
            'name': f'POS Order - {display_order_number}',
            'order_number': order_number,
            'invoice_number': vals.get('invoice_number',''),
            'edc_type': vals.get('edc_type',''),
            'payment_state': status,
            'payment_type': vals.get('payment_type', ''),
            'pos_order_id': pos_order_id,
        }

        if data.get('version'):
            values['version'] = data['version']
            
        if data.get('trans_type'):
            values['trans_type'] = data['trans_type']
            if data['trans_type'] == '01':
                values['payment_type'] = 'card'
            if data['trans_type'] in ['31','32']:
                values['payment_type'] = 'qris'

        if data.get('trans_amount'):
            values['trans_amount'] = data['trans_amount']
        if data.get('other_amount'):
            values['other_amount'] = data['other_amount']
        if data.get('pan'):
            values['pan'] = data['pan']
        if data.get('expiry_date'):
            values['expiry_date'] = data['expiry_date']
        if data.get('resp_code'):
            values['resp_code'] = data['resp_code']
        if data.get('rrn'):
            values['rrn'] = data['rrn']
        if data.get('approval_code'):
            values['approval_code'] = data['approval_code']
        if data.get('date'):
            values['date'] = data['date']
        if data.get('time'):
            values['time'] = data['time']
        if data.get('merchant_id'):
            values['merchant_id'] = data['merchant_id']
        if data.get('terminal_id'):
            values['terminal_id'] = data['terminal_id']
        if data.get('offline_flag'):
            values['offline_flag'] = data['offline_flag']
        if data.get('cardholder_name'):
            values['cardholder_name'] = data['cardholder_name']
        if data.get('pan_cashier_card'):
            values['pan_cashier_card'] = data['pan_cashier_card']
        if data.get('invoice_number'):
            values['invoice_number'] = data['invoice_number']
        if data.get('batch_number'):
            values['batch_number'] = data['batch_number']
        if data.get('issuer_id'):
            values['issuer_id'] = data['issuer_id']
        if data.get('InstallmentFlag'):
            values['installment_flag'] = data['InstallmentFlag']
        if data.get('dcc_flag'):
            values['dcc_flag'] = data['dcc_flag']
        if data.get('reedem_flag'):
            values['reedem_flag'] = data['reedem_flag']
        if data.get('info_amount'):
            values['info_amount'] = data['info_amount']
        if data.get('dcc_decimal_place'):
            values['dcc_decimal_place'] = data['dcc_decimal_place']
        if data.get('dcc_currency_name'):
            values['dcc_currency_name'] = data['dcc_currency_name']
        if data.get('dcc_exchange_rate'):
            values['dcc_exchange_rate'] = data['dcc_exchange_rate']
        if data.get('coupon_flag'):
            values['coupon_flag'] = data['coupon_flag']
        return values