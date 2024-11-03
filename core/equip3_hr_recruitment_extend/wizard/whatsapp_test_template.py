from odoo import fields, models, api
import requests
from odoo.exceptions import ValidationError

class WhatsAppTestTemplate(models.TransientModel):
    _name = 'whatsapp.test.template'

    wa_id = fields.Many2one('wa.template.message')
    phone_number = fields.Char(default="+62")
    broadcast_template_id = fields.Many2one('qiscus.wa.template.content',string="Broadcast Template")

    def send(self):
        self.ensure_one()
        domain = self.env['ir.config_parameter'].sudo().get_param('qiscus.api.url') 
        token = self.env['ir.config_parameter'].sudo().get_param('qiscus.api.secret_key') 
        app_id = self.env['ir.config_parameter'].sudo().get_param('qiscus.api.appid') 
        channel_id = self.env['ir.config_parameter'].sudo().get_param('qiscus.api.channel_id') 
        headers = {'content-type': 'application/json'}
        phone_num = str(self.phone_number)
        if "+" in phone_num:
            phone_num =  int(phone_num.replace("+",""))
        param = {
            "to":phone_num,
            "type":"template",
            "template": {
            "namespace":self.broadcast_template_id.template_id.namespace,
            "name": self.broadcast_template_id.template_id.name,
            "language": {
                "policy": "deterministic",
                "code": f"{self.broadcast_template_id.language}"
            },
                "components": [

                {
                    "type" : "body",
                    "parameters": [
                        {
                            "type": "text",
                            "text": f"{self.wa_id.message}".replace("$","")
                        }
                        
                    ]
                }
            ]
            }
            }
        try:
            headers['Qiscus-App-Id'] = app_id
            headers['Qiscus-Secret-Key'] = token
            request_server = requests.post(f'{domain}{app_id}/{channel_id}/messages', json=param,headers=headers,verify=True)
            if request_server.status_code != 200:
                data = request_server.json()
                raise ValidationError(f"""{data["errors"]["message"]}. Please contact your administrator.""")
        except ConnectionError:
            raise ValidationError("Not connect to API Chat Server. Limit reached or not active")

