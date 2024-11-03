# -*- coding: utf-8 -*-
# Copyright 2022 IZI PT Solusi Usaha Mudah
import base64
import logging
import random
import re
import time

from odoo.exceptions import AccessDenied, ValidationError

from odoo import http, _
from odoo.http import request
from odoo.addons.web.controllers.main import Home as HomeOrigin
from odoo.addons.auth_totp.models.res_users import TIMESTEP, hotp, TOTP

from odoo.addons.izi_lazada_datamoat.utils.lazada.datamoat import LazadaDatamoat

_logger = logging.getLogger(__name__)


class Home(HomeOrigin):
    @http.route()
    def web_login(self, redirect=None, **kw):
        response = super(Home, self).web_login(redirect, **kw)
        qcontext = response.qcontext

        if request.httprequest.method == 'POST':
            # noinspection PyUnresolvedReferences
            appkey = request.lazop_app_key()
            if appkey and request.httprequest.environ.get('HTTP_X_FORWARDED_FOR'):
                mp_account_obj_sudo = request.env['mp.account'].sudo()

                mp_account = mp_account_obj_sudo.search([('lz_app_key', '=', appkey)])
                lz_account = mp_account.lazada_get_account(host='all')
                lz_datamoat = LazadaDatamoat(lz_account, **{
                    'user_login': request.params.get('login'),
                    'user_ip': request.httprequest.environ['HTTP_X_FORWARDED_FOR'],
                    'ati': request.httprequest.cookies.get('_ati')
                })

                # Invoke Datamoat Login API
                lz_response = lz_datamoat.login(**{
                    'login_result': 'success' if 'error' not in qcontext else 'fail',
                    'login_msg': qcontext.get('error', 'Success')
                })
                if not lz_response.body.get('result').get('success'):
                    raise ValidationError(lz_response.body.get('result').get('msg'))

        return response

    @http.route('/web/login/datamoat/totp', type='http', auth='public', methods=['GET', 'POST'], sitemamp=False,
                website=True)
    def web_datamoat_totp(self, redirect=None, **kwargs):
        if request.session.uid:
            return http.redirect_with_hash(self._login_redirect(request.session.uid, redirect=redirect))

        if not request.session.pre_uid:
            return http.redirect_with_hash('/web/login')

        error = None
        user = request.env['res.users'].browse(request.session.pre_uid)
        if user and request.httprequest.method == 'POST':
            # Validate OTP
            key = base64.b32encode(request.httprequest.values.get('csrf_token').encode())
            try:
                with user._assert_can_auth():
                    match = TOTP(key).match(int(re.sub(r'\s', '', kwargs['totp_token'])))
                    if match is None:
                        _logger.info("2FA check: FAIL for %s %r", self, "self.login")
                        raise AccessDenied()
                    _logger.info("2FA check: SUCCESS for %s %r", self, "self.login")
            except AccessDenied:
                error = _("Verification failed, please double-check the 6-digit code")
            except ValueError:
                error = _("Invalid authentication code format.")
            else:
                request.session.finalize()
                response = http.redirect_with_hash(self._login_redirect(request.session.uid, redirect=redirect))
                return response

        return request.render('izi_lazada_datamoat.lazop_datamoat_totp_form', {
            'error': error,
            'redirect': redirect,
        })

    @http.route('/web/login/datamoat/totp/ask', type='json', auth='public', methods=['POST'], sitemamp=False,
                website=True)
    def web_datamoat_totp_ask(self, **kwargs):
        # Generate OTP
        t = time.time()
        secret = base64.b32encode(kwargs.get('csrf_token').encode())
        low = int((t - TIMESTEP) / TIMESTEP)
        high = int((t + TIMESTEP) / TIMESTEP) + 1
        otp = hotp(secret, random.choice([counter for counter in range(low, high)]))

        # Send the OTP via Email
        user_obj_sudo = request.env['res.users'].sudo()
        context = {'mail_ctx': {'otp': otp}}
        user_obj_sudo.with_context(context).lazada_datamoat_send_otp(int(request.session.get('pre_uid')))

        return {'wait_time': TIMESTEP}
