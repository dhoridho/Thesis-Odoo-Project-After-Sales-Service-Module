# -*- coding: utf-8 -*-
#################################################################################
#
#   Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#   See LICENSE file for full copyright and licensing details.
#   If not, see <https://store.webkul.com/license.html/>
#
#################################################################################

from odoo import fields, models, _


class WebkulWebsiteAddons(models.TransientModel):
    _inherit = 'webkul.website.addons'

    module_otp_auth = fields.Boolean(
        string="OTP Authentication")
