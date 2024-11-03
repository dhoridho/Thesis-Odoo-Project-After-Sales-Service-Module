# -*- coding: utf-8 -*-
import logging
import werkzeug

from odoo import http
from odoo.http import request
_logger = logging.getLogger(__name__)


class XenditController(http.Controller):
    @http.route('/xendit/invoice/paid', methods=['GET', 'POST'], auth='public', type='json', website=True)
    def invoice_paid(self, **kw):
        data = request.jsonrequest
        # Xendit Return data
        # data = {
        #     'id': '60d9885f3ef08841979f92f1',
        #     'external_id': '72',
        #     'user_id': '5d9c042085a454533720c39f',
        #     'is_high': False,
        #     'credit_card_charge_id': '60d9887b616b5e002083bc6a',
        #     'payment_method': 'CREDIT_CARD',
        #     'status': 'PAID',
        #     'merchant_name': 'PrintArt',
        #     'amount': 110000,
        #     'paid_amount': 110000,
        #     'paid_at': '2021-06-28T08:29:47.100Z',
        #     'payer_email': 'kelvin@witech.co.id',
        #     'description': 'SO/2021/20300-4',
        #     'adjusted_received_amount': 110000,
        #     'created': '2021-06-28T08:29:19.599Z',
        #     'updated': '2021-06-28T08:29:47.447Z',
        #     'currency': 'IDR',
        #     'payment_channel': 'CREDIT_CARD'
        # }
        _logger.info(data)
        payment_transaction = request.env['payment.transaction'].sudo().search(
            [('id', '=', data['external_id'])])
        if data['status'] == 'PAID':
            payment_transaction._set_transaction_done()
