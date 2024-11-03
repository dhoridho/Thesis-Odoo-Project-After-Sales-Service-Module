# -*- coding: utf-8 -*-

import base64
from odoo import http
from odoo.http import request

class Equip3ReportingAssetWeb(http.Controller):

    @http.route(['/reporting-asset/content/<string:model>/<int:id>/<string:field>/<string:filename>'],type='http', auth="user")
    def export_content(self, model='cn.mod.cashflow.report.wizard', id=None, field='datas', filename=None,  **kw):
        res = request.env[model].search([('id','=', id)])
        content = res.datas
        if not filename and res.filename:
            filename = res.filename
        if not content:
            return request.not_found()

        content_base64 = base64.b64decode(content)
        headers = [('Content-Type', 'application/octet-stream'),('Content-Disposition','inline; filename="%s"' % (filename))]
        headers.append(('Content-Length', len(content_base64)))
        response = request.make_response(content_base64, headers)
        return  response
