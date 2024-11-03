# -*- coding: utf-8 -*
import json
import os
import odoo
from odoo import http, _
from odoo.http import request, content_disposition, dispatch_rpc, serialize_exception as _serialize_exception, Response



class EQ3PosReportPH(http.Controller):

    @http.route(['/download_journal_entry_txt'], type='http', auth="public", website=True)
    def download_journal_entry_txt(self, **post):
        move_obj = request.env['account.move'].sudo()
        move_id = int(post['id'])
        acc_move = move_obj.browse(move_id)
        filename = 'Journal Entry'
        if acc_move.name and acc_move.name != '/':
            filename+=' '+ acc_move.name


        content = acc_move.set_content_for_download_txt()

        return request.make_response(content,
                            [('Content-Type', 'application/octet-stream'),
                            ('Content-Disposition', content_disposition(filename+'.txt'))])