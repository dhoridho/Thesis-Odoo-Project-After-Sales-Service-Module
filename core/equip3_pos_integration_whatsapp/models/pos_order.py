# -*- coding: utf-8 -*-

import logging
import requests
import json
import base64
import os

from datetime import datetime, timedelta

from odoo import api, fields, models, tools
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _inherit = "pos.order"

    def _whatsapp_filepath(self):
        return str(os.path.dirname(__file__)) + f'/../static/receipt/'

    def auto_remove_whatsapp_receipt_files(self):
        path = self._whatsapp_filepath()
        images = os.listdir(path)

        if not images:
            return

        limit = 3000
        images = filter(lambda x: x[-3:] in ['jpg'] and '-dt-' in x, images)
        # Check if image already created 30 minutes ago
        images = filter(lambda x: datetime.strptime(x.split('-dt-')[1][:14],'%Y%m%d%H%M%S') < (datetime.now()-timedelta(minutes=30)) , images)
        images = list(images)[:limit]

        for image in images:
            image_path = path + image
            os.remove(image_path)
        
        _logger.info("POS auto remove unused whatsapp receipt files --> Images: %s" % str(len(images)))

    def action_whatsapp_save_receipt(self, name, ticket):
        if not self:
            return {'status': 'error', 'message': 'Error Self'}
        
        name = name[6:]
        filename = f'{name}-dt-' + datetime.now().strftime('%Y%m%d%H%M%S') + '.jpg'
        path = self._whatsapp_filepath()

        # Store image to file
        f = open(f'{path}/{filename}', 'wb')
        f.write(base64.b64decode(ticket))
        f.close()

        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        media = [{
            'type': 'image',
            'image': { 
                'link': f'{base_url}/equip3_pos_integration_whatsapp/static/receipt/{filename}',
            }
        }]
        return { 'status': 'success', 'media': media }


    def action_whatsapp_message_to_customer(self, sent_to, media=[],dictorder=False):
        order = self
        if not self:
            return {'status': 'error', 'message': 'Error Self'}

        template = self.env.ref('equip3_pos_integration_whatsapp.template_for_send_receipt_via_whatsapp')
        channel_id = self.env['ir.config_parameter'].get_param('qiscus.api.channel_id')
        token = self.env['ir.config_parameter'].get_param('qiscus.api.secret_key')
        base_url = self.env['ir.config_parameter'].get_param('qiscus.api.url')
        app_id = self.env['ir.config_parameter'].get_param('qiscus.api.appid')
        qiscus_endpoint_url = f'{base_url}{app_id}/{channel_id}/messages'

        sent_to = sent_to.replace('+', '').replace(' ', '').replace('-', '')
        header_parameters = media
        body_parameters = order._get_body_parameters(template,dictorder)
        params = {
            "to": sent_to,
            "type": "template",
            "template": {
                "name": 'hm_pos_customer_receipt',
                "namespace": 'f034d708_96a1_4438_8553_b6bfde47008a',
                "language": {
                    "policy": "deterministic",
                    "code": "en"
                },
                "components": [
                    { "type": "header", "parameters": header_parameters },
                    { "type": "body", "parameters": body_parameters }
                ]
            }
        }
        headers = {
            "content-type": "application/json",
            "Qiscus-App-Id": app_id,
            "Qiscus-Secret-Key": token
        }
        values = { 'status': 'error', 'message': 'None' }

        _logger.info(f'POS Whatsapp message ({order.pos_reference}): Sending request...')
        try:
            response = requests.post(qiscus_endpoint_url, json=params, headers=headers, verify=True)
            _logger.info("\nPOS Whatsapp --> Send e-receipt to customer:\n-->Header: %s \n-->Parameter: %s \n-->Result: %s" % (headers, params, response.json()))
            values['status_code'] = response.status_code
            values['message'] = response.text
            if response.status_code in [200]:
                values['status'] = 'success'
            else:
                values['status'] = 'error'
        except ConnectionError:
            raise ValidationError("Not connect to API Chat Server. Limit reached or not active!")

        _logger.info(f'POS Whatsapp message ({order.pos_reference}): Done')
        values['sent_to'] = json.dumps(params['to'])
        values['components'] = json.dumps(params['template']['components'])
        return values

    def _get_body_parameters(self, template,dictorder=False):
        message = str(tools.html2plaintext(template.body_html))
        message = message.replace('\n','')
        dateorder = datetime.strptime(dictorder['date_order'],'%m/%d/%Y')
        if "${customer}" in message:
            message = message.replace('${customer}', dictorder['customer'] or 'Customer')
        if "${order_number}" in message:
            message = message.replace('${order_number}', dictorder['pos_reference'] or '-')
        if "${day}" in message:
            message = message.replace('${day}', dictorder['day'])
        if "${date}" in message:
            message = message.replace('${date}', dateorder.strftime('%d %B %Y'))
        if "${grand_total}" in message:
            amount_paid = self._format_currency_amount(float(dictorder['amount_paid']))
            message = message.replace('${grand_total}', amount_paid)

        #Split to get parameters required
        message = message.split('${br}')
        parameters = []
        for _message in message:
            parameters += [{ "type": "text", "text": _message }]
        return parameters


    def _format_currency_amount(self, amount):
        pre = post = u''
        if self.currency_id.position == 'before':
            pre = u'{symbol}\N{NO-BREAK SPACE}'.format(symbol=self.currency_id.symbol or '')
        else:
            post = u'\N{NO-BREAK SPACE}{symbol}'.format(symbol=self.currency_id.symbol or '')

        amount = '{:,.0f}'.format(amount)
        format_amount = '{pre}{amount}{post}'.format(amount=amount, pre=pre, post=post)
        format_amount = str(format_amount)
        format_amount = ' '.join(format_amount.split())
        return format_amount