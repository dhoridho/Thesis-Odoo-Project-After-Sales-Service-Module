
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

class SendMessageMass(models.TransientModel):
    _name = 'send.message.mass'
    _description = 'Send Message Mass'

    # message_chat_ids = fields.Many2many('acrux.chat.message.wizard', string='Message Chat')
    message_chat_ids = fields.One2many('acrux.chat.message.wizard', 'message_mass_id', string='Message Chat')
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


    def send_message(self):
        for record in self.sale_ids:
            action_id = self.env.ref('sale.action_quotations_with_onboarding')
            wa_approved_template_id = self.env.ref('equip3_sale_operation.email_template_sale_order_approval_approved_wa')
            is_over_limit_validation = self.env['ir.config_parameter'].sudo().get_param('is_over_limit_validation', False)
            is_customer_approval_matrix = self.env['ir.config_parameter'].sudo().get_param('is_customer_approval_matrix', False)

            send = True
            if is_over_limit_validation and is_customer_approval_matrix:
                if record.state != 'quotation_approved':
                    raise ValidationError('There is Quotation that has not approved')
            elif not is_over_limit_validation and not is_customer_approval_matrix:
                if record.state != 'draft':
                    send = False

            user = self.env.user
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/web#id=' + str(record.id) + '&action='+ str(action_id.id) + '&view_type=form&model=sale.order'
            phone_num = str(record.user_id.partner_id.mobile) or str(record.user_id.partner_id.phone)

            if send:
                # record._send_whatsapp_message_approval(wa_approved_template_id, record.user_id.partner_id, phone_num, url)
                record._send_qiscus_whatsapp_approval(wa_approved_template_id, record.user_id.partner_id, phone_num, url)

    def send_mass(self):
        is_over_limit_validation = self.env['ir.config_parameter'].sudo().get_param('is_over_limit_validation', False)
        is_customer_approval_matrix = self.env['ir.config_parameter'].sudo().get_param('is_customer_approval_matrix', False)

        error = False
        error_channel = False
        error_number = False
        self._onchange_conversation_id()
        for line in self.message_chat_ids:
            if not line.mobile:
                error_number = True

            if line.sale_id:
                if line.sale_id.state != 'sale':
                    if is_over_limit_validation and is_customer_approval_matrix:
                        if line.sale_id.state != 'quotation_approved':
                            error = True

            if not line.connector_id:
                error_channel = True

        if error:
            raise ValidationError('There is Quotation that has not approved')
        elif error_channel:
            raise ValidationError(_('Please select Channel to send message.'))
        elif error_number:
            raise ValidationError('Mobile number must be filled!')
        else:
            for line in self.message_chat_ids:
                line.send_message_wizard_mass()
