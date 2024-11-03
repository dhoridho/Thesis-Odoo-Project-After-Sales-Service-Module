from odoo import fields, models, api, _


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    notifications_expiry_voucher = fields.Boolean("Email Notification for expiry voucher", default=True)
    notifications_time = fields.Integer("Notification Time", default=7)

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        res.update({
            'notifications_expiry_voucher': IrConfigParam.get_param('notifications_expiry_voucher', False),
            'notifications_time': IrConfigParam.get_param('notifications_time', False),
        })
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('notifications_expiry_voucher', self.notifications_expiry_voucher)
        self.env['ir.config_parameter'].sudo().set_param('notifications_time', self.notifications_time)
