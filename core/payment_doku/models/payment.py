# -*- coding: utf-8 -*-
#################################################################################
#
#    Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#
#################################################################################

from odoo import api, fields, models, _
import time
import random, string
import hashlib
import logging
from urllib.parse import urlparse,urljoin
import json
_logger = logging.getLogger(__name__)
from odoo.addons.payment.models.payment_acquirer import ValidationError


def _default_unique_key(size, chars=string.ascii_uppercase + string.digits):
	return ''.join(random.choice(chars) for x in range(size))



class paymentAcquirerDoku(models.Model):
    _inherit = 'payment.acquirer'

    provider = fields.Selection(selection_add=[('doku', 'Doku')],ondelete={'doku': 'set default'})
    doku_sharedkey = fields.Char(string='Doku Shared Key', required_if_provider='doku', groups='base.group_user')
    doku_mall_id = fields.Char(string='Doku Mall ID', required_if_provider='doku',groups='base.group_user',help='The Mall ID or payment store Id')
    doku_use_notify = fields.Boolean('Use Notify',default=True)
    doku_chain_merchant = fields.Char(string="Chain Merchant",required_if_provider='doku' )

    def doku_form_generate_values(self, values):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        doku_form_values = dict(values)
        doku_mall_id = self.doku_mall_id
        doku_sharedkey = self.doku_sharedkey
        doku_chain_merchant = self.doku_chain_merchant
        doku_transid_merchant =  _default_unique_key(12)
        if values['reference'] :
            doku_sessionid =  values['reference']
            amount = "{:0.2f}".format(float(round(values['amount'])))
            wor = "%s%s%s%s" % (amount, doku_mall_id, doku_sharedkey, doku_transid_merchant)
            words = hashlib.sha1(wor.encode('utf-8')).hexdigest()
            doku_form_values.update({
                'cmd': '_xclick',
                'basket': 'Item 1,10000.00,1,10000.00',
                'reference': values['reference'],
                'amount': amount,
                'currency_code':360,
                'address1': values.get('partner_address'),
                'city': values.get('partner_city'),
                'country': 'ID',
                'state': values.get('partner_state') and (values.get('partner_state').code or values.get('partner_state').name) or '',
                'email': values.get('partner_email') or 'partner_email@dnimall.com',
                'zip_code': values.get('partner_zip'),
                'first_name': values.get('partner_first_name'),
                'last_name': values.get('partner_last_name'),
                'phone': values.get('partner_phone'),
                # 'doku_redirect': '%s' % urljoin(base_url, Doku._redirect_url),
                # 'notify_url': '%s' % urljoin(base_url, Doku._notify_url),
                # 'cancel_return': '%s' % urljoin(base_url, Doku._cancel_url),
                'handling': '%.2f' % doku_form_values.pop('fees', 0.0) if self.fees_active else False,
                'custom': json.dumps({'return_url': '%s' % doku_form_values.pop('return_url')}) if doku_form_values.get('return_url') else False,
                'doku_mall_id': doku_mall_id,
                'doku_sharedkey': doku_sharedkey,
                "doku_chain_merchant":doku_chain_merchant,
                'doku_transid_merchant': doku_transid_merchant,
                'doku_sessionid': doku_sessionid,
                'words': words,
                'datetime': time.strftime("%Y%m%d%H%M%S"),
                'tx_url' : self.doku_get_form_action_url()

            })
        else:
            _logger.info("--NO refernece values---values-----")
        return doku_form_values

    @api.model
    def _get_doku_urls(self, state):
        """ Doku payment URLS """
        if state == 'enabled':
            return {
                'doku_form_url': 'https://pay.doku.com/Suite/Receive',
            }
        else:
            return {
                'doku_form_url': 'https://staging.doku.com/Suite/Receive',
            }

    def doku_get_form_action_url(self):
        return self._get_doku_urls(self.state).get('doku_form_url')




class TxDokuPayment(models.Model):
    _inherit = 'payment.transaction'

    doku_txn_words = fields.Char(string='Doku Transaction words')

    @api.model
    def _doku_form_get_tx_from_data(self, data):
        if data.get('SESSIONID'):
            reference = data.get('SESSIONID')
            if not reference:
                error_msg = _(
                    'Doku: received data with missing '
                    'reference (%s)') % (reference)
                _logger.info(error_msg)
                raise ValidationError(error_msg)
            transaction = self.search([('reference', '=', reference)])
            if not transaction:
                error_msg = (_('Doku: received data for reference %s; no '
                               'order found') % (reference))
                raise ValidationError(error_msg)
            elif len(transaction) > 1:
                error_msg = (_('Doku: received data for reference %s; '
                               'multiple orders found') % (reference))
                raise ValidationError(error_msg)
            return transaction

    def _doku_form_validate(self, data):
        res = {}
        if data.get('STATUSCODE') == '0000':
            _logger.info(
                'Validated Doku payment for tx %s: '
                'set as done' % (self.reference))
            res.update(
				date=fields.datetime.now(),
                acquirer_reference=data.get('TRANSIDMERCHANT'),
				doku_txn_words=data.get('WORDS')
				)
            self.write(res)
            return self._set_transaction_done()
        else:
            error = 'Received unrecognized data for Doku payment %s, set as error' % (self.reference)
            _logger.info(error)
            res.update(
				date=fields.datetime.now(),
				state_message=error,
				)
            self.write(res)
            return self._set_transaction_error(msg=error)
