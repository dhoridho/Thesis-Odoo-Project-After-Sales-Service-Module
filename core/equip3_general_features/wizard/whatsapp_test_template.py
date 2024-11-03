from odoo import fields, models, api
import requests
from odoo.exceptions import ValidationError

class WhatsAppTestTemplate(models.TransientModel):
    _name = 'master.test.template'

    wa_id = fields.Many2one('master.template.message')
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
        parameter = []
        if self.wa_id.message_line_ids:
            for line in self.wa_id.message_line_ids:
                parameter.append({'type':"text",
                                  "text":line.message
                                  })
                
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
                    "parameters": parameter
                }
            ]
            }
            }
        
        if self.wa_id.use_header:
            if self.wa_id.header_type == 'media':
                param['template']['components'].append({
                            "type": "header",
                            "parameters": [
                            {
                                "type": self.wa_id.file_type,
                                f"{self.wa_id.file_type}": {
                                "link": self.wa_id.link_file
                                }
                            }
                            ]
                        })
                
            if self.wa_id.header_type == 'text':
                param['template']['components'].append({
                            "type": "header",
                            "parameters": [
                            {
                                "type":"text",
                               "text": self.wa_id.header_text
                                
                            }
                            ]
                        })
        
        
        
        try:
            headers['Qiscus-App-Id'] = app_id
            headers['Qiscus-Secret-Key'] = token
            request_server = requests.post(f'{domain}{app_id}/{channel_id}/messages', json=param,headers=headers,verify=True)
            if request_server.status_code != 200:
                data = request_server.json()
                raise ValidationError(f"""{data["error"]["message"]}. Please contact your administrator. \n {param}""")
        except ConnectionError:
            raise ValidationError("Not connect to API Chat Server. Limit reached or not active")

