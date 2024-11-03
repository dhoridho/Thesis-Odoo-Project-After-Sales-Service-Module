import base64
from datetime import datetime, timedelta

from PyPDF2 import PdfFileReader, PdfFileWriter
import io
import logging
from odoo import http, _
from odoo.http import request
_logger = logging.getLogger(__name__)


class TiktokDownloadPDF(http.Controller):

    @http.route('/web/binary/tiktok/download_pdf/', type='http', auth="public", website=True)
    def download_pdf(self, **kw):
        output_stream = io.BytesIO()
        output = PdfFileWriter()
        time_now = str((datetime.now() + timedelta(hours=7)) .strftime("%Y%m%d_%H:%M:%S"))
        output_filename = 'tiktok_label_%s' % (time_now)
        order_ids = kw.get('order_ids').split(',')
        for index, so in enumerate(order_ids):
            so_awb_datas = request.env['sale.order'].sudo().search([('id', '=', int(so))]).mp_awb_datas
            awb_file = PdfFileReader(io.BytesIO(base64.b64decode(so_awb_datas)))
            for page in awb_file.pages:
                output.addPage(page)
                output_page = output.getPage(index)
                output_page.mediaBox.lowerRight = (407, 0)

        headers = [
            ('Content-Type', 'application/pdf'),
            ('Content-Disposition', 'attachment; filename=' + '%s.pdf;' % output_filename)
        ]
        output.write(output_stream)
        data = output_stream.getvalue()
        return http.request.make_response(data, headers)

    @http.route('/web/binary/tiktok/open_pdf/', type='http', auth="public", website=True)
    def open_pdf(self, **kw):
        output_stream = io.BytesIO()
        output = PdfFileWriter()
        order_ids = kw.get('order_ids').split(',')
        for index, so in enumerate(order_ids):
            so_awb_datas = request.env['sale.order'].sudo().search([('id', '=', int(so))]).mp_awb_datas
            if so_awb_datas:
                awb_file = PdfFileReader(io.BytesIO(base64.b64decode(so_awb_datas)))
                for page in awb_file.pages:
                    output.addPage(page)
                    output_page = output.getPage(index)
                    output_page.mediaBox.lowerRight = (300, 0)

        if output:
            output.write(output_stream)
            data = output_stream.getvalue()
            headers = [
                ('Content-Type', 'application/pdf'),
                ('Content-Length', len(data))
            ]
            return http.request.make_response(data, headers)
