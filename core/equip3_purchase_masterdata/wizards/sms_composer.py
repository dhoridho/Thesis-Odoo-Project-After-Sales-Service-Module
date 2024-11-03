from odoo import models


class SMSComposerInherit(models.TransientModel):
    _inherit = 'sms.composer'

    def action_send_whatsapp(self):
        if self.body and self.recipient_single_number_itf:
                message_string = ''
                message = self.body.split(' ')
                for msg in message:
                    message_string = message_string + msg + '%20'
                message_string = message_string[:(len(message_string) - 3)]
                number = self.recipient_single_number_itf
                link = "https://web.whatsapp.com/send?phone=" + number
                send_msg = {
                    'type': 'ir.actions.act_url',
                    'url': link + "&text=" + message_string,
                    'target': 'new',
                    'res_id': self.id,
                }

                return send_msg
