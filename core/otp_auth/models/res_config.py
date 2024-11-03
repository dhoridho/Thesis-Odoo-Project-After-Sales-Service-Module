# -*- coding: utf-8 -*-
#################################################################################
#
#   Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#   See LICENSE file for full copyright and licensing details.
#   If not, see <https://store.webkul.com/license.html/>
#
#################################################################################

from odoo import api, fields, models, _

class WebsiteOTPSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    _name = 'website.otp.settings'
    _description = 'Website Otp Settings'
    signin_auth = fields.Boolean(string="Sign-in Authentication")
    signup_auth = fields.Boolean(string="Sign-up Authentication")
    otp_type = fields.Selection([('4', 'Text'), ('3', 'Password')], string="OTP type",
                                  help="""OTP type for user view.
                                    * [Text] OTP will be visible as text type to the user
                                    * [Password] OTP will be visible as password type to the user""")
    otp_time_limit = fields.Integer('OTP Time Limit',
                            help="OTP expiry time")

    # @api.multi
    def set_values(self):
        super(WebsiteOTPSettings, self).set_values()
        IrDefault = self.env['ir.default'].sudo()
        IrDefault.set('website.otp.settings','signin_auth', self.signin_auth)
        IrDefault.set('website.otp.settings','signup_auth', self.signup_auth)
        IrDefault.set('website.otp.settings','otp_time_limit', self.otp_time_limit)
        IrDefault.set('website.otp.settings','otp_type', self.otp_type)
        return True

    # @api.multi
    def get_values(self):
        res = super(WebsiteOTPSettings, self).get_values()
        IrDefault = self.env['ir.default'].sudo()
        res.update({
            'signin_auth':IrDefault.get('website.otp.settings','signin_auth', self.signin_auth),
            'signup_auth':IrDefault.get('website.otp.settings','signup_auth', self.signup_auth),
            'otp_type':IrDefault.get('website.otp.settings','otp_type', self.otp_type),
        })
        return res
