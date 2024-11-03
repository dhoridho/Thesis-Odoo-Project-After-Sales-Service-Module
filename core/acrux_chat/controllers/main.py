# -*- coding: utf-8 -*-
import logging
import unicodedata
import json
import werkzeug
import base64
from odoo import http, _
from odoo.http import request, Response
from odoo.addons.web.controllers.main import serialize_exception
from odoo.exceptions import UserError
_logger = logging.getLogger(__name__)


class WebhookController(http.Controller):

    @http.route('/acrux_chat/new_message', type='json', auth='user', method=['OPTIONS', 'POST'])
    def new_message(self, **params):
        AcruxChatConnector = request.env['acrux.chat.connector'].sudo()
        AcruxChatConversation = request.env['acrux.chat.conversation'].sudo()
        params['connector_id'] = AcruxChatConnector.search([], limit=1).id
        params['ttype'] = 'text'
        AcruxChatConversation.new_message(params)
        return 'prueba'

    def chek_error(self, status, content, headers):
        if status == 304:
            return Response(status=304, headers=headers)
        elif status == 301:
            return werkzeug.utils.redirect(content, code=301)
        if not content:
            return Response(status=404)

    @http.route('/web/chatresource/<int:res_id>', type='http', auth='user')
    def acrux_web_content_login(self, res_id):
        status, headers, content = request.env['ir.http'].sudo().binary_content(model='ir.attachment',
                                                                                id=res_id, field='datas')
        error = self.chek_error(status, content, headers)
        if error:
            return error
        content_b64 = base64.b64decode(content)
        headers.append(('Content-Length', len(content_b64)))
        headers.append(('Accept-Ranges', 'bytes'))
        response = request.make_response(content_b64, headers)
        response.status_code = status
        return response

    @http.route(['/web/chatresource/<int:id>/<string:access_token>',
                 '/web/static/chatresource/<string:model>/<string:id>/<string:field>'],
                type='http', auth='public', sitemap=False)
    def acrux_web_content(self, id=None, model=None, field=None, access_token=None):
        '''
        /web/chatresource/...        -> for attachment
        /web/static/chatresource/... -> for product image
        :param field: field (binary image, PNG or JPG) name in model. Only support 'image'.
        '''

        if id and access_token and not model and not field:
            status, headers, content = request.env['ir.http'].sudo().binary_content(model='ir.attachment',
                                                                                    id=int(id), field='datas',
                                                                                    access_token=access_token)
            error = self.chek_error(status, content, headers)
            if error:
                return error
            content_b64 = base64.b64decode(content)
        else:
            if not id or not field.startswith('image') or model not in ['product.template', 'product.product']:
                return Response(status=404)

            id, sep, unique = id.partition('_')
            status, headers, content = request.env['ir.http'].sudo().binary_content(model=model, id=int(id),
                                                                                    field=field, unique=unique)
            error = self.chek_error(status, content, headers)
            if error:
                return error
            content_b64 = base64.b64decode(content)

        headers.append(('Content-Length', len(content_b64)))
        response = request.make_response(content_b64, headers)
        response.status_code = status
        return response


class Binary(http.Controller):

    @http.route('/web/binary/upload_attachment_chat', type='http', auth="user")
    @serialize_exception
    def upload_attachment_chat(self, callback, model, id, ufile):
        ''' Source: web.controllers.main.Binary.upload_attachment '''
        files = request.httprequest.files.getlist('ufile')
        Model = request.env['ir.attachment']
        out = """<script language="javascript" type="text/javascript">
                    var win = window.top.window;
                    win.jQuery(win).trigger(%s, %s);
                </script>"""
        args = []
        for ufile in files:
            datas = ufile.read()
            filename = ufile.filename
            if request.httprequest.user_agent.browser == 'safari':
                # Safari sends NFD UTF-8 (where é is composed by 'e' and [accent])
                # we need to send it the same stuff, otherwise it'll fail
                filename = unicodedata.normalize('NFD', ufile.filename)

            try:
                if len(datas) > 2000000:
                    raise UserError(_('Too big, max. %s (%s)') % ('2 Mb', filename))
                attachment = Model.create({
                    'delete_old': True,
                    'name': filename,
                    'datas': base64.encodebytes(datas),
                    'store_fname': filename,
                    'res_model': 'acrux.chat.message',
                    'res_id': 0
                })
            except UserError as e:
                args.append({'error': e.args[0]})
                _logger.exception("Fail to upload attachment %s" % ufile.filename)
            except Exception:
                args.append({'error': _("Something horrible happened")})
                _logger.exception("Fail to upload attachment %s" % ufile.filename)
            else:
                args.append({
                    'filename': filename,
                    'mimetype': ufile.content_type,
                    'id': attachment.id
                })
        return out % (json.dumps(callback), json.dumps(args))
