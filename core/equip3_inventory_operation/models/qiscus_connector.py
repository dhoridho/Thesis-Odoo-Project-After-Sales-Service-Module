import requests
from odoo import _
from werkzeug.urls import url_encode
from odoo.exceptions import ValidationError


def get_form_url(self, action_xmlid, menu_xmlid):
    self.ensure_one()
    action_id = self.env.ref(action_xmlid).id
    menu_id = self.env.ref(menu_xmlid).id
    params = {
        'id': self.id,
        'model': self._name,
        'action': action_id,
        'menu_id': menu_id,
        'view_type': 'form'
    }
    form_url = '/web#%s' % url_encode(params)
    return self.env['ir.config_parameter'].sudo().get_param('web.base.url') + form_url


def qiscus_request(self, values):
    self.ensure_one()

    phone_number = values['receiver'].partner_id.mobile
    if not phone_number:
        raise ValidationError(_('Phone number must be set for %s!' %
                              values['receiver'].partner_id.display_name))
    phone_number = phone_number.replace('+', '')

    broadcast_template_id = self.env['qiscus.wa.template.content'].search([
        ('language', '=', 'en'),
        ('template_id.name', '=', 'hm_notification_template')
    ], limit=1)

    if not broadcast_template_id:
        raise ValidationError(
            _("Cannot find Whatsapp template with name = 'hm_notification_template'!"))

    message = "Dear {receiver}, {sender} has requested approval for {name} ({no}) on {datetime}, Please Approve the {name} at the following link: {form_url} Best Regards.".format(
        receiver=values['receiver'].partner_id.name,
        sender=values['sender'].partner_id.name,
        name=values['name'],
        no=values['no'],
        datetime=values['datetime'],
        form_url=get_form_url(
            self, values['action_xmlid'], values['menu_xmlid'])
    )

    domain = self.env['ir.config_parameter'].get_param('qiscus.api.url')
    token = self.env['ir.config_parameter'].get_param('qiscus.api.secret_key')
    app_id = self.env['ir.config_parameter'].get_param('qiscus.api.appid')
    channel_id = self.env['ir.config_parameter'].get_param(
        'qiscus.api.channel_id')

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
                "type": "body",
                "parameters": [{
                        "type": "text",
                        "text": message
                }]}
            ]
        }
    }
    try:
        response = requests.post(
            url, json=params, headers=headers, verify=True)
    except Exception as err:
        raise ValidationError(err)
