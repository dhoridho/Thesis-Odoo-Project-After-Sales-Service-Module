# -*- coding: utf-8 -*-

from odoo import models, api, fields

class ResConfigSetting(models.TransientModel):
    _inherit = 'res.config.settings'

    customer_esignature = fields.Boolean(string="Customer Signature")
    privy_url = fields.Char(string='URL')
    privy_username = fields.Char(string='Username')
    privy_password = fields.Char(string='Password')
    privy_merchant_key = fields.Char(string='Merchant-Key')

    @api.model
    def get_values(self):
        res = super(ResConfigSetting, self).get_values()
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        res.update({
            'customer_esignature': IrConfigParam.get_param('customer_esignature'),
            'privy_url': IrConfigParam.get_param('privy_url'),
            'privy_username': IrConfigParam.get_param('privy_username'),
            'privy_password': IrConfigParam.get_param('privy_password'),
            'privy_merchant_key': IrConfigParam.get_param('privy_merchant_key'),
        })
        return res

    def set_values(self):
        super(ResConfigSetting, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('customer_esignature', self.customer_esignature)
        self.env['ir.config_parameter'].sudo().set_param('privy_url', self.privy_url)
        self.env['ir.config_parameter'].sudo().set_param('privy_username', self.privy_username)
        self.env['ir.config_parameter'].sudo().set_param('privy_password', self.privy_password)
        self.env['ir.config_parameter'].sudo().set_param('privy_merchant_key', self.privy_merchant_key)
