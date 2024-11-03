import base64
from datetime import datetime, timedelta
import io
import imgkit
import pdfkit
from PIL import Image, ImageChops
from odoo import http, _
from odoo.http import request, Response, content_disposition
from odoo.tools import html_escape
import werkzeug
import json
from odoo.addons.web.controllers.main import _serialize_exception


def img_trim(im):
    bg = Image.new(im.mode, im.size, im.getpixel((0, 0)))
    diff = ImageChops.difference(im, bg)
    diff = ImageChops.add(diff, diff)
    bbox = diff.getbbox()
    if bbox:
        return im.crop(bbox)


class TokopediaDownloadPDF(http.Controller):

    @http.route('/web/binary/tokopedia/download_pdf', type='http', auth='public', website=True)
    def download_pdf(self, **kw):
        html_string = ''
        so_obj = request.env['sale.order'].sudo()
        time_now = str((datetime.now() + timedelta(hours=7)) .strftime("%Y%m%d_%H:%M:%S"))
        order_ids = kw.get('order_ids').split('_')
        mp_awb_number = ''
        if 'mp_awb_number' in kw:
            mp_awb_number = kw.get('mp_awb_number')
        output_filename = 'tokopedia_label_%s' % (mp_awb_number)
        imgkit_opts = {
            'zoom': 2,
            'width': 1920 * 2,
            'height': 1080 * 2,
            'quality': 100
        }
        if len(order_ids) == 1:
            im_buff = io.BytesIO()
            order_id = order_ids[0]
            order = so_obj.browse(int(order_id))
            im = img_trim(Image.open(io.BytesIO(imgkit.from_string(order.mp_awb_html, False, imgkit_opts))))
            im.save(im_buff, format("JPEG"))
            label_img = base64.b64encode(im_buff.getvalue()).decode()
            html_string += '<div><img src="data:image/jpg;base64,%s"/></div>' \
                % (label_img)
        else:
            order_ids = [int(order) for order in order_ids]
            order_rec_ids = so_obj.search([('id', 'in', order_ids)])
            for order_id in order_rec_ids:
                im_buff = io.BytesIO()
                im = img_trim(Image.open(io.BytesIO(imgkit.from_string(order_id.mp_awb_html, False, imgkit_opts))))
                im.save(im_buff, format("JPEG"))
                label_img = base64.b64encode(im_buff.getvalue()).decode()
                html_string += '<div><img src="data:image/jpg;base64,%s"/></div>' \
                    % (label_img)
        pdf = pdfkit.from_string(html_string, False)
        if pdf:
            headers = [
                ('Content-Type', 'application/pdf'),
                ('Content-Length', len(pdf)),
                ('Content-Disposition', content_disposition('%s.pdf' % output_filename))
            ]
            return http.request.make_response(pdf, headers=headers)
        else:
            # res = Response('Order Not Available', status=200)
            return Response('Order Not Available', status=200)

    @http.route('/web/binary/tokopedia/open_pdf', type='http', auth="public", website=True)
    def open_pdf(self, **kw):
        html_string = ''
        so_obj = request.env['sale.order'].sudo()
        order_ids = kw.get('order_ids').split('_')
        imgkit_opts = {
            'zoom': 2,
            'width': 1920 * 2,
            'height': 1080 * 2,
            'quality': 100
        }
        if len(order_ids) == 1:
            im_buff = io.BytesIO()
            order_id = order_ids[0]
            order = so_obj.browse(int(order_id))
            im = img_trim(Image.open(io.BytesIO(imgkit.from_string(order.mp_awb_html, False, imgkit_opts))))
            im.save(im_buff, format("JPEG"))
            label_img = base64.b64encode(im_buff.getvalue()).decode()
            html_string += '<div><img src="data:image/jpg;base64,%s"/></div>' \
                % (label_img)
        else:
            order_ids = [int(order) for order in order_ids]
            order_rec_ids = so_obj.search([('id', 'in', order_ids)])
            for order_id in order_rec_ids:
                im_buff = io.BytesIO()
                im = img_trim(Image.open(io.BytesIO(imgkit.from_string(order_id.mp_awb_html, False, imgkit_opts))))
                im.save(im_buff, format("JPEG"))
                label_img = base64.b64encode(im_buff.getvalue()).decode()
                html_string += '<div><img src="data:image/jpg;base64,%s"/></div>' \
                    % (label_img)

        pdf = pdfkit.from_string(html_string, False)
        if pdf:
            headers = [
                ('Content-Type', 'application/pdf'),
                ('Content-Length', len(pdf))
            ]
            return http.request.make_response(pdf, headers=headers)
        else:
            res = Response('Order Not Available', status=200)
            return res

    @http.route('/product/y-img/<int:id>.jpg', type='http', auth="user", website=True)
    def get_product_image(self, id, image_type="image", **kw):
        image_type = image_type and image_type or 'image'
        record = request.env['product.template.image'].browse(id)
        try:
            attachment_ids = request.env['ir.attachment'].sudo().search([
                ('res_model', '=', record._name), 
                ('res_field', '=', image_type), 
                ('res_id', '=', record.id)
            ])
            if attachment_ids:
                for attachment_obj in attachment_ids:
                    filecontent = base64.b64decode(attachment_obj.datas)
                    disposition = 'inline; filename=%s' % werkzeug.urls.url_quote(attachment_obj.store_fname)
                    return request.make_response(
                        filecontent,
                        [('Content-Type', attachment_obj.mimetype),
                         ('Content-Length', len(filecontent)),
                         ('Content-Disposition', disposition)])
            else:
                error = {
                'code': 200,
                'message': "Unable to find the attachments",
                }
            return request.make_response(html_escape(json.dumps(error)))
            
        except Exception as e:
            se = _serialize_exception(e)
            error = {
                'code': 400,
                'message': "An error occurred",
                'data': se
            }
            return request.make_response(html_escape(json.dumps(error)))