from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    sales_to_manufacturing = fields.Boolean('Sales To Production', related='company_id.sales_to_manufacturing', readonly=False)
    send_email_so_confirm = fields.Boolean('Email Notification', related='company_id.send_email_so_confirm', readonly=False)
    send_system_so_confirm = fields.Boolean('System Notification', related='company_id.send_system_so_confirm', readonly=False)
    send_whatsapp_so_confirm = fields.Boolean('SO WhatsApp Notification', related='company_id.send_whatsapp_so_confirm', readonly=False)
    connector_whatsapp_so_confirm = fields.Many2one('acrux.chat.connector', config_parameter='equip3_manuf_sale.connector_whatsapp_so_confirm')
    check_availability = fields.Boolean(related='company_id.check_availability', readonly=False)

    @api.model
    def create(self, vals):
        sales_to_manufacturing = vals.get('sales_to_manufacturing')
        group_id = self.env.ref('equip3_manuf_accessright_settings.group_mrp_notification')
        if sales_to_manufacturing:
            group_id.users = [(4, self.env.user.id)]
        else:
            group_id.users = [(3, self.env.user.id)]
        return super(ResConfigSettings, self).create(vals)

    @api.onchange('manufacturing')
    def _onchange_manufacturing(self):
        if not self.manufacturing:
            self.sales_to_manufacturing = False
