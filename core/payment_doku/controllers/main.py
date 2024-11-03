# -*- coding: utf-8 -*-
#################################################################################
#
#    Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#
#################################################################################

import pprint
import werkzeug
from odoo.http import request
from odoo import http
import logging
_logger = logging.getLogger(__name__)
import urllib.parse

class DukuPayment(http.Controller):

    @http.route('/payment/doku/return', type='http', auth="none",methods=['GET', 'POST'], csrf=False)
    def Doku_form_redirect(self, **post):
        """ Gets the URL from doku and redirect to that URL for payment """
        _logger.info(
            'Beginning form_feedback with post data %s', pprint.pformat(post))
        if post:
            res = request.env['payment.transaction'].sudo().form_feedback(post, 'doku')
        return werkzeug.utils.redirect('/payment/process')

    @http.route('/payment/doku/notify', type='http', auth="none",methods=['GET', 'POST'], csrf=False)
    def Doku_form_notify(self, **post):
        """ Gets the URL from doku and notify to that URL for payment """
        _logger.info(
            'Beginning notify with post data %s', pprint.pformat(post))
        return True
