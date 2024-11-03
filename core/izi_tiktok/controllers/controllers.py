# -*- coding: utf-8 -*-
# Copyright 2023 IZI PT Solusi Usaha Mudah

from odoo import http
from odoo.http import *
from odoo.http import local_redirect, request
from odoo.addons.web.controllers.main import ensure_db
import logging
_logger = logging.getLogger(__name__)

# auth_state = 'IZITIKTOKSHOP'
auth_state = 'HMTIKTOKSHOP'


class IZITikTok(http.Controller):

    @http.route('/tiktok/callback', type='http', csrf=False, auth='public')
    def tiktok_callback(self, **kwargs):
        if kwargs.get('code') and kwargs.get('state'):
            mp_id = kwargs.get('state').split(auth_state)
            if mp_id and len(mp_id) == 2:
                mp_account = request.env['mp.account'].sudo().browse(int(mp_id[1]))
                mp_account.tiktok_get_access_token(kwargs.get('code'))
        _logger.info("Closing page")
        return '''
        <!DOCTYPE html>
        <html>
            <body>
                <script type="text/javascript">
                    /* alert('Auth Success.'); */
                    window.onunload = function() {window.opener.location.reload()}
                    window.close();
                </script>
            </body>
        </html>
        '''

    @http.route('/tiktok/webhook', type='http', csrf=False, auth='public')
    def tiktok_webhook(self, **kwargs):
        print(kwargs)
        return True
