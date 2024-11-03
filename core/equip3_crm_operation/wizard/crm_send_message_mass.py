from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

class CRMSendMessageMass(models.TransientModel):
    _name = 'crm.send.message.mass'
    _description = 'Send Message Mass'
    
    message_chat_ids = fields.One2many('acrux.chat.message.wizard', 'crm_message_mass_id', string='Message Chat')
    conversation_id = fields.Many2one('acrux.chat.conversation', string='ChatRoom', ondelete='set null')
    connector_id = fields.Many2one('acrux.chat.connector', string='Channel', ondelete='set null')

    @api.onchange('conversation_id', 'connector_id')
    def _onchange_conversation_id(self):
        for rec in self:
            for line in rec.message_chat_ids:
                if rec.conversation_id:
                    line.conversation_id = rec.conversation_id
                if rec.connector_id:
                    line.connector_id = rec.connector_id
    
    def send_mass(self):
        error_channel = False
        error_number = False
        self._onchange_conversation_id()
        for line in self.message_chat_ids:
            if not line.mobile:
                error_number = True
            
            if not line.connector_id:
                error_channel = True

        if error_channel:
            raise ValidationError(_('Please select Channel to send message.'))
        elif error_number:
            raise ValidationError('Mobile number must be filled!')
        else:
            for line in self.message_chat_ids:
                line.send_message_wizard_mass()
    

class ChatMessageWizard(models.TransientModel):
    ''' Partner required '''
    _inherit = 'acrux.chat.message.wizard'
    
    opportunity_id = fields.Many2one('crm.lead', string='Opportunity')
    whatsapp_template_id = fields.Many2one('whatsapp.template', string='Whatsapp Template')
    crm_message_mass_id = fields.Many2one('crm.send.message.mass', string='Message Mass')
    
    mobile = fields.Char('Mobile')
    attachment_ids = fields.Many2many(
        'ir.attachment', 'send_whatsapp_compose_message_ir_attachments_rel',
        'wizard_id', 'attachment_id', 'Attachments')

    @api.onchange("whatsapp_template_id")
    def on_change_whatsapp_template_id(self):
        for rec in self:
            if self.whatsapp_template_id:
                self.text = self.whatsapp_template_id.message
    
