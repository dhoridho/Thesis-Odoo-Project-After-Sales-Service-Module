# -*- coding: utf-8 -*-

import base64
import json
import odoo

from odoo.tools import image_process, date_utils
from odoo.modules import  get_resource_path
from odoo import http, tools
from odoo.http import  request, serialize_exception as _serialize_exception, Response, JsonRequest


class OnlineOutletController(http.Controller):

    @staticmethod
    def oloutlet_placeholder(image='placeholder.png'):
        image_path = image.lstrip('/').split('/') if '/' in image else ['web', 'static', 'src', 'img', image]
        with tools.file_open(get_resource_path(*image_path), 'rb') as fd:
            return fd.read()

    @http.route([ 
        '/outlets/assets/<string:ttype>/<int:id>/<string:field>/<string:filename>'
    ], type='http', auth="public")
    def content_image(self, xmlid=None, model='ir.attachment', id=None, field='datas',
                      filename_field='name', unique=None, filename=None, mimetype=None,
                      download=None, width=0, height=0, crop=False, access_token=None, ttype=None,
                      **kwargs):

        if ttype not in ['product']:
            return request.not_found()

        if ttype == 'product':
            model = 'product.template'

        # other kwargs are ignored on purpose
        res = self._content_image(xmlid=xmlid, model=model, id=id, field=field,
            filename_field=filename_field, unique=unique, filename=filename, mimetype=mimetype,
            download=download, width=width, height=height, crop=crop,
            quality=int(kwargs.get('quality', 0)), access_token=access_token) 
        return res

    def _content_image(self, xmlid=None, model='ir.attachment', id=None, field='datas',
                       filename_field='name', unique=None, filename=None, mimetype=None,
                       download=None, width=0, height=0, crop=False, quality=0, access_token=None,
                       placeholder=None, **kwargs):
        status, headers, image_base64 = request.env['ir.http'].sudo().binary_content(
            xmlid=xmlid, model=model, id=id, field=field, unique=unique, filename=filename,
            filename_field=filename_field, download=download, mimetype=mimetype,
            default_mimetype='image/png', access_token=access_token) 

        return OnlineOutletController._content_image_get_response(
            status, headers, image_base64, model=model, id=id, field=field, download=download,
            width=width, height=height, crop=crop, quality=quality,
            placeholder=placeholder)

    @staticmethod
    def _content_image_get_response(
            status, headers, image_base64, model='ir.attachment', id=None,
            field='datas', download=None, width=0, height=0, crop=False,
            quality=0, placeholder='placeholder.png'):
        if status in [301, 304] or (status != 200 and download):
            return request.env['ir.http']._response_by_status(status, headers, image_base64)
        if not image_base64:
            if placeholder is None and model in request.env:
                # Try to browse the record in case a specific placeholder
                # is supposed to be used. (eg: Unassigned users on a task)
                record = request.env[model].sudo().browse(int(id)) if id else request.env[model].sudo()
                placeholder_filename = record._get_placeholder_filename(field=field)
                placeholder_content = OnlineOutletController.oloutlet_placeholder(image=placeholder_filename)
            else:
                placeholder_content = OnlineOutletController.oloutlet_placeholder()
            # Since we set a placeholder for any missing image, the status must be 200. In case one
            # wants to configure a specific 404 page (e.g. though nginx), a 404 status will cause
            # troubles.
            status = 200
            image_base64 = base64.b64encode(placeholder_content)

            if not (width or height):
                width, height = odoo.tools.image_guess_size_from_field_name(field)

        try:
            image_base64 = image_process(image_base64, size=(int(width), int(height)), crop=crop, quality=int(quality))
        except Exception:
            return request.not_found()

        content = base64.b64decode(image_base64)
        headers = http.set_safe_image_headers(headers, content)
        response = request.make_response(content, headers)
        response.status_code = status
        return response