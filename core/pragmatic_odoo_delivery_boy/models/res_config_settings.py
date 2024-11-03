import time
from io import BytesIO
import logging
_logger = logging.getLogger(__name__)


from odoo import api, fields, models, _
import requests
import base64
import json



class base(models.TransientModel):
    _inherit = "res.config.settings"

    whatsapp_instance_id = fields.Char('Whatsapp Instance ID')
    whatsapp_token = fields.Char('Whatsapp Token')
    qr_code_image = fields.Binary("QR code")
    whatsapp_authenticate = fields.Boolean('Authenticate', default=False)

    @api.model
    def get_values(self):
        res = super(base, self).get_values()
        Param = self.env['ir.config_parameter'].sudo()
        res['whatsapp_instance_id'] = Param.sudo().get_param('pragmatic_odoo_delivery_boy.whatsapp_instance_id')
        res['whatsapp_token'] = Param.sudo().get_param('pragmatic_odoo_delivery_boy.whatsapp_token')
        res['whatsapp_authenticate'] = Param.sudo().get_param('pragmatic_odoo_delivery_boy.whatsapp_authenticate')
        res.update(qr_code_image=Param.sudo().get_param('pragmatic_odoo_delivery_boy.qr_code_image'))
        return res


    def set_values(self):
        super(base, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('pragmatic_odoo_delivery_boy.whatsapp_instance_id', self.whatsapp_instance_id)
        self.env['ir.config_parameter'].sudo().set_param('pragmatic_odoo_delivery_boy.whatsapp_token', self.whatsapp_token)
        # self.env['ir.config_parameter'].sudo().set_param('pragmatic_odoo_whatsapp_integration.group_send_report_url_in_message', self.group_send_report_url_in_message)
        self.env['ir.config_parameter'].sudo().set_param('pragmatic_odoo_delivery_boy.qr_code_image', self.qr_code_image)

    def action_get_qr_code(self):
        return {
            'name': _("Scan WhatsApp QR Code"),
            'view_mode': 'form',
            # 'view_id': view_id,
            'view_type': 'form',
            'res_model': 'whatsapp.scan.qr',
            'type': 'ir.actions.act_window',
            'target': 'new',
            # 'context': context,
        }

    def action_logout_from_whatsapp(self):
        Param = self.sudo().get_values()
        url = 'https://api.chat-api.com/instance' + Param.get('whatsapp_instance_id') + '/logout?token=' + Param.get('whatsapp_token')
        headers = {
            "Content-Type": "application/json",
        }

        tmp_dict = {
            "accountStatus": "Logout request sent to WhatsApp"
        }

        response = requests.post(url, json.dumps(tmp_dict), headers=headers)

        if response.status_code == 201 or response.status_code == 200:
            _logger.info("\nWhatsapp logout successfully")
            self.env['ir.config_parameter'].sudo().set_param('pragmatic_odoo_delivery_boy.whatsapp_authenticate', False)


