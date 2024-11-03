# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
import logging

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError

from odoo.http import request
from . import xendit_client
from . import encrypt

_logger = logging.getLogger(__name__)

class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    def _get_payment_terminal_selection(self):
        return super(PosPaymentMethod, self)._get_payment_terminal_selection() + [('xendit_pos', 'Xendit')]

    xendit_pos_secret_key = fields.Char(string="Xendit Secret Key", help='Enter your xendit secret key.', copy=False)
    xendit_pos_terminal_identifier = fields.Char(help='[Terminal model]-[Serial number], for example: P400Plus-123456789', copy=False)
    xendit_pos_test_mode = fields.Boolean(help='Run transactions in the test environment.')
    xendit_pos_latest_response = fields.Char(help='Technical field used to buffer the latest asynchronous notification from Xendit.', copy=False, groups='base.group_erp_manager')
    xendit_pos_latest_diagnosis = fields.Char(help='Technical field used to determine if the terminal is still connected.', copy=False, groups='base.group_erp_manager')
    xendit_pos_encrypt_key = fields.Char(string="Xendit Encrypt Key", copy=False)

    xendit_invoice_id = ''
    xenditClient = xendit_client.XenditClient

    @api.onchange('xendit_pos_secret_key')
    def _onchange_xendit_secret_key(self):
        if self.xendit_pos_secret_key:

            # Generate the encrypt key using to encrypt secret key
            if self.xendit_pos_encrypt_key is False or self.xendit_pos_encrypt_key == '':
                self.xendit_pos_encrypt_key = encrypt.generateKey()

            # Set terminal_identifier and encrypt secret key
            if self.xendit_pos_terminal_identifier is False or self.xendit_pos_terminal_identifier == '':
                self.xendit_pos_terminal_identifier = encrypt.generateKey()

            # encrypt secret key
            self.xendit_pos_secret_key = encrypt.encrypt(self.xendit_pos_secret_key, self.xendit_pos_encrypt_key)
        else:
            ValidationError('Invalid xendit_pos_secret_key')

    def get_current_xendit_payment_method(self, terminal_id):
        return request.env['pos.payment.method'].sudo().search(
            [
                ('use_payment_terminal', '=', 'xendit_pos'),
                ('xendit_pos_terminal_identifier', '=', terminal_id if self.xendit_pos_terminal_identifier is False else self.xendit_pos_terminal_identifier)
            ], limit=1)

    @api.constrains('xendit_pos_terminal_identifier')
    def _check_xendit_pos_terminal_identifier(self):
        for payment_method in self:
            if not payment_method.xendit_pos_terminal_identifier:
                continue
            existing_payment_method = self.search([('id', '!=', payment_method.id),
                                                   ('xendit_pos_terminal_identifier', '=', payment_method.xendit_pos_terminal_identifier)],
                                                  limit=1)
            if existing_payment_method:
                raise ValidationError(_('Terminal %s is already used on payment method %s.')
                                      % (payment_method.xendit_pos_terminal_identifier, existing_payment_method.display_name))

    def _is_write_forbidden(self, fields):
        whitelisted_fields = set(('xendit_pos_latest_response', 'xendit_pos_latest_diagnosis'))
        return super(PosPaymentMethod, self)._is_write_forbidden(fields - whitelisted_fields)

    @api.model
    def get_latest_xendit_pos_status(self, data):
        '''See the description of proxy_xendit_pos_request as to why this is an
        @api.model function.
        '''

        # Poll the status of the terminal if there's no new
        # notification we received. This is done so we can quickly
        # notify the user if the terminal is no longer reachable due
        # to connectivity issues.

        payment_method = self.get_current_xendit_payment_method(data['terminal_id'])
        payment_method.xendit_pos_latest_response = ''  # avoid handling old responses multiple times

        invoice = self.xenditClient.get_invoice(
            self.xenditClient,
            payment_method,
            data["xendit_invoice_id"]
        )
        return { 'response': invoice }

    @api.model
    def request_payment(self, data):
        '''Necessary because Xendit's endpoints don't have CORS enabled. This is an
        @api.model function to avoid concurrent update errors. Xendit's
        async endpoint can still take well over a second to complete a
        request. By using @api.model and passing in all data we need from
        the POS we avoid locking the pos_payment_method table. This way we
        avoid concurrent update errors when Xendit calls us back on
        /xendit/notification which will need to write on
        pos.payment.method.
        '''

        invoice = self.xenditClient.create_invoice(
            self.xenditClient,
            self.get_current_xendit_payment_method(data['terminal_id']),
            json.loads(json.dumps(data))
        )
        return invoice

    @api.model
    def cancel_payment(self, data):
        res = self.xenditClient.cancel_invoice(
            self.xenditClient,
            self.get_current_xendit_payment_method(data['terminal_id']),
            data['invoice_id'],
        )
        return res

    @api.onchange('use_payment_terminal')
    def _onchange_use_payment_terminal(self):
        super(PosPaymentMethod, self)._onchange_use_payment_terminal()
        if self.use_payment_terminal != 'xendit_pos':
            self.xendit_pos_secret_key = False
            self.xendit_pos_terminal_identifier = False

    @api.model
    def metric_update_order_status(self, data):
        payment_method = self.get_current_xendit_payment_method(data['terminal_id'])
        xendit_payment_method = None
        xendit_payment_status = None
        if('payment_channel' in data['xendit_invoice']):
            xendit_payment_method = data['xendit_invoice']['payment_channel']

        if('status' in data['xendit_invoice']):
            xendit_payment_status = data['xendit_invoice']['status']

        res = self.xenditClient.send_metric(
            self.xenditClient,
            self.xenditClient.generate_header(self.xenditClient, payment_method),
            self.xenditClient.generate_metric_payload(
                self.xenditClient,
                'update_order_status',
                'success',
                xendit_payment_method,
                xendit_payment_status
            )
        )
        return res