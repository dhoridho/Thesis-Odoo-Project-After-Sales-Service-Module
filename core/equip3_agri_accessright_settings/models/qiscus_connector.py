import re
import requests
from odoo import _
from odoo.exceptions import ValidationError


def qiscus_request(self, message, phone_number):
    self.ensure_one()

    broadcast_template_id = self.env['qiscus.wa.template.content'].search([
        ('language', '=', 'en'),
        ('template_id.name', '=', 'hm_notification_template')
    ], limit=1)

    if not broadcast_template_id:
        raise ValidationError(_("Cannot find Whatsapp template with name = 'hm_notification_template'!"))

    message = re.sub(r'\n+', ', ', message)
    domain = self.env['ir.config_parameter'].get_param('qiscus.api.url') 
    token = self.env['ir.config_parameter'].get_param('qiscus.api.secret_key') 
    app_id = self.env['ir.config_parameter'].get_param('qiscus.api.appid') 
    channel_id = self.env['ir.config_parameter'].get_param('qiscus.api.channel_id') 

    headers = {
        'content-type': 'application/json',
        'Qiscus-App-Id': app_id,
        'Qiscus-Secret-Key': token
    }

    url = f'{domain}{app_id}/{channel_id}/messages'

    params = {
        "to": phone_number,
        "type": "template",
        "template": {
            "namespace": broadcast_template_id.template_id.namespace,
            "name": broadcast_template_id.template_id.name,
            "language": {
                "policy": "deterministic",
                "code": 'en'
            },
                "components": [{
                    "type" : "body",
                    "parameters": [{
                        "type": "text",
                        "text": message
                    }]}
                ]
            }
        }
    try:
        response = requests.post(url, json=params, headers=headers, verify=True)
    except Exception as err:
        raise ValidationError(err)
