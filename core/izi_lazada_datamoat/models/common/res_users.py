# -*- coding: utf-8 -*-
# Copyright 2022 IZI PT Solusi Usaha Mudah
import logging

from odoo.exceptions import ValidationError
from odoo.http import request

from odoo import api, fields, models
from odoo.addons.izi_lazada_datamoat.utils.lazada.datamoat import LazadaDatamoat

_logger = logging.getLogger(__name__)


class Users(models.Model):
    _inherit = 'res.users'

    @api.model
    def lazada_datamoat_send_otp(self, rec_id):
        mail_obj_sudo = self.env['mail.mail'].sudo()

        mail_ctx = self._context.get('mail_ctx', {})
        mail_tmpl = self.env.ref('izi_lazada_datamoat.mail_tmpl_datamoat_totp')
        assert mail_tmpl._name == 'mail.template'
        mail_id = mail_tmpl.with_context(mail_ctx).sudo().send_mail(rec_id, force_send=True)
        mail = mail_obj_sudo.browse(mail_id)
        _logger.info('An email with subject "%s" created and will be sent immediately.' % mail.subject)

    def _mfa_url(self):
        r = super(Users, self)._mfa_url()
        if r is not None:
            return r

        # noinspection PyUnresolvedReferences
        appkey = request.lazop_app_key()
        if appkey and request.httprequest.environ.get('HTTP_X_FORWARDED_FOR'):
            mp_account_obj_sudo = self.env['mp.account'].sudo()

            mp_account = mp_account_obj_sudo.search([('lz_app_key', '=', appkey)])
            lz_account = mp_account.lazada_get_account(host='all')
            lz_datamoat = LazadaDatamoat(lz_account, **{
                'user_login': request.params.get('login'),
                'user_ip': request.httprequest.environ['HTTP_X_FORWARDED_FOR'],
                'ati': request.httprequest.cookies.get('_ati')
            })

            # Invoke Datamoat Compute Risk API
            lz_response = lz_datamoat.compute_risk()
            if 'result' in lz_response.body:
                if not lz_response.body.get('result').get('success'):
                    raise ValidationError(lz_response.body.get('result').get('msg'))

                datamoat_risk = float(lz_response.body.get('result').get('risk'))
                if datamoat_risk >= 0.5:
                    return '/web/login/datamoat/totp'
