# coding: utf-8
import logging
import pprint
import json
from odoo import fields, http
from odoo.http import request

_logger = logging.getLogger(__name__)

class PosXenditController(http.Controller):
    @http.route('/xendit/notification', type='json', methods=['POST'], auth='none', csrf=False)
    def notification(self):
        print('\n-----/xendit/notification ---------')
        data = json.loads(request.httprequest.data)

        print(repr(data))
        payment_method = request.env['pos.payment.method'].sudo().search([('use_payment_terminal', '=', 'xendit_pos')], limit=1)
        payment_method.xendit_pos_latest_response = json.dumps(data)
