# -*- coding: utf-8 -*-
import json
import requests
from datetime import datetime

from odoo.http import request
from odoo import models, fields
from . import data_utils,  error_handler, encrypt, qrcode

class XenditClient():

    plugin_name = 'ODOO_POS'
    plugin_version = '1.0.3'

    tpi_server_url = "https://tpi.xendit.co"
    xendit_secret_key = ''
    dataUtils = data_utils.DataUtils()
    errorHandler = error_handler.ErrorHandler()
    qrCode = qrcode.Qrcode()

    def get_xendit_secret_key(self, payment_method):
        if payment_method.xendit_pos_encrypt_key is False:
            return payment_method.xendit_pos_secret_key

        return encrypt.decrypt(payment_method.xendit_pos_secret_key, payment_method.xendit_pos_encrypt_key)

    def generate_header(self, payment_method):
        self.xendit_secret_key = self.get_xendit_secret_key(self, payment_method)
        return self.dataUtils.generateHeader(
            self.xendit_secret_key,
            self.plugin_name,
            self.plugin_version
        )

    def generate_external_id(self, data):
        order_id = data['name'].split(' ')[1]
        timestamp = round(datetime.timestamp(datetime.now()) * 1000)
        return self.plugin_name+ '_' + order_id + '_' + str(timestamp)

    def generate_payload(self, data):
        customerObject = self.dataUtils.generateInvoiceCustomer(data['client'])
        payload = {
            'external_id': self.generate_external_id(self, data),
            'amount': data['amount'],
            'currency': data['currency']['name'],
            'description': data['name'],
            'items': self.dataUtils.generateInvoiceItems(data),
            'customer': customerObject,
            'client_type': 'INTEGRATION',
        }

        if len(customerObject) > 0 and not self.dataUtils.isEmptyString(customerObject['email']):
            payload['payer_email'] = customerObject['email']

        return payload

    def create_invoice(self, payment_method, data):
        endpoint = self.tpi_server_url + '/payment/xendit/invoice'
        headers = self.generate_header(self, payment_method)
        payload = self.generate_payload(self, data)

        try:
            res = requests.post(endpoint, json=payload, headers=headers, timeout=10)
        except requests.exceptions.RequestException as err:
            self.send_metric(
                self,
                headers,
                self.generate_metric_payload(self, 'checkout'),
            )
            return self.errorHandler.handleError('create_invoice', err)

        response = json.loads(res.text)

        # If error
        if res.status_code != 200:
            return self.errorHandler.handleError(
                'create_invoice',
                response["message"],
                res.status_code
            )

        # generate qrcode
        response['qrcode_image'] = self.qrCode.renderQrcode(response['invoice_url'])
        return response

    def get_invoice(self, payment_method, invoice_id):
        endpoint = self.tpi_server_url + '/payment/xendit/invoice/' + invoice_id
        headers = self.generate_header(self, payment_method)

        try:
            res = requests.get(endpoint, headers=headers, timeout=10)
        except requests.exceptions.RequestException as err:
            return self.errorHandler.handleError('get_invoice', err)

        response = json.loads(res.text)

        # If error
        if res.status_code != 200:
            return self.errorHandler.handleError(
                'get_invoice',
                response["message"],
                res.status_code
            )

        return response

    def cancel_invoice(self, payment_method, invoice_id):
        endpoint = self.tpi_server_url + '/payment/xendit/invoice/' + invoice_id + '/expire'
        headers = self.generate_header(self, payment_method)

        try:
            res = requests.post(endpoint, headers=headers, timeout=10)
        except requests.exceptions.RequestException as err:
            return self.errorHandler.handleError('cancel_invoice', err)

        # If error
        if res.status_code != 200:
            return self.errorHandler.handleError(
                'cancel_invoice',
                'Xendit invoice is not found or cancel failed.',
                res.status_code
            )

        if(res.status_code == 200):
            return True

        return False

    def generate_metric_payload(self, name, type='error', payment_method=None, payment_status=None):
        additional_tags = {
                'version': self.plugin_version,
                'is_live': self.xendit_secret_key.index('development') == -1,
                'type': type,
                'payment_status': payment_status
            }

        if(payment_method is not None and payment_method):
            additional_tags['payment_method'] = payment_method

        return {
            'name': self.plugin_name.lower() + '_' + name,
            'additional_tags': additional_tags
        }

    def send_metric(self, headers, payload):
        try:
            endpoint = self.tpi_server_url + '/log/metrics/count'
            requests.post(endpoint, json=payload, headers=headers, timeout=10)
        except requests.exceptions.RequestException as err:
            return self.errorHandler.handleError('send_metric')