# -*- coding: utf-8 -*-

import logging
import os
import re
import traceback
import unicodedata
import werkzeug.exceptions
import werkzeug.routing
import werkzeug.urls
import odoo
from odoo import api, models, registry, exceptions, tools
from odoo.addons.base.models.ir_http import RequestUID, ModelConverter
from odoo.addons.base.models.qweb import QWebException
from odoo.http import request
from odoo.osv import expression
from odoo.tools import config, ustr, pycompat
from  odoo.addons.http_routing.models.ir_http import IrHttp
# from .....addons.http_routing.models.ir_http import IrHttp

_logger = logging.getLogger(__name__)




class IrHttnew(IrHttp):
    
    
    # @classmethod
    def _handle_exception_custom(cls, exception):
        is_frontend_request = bool(getattr(request, 'is_frontend', False))
        if not is_frontend_request:
            # Don't touch non frontend requests exception handling
            return super(IrHttp, cls)._handle_exception(exception)
        try:
            response = super(IrHttp, cls)._handle_exception(exception)

            if isinstance(response, Exception):
                exception = response
            else:
                # if parent excplicitely returns a plain response, then we don't touch it
                return response
        except Exception as e:
            if 'werkzeug' in config['dev_mode']:
                raise e
            exception = e


        code, values = cls._get_exception_code_values(exception)

        if code is None:

            return exception

        if not request.uid:
            cls._auth_method_public()

        request.env.cr.rollback()

        with registry(request.env.cr.dbname).cursor() as cr:
            env = api.Environment(cr, request.uid, request.env.context)
            if code == 500:
                _logger.error("500 Internal Server Error:\n\n%s", values['traceback'])
                values = cls._get_values_500_error(env, values, exception)
            elif code == 403:
                _logger.warning("403 Forbidden:\n\n%s", values['traceback'])
            elif code == 400:
                _logger.warning("400 Bad Request:\n\n%s", values['traceback'])
            try:
                code, html = cls._get_error_html(env, code, values)
            except Exception:
                
                code, html = 418, env['ir.ui.view']._render_template('http_routing.http_error', values)
        hide_traceback = odoo.tools.config.get('hide_traceback',False)
        if hide_traceback and code == 500:
        #     code = 403
            return request.render('equip3_general_security.page_error_redirect', None)

        return werkzeug.wrappers.Response(html, status=code, content_type='text/html;charset=utf-8')

def _patch_http():
    IrHttp._handle_exception = classmethod(IrHttnew._handle_exception_custom)
    
    
    
    

    
    
    


