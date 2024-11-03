from odoo import fields, models, api, _


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    notifications_expiry_customer_bank_guarantee = fields.Boolean("Email Notification for Bank Guarantee", default=True)
    notifications_expiry_customer_bank_guarantee_time = fields.Integer("Notification for Bank Guarantee Time", default=7)

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        res.update({
            'notifications_expiry_customer_bank_guarantee': IrConfigParam.get_param('notifications_expiry_customer_bank_guarantee', False),
            'notifications_expiry_customer_bank_guarantee_time': IrConfigParam.get_param('notifications_expiry_customer_bank_guarantee_time', False),
        })
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('notifications_expiry_customer_bank_guarantee', self.notifications_expiry_customer_bank_guarantee)
        self.env['ir.config_parameter'].sudo().set_param('notifications_expiry_customer_bank_guarantee_time', self.notifications_expiry_customer_bank_guarantee_time)
