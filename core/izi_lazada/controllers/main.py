# -*- coding: utf-8 -*-
# Copyright 2022 IZI PT Solusi Usaha Mudah

from odoo import http


class IZILazada(http.Controller):
    @http.route('/api/user/auth/lazada/<model("mp.account"):mp_id>/', auth='public')
    def get_oauth_code(self, mp_id, **kwargs):
        mp_id.sudo().lazada_get_token(**kwargs)
        return """
        <!DOCTYPE html>
        <html>
            <body>
                <script type="text/javascript">
                    window.onunload = function() {window.opener.location.reload()}
                    window.close();
                </script>
            </body>
        </html>
        """
