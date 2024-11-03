# -*- coding: utf-8 -*-
#################################################################################
#
#   Copyright (c) 2015-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#   See LICENSE file for full copyright and licensing details.
#   If not, see <https://store.webkul.com/license.html/>
#
#################################################################################

from odoo import api, models, _
from odoo.http import request

from odoo.exceptions import AccessDenied

class Users(models.Model):
    _inherit = 'res.users'

    @api.model
    def _check_credentials(self, password,user_agent_env):
        totp = request.session.get('otploginobj')
        if totp and request.session.get('radio-otp',None)=='radiotp':
            if password.isdigit() and totp.isdigit():
                    if int(totp) == int(password):
                        request.session['otpverified'] = True
                    else:
                        request.session['otpverified'] = False
                        super(Users, self)._check_credentials(password,user_agent_env)
            else:
                raise AccessDenied()
        else:
            super(Users, self)._check_credentials(password,user_agent_env)
