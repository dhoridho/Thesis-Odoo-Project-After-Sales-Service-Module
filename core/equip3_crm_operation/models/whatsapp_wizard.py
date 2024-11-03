
from odoo import api, fields, models, _
import html2text
from odoo.exceptions import UserError, ValidationError, Warning
from odoo.addons.acrux_chat.tools import phone_format

class ChatMessageWizard(models.TransientModel):
    ''' Partner required '''
    _inherit = 'acrux.chat.message.wizard'

    phone = fields.Char("Phone")
    is_crm = fields.Boolean("CRM")

class AcruxChatConversation(models.Model):
    _inherit = 'acrux.chat.conversation'

    @api.model
    def conversation_create(self, partner_id, id_connector=False, number=False):
        ''' Set 'number' if not take from partner. '''
        def validate_number(partner_id, number):
            number = number or partner_id.mobile or partner_id.phone
            if self.env.context.get('default_is_crm') != None:
                if not self.env.context.get('default_phone'):
                    raise ValidationError(_('Phone field is required!'))
                phone = phone_format(self.env.context.get('default_phone').lstrip('+'), partner_id.country_id)
                if number != phone:
                    number = phone
            if not number:
                raise ValidationError(_('Partner does not have mobile number'))
            return phone_format(number.lstrip('+'), partner_id.country_id)

        if not id_connector:
            id_connector = self.env['acrux.chat.connector'].search([], limit=1).id
        number = validate_number(partner_id, number)
        conv_id = self.create({'name': partner_id.name,
                               'number': number,
                               'connector_id': id_connector,
                               'res_partner_id': partner_id.id,
                               'status': 'current',
                               'sellman_id': self.env.user.id})
        return conv_id

class WhatsappSendMessage(models.TransientModel):
    _inherit = 'whatsapp.message.wizard'

    crm_lead = fields.Boolean("CRM")
    company_name = fields.Char("Company Name")

    def send_message(self):
        context = dict(self.env.context) or {}
        if context.get('active_model') == "crm.lead":
            number = self._context.get('default_mobile_number', False)
            if number:
                self.mobile_number = number
            if self.message and self.mobile_number:
                message_string = ''
                message = self.message.split(' ')
                for msg in message:
                    message_string = message_string + msg + '%20'
                message_string = message_string[:(len(message_string) - 3)]
                number = self.mobile_number
                link = "https://web.whatsapp.com/send?phone=" + number
                send_msg = {
                    'type': 'ir.actions.act_url',
                    'url': link + "&text=" + message_string,
                    'target': 'new',
                    'res_id': self.id,
                }
                return send_msg
        else:
            return super(WhatsappSendMessage, self).send_message()
