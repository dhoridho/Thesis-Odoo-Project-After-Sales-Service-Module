import babel.messages.pofile
import base64
import csv
import datetime
import functools
import glob
import hashlib
import imghdr
import itertools
import jinja2
import json
import logging
import werkzeug.utils
import werkzeug.wrappers
from odoo.addons.web.controllers.main import Home, ensure_db
from odoo import http
from odoo.http import content_disposition, dispatch_rpc, request, \
                      serialize_exception as _serialize_exception

_logger = logging.getLogger(__name__)

def binary_content(xmlid=None, model='ir.attachment', id=None, field='datas', unique=False, filename=None, filename_field='datas_fname', download=False, mimetype=None, default_mimetype='application/octet-stream', env=None):
    return request.registry['ir.http'].binary_content(
        xmlid=xmlid, model=model, id=id, field=field, unique=unique, filename=filename, filename_field=filename_field,
        download=download, mimetype=mimetype, default_mimetype=default_mimetype, env=env)

class Binary(http.Controller):
    @http.route(['/web/download'], type='http', auth="public")
    def content_common(self, debug=False, xmlid=None, model='ir.attachment', id=None, field='datas', filename=None, filename_field='datas_fname', unique=None, mimetype=None, download=None, data=None, token=None):
        status, headers, content = binary_content(xmlid=xmlid, model=model, id=id, field=field, unique=unique, filename=filename, filename_field=filename_field, download=download, mimetype=mimetype)
        if status == 304:
            response = werkzeug.wrappers.Response(status=status, headers=headers)
        elif status == 301:
            return werkzeug.utils.redirect(content, code=301)
        elif status != 200:
            response = request.not_found()
        else:
            content_base64 = base64.b64decode(content)
            headers.append(('Content-Length', len(content_base64)))
            response = request.make_response(content_base64, headers)
        if token:
            response.set_cookie('fileToken', token)
        return response


class Peppol(Home):
    @http.route()
    def web_login(self, redirect=None, **kw):
        ensure_db()
        action      = request.env.ref('base.action_res_company_form')
        company_ids = request.env['res.company'].search([], order="id DESC")
        for company in company_ids:
            if not company.base_uri or not company.api_version or not company.api_key or not company.api_secret:
                redirect = '/web?debug#id=%s&view_type=form&model=res.company&action=%s' % (company.id, action.id)
            # return werkzeug.utils.redirect(redirect, 303)
        response = super(Peppol, self).web_login(redirect, **kw)
        return response